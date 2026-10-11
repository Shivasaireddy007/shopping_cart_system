from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentAdmin, SessionDep
from app.core.text import slugify, unique_slug
from app.models import Category, Product
from app.schemas.catalog import CategoryCreate, CategoryOut, ProductCreate, ProductOut, ProductUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/admin", tags=["Admin"])

PER_PAGE = 50


async def _load_product(session: SessionDep, product_id: int) -> Product:
    product = await session.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.category))
        .execution_options(populate_existing=True)
    )
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found.")
    return product


async def _commit_or_conflict(session: SessionDep) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "SKU or slug already in use, or the category doesn't exist."
        ) from exc


@router.get("/products")
async def list_products(
    _: CurrentAdmin,
    session: SessionDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
) -> Page[ProductOut]:
    """List all products, including archived ones, optionally searched by SKU or name."""
    query = select(Product)
    if search:
        pattern = "%" + search.replace("%", r"\%").replace("_", r"\_") + "%"
        query = query.where(or_(Product.sku == search, Product.name.ilike(pattern)))

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await session.scalars(
        query.options(selectinload(Product.category))
        .order_by(Product.id.desc())
        .limit(PER_PAGE)
        .offset((page - 1) * PER_PAGE)
    )
    return Page(items=[ProductOut.model_validate(p) for p in rows], total=total, page=page, per_page=PER_PAGE)


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, _: CurrentAdmin, session: SessionDep) -> ProductOut:
    """Create a product. The slug is generated from the name if not given."""
    values = data.model_dump(exclude={"slug", "attributes"})
    product = Product(
        **values,
        slug=data.slug or unique_slug(data.name),
        attributes=data.attributes.model_dump(exclude_none=True),
    )
    session.add(product)
    await _commit_or_conflict(session)
    return ProductOut.model_validate(await _load_product(session, product.id))


@router.patch("/products/{product_id}")
async def update_product(
    product_id: int, data: ProductUpdate, _: CurrentAdmin, session: SessionDep
) -> ProductOut:
    """Update a product, e.g. its price or stock."""
    product = await _load_product(session, product_id)
    changes = data.model_dump(exclude_unset=True, exclude={"attributes"})
    if data.attributes is not None:
        changes["attributes"] = data.attributes.model_dump(exclude_none=True)

    new_price = changes.get("price", product.price)
    new_mrp = changes.get("mrp", product.mrp)
    if new_mrp is not None and new_mrp < new_price:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "mrp must be greater than or equal to price"
        )

    for field, value in changes.items():
        setattr(product, field, value)
    await _commit_or_conflict(session)
    return ProductOut.model_validate(await _load_product(session, product_id))


@router.delete("/products/{product_id}")
async def archive_product(product_id: int, _: CurrentAdmin, session: SessionDep) -> ProductOut:
    """Archive a product instead of deleting it, so past orders keep their link to it."""
    product = await _load_product(session, product_id)
    product.is_active = False
    await session.commit()
    return ProductOut.model_validate(await _load_product(session, product_id))


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, _: CurrentAdmin, session: SessionDep) -> CategoryOut:
    """Create a category."""
    category = Category(name=data.name, slug=data.slug or slugify(data.name), parent_id=data.parent_id)
    session.add(category)
    await _commit_or_conflict(session)
    return CategoryOut.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, _: CurrentAdmin, session: SessionDep) -> None:
    """Delete an empty category. 409 if it still has products."""
    category = await session.get(Category, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found.")

    if await session.scalar(select(Product.id).where(Product.category_id == category_id).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Move or archive this category's products first.")

    await session.delete(category)
    await session.commit()
