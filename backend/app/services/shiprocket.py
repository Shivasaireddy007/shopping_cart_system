"""Shiprocket external API: https://apidocs.shiprocket.in/"""

from typing import Any

import httpx
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.redis import get_redis
from app.models import Order, User

TOKEN_KEY = "shiprocket:token"
TOKEN_SECONDS = 9 * 24 * 3600  # tokens last 10 days


class ShiprocketClient:
    def __init__(
        self, settings: Settings, redis: Redis, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._settings = settings
        self._redis = redis
        self._http = httpx.AsyncClient(base_url=settings.shiprocket_base_url, timeout=15, transport=transport)

    @property
    def configured(self) -> bool:
        return bool(self._settings.shiprocket_email and self._settings.shiprocket_password)

    async def create_order(self, order: Order, customer: User) -> tuple[int, int]:
        """Creates a Shiprocket order and returns (shiprocket_order_id, shipment_id)."""
        address = order.shipping_address
        first, _, last = address["name"].partition(" ")
        weight_kg = max(0.1, sum(i.weight_grams * i.quantity for i in order.items) / 1000)
        body = await self._send(
            "POST",
            "/orders/create/adhoc",
            {
                "order_id": order.number,
                "order_date": order.created_at.strftime("%Y-%m-%d %H:%M"),
                "pickup_location": self._settings.shiprocket_pickup_location,
                "billing_customer_name": first,
                "billing_last_name": last,
                "billing_address": address["line1"],
                "billing_address_2": address.get("line2") or "",
                "billing_city": address["city"],
                "billing_pincode": address["pincode"],
                "billing_state": address["state"],
                "billing_country": "India",
                "billing_email": customer.email,
                "billing_phone": address["phone"],
                "shipping_is_billing": True,
                "order_items": [
                    {"name": i.name, "sku": i.sku, "units": i.quantity, "selling_price": i.unit_price / 100}
                    for i in order.items
                ],
                "payment_method": "Prepaid",
                "shipping_charges": order.shipping_fee / 100,
                "sub_total": order.subtotal / 100,
                "length": 30,
                "breadth": 20,
                "height": 10,
                "weight": round(weight_kg, 2),
            },
        )
        return int(body["order_id"]), int(body["shipment_id"])

    async def assign_awb(self, shipment_id: int) -> tuple[str, str]:
        """Assigns a courier; returns (awb_code, courier_name)."""
        body = await self._send("POST", "/courier/assign/awb", {"shipment_id": shipment_id})
        data = body["response"]["data"]
        return str(data["awb_code"]), str(data["courier_name"])

    async def track(self, awb: str) -> dict[str, Any]:
        body = await self._send("GET", f"/courier/track/awb/{awb}")
        tracking: dict[str, Any] = body.get("tracking_data") or {}
        return tracking

    async def _send(self, method: str, path: str, json: Any = None) -> dict[str, Any]:
        response = await self._http.request(method, path, json=json, headers=await self._auth())
        if response.status_code == 401:  # token revoked early: log in again once
            await self._redis.delete(TOKEN_KEY)
            response = await self._http.request(method, path, json=json, headers=await self._auth())
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def _auth(self) -> dict[str, str]:
        token = await self._redis.get(TOKEN_KEY)
        if token is None:
            response = await self._http.post(
                "/auth/login",
                json={
                    "email": self._settings.shiprocket_email,
                    "password": self._settings.shiprocket_password,
                },
            )
            response.raise_for_status()
            token = response.json()["token"]
            await self._redis.set(TOKEN_KEY, token, ex=TOKEN_SECONDS)
        return {"Authorization": f"Bearer {token!s}"}


_client: ShiprocketClient | None = None


def get_shiprocket() -> ShiprocketClient:
    global _client
    _client = _client or ShiprocketClient(get_settings(), get_redis())
    return _client
