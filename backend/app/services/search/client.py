import json
from typing import Any

import httpx

from app.core.config import get_settings


class SearchClient:
    """Minimal async REST client for OpenSearch (also works with Elasticsearch 8)."""

    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url, timeout=httpx.Timeout(5, connect=2), transport=transport
        )

    async def request(self, method: str, path: str, body: Any = None) -> httpx.Response:
        return await self._http.request(method, path, json=body)

    async def bulk(self, actions: list[tuple[dict[str, Any], dict[str, Any] | None]]) -> dict[str, Any]:
        lines = []
        for action, document in actions:
            lines.append(json.dumps(action))
            if document is not None:
                lines.append(json.dumps(document))
        response = await self._http.post(
            "/_bulk", content="\n".join(lines) + "\n", headers={"Content-Type": "application/x-ndjson"}
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        if result.get("errors"):
            failed = [item for item in result["items"] if next(iter(item.values())).get("error")][:3]
            raise RuntimeError(f"Bulk indexing failed: {failed}")
        return result


_client: SearchClient | None = None


def get_search_client() -> SearchClient:
    global _client
    _client = _client or SearchClient(get_settings().search_url)
    return _client
