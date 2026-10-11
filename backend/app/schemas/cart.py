from pydantic import BaseModel, Field


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    sku: str
    name: str
    unit_price: int
    quantity: int
    line_total: int


class CartOut(BaseModel):
    items: list[CartItemOut]
    subtotal: int
    shipping_fee: int
    total: int
    currency: str = "INR"
