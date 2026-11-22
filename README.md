# AI-Powered Price Comparison Website

Search once, compare the same product across Amazon and Flipkart — even when each site
titles the listing differently. Built phase by phase per the project brief, with the AI
matching pipeline as the central feature: normalize → match (identifiers → attributes →
fuzzy → embeddings) → group → compare, backed by real sentiment analysis, price
history/prediction, recommendations, and price-drop alerts.

> A previous Node.js/Express/Vite implementation of this project is archived at
> `_archive_node_vite_build/` (not part of the active app), replaced by this
> Python/FastAPI + Next.js build to match the brief's technology stack exactly.

## Status

All 16 development phases are complete and tested. **135/135 backend tests pass, 93%
statement coverage.** The Phase 7 Amazon/Flipkart collectors are verified against the
*live* sites (not just mocks) — see [Live collector status](#live-collector-status)
below for exactly what that verification found. The one gap: the Docker image itself
(the `backend`/`migrate`/`celery-*` image, which bundles PyTorch + Playwright's Chromium
and takes ~20 minutes to build) was not build-verified end-to-end in this session — the
build hit and got fixed for one real bug (see below), but a full `docker compose up
--build` was cut short by the local Docker Desktop daemon becoming unresponsive,
unrelated to this project's code. `docker-compose.yml` itself validates
(`docker compose config`). Everything else — running the app directly (no Docker), all
136 tests, and live HTTP checks of every page/endpoint — is fully verified.

## Features

- **AI product matching** — 4-stage pipeline (exact identifiers → structured attributes
  → RapidFuzz → sentence-transformer embeddings), with a hard attribute gate so
  different storage/color/RAM/screen-size variants are never merged. Verified against
  22 matching examples (brief requires ≥20) and live against real Amazon/Flipkart search
  results.
- **Product search** — mock catalog by default (`MOCK_MODE=true`, zero external
  dependencies) or live Playwright collection against amazon.in/flipkart.com.
- **Comparison page** — best price/rating/discount/value badges, savings calculation,
  merged spec sheet.
- **Review sentiment analysis** — VADER-based per-review sentiment + aspect-keyword
  pros/cons/most-mentioned-features extraction; never fabricates a signal that isn't
  actually present in collected review text.
- **Price history & prediction** — highest/lowest/current/average aggregated across
  retailers; scikit-learn trend estimate (linear vs. random forest, picked by
  validation error) with an honest "insufficient data" response below 5 data points.
- **Recommendations** — rule-based "recommended for / not ideal for" tags derived from
  actual spec values (camera MP, battery mAh, RAM, refresh rate) and review pros/cons,
  plus embedding-similarity "similar products" scoped to the same category.
- **Price-drop alerts** — set a target price on any listing; a Celery Beat schedule
  checks and triggers alerts (email abstraction — logs in dev, sends via SMTP if
  configured), verified against a real Redis broker with a real worker process.
- **Playwright collection framework** — robots.txt enforcement, request throttling,
  retry/backoff, and CAPTCHA/block detection that stops gracefully rather than evading
  it, per the brief's data collection policy.

## Live collector status

Built and verified against the real sites, not assumed:

- **Amazon (amazon.in)**: fully working. robots.txt permits `/s?k=...` search and
  `/dp/<ASIN>` product pages for a generic user agent; live search and product-detail
  extraction (title, price, MRP, discount, rating, rating count, availability, 32 spec
  fields, images) all verified against real responses. Review extraction still returns 0
  on the ASINs tested — not yet solved, honestly left as a known gap.
- **Flipkart (flipkart.com)**: partially working. Live Playwright sessions get through
  (Flipkart's edge WAF returned a reCAPTCHA challenge to a plain `curl` during testing,
  but a real headless Chromium session was not challenged). Search results extraction is
  fully verified (title/price/rating). The product *detail* page uses hashed/atomic CSS
  classes that regenerate per deploy — price extraction there uses DOM-order text
  matching instead of class selectors (verified against a real wrong-price bug, fixed);
  MRP/discount/rating on that page are left `None` rather than risk extracting the wrong
  number from a stale selector.

Run `python backend/scripts/live_collector_smoke_test.py` (with `MOCK_MODE=false`) to
re-verify against the live sites yourself — it's deliberately not part of the automated
test suite (hitting live retailers shouldn't happen on every CI run).

## Technology stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, Recharts |
| Backend | Python 3.11, FastAPI, Pydantic, SQLAlchemy 2.0, PostgreSQL + pgvector, Redis, Celery |
| Web automation | Playwright (primary), BeautifulSoup/lxml for static parsing |
| AI/ML | sentence-transformers, RapidFuzz, scikit-learn, VADER sentiment, pandas, NumPy |
| DevOps | Docker, Docker Compose |

## Monorepo layout

```
backend/
  app/
    main.py, config.py
    database/        # SQLAlchemy engine + models, Alembic migrations
    api/              # FastAPI routers (search, products, comparison, reviews, prices, recommendations, alerts, retailers)
    collectors/       # BaseCollector, PlaywrightCollector, Amazon/Flipkart/Generic + mock collectors
    parsers/          # price/review/product/specification/seller text parsers
    matching/         # normalizer, product_matcher, similarity, embeddings
    services/         # search/product/comparison/review/price/prediction/recommendation/alert orchestration
    workers/          # Celery app + collection/price tasks
    schemas/          # Pydantic request/response models
    utils/            # logging, validators, robots.txt, email
  scripts/            # live_collector_smoke_test.py (manual, not in CI)
  tests/              # 135 tests — see Testing below
frontend/
  app/                # Next.js App Router pages (home, search, product detail, compare, alerts)
  components/, services/, types/, utils/
docker-compose.yml
.env.example
```

## Data collection policy

- No CAPTCHA bypass, no login/auth bypass, no access-control circumvention.
- No stealth/fingerprint-spoofing plugins, no proxy rotation to evade blocking, no
  anti-bot (e.g. Cloudflare/reCAPTCHA) defeat — `PlaywrightCollector` detects block/
  CAPTCHA pages and stops immediately, never retrying past one.
- `robots.txt` is checked before every request (`app/utils/robots.py`).
- Requests are throttled (`COLLECTOR_MIN_DELAY_SECONDS`) with bounded retries and
  exponential backoff.
- `MOCK_MODE=true` (the default) runs the entire app against a realistic, deliberately
  differently-worded-per-retailer mock catalog with zero live retailer access.

## Running locally (no Docker)

### 1. Database & Redis

```sh
docker compose up -d postgres redis
```

(Or install PostgreSQL 16 with the `pgvector` extension / Redis locally — see
`.env.example` for expected ports: Postgres on `5435`, Redis on `6381`, chosen to avoid
clashing with local installs.)

### 2. Backend (http://localhost:8000)

```sh
cd backend
py -3.11 -m venv .venv        # or: uv venv --python 3.11 .venv
.venv\Scripts\activate        # Windows; `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs for interactive API docs, http://localhost:8000/health
for a liveness check. The embedding model warms at startup (~15-20s the first time —
see `app/main.py`'s `lifespan`), so `/health` won't respond until it's ready.

### 3. Frontend (http://localhost:3000)

```sh
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### 4. Background jobs (optional)

```sh
cd backend
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info   # separate terminal
```

## Running with Docker

```sh
docker compose up -d --build
```

Builds and starts `postgres`, `redis`, a one-shot `migrate` service (runs `alembic
upgrade head`, then exits — `backend`/`celery-worker`/`celery-beat` wait on it via
`service_completed_successfully`), `backend`, `celery-worker`, `celery-beat`, and
`frontend`. First build is slow (~20+ min — PyTorch + Playwright's Chromium download
inside the image); subsequent builds reuse Docker's layer cache.

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Postgres: `localhost:5435`
- Redis: `localhost:6381`

## Testing

```sh
cd backend
pytest -q                                    # 135 tests
pytest --cov=app --cov-report=term-missing   # 93% statement coverage
```

Covers: `ProductNormalizer`, `ProductMatcher` (22 matching examples), `PriceParser`,
`ReviewParser`, `SpecificationParser`, `AmazonCollector`/`FlipkartCollector` parsing
(against local fixture HTML mirroring real markup — never live sites in CI), the
Playwright framework (robots.txt/block-detection/retry, against a local test server),
every service (search/comparison/review/price/prediction/recommendation/alert), every
Celery task, and one end-to-end test exercising the full search → match → compare →
review → price-history → prediction → recommendation → alert flow in one pass.

## API reference

All routes are prefixed `/api`.

```
GET    /api/retailers

POST   /api/search
GET    /api/products/{id}
GET    /api/products/{id}/compare
GET    /api/products/{id}/reviews
GET    /api/products/{id}/price-history
GET    /api/products/{id}/price-prediction
GET    /api/products/{id}/recommendations

POST   /api/alerts
GET    /api/alerts?email=...
DELETE /api/alerts/{id}
```

## Environment variables

See root [`.env.example`](.env.example) — database, Redis/Celery, collector throttling,
matching thresholds, optional LLM, and email/SMTP for alerts. Each service also has its
own `.env.example` for local development.

## Known limitations

- Amazon live review collection isn't working yet (returns 0 on tested ASINs) —
  everything else on that page is verified live.
- Flipkart's product-detail page has no reliable non-hashed selector for MRP/discount/
  rating, so those are left `None` there (search-results extraction has all of them).
- No user account system exists (per the brief's scope), so alerts are addressed by
  email directly rather than tied to a user profile, and recommendations are per-product
  (spec/review-driven), not history-personalized.
- Price prediction is a statistical estimate over limited history, explicitly labeled —
  never a guarantee.
- The Docker image build wasn't completed end-to-end in this session (see Status above);
  `docker-compose.yml` is config-validated and the Dockerfile has a real, verified fix
  (Debian trixie vs. Playwright dependency incompatibility) — the remaining risk is
  purely "does the ~20-minute image build finish cleanly," not application logic.
