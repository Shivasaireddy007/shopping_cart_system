import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import SearchParams
from app.services.search import index
from app.services.search.query import build_query
from tests.conftest import Factory, FakeSearch


def test_facet_selections_go_to_post_filter_not_the_main_query() -> None:
    query = build_query(SearchParams(brand=["Nike"], color=["red"]))

    assert query["query"]["bool"]["filter"] == []
    assert query["post_filter"]["bool"]["filter"] == [
        {"terms": {"brand": ["Nike"]}},
        {"terms": {"color": ["red"]}},
    ]


def test_each_facet_ignores_its_own_selection() -> None:
    query = build_query(SearchParams(brand=["Nike"], color=["red"]))

    assert query["aggs"]["brand"]["filter"]["bool"]["filter"] == [{"terms": {"color": ["red"]}}]
    assert query["aggs"]["color"]["filter"]["bool"]["filter"] == [{"terms": {"brand": ["Nike"]}}]
    assert len(query["aggs"]["size"]["filter"]["bool"]["filter"]) == 2


def test_price_and_stock_narrow_everything() -> None:
    query = build_query(SearchParams(min_price=10000, max_price=50000, in_stock=True))

    assert {"range": {"price": {"gte": 10000, "lte": 50000}}} in query["query"]["bool"]["filter"]
    assert {"term": {"in_stock": True}} in query["query"]["bool"]["filter"]


def test_text_query_is_fuzzy_and_sorted_by_relevance() -> None:
    query = build_query(SearchParams(q="runing shoe"))

    match = query["query"]["bool"]["must"][0]["multi_match"]
    assert (match["query"], match["fuzziness"]) == ("runing shoe", "AUTO")
    assert query["sort"][0] == "_score"


def test_pagination() -> None:
    query = build_query(SearchParams(page=3, per_page=20))

    assert (query["from"], query["size"]) == (40, 20)


async def test_search_returns_products_in_ranking_order_with_facets(
    client: AsyncClient, factory: Factory, search: FakeSearch
) -> None:
    category = await factory.category()
    first, second = await factory.product(category), await factory.product(category)
    search.next_search = {
        "hits": {"total": {"value": 2}, "hits": [{"_id": str(second.id)}, {"_id": str(first.id)}]},
        "aggregations": {
            "brand": {
                "values": {"buckets": [{"key": "Nike", "doc_count": 7}, {"key": "Puma", "doc_count": 3}]}
            },
            "price": {"ranges": {"buckets": [{"key": "under-500", "doc_count": 1}]}},
        },
    }

    body = (await client.get("/api/v1/search", params={"q": "shoe", "brand": ["Nike"]})).json()

    assert body["engine"] == "opensearch"
    assert [p["id"] for p in body["items"]] == [second.id, first.id]
    assert body["facets"]["brand"][0] == {"value": "Nike", "count": 7}
    assert body["facets"]["price"][0]["value"] == "under-500"
    sent = next(b for m, path, b in search.requests if path.endswith("/_search"))
    assert sent["post_filter"]["bool"]["filter"] == [{"terms": {"brand": ["Nike"]}}]


async def test_search_falls_back_to_the_database(
    client: AsyncClient, factory: Factory, search: FakeSearch
) -> None:
    search.down = True
    category = await factory.category()
    await factory.product(category, brand="Nike")
    await factory.product(category, brand="Puma")

    body = (await client.get("/api/v1/search", params={"brand": ["Nike"]})).json()

    assert (body["engine"], body["facets"], body["total"]) == ("database", None, 1)


async def test_search_validates_parameters(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/search", params={"per_page": 100})).status_code == 422


async def test_product_changes_are_indexed_by_the_search_consumer(
    factory: Factory, search: FakeSearch, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.events import handlers

    monkeypatch.setattr(handlers, "get_search_client", lambda: search.client)
    index_product = handlers.index_product

    active = await factory.product(name="Trail Runner")
    archived = await factory.product(is_active=False)

    for product_id in (active.id, archived.id):
        await index_product(
            session, {"event_id": "x", "type": "product.changed", "data": {"product_id": product_id}}
        )

    indexed, removed = search.bulk_bodies()
    assert indexed[0] == {"index": {"_index": "products", "_id": str(active.id)}}
    assert indexed[1]["name"] == "Trail Runner"
    assert removed == [{"delete": {"_index": "products", "_id": str(archived.id)}}]


async def test_rebuild_fills_a_new_index_and_swaps_the_alias(
    factory: Factory, search: FakeSearch, session: AsyncSession
) -> None:
    category = await factory.category()
    for _ in range(3):
        await factory.product(category)
    await factory.product(category, is_active=False)

    assert await index.rebuild(search.client, session, batch=2) == 3

    calls = [(m, p) for m, p, _ in search.requests]
    new_index = calls[0][1]
    assert calls[0][0] == "PUT" and new_index.startswith("/products_")
    assert [p for m, p in calls].count("/_bulk") == 2
    alias_actions = next(b for m, p, b in search.requests if p == "/_aliases")["actions"]
    assert alias_actions[0] == {"add": {"index": new_index.lstrip("/"), "alias": "products"}}


async def test_failed_rebuild_removes_the_half_built_index(
    factory: Factory, search: FakeSearch, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await factory.product()

    async def broken_bulk(*_: object) -> None:
        raise RuntimeError("bulk failed")

    monkeypatch.setattr(search.client, "bulk", broken_bulk)

    with pytest.raises(RuntimeError):
        await index.rebuild(search.client, session)

    assert search.requests[-1][0] == "DELETE"
