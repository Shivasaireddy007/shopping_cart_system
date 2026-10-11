from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

INDIAN_STATES = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep",
    "Puducherry",
)  # fmt: skip


class ShippingAddress(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=r"^[6-9]\d{9}$", description="10-digit Indian mobile number")
    line1: str = Field(min_length=1, max_length=255)
    line2: str | None = Field(None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: Literal[INDIAN_STATES]  # type: ignore[valid-type]
    pincode: str = Field(pattern=r"^[1-9]\d{5}$", description="6-digit PIN code")


class CheckoutIn(BaseModel):
    shipping_address: ShippingAddress


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str
    name: str
    unit_price: int
    quantity: int
    line_total: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: str
    status: str
    subtotal: int
    shipping_fee: int
    total: int
    currency: str
    shipping_address: ShippingAddress
    items: list[OrderItemOut]
    paid_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime


class RazorpayCheckout(BaseModel):
    """Everything the frontend needs to open Razorpay Checkout."""

    key_id: str
    order_id: str
    amount: int
    currency: str


class CheckoutOut(BaseModel):
    order: OrderOut
    razorpay: RazorpayCheckout


class VerifyPaymentIn(BaseModel):
    razorpay_payment_id: str = Field(max_length=64)
    razorpay_signature: str = Field(max_length=128)
