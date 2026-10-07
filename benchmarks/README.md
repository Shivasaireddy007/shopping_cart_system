# Catalog performance benchmark

Load test of the catalog API (`GET /api/v1/products` and `GET /api/v1/products/{slug}`)
on a 100,000-product catalog, run in three stages to show what each optimisation contributes.

## Results

Fixed load of **150 requests/second for 60 seconds** (9,000+ requests per run, 0 errors in every run).

| Stage | Overall p95 | Listing p95 | Product page p95 | Listing p50 |
|---|---|---|---|---|
| 1. Baseline (MySQL only) | 211 ms | **277 ms** | 33 ms | 11.0 ms |
| 2. + composite indexes for listing sorts | 19 ms | 61 ms | 4.0 ms | 5.9 ms |
| 3. + Redis catalog cache | 10 ms | **10.8 ms** | 4.0 ms | 3.1 ms |

Listing p95 went from **277 ms to 10.8 ms (about 25x faster)**:

- **Indexes (277 → 61 ms).** Listings sorted by price or name were filesorting about 49,000 active
  rows. Composite indexes on `(is_active, price, id)`, `(is_active, name, id)` and
  `(is_active, category_id, price)` let MySQL read pages in index order. The `id` tiebreaker now
  follows the main sort direction; mixing directions (`price ASC, id DESC`) stopped the index
  from being used for the sort.
- **Redis cache (61 → 10.8 ms).** Listing pages are cached under keys that include a catalog
  version, so one product change retires every cached listing without scanning keys. Product
  pages are cached per slug, views are counted in hourly Redis sorted sets, and the top 100
  products are pre-warmed every 5 minutes with a longer TTL. Stage 3 started with an empty cache,
  so its numbers include the cache misses while it filled.

Raw k6 summaries are in [`results/`](results/).

## Workload

[`catalog.js`](catalog.js) shapes traffic like a real shop:

- 70% listing pages, 30% product pages
- Popular categories and products get most of the views (power-law picks)
- 60% of listings are page 1; the rest are pages 2 to 5
- Some listings add filters: brand (15%), price range (15%), in stock (25%)
- Sorts: newest 50%, price ascending 20%, price descending 20%, name 10%

## Environment

- MacBook Air (Apple Silicon), everything on one machine
- PHP 8.3 built-in server with 8 workers, opcache on, `APP_DEBUG=false`, config and routes cached
- MySQL 8.4 (Unix socket), Redis 8
- 100,000 products in 24 categories

These are laptop numbers, not production numbers: a real deployment would use PHP-FPM or
Octane behind nginx on separate database and cache servers. The comparison between stages is
what matters, since every run used the same machine, data and load.

The fixed arrival rate is deliberate. PHP's built-in server closes the connection after every
request, so an unthrottled test runs macOS out of local ports (`can't assign requested address`)
long before the app is the bottleneck.

## Reproduce

```bash
# 1. Seed 100k products
SEED_PRODUCTS=100000 php -d memory_limit=1G artisan db:seed --class=CatalogSeeder

# 2. In .env: APP_DEBUG=false, API_RATE_LIMIT=1000000, CATALOG_CACHE_ENABLED=false (stage 1-2) or true (stage 3)
php artisan config:cache && php artisan route:cache

# 3. Serve with several workers (run from public/)
cd public && PHP_CLI_SERVER_WORKERS=8 php -d opcache.enable_cli=1 \
    -S 127.0.0.1:8000 ../vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php

# 4. Run the load test
k6 run -e RATE=150 -e DURATION=60s --summary-export=benchmarks/results/run.json benchmarks/catalog.js
```

For stage 1 numbers, roll back the index migration (`php artisan migrate:rollback --step=1`)
and restore the previous `ProductQuery` tiebreaker.
