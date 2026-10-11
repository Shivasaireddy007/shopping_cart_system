from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    parent_id: int | None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    slug: str
    description: str | None
    brand: str
    price: int = Field(description="Price in paise")
    mrp: int | None = Field(description="Maximum retail price in paise")
    stock: int
    attributes: dict[str, Any]
    is_active: bool
    category: CategoryOut

    @computed_field  # type: ignore[prop-decorator]
    @property
    def in_stock(self) -> bool:
        return self.stock > 0


class ProductSort(StrEnum):
    newest = "newest"
    price_asc = "price_asc"
    price_desc = "price_desc"
    name = "name"


class ProductFilters(BaseModel):
    category: str | None = Field(None, max_length=255, description="Category slug")
    brand: str | None = Field(None, max_length=100)
    min_price: int | None = Field(None, ge=0, description="In paise")
    max_price: int | None = Field(None, ge=0, description="In paise")
    in_stock: bool = False
    sort: ProductSort = ProductSort.newest
    page: int = Field(1, ge=1)
    per_page: int = Field(24, ge=1, le=50)

    @model_validator(mode="after")
    def check_price_range(self) -> "ProductFilters":
        if self.min_price is not None and self.max_price is not None and self.max_price < self.min_price:
            raise ValueError("max_price must be greater than or equal to min_price")
        return self


class ProductAttributes(BaseModel):
    color: str | None = Field(None, max_length=50)
    size: str | None = Field(None, max_length=20)


class ProductCreate(BaseModel):
    category_id: int
    sku: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(None, max_length=5000)
    brand: str = Field(min_length=1, max_length=100)
    price: int = Field(ge=100, description="In paise")
    mrp: int | None = Field(None, description="In paise")
    stock: int = Field(ge=0)
    weight_grams: int = Field(500, ge=1, le=50000)
    attributes: ProductAttributes = ProductAttributes()
    is_active: bool = True

    @model_validator(mode="after")
    def check_mrp(self) -> "ProductCreate":
        if self.mrp is not None and self.mrp < self.price:
            raise ValueError("mrp must be greater than or equal to price")
        return self


class ProductUpdate(BaseModel):
    category_id: int | None = None
    sku: str | None = Field(None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(None, max_length=5000)
    brand: str | None = Field(None, min_length=1, max_length=100)
    price: int | None = Field(None, ge=100)
    mrp: int | None = None
    stock: int | None = Field(None, ge=0)
    weight_grams: int | None = Field(None, ge=1, le=50000)
    attributes: ProductAttributes | None = None
    is_active: bool | None = None


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=255, pattern=r"^[a-z0-9-]+$")
    parent_id: int | None = None
