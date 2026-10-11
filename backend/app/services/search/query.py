"""Faceted product search.

Facets are disjunctive: ticking brand=Nike still shows counts for every other brand.
So facet selections go into a post_filter, and each facet's aggregation applies every
selection except its own. Price range and stock filters narrow everything, facets included.
"""

from typing import Any

from pydantic import BaseModel

from app.schemas.search import Facet, SearchParams, SearchSort
from app.services.search.client import SearchClient
from app.services.search.index import alias

FACETS = ("brand", "category", "color", "size")

PRICE_RANGES = [
    {"key": "under-500", "to": 50000},
    {"key": "500-1000", "from": 50000, "to": 100000},
    {"key": "1000-2500", "from": 100000, "to": 250000},
    {"key": "2500-5000", "from": 250000, "to": 500000},
    {"key": "over-5000", "from": 500000},
]


class SearchHits(BaseModel):
    ids: list[int]
    total: int
    facets: dict[str, list[Facet]]


def build_query(params: SearchParams) -> dict[str, Any]:
    selected = {f: getattr(params, f) for f in FACETS if getattr(params, f)}

    def all_except(facet: str | None) -> dict[str, Any]:
        return {"bool": {"filter": [{"terms": {f: v}} for f, v in selected.items() if f != facet]}}

    filters: list[dict[str, Any]] = []
    if params.min_price is not None or params.max_price is not None:
        price = {k: v for k, v in (("gte", params.min_price), ("lte", params.max_price)) if v is not None}
        filters.append({"range": {"price": price}})
    if params.in_stock:
        filters.append({"term": {"in_stock": True}})

    text: dict[str, Any] = (
        {
            "multi_match": {
                "query": params.q,
                "fields": ["name^3", "brand^2", "description"],
                "fuzziness": "AUTO",
                "operator": "and",
            }
        }
        if params.q
        else {"match_all": {}}
    )

    aggs: dict[str, Any] = {
        facet: {"filter": all_except(facet), "aggs": {"values": {"terms": {"field": facet, "size": 30}}}}
        for facet in FACETS
    }
    aggs["price"] = {
        "filter": all_except(None),
        "aggs": {"ranges": {"range": {"field": "price", "ranges": PRICE_RANGES}}},
    }

    sort: list[Any] = {
        SearchSort.price_asc: [{"price": "asc"}, {"id": "asc"}],
        SearchSort.price_desc: [{"price": "desc"}, {"id": "desc"}],
        SearchSort.newest: [{"created_at": "desc"}, {"id": "desc"}],
        SearchSort.relevance: ["_score", {"id": "desc"}]
        if params.q
        else [{"created_at": "desc"}, {"id": "desc"}],
    }[params.sort]

    return {
        "query": {"bool": {"must": [text], "filter": filters}},
        "post_filter": all_except(None),
        "aggs": aggs,
        "sort": sort,
        "from": (params.page - 1) * params.per_page,
        "size": params.per_page,
        "track_total_hits": True,
        "_source": False,
    }


async def search(client: SearchClient, params: SearchParams) -> SearchHits:
    response = await client.request("POST", f"/{alias()}/_search", build_query(params))
    response.raise_for_status()
    body = response.json()
    aggs = body.get("aggregations", {})

    facets = {
        facet: [
            Facet(value=str(b["key"]), count=b["doc_count"])
            for b in aggs.get(facet, {}).get("values", {}).get("buckets", [])
        ]
        for facet in FACETS
    }
    facets["price"] = [
        Facet(value=b["key"], count=b["doc_count"])
        for b in aggs.get("price", {}).get("ranges", {}).get("buckets", [])
    ]
    return SearchHits(
        ids=[int(hit["_id"]) for hit in body["hits"]["hits"]],
        total=body["hits"]["total"]["value"],
        facets=facets,
    )
