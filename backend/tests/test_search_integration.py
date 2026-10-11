"""Index and search against a real OpenSearch, to catch mapping or query mistakes fakes can't.

Runs when OPENSEARCH_TEST_URL points at a reachable engine (CI starts one as a service).
"""

import os
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.schemas.search import SearchParams
from app.services.search import index
from app.services.search.client import SearchClient
from app.services.search.query import search
from tests.conftest import Factory

URL = os.environ.get("OPENSEARCH_TEST_URL", "")


def _reachable() -> bool:
    try:
        return bool(URL) and httpx.get(URL, timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="set OPENSEARCH_TEST_URL to a running OpenSearch")


@pytest.fixture
async def engine(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[SearchClient]:
    monkeypatch.setattr(get_settings(), "search_index", "products_test")
    client = SearchClient(URL)
    yield client
    for name in (await client.request("GET", "/_alias/products_test")).json() or []:
        await client.request("DELETE", f"/{name}")


async def test_real_engine_returns_disjunctive_facets_and_fuzzy_matches(
    engine: SearchClient, factory: Factory, session: AsyncSession
) -> None:
    shoes = await factory.category("running-shoes")
    await factory.product(
        shoes, name="Nike Air Zoom Running Shoes", brand="Nike", price=899900, attributes={"color": "black"}
    )
    await factory.product(
        shoes, name="Nike Pegasus Trail Shoes", brand="Nike", price=45000, attributes={"color": "red"}
    )
    await factory.product(
        shoes, name="Puma Velocity Running Shoes", brand="Puma", price=749900, attributes={"color": "black"}
    )
    await factory.product(shoes, name="Old Model", brand="Puma", price=10000, is_active=False)

    assert await index.rebuild(engine, session) == 3

    nike = await search(engine, SearchParams(brand=["Nike"]))
    assert nike.total == 2
    assert {f.value: f.count for f in nike.facets["brand"]} == {"Nike": 2, "Puma": 1}, (
        "brand ignores its own filter"
    )
    assert {f.value: f.count for f in nike.facets["color"]} == {"black": 1, "red": 1}, "colour respects brand"

    typo = await search(engine, SearchParams(q="runing shoe"))
    assert typo.total == 2

    cheap = await search(engine, SearchParams(max_price=50000, sort="price_asc"))
    assert cheap.total == 1
