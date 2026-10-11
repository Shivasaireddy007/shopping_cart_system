from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import InsufficientStock, NotFound
from app.models import Cart, CartItem, Product
from app.schemas.cart import CartItemOut, CartOut
from app.services.shipping import shipping_fee


async def get_cart(session: AsyncSession, user_id: int) -> Cart:
    """Returns the user's cart with items and products loaded, creating it on first use."""
    query = (
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .execution_options(populate_existing=True)
    )
    cart = await session.scalar(query)
    if cart is None:
        session.add(Cart(user_id=user_id))
        await session.commit()
        cart = await session.scalar(query)
    assert cart is not None
    return cart


async def add_item(session: AsyncSession, user_id: int, product_id: int, quantity: int) -> Cart:
    product = await session.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFound("Product not found.")

    cart = await get_cart(session, user_id)
    existing = next((item for item in cart.items if item.product_id == product_id), None)
    await _set_quantity(session, cart, product, (existing.quantity if existing else 0) + quantity)
    return await get_cart(session, user_id)


async def update_item(session: AsyncSession, user_id: int, item_id: int, quantity: int) -> Cart:
    cart = await get_cart(session, user_id)
    item = next((item for item in cart.items if item.id == item_id), None)
    if item is None:
        raise NotFound("Cart item not found.")

    await _set_quantity(session, cart, item.product, quantity)
    return await get_cart(session, user_id)


async def remove_item(session: AsyncSession, user_id: int, item_id: int) -> Cart:
    cart = await get_cart(session, user_id)
    item = next((item for item in cart.items if item.id == item_id), None)
    if item is None:
        raise NotFound("Cart item not found.")

    await session.delete(item)
    await session.commit()
    return await get_cart(session, user_id)


async def clear(session: AsyncSession, user_id: int) -> None:
    cart = await get_cart(session, user_id)
    for item in cart.items:
        await session.delete(item)
    await session.commit()


async def _set_quantity(session: AsyncSession, cart: Cart, product: Product, quantity: int) -> None:
    quantity = min(quantity, get_settings().max_quantity_per_item)

    if not product.is_in_stock(quantity):
        raise InsufficientStock(product.sku, product.stock, quantity)

    item = next((item for item in cart.items if item.product_id == product.id), None)
    if item is None:
        session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity))
    else:
        item.quantity = quantity
    await session.commit()


def to_out(cart: Cart) -> CartOut:
    """Prices come from the products at read time, so the cart always shows current prices."""
    items = [
        CartItemOut(
            id=item.id,
            product_id=item.product_id,
            sku=item.product.sku,
            name=item.product.name,
            unit_price=item.product.price,
            quantity=item.quantity,
            line_total=item.line_total,
        )
        for item in cart.items
    ]
    subtotal = sum(item.line_total for item in items)
    fee = shipping_fee(subtotal)
    return CartOut(items=items, subtotal=subtotal, shipping_fee=fee, total=subtotal + fee)
