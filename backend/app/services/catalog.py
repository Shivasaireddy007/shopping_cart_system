from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Product
from app.schemas.catalog import ProductFilters, ProductSort

_SORTS = {
    ProductSort.newest: (Product.id.desc(),),
    # Tiebreak in the same direction so the composite indexes can serve the sort.
    ProductSort.price_asc: (Product.price.asc(), Product.id.asc()),
    ProductSort.price_desc: (Product.price.desc(), Product.id.desc()),
    ProductSort.name: (Product.name.asc(), Product.id.asc()),
}


def _filtered(filters: ProductFilters) -> Select[Product]:
    query = select(Product).where(Product.is_active.is_(True))

    if filters.category:
        query = query.join(Category).where(Category.slug == filters.category)
    if filters.brand:
        query = query.where(Product.brand == filters.brand)
    if filters.min_price is not None:
        query = query.where(Product.price >= filters.min_price)
    if filters.max_price is not None:
        query = query.where(Product.price <= filters.max_price)
    if filters.in_stock:
        query = query.where(Product.stock > 0)

    return query


async def list_products(session: AsyncSession, filters: ProductFilters) -> tuple[list[Product], int]:
    base = _filtered(filters)
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0

    rows = await session.scalars(
        base.options(selectinload(Product.category))
        .order_by(*_SORTS[filters.sort])
        .limit(filters.per_page)
        .offset((filters.page - 1) * filters.per_page)
    )
    return list(rows), total


async def get_active_product(session: AsyncSession, slug: str) -> Product | None:
    product: Product | None = await session.scalar(
        select(Product)
        .where(Product.slug == slug, Product.is_active.is_(True))
        .options(selectinload(Product.category))
    )
    return product
