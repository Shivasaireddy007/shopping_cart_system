from httpx import AsyncClient

from tests.conftest import Factory


async def test_metrics_record_latency_by_route_template(client: AsyncClient, factory: Factory) -> None:
    product = await factory.product()
    await client.get(f"/api/v1/products/{product.slug}")
    await client.get(f"/api/v1/products/{product.slug}")

    body = (await client.get("/metrics")).text

    assert (
        'http_request_duration_seconds_count{method="GET",route="/api/v1/products/{slug}",status="200"}'
        in body
    )
    assert product.slug not in body, "raw paths would create a metric series per product"
    assert 'catalog_cache_lookups_total{kind="product",result="hit"}' in body


async def test_checkout_outcomes_are_counted(client: AsyncClient) -> None:
    body = (await client.get("/metrics")).text

    assert "checkouts_total" in body
    assert "orders_paid_total" in body
