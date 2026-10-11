import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.models import WebhookEvent
from app.services import payments, shipments
from app.services.razorpay import RazorpayClient, get_razorpay

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
log = logging.getLogger(__name__)


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    session: SessionDep,
    razorpay: Annotated[RazorpayClient, Depends(get_razorpay)],
    x_razorpay_signature: Annotated[str, Header()] = "",
    x_razorpay_event_id: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Receive Razorpay payment events, verified with the HMAC signature of the raw body.

    The event is recorded in the same transaction as its effect, so either both commit or
    neither does and Razorpay's retry is processed. Repeated deliveries return `duplicate`.
    """
    body = await request.body()
    if not razorpay.is_valid_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid signature.")

    event: dict[str, Any] = json.loads(body)
    event_id = x_razorpay_event_id or event.get("id") or ""
    inserted = await session.scalar(
        insert(WebhookEvent)
        .values(
            provider="razorpay",
            event_id=event_id,
            type=event.get("event", "unknown"),
            received_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=["provider", "event_id"])
        .returning(WebhookEvent.id)
    )
    if inserted is None:
        await session.rollback()
        return {"status": "duplicate"}

    payment = event.get("payload", {}).get("payment", {}).get("entity", {})
    if payment.get("order_id"):
        match event.get("event"):
            case "payment.captured" | "order.paid":
                await payments.record_captured(
                    session, payment["order_id"], payment["id"], int(payment["amount"]), payment.get("method")
                )
            case "payment.failed":
                await payments.record_failed(
                    session,
                    payment["order_id"],
                    payment["id"],
                    int(payment["amount"]),
                    payment.get("error_description"),
                )

    await session.commit()
    return {"status": "ok"}


@router.post("/shiprocket")
async def shiprocket_webhook(
    request: Request,
    session: SessionDep,
    x_api_key: Annotated[str, Header()] = "",
) -> dict[str, str]:
    """Receive Shiprocket shipment status updates, authenticated with the `x-api-key` header.

    Shiprocket sends no event id, so the AWB and status identify a delivery. Orders only
    move forward (paid, shipped, delivered), so late or repeated updates change nothing.
    """
    token = get_settings().shiprocket_webhook_token
    if not token or not hmac.compare_digest(token, x_api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token.")

    body: dict[str, Any] = await request.json()
    awb, current = str(body.get("awb") or ""), str(body.get("current_status") or "")
    if not awb or not current:
        return {"status": "ignored"}

    event_id = hashlib.sha256(f"{awb}|{current.upper()}".encode()).hexdigest()
    inserted = await session.scalar(
        insert(WebhookEvent)
        .values(provider="shiprocket", event_id=event_id, type=current.lower(), received_at=datetime.now(UTC))
        .on_conflict_do_nothing(index_elements=["provider", "event_id"])
        .returning(WebhookEvent.id)
    )
    if inserted is None:
        await session.rollback()
        return {"status": "duplicate"}

    await shipments.apply_status(session, awb, current)
    await session.commit()
    return {"status": "ok"}
