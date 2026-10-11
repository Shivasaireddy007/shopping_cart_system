from httpx import AsyncClient


async def test_health_and_ready(client: AsyncClient) -> None:
    assert (await client.get("/health")).json() == {"status": "ok"}

    ready = await client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok", "database": "ok", "redis": "ok"}
