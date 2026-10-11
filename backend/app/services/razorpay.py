"""Razorpay Orders API and signature checks.

https://razorpay.com/docs/api/orders/create/
https://razorpay.com/docs/payments/server-integration/python/payment-gateway/build-integration/#verify-payment-signature
"""

import hashlib
import hmac
import secrets

import httpx

from app.core.config import Settings, get_settings


class RazorpayError(Exception):
    pass


DEMO_KEY_ID = "rzp_demo"


class RazorpayClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.demo = settings.demo_payments
        self.key_id = DEMO_KEY_ID if self.demo else settings.razorpay_key_id
        self._key_secret = (
            hashlib.sha256(f"demo-payments:{settings.jwt_secret}".encode()).hexdigest()
            if self.demo
            else settings.razorpay_key_secret
        )
        self._webhook_secret = settings.razorpay_webhook_secret
        self._http = httpx.AsyncClient(
            base_url=settings.razorpay_base_url,
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            timeout=10,
            transport=transport,
        )

    async def create_order(self, amount: int, receipt: str) -> str:
        """Creates a Razorpay order for an amount in paise and returns its id (order_...)."""
        if self.demo:
            return f"order_demo{secrets.token_hex(7)}"
        try:
            response = await self._http.post(
                "/orders",
                json={
                    "amount": amount,
                    "currency": "INR",
                    "receipt": receipt,
                    "notes": {"order_number": receipt},
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RazorpayError(f"Could not create Razorpay order: {exc}") from exc
        return str(response.json()["id"])

    def demo_payment(self, razorpay_order_id: str) -> tuple[str, str]:
        """Demo mode: a payment id and the signature Razorpay Checkout would return for it."""
        payment_id = f"pay_demo{secrets.token_hex(7)}"
        message = f"{razorpay_order_id}|{payment_id}".encode()
        return payment_id, hmac.new(self._key_secret.encode(), message, hashlib.sha256).hexdigest()

    def is_valid_payment_signature(self, razorpay_order_id: str, payment_id: str, signature: str) -> bool:
        """Checks the signature Razorpay Checkout returns after a successful payment."""
        message = f"{razorpay_order_id}|{payment_id}".encode()
        expected = hmac.new(self._key_secret.encode(), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def is_valid_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Checks the X-Razorpay-Signature header against the raw request body."""
        if not self._webhook_secret:
            return False
        expected = hmac.new(self._webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


_client: RazorpayClient | None = None


def get_razorpay() -> RazorpayClient:
    """FastAPI dependency; tests override it with a client on a mock transport."""
    global _client
    _client = _client or RazorpayClient(get_settings())
    return _client
