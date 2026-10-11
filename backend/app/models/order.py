from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin


class OrderStatus(StrEnum):
    pending_payment = "pending_payment"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class Order(TimestampMixin, Base):
    """An order. Amounts are paise; prices are copied from products at checkout time."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_payment', 'paid', 'shipped', 'delivered', 'cancelled')", name="valid_status"
        ),
        CheckConstraint("total = subtotal + shipping_fee", name="total_adds_up"),
        Index("ix_orders_user_created", "user_id", "created_at"),
        # Finds unpaid orders to expire without scanning paid ones.
        Index("ix_orders_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.pending_payment)
    subtotal: Mapped[int] = mapped_column(Integer)
    shipping_fee: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    shipping_address: Mapped[dict[str, Any]] = mapped_column(JSONB)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="raise", order_by="OrderItem.id"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    sku: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    unit_price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(SmallInteger)
    line_total: Mapped[int] = mapped_column(Integer)
    weight_grams: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items", lazy="raise")


class Payment(TimestampMixin, Base):
    """A Razorpay payment attempt. The payment id is unique, so a repeated report updates one row."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String(64), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    method: Mapped[str | None] = mapped_column(String(32))
    error_description: Mapped[str | None] = mapped_column(String(255))


class WebhookEvent(Base):
    """Delivered webhook events. The unique key turns at-least-once delivery into once-only processing."""

    __tablename__ = "webhook_events"
    __table_args__ = (Index("uq_webhook_events_provider_event", "provider", "event_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    event_id: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
