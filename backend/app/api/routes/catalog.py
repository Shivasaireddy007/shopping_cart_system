import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.redis import get_redis
from app.models import Category, Product
from app.schemas.catalog import CategoryOut, ProductFilters, ProductOut
from app.schemas.common import Page
from app.schemas.search import SearchOut, SearchParams, SearchSort
from app.services import catalog
from app.services.cache import CatalogCache
from app.services.search import query as search_query
from app.services.search.client import SearchClient, get_search_client

router = APIRouter(tags=["Catalog"])
log = logging.getLogger(__name__)


def get_catalog_cache() -> CatalogCache:
    return CatalogCache(get_redis())


CacheDep = Annotated[CatalogCache, Depends(get_catalog_cache)]
SearchDep = Annotated[SearchClient, Depends(get_search_client)]


def _json(payload: str, cache: CatalogCache) -> Response:
    """A cached JSON body, with X-Cache saying whether Redis served it."""
    return Response(
        content=payload, media_type="application/json", headers={"X-Cache": cache.last_lookup.upper()}
    )


@router.get("/categories")
async def list_categories(session: SessionDep) -> list[CategoryOut]:
    """List categories."""
    rows = await session.scalars(select(Category).order_by(Category.name))
    return [CategoryOut.model_validate(row) for row in rows]


@router.get("/products", response_model=Page[ProductOut])
async def list_products(
    session: SessionDep, cache: CacheDep, filters: Annotated[ProductFilters, Query()]
) -> Response:
    """List active products, filtered by category, brand, price (paise) and stock. Cached in Redis."""

    async def build() -> str:
        products, total = await catalog.list_products(session, filters)
        page = Page[ProductOut](
            items=[ProductOut.model_validate(p) for p in products],
            total=total,
            page=filters.page,
            per_page=filters.per_page,
        )
        return page.model_dump_json()

    return _json(await cache.listing(filters.model_dump(mode="json"), build), cache)


@router.get("/products/{slug}", response_model=ProductOut)
async def get_product(slug: str, session: SessionDep, cache: CacheDep) -> Response:
    """Get an active product by its slug. Cached in Redis; each request counts as a view."""

    async def build() -> str | None:
        product = await catalog.get_active_product(session, slug)
        return ProductOut.model_validate(product).model_dump_json() if product else None

    payload = await cache.product(slug, build)
    if payload is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found.")
    await cache.record_view(json.loads(payload)["id"])
    return _json(payload, cache)


@router.get("/search")
async def search(
    session: SessionDep, client: SearchDep, params: Annotated[SearchParams, Query()]
) -> SearchOut:
    """Full-text search with brand, category, colour, size and price facets.

    Each facet's counts ignore its own selection, so other options stay visible. If the
    search engine is unavailable, falls back to database filtering with `facets: null`.
    """
    if get_settings().search_enabled:
        try:
            hits = await search_query.search(client, params)
        except httpx.HTTPError:
            log.warning("Search engine unavailable, falling back to the database", exc_info=True)
        else:
            rows = await session.scalars(
                select(Product).where(Product.id.in_(hits.ids)).options(selectinload(Product.category))
            )
            by_id = {p.id: p for p in rows}
            items = [ProductOut.model_validate(by_id[i]) for i in hits.ids if i in by_id]
            return SearchOut(
                items=items, total=hits.total, page=params.page, per_page=params.per_page,
                facets=hits.facets, engine="opensearch",
            )  # fmt: skip

    # Degraded mode: database filtering on the first selected value of each facet.
    sort = {SearchSort.price_asc: "price_asc", SearchSort.price_desc: "price_desc"}.get(params.sort, "newest")
    filters = ProductFilters(
        category=params.category[0] if params.category else None,
        brand=params.brand[0] if params.brand else None,
        min_price=params.min_price,
        max_price=params.max_price,
        in_stock=params.in_stock,
        sort=sort,
        page=params.page,
        per_page=params.per_page,
    )
    products, total = await catalog.list_products(session, filters)
    return SearchOut(
        items=[ProductOut.model_validate(p) for p in products],
        total=total, page=params.page, per_page=params.per_page, facets=None, engine="database",
    )  # fmt: skip
