# Load test results

Catalog and search API on a **100,000-product catalog** (98,000 active), measured with
[k6](https://k6.io) using [`catalog.js`](catalog.js). Every run is 60 seconds at a fixed arrival
rate, so each run sees identical load.

## Results

| Run | Load | Overall p95 | Listing p95 | Product p95 | Search p95 | Dropped | Errors |
|---|---|---|---|---|---|---|---|
| No cache | 300 req/s | 9.2 ms | 15.9 ms | 2.1 ms | 6.3 ms | 0 | 0 |
| No cache | 1,000 req/s | 99.1 ms | 95.3 ms | 90.2 ms | 120.6 ms | 63 | 0 |
| **Redis cache** | **1,000 req/s** | **5.5 ms** | **4.9 ms** | **2.0 ms** | **6.2 ms** | **0** | **0** |

At 1,000 requests per second, the Redis cache cut **overall p95 latency from 99 ms to 5.5 ms**
(about 18×) and **listing p95 from 95 ms to 4.9 ms**, and the server kept up with every request. The
cache run started empty, so its numbers include the misses while it filled; one worker's counters
showed about 88% of listing and 93% of product-page lookups served from Redis.

At 300 requests per second the database alone is already fast (listing p95 under 16 ms) because of
the composite indexes on the listing sorts; the cache matters once load rises. Search p95 also falls
at 1,000 req/s with the cache on, even though search isn't cached, because the database has
spare capacity again.

Raw k6 summaries are in [`results/`](results/).

## Workload

- 55% listing pages, 25% product pages, 20% searches
- Popular categories, products and queries get most of the traffic (power-law picks)
- 60% of listings are page 1; some add a brand (15%), price range (15%) or in-stock (25%) filter
- Sorts: newest 50%, price ascending 20%, price descending 20%, name 10%
- Searches use OpenSearch; 30% add a brand facet

## Environment

- MacBook Air (Apple Silicon); the API, databases and k6 all on the same machine
- FastAPI under uvicorn with 4 workers; PostgreSQL 17, Redis 8, OpenSearch 3.3
- 100,000 products generated with SQL (`generate_series`) across 16 categories

These are single-laptop numbers, not production capacity. The comparison between runs is what
matters: same machine, data and load, with only the cache switched.

## Reproduce

```bash
createdb bench
DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:5432/bench uv run alembic upgrade head
psql bench -f benchmarks/sql/seed_100k_products.sql
DATABASE_URL=… SEARCH_INDEX=bench_products uv run python -m app.jobs.reindex
DATABASE_URL=… REDIS_URL=redis://127.0.0.1:6379/3 SEARCH_INDEX=bench_products \
  CATALOG_CACHE_ENABLED=false uv run uvicorn app.main:app --port 8001 --workers 4
k6 run -e RATE=1000 -e DURATION=60s --summary-export=results/run.json benchmarks/catalog.js
```
