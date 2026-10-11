"""Import every model so Alembic and create_all see the full schema."""

from app.models.cart import Cart, CartItem
from app.models.catalog import Category, Product
from app.models.events import OutboxEvent, ProcessedEvent
from app.models.order import Order, OrderItem, OrderStatus, Payment, WebhookEvent
from app.models.shipment import Shipment
from app.models.user import User

__all__ = [
    "Cart",
    "CartItem",
    "Category",
    "Order",
    "OrderItem",
    "OrderStatus",
    "OutboxEvent",
    "Payment",
    "ProcessedEvent",
    "Product",
    "Shipment",
    "User",
    "WebhookEvent",
]
