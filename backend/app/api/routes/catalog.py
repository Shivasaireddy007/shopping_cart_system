from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import Category
from app.schemas.catalog import CategoryOut, ProductFilters, ProductOut
from app.schemas.common import Page
from app.services import catalog

router = APIRouter(tags=["Catalog"])


@router.get("/categories")
async def list_categories(session: SessionDep) -> list[CategoryOut]:
    """List categories."""
    rows = await session.scalars(select(Category).order_by(Category.name))
    return [CategoryOut.model_validate(row) for row in rows]


@router.get("/products")
async def list_products(session: SessionDep, filters: Annotated[ProductFilters, Query()]) -> Page[ProductOut]:
    """List active products, filtered by category, brand, price (paise) and stock."""
    products, total = await catalog.list_products(session, filters)
    return Page(
        items=[ProductOut.model_validate(p) for p in products],
        total=total,
        page=filters.page,
        per_page=filters.per_page,
    )


@router.get("/products/{slug}")
async def get_product(slug: str, session: SessionDep) -> ProductOut:
    """Get an active product by its slug."""
    product = await catalog.get_active_product(session, slug)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found.")
    return ProductOut.model_validate(product)
