from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)


class Product(TimestampMixin, Base):
    """A sellable product. Prices are integers in paise (₹1 = 100 paise)."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("mrp IS NULL OR mrp >= price", name="mrp_at_least_price"),
        CheckConstraint("stock >= 0", name="stock_not_negative"),
        # Composite indexes matching the listing sorts, so pages are read in index order.
        Index("ix_products_active_price", "is_active", "price", "id"),
        Index("ix_products_active_name", "is_active", "name", "id"),
        Index("ix_products_active_category_price", "is_active", "category_id", "price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str] = mapped_column(String(100), index=True)
    price: Mapped[int] = mapped_column(Integer)
    mrp: Mapped[int | None] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    weight_grams: Mapped[int] = mapped_column(Integer, default=500)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    category: Mapped[Category] = relationship(lazy="raise")

    def is_in_stock(self, quantity: int = 1) -> bool:
        return self.is_active and self.stock >= quantity
