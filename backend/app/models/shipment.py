from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin


class Shipment(TimestampMixin, Base):
    """A Shiprocket shipment. Each step is saved as it succeeds, so a retry resumes."""

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True)
    shiprocket_order_id: Mapped[int | None] = mapped_column(BigInteger)
    shiprocket_shipment_id: Mapped[int | None] = mapped_column(BigInteger)
    awb_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    courier_name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(64), default="pending")
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
