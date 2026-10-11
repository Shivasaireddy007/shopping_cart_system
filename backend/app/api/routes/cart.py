from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.cart import CartItemIn, CartItemUpdate, CartOut
from app.services import cart as carts

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("")
async def show_cart(user: CurrentUser, session: SessionDep) -> CartOut:
    """Get the cart with current prices, shipping fee and total."""
    return carts.to_out(await carts.get_cart(session, user.id))


@router.post("/items")
async def add_item(data: CartItemIn, user: CurrentUser, session: SessionDep) -> CartOut:
    """Add a product, or increase its quantity if it is already in the cart. 409 if stock is short."""
    return carts.to_out(await carts.add_item(session, user.id, data.product_id, data.quantity))


@router.patch("/items/{item_id}")
async def update_item(item_id: int, data: CartItemUpdate, user: CurrentUser, session: SessionDep) -> CartOut:
    """Set the quantity of a cart item."""
    return carts.to_out(await carts.update_item(session, user.id, item_id, data.quantity))


@router.delete("/items/{item_id}")
async def remove_item(item_id: int, user: CurrentUser, session: SessionDep) -> CartOut:
    """Remove an item from the cart."""
    return carts.to_out(await carts.remove_item(session, user.id, item_id))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(user: CurrentUser, session: SessionDep) -> None:
    """Empty the cart."""
    await carts.clear(session, user.id)
