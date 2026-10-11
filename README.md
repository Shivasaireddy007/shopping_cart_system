# Shopping Cart

[![ci](https://github.com/Shivasaireddy007/shopping_cart_system/actions/workflows/ci.yml/badge.svg)](https://github.com/Shivasaireddy007/shopping_cart_system/actions/workflows/ci.yml)

A full-stack e-commerce app: a **React + TypeScript** storefront and admin panel on a
**FastAPI** backend with **PostgreSQL**, with Razorpay payments. Prices are in rupees;
Shiprocket shipping, search and caching are on the roadmap.

![Catalog filtered to running shoes, sorted by price](docs/images/catalog.png)

| Product page | Cart |
|---|---|
| ![Product page with price, MRP and discount](docs/images/product.png) | ![Cart with live totals and free shipping](docs/images/cart.png) |

| Checkout | Order confirmation |
|---|---|
| ![Delivery address form with order summary](docs/images/checkout.png) | ![Paid order with items, payment and address](docs/images/order-confirmation.png) |

| Admin: products | Admin: edit product |
|---|---|
| ![Admin product list with stock and status](docs/images/admin-products.png) | ![Admin product form](docs/images/admin-edit-product.png) |

## Status

The project is built in stages. Each stage is complete and tested before the next starts.

| Stage | Scope | Status |
|---|---|---|
| 1 | Catalog, cart, JWT auth, admin products, React storefront and admin, CI | ✅ Done |
| 2 | Checkout with row-locked stock reservation, Razorpay payments and signed webhooks | ✅ Done |
| 3 | Redis caching for hot products, OpenSearch faceted search | Next |
| 4 | Kafka order events with the transactional outbox pattern, Shiprocket shipping | Planned |
| 5 | Docker and Kubernetes (Helm), observability, k6 load tests, live demo | Planned |

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 19, TypeScript, Vite, React Router, TanStack Query, Zustand, React Hook Form + Zod, Tailwind CSS |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic |
| Database | PostgreSQL 17 |
| Auth | JWT access and refresh tokens, Argon2 password hashing, admin role |
| Quality | pytest, Vitest + Testing Library, ruff, mypy (strict), oxlint, GitHub Actions |
| Payments | Razorpay Orders API, Razorpay Checkout, HMAC-signed webhooks |
| Planned | Redis, OpenSearch, Kafka, Shiprocket, Docker, Kubernetes, Playwright, k6 |

## Design decisions

- **No overselling, proven.** Checkout locks the product rows (`SELECT … FOR UPDATE`, in id order so
  concurrent checkouts can't deadlock) before reserving stock. A test runs ten checkouts at the same
  moment on separate database connections for three units: exactly three succeed. With the lock removed,
  all ten "succeed" and the stock is oversold
  ([`tests/test_concurrency.py`](backend/tests/test_concurrency.py)).
- **No locks held during network calls.** The stock reservation commits before Razorpay is called. If
  Razorpay fails, the order is cancelled, the stock goes back and the cart is kept.
- **Payments recorded exactly once.** The checkout callback and Razorpay's webhook can both report a
  payment, and webhooks can repeat or arrive out of order. Payment ids are unique, a late "failed" never
  downgrades a captured payment, and amounts are checked against the order total.
- **Webhooks are atomic.** Each webhook's event id is inserted with `ON CONFLICT DO NOTHING` in the same
  transaction as its effect: a repeat is detected even under concurrency, and if handling fails, nothing
  commits and Razorpay's retry is processed. Signatures are HMAC-SHA256 over the raw body, compared in
  constant time.
- **Abandoned checkouts release stock.** Unpaid orders are cancelled after 30 minutes by a job
  (`python -m app.jobs.expire_orders`), which returns their stock.

- **End-to-end types.** The backend's OpenAPI spec ([`docs/openapi.json`](docs/openapi.json)) generates
  the frontend's API types. If a backend field changes, the frontend stops compiling, and CI fails if
  either side is out of date.
- **Money as integers.** Amounts are stored and sent in paise (₹1 = 100 paise), so there are no
  floating-point rounding errors; the UI formats them with Indian digit grouping (₹1,09,999).
- **Rules enforced by the database too.** CHECK constraints stop negative stock, non-positive prices and
  an MRP below the price, even if application code has a bug.
- **No hidden queries.** Relationships are `lazy="raise"`, so an accidental lazy load raises an error
  instead of silently running N+1 queries; data is loaded explicitly with `selectinload`.
- **Indexes that match the sorts.** Composite indexes on `(is_active, price, id)`, `(is_active, name, id)`
  and `(is_active, category_id, price)` let paginated listings read in index order. The `id` tiebreaker
  follows the main sort direction so the index can serve it.
- **Short-lived tokens.** Access tokens last 15 minutes; the frontend swaps the refresh token for a new
  pair on a 401, and concurrent requests share a single refresh.
- **Fast, isolated tests.** Each backend test runs in a transaction that is rolled back afterwards, with
  the app's own commits turned into savepoints; the suite runs in under a second.

## API

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/register`, `/auth/login`, `/auth/refresh` | – | Get a token pair |
| GET | `/api/v1/auth/me` | JWT | Current user |
| GET | `/api/v1/categories` | – | Category list |
| GET | `/api/v1/products` | – | Filter by category, brand, price and stock; sort; paginate |
| GET | `/api/v1/products/{slug}` | – | Product details |
| GET / DELETE | `/api/v1/cart` | JWT | View or empty the cart |
| POST / PATCH / DELETE | `/api/v1/cart/items[/{id}]` | JWT | Add (stock checked, `409` if short), change quantity, remove |
| GET / POST | `/api/v1/admin/products` | Admin | List all products (incl. archived), create |
| PATCH / DELETE | `/api/v1/admin/products/{id}` | Admin | Update price, stock or details; archive |
| POST / DELETE | `/api/v1/admin/categories[/{id}]` | Admin | Manage categories |
| POST | `/api/v1/checkout` | JWT | Reserve stock, create the order and a Razorpay order |
| GET | `/api/v1/orders`, `/api/v1/orders/{number}` | JWT | Order history and details |
| POST | `/api/v1/orders/{number}/verify-payment` | JWT | Confirm payment with Razorpay's signature |
| POST | `/api/v1/orders/{number}/payment` | JWT | Get Razorpay details again to pay later |
| POST | `/api/v1/orders/{number}/cancel` | JWT | Cancel an unpaid order and release its stock |
| POST | `/api/webhooks/razorpay` | Signature | Payment captured or failed |

With the backend running, interactive docs are at [`/docs`](http://127.0.0.1:8000/docs).

## Running locally

You need Python 3.12 with [uv](https://docs.astral.sh/uv/), Node.js 22+ and PostgreSQL.

```bash
# Backend: http://127.0.0.1:8000
cd backend
uv sync
createdb shop
uv run alembic upgrade head
uv run python -m app.seed --products 1000
uv run uvicorn app.main:app --reload
```

For payments, create Razorpay **test mode** keys and set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`
and `RAZORPAY_WEBHOOK_SECRET` in `backend/.env`. Pay with Razorpay's
[test cards or UPI IDs](https://razorpay.com/docs/payments/payments/test-card-details/).

```bash
# Frontend: http://localhost:5173 (proxies /api to the backend)
cd frontend
npm ci
npm run dev
```

Demo logins: `demo@example.com` (customer) and `admin@example.com` (admin), password `demo-password`.

## Tests and checks

```bash
cd backend && createdb shop_test && uv run pytest && uv run ruff check . && uv run mypy app
cd frontend && npm test && npm run typecheck && npm run lint
```

After changing the API, regenerate the spec and the frontend types:

```bash
cd backend && uv run python -m app.export_openapi ../docs/openapi.json
cd frontend && npm run api:types
```

## Planned screens

Design mockups for the stages still to come. They'll be replaced with screenshots once built.

| Faceted search (stage 3) | Admin shipments (stage 4) |
|---|---|
| ![Search with brand, colour, price and size facets](docs/images/planned-search-facets.png) | ![Shipments with courier status](docs/images/planned-admin-shipments.png) |

| Order tracking (stage 4) | Admin dashboard |
|---|---|
| ![Shiprocket tracking timeline](docs/images/planned-order-tracking.png) | ![Orders, revenue, low stock and hot products](docs/images/planned-admin-dashboard.png) |

| Admin orders | |
|---|---|
| ![Orders with payment and shipment status](docs/images/planned-admin-orders.png) | |

## License

[MIT](LICENSE)
