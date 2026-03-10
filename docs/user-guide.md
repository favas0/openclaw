# OpenClaw User Guide

## Purpose

OpenClaw is a local product research agent for UK high-ticket dropshipping research. It collects marketplace listings, normalizes them, clusters similar products, enriches clusters with LLM-generated product intelligence, scores opportunities, and produces reports for operator review.

OpenClaw is not a storefront, order system, or auto-publisher. It is a research and decision-support tool.

## What OpenClaw Can Do

- Collect eBay listing data in demo mode or through the official eBay Browse API
- Collect Amazon scout listing data through a separate demo-only command
- Normalize raw listing titles into cleaner comparable forms
- Cluster similar listings into product groups
- Enrich clusters with structured product intelligence using Ollama
- Score clusters with deterministic economics and research heuristics
- Snapshot score and market trend data across repeated runs
- Export ranked products and shortlists
- Expose an optional web shell for approval pages, support URLs, health checks, and OAuth callbacks

## Current Limits

- Only eBay has a live API-backed source today
- Amazon now exists as a source-specific demo scout path, not a live API integration
- Etsy and TikTok collectors do not exist yet
- Supplier intelligence and competitor intelligence are heuristic, not live API-backed
- Trend monitoring depends on repeated ingestion and snapshot runs
- LLM enrichment improves context, but ranking remains partly heuristic and should be reviewed by a human

## Required Setup

You need:

- Docker and Docker Compose
- The repository checked out locally
- A writable data directory mounted at `/data` in the container
- Ollama running through Docker as defined in `docker-compose.yml`
- Optional eBay production credentials if you want live eBay API ingestion

## Environment File

Docker Compose loads environment variables from:

`/home/favas/.config/openclaw/.env`

Example values:

```env
APP_ENV=dev
LOG_LEVEL=INFO

OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b

OPENCLAW_DATA_DIR=/data
OPENCLAW_DB_PATH=/data/db/openclaw.sqlite3
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEB_BASE_URL=http://localhost:8000
WEB_SUPPORT_EMAIL=support@example.com

EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=
EBAY_DEV_ID=
EBAY_ENV=production
EBAY_MARKETPLACE_ID=EBAY_GB
```

If `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` are blank, `collect-ebay` defaults to demo mode unless `--api` is explicitly requested.

## First-Time Setup

Build the container image:

```bash
docker compose build
```

Check the environment and paths:

```bash
docker compose run --rm openclaw python -m app.cli doctor
```

Create database tables:

```bash
docker compose run --rm openclaw python -m app.cli initdb
```

If you already have a database and have pulled newer schema changes, run `initdb` again. It creates missing additive tables such as `cluster_market_snapshots` and newer additive columns used for structured research signals and query-aware score snapshots.

## Optional Web Shell

OpenClaw includes a thin FastAPI web shell for marketplace approval and reviewer access. It is not a rewrite of the product and does not replace the CLI workflow.

Start it locally:

```bash
python -m app.cli serve-web --host 0.0.0.0 --port 8000
```

Start it through Docker:

```bash
docker compose run --rm --service-ports openclaw python -m app.cli serve-web --host 0.0.0.0 --port 8000
```

Key pages:

- `/` product homepage
- `/review` reviewer/demo overview
- `/privacy` privacy policy
- `/terms` terms of service
- `/support` support and contact page
- `/health` JSON health check
- `/oauth/etsy/callback` Etsy callback URL
- `/oauth/tiktok/callback` TikTok callback URL

Reviewer notes:

- the reviewer page can show real database-backed stats and ranked products when the CLI pipeline has already populated SQLite
- if the database is empty or not mounted, the web shell still loads and explains the empty state cleanly

## Standard Research Workflow

### 1. Collect Listings

Demo mode:

```bash
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --demo --limit 10
```

Official eBay API mode:

```bash
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --api --limit 20 --marketplace-id EBAY_GB
```

Default behavior:

- if eBay credentials are configured, OpenClaw uses the official API
- if eBay credentials are missing, OpenClaw uses demo data

Amazon scout demo mode:

```bash
docker compose run --rm openclaw python -m app.cli collect-amazon "standing desk" --demo --limit 10
```

Amazon notes:

- `collect-amazon` is separate from `collect-ebay`
- it currently supports demo mode only
- it exists to exercise a second source path without changing the downstream pipeline

### 2. Normalize Listings

```bash
docker compose run --rm openclaw python -m app.cli normalize-listings
```

This computes normalized titles, canonical tokens, total price, brand-risk flags, and high-ticket flags.

### 3. Cluster Products

```bash
docker compose run --rm openclaw python -m app.cli cluster-products
```

This groups similar normalized listings into product clusters.

### 4. Enrich Clusters

```bash
docker compose run --rm openclaw python -m app.cli enrich-clusters
```

This asks Ollama for structured product intelligence such as product type, category hint, supplier search terms, confidence, visual hook score, fragility risk, and assembly complexity.

### 5. Score Products

```bash
docker compose run --rm openclaw python -m app.cli score-products
```

This computes:

- demand score
- sales signal score
- competition score
- supplier fit score
- risk score
- economics such as gross profit and max CPA
- final recommendation

### 6. Build Research Signals

```bash
docker compose run --rm openclaw python -m app.cli research-signals
```

This adds secondary heuristics such as supplier intelligence, ad signal quality, multi-market potential, and trend suitability.

The research signal output now includes:

- structured supplier breakdowns such as catalog fit, shipping profile, margin support, evidence, and confidence
- structured competitor breakdowns such as seller pressure, listing pressure, price pressure, and market maturity
- clearer supplier and competitor notes for operator review

### 7. Review Results

Top products:

```bash
docker compose run --rm openclaw python -m app.cli top-products --limit 20
```

`top-products` now includes merged research signal fields when they exist, so supplier and competitor context shows up alongside the main score row.

Shortlist:

```bash
docker compose run --rm openclaw python -m app.cli shortlist-products --min-profit 60 --min-cpa 30 --min-listings 2 --limit 10
```

Explain a single cluster:

```bash
docker compose run --rm openclaw python -m app.cli explain-product 1
```

Export ranked products:

```bash
docker compose run --rm openclaw python -m app.cli export-products --format both
```

Export shortlist:

```bash
docker compose run --rm openclaw python -m app.cli export-shortlist --format both
```

Export a review pack:

```bash
docker compose run --rm openclaw python -m app.cli export-review-pack --query "walking pad" --source-name ebay --format both --limit 10
docker compose run --rm openclaw python -m app.cli export-review-pack --query "standing desk" --source-name amazon --format both --limit 10
```

## Trend Workflow

Trend reporting becomes useful after multiple ingestion cycles for the same query.

Take a snapshot after scoring:

```bash
docker compose run --rm openclaw python -m app.cli snapshot-trends
```

You can also snapshot a specific run:

```bash
docker compose run --rm openclaw python -m app.cli snapshot-trends --run-id 3
```

When a previously tracked cluster disappears from the latest run for the same query, `snapshot-trends` now backfills a zero-listing market snapshot and a placeholder score snapshot for that series. That keeps disappearance and later reappearance visible in `trend-report` instead of silently dropping the series.

Then review trend movement:

```bash
docker compose run --rm openclaw python -m app.cli trend-report --limit 20
```

Filter to one query or source when you want a cleaner operational view:

```bash
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --source-name ebay --sort-by movement --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by new-items --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by recommendation-change --recommendation-changed-only --min-market-snapshots 2 --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by stable-supply-price --min-market-snapshots 2 --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by coverage --series-status disappeared --score-coverage-status market_absent --limit 20
```

The trend report includes:

- listing count change
- seller count change
- median price change
- items appearing since the previous snapshot
- items disappearing since the previous snapshot
- score movement over time

`trend-report` options:

- `--query` filters to one exact ingestion query
- `--source-name` filters to one source such as `ebay`
- `--sort-by movement|score|price|new-items|coverage|recommendation-change|stable-supply-price` changes ranking priority without changing the underlying data
- `--min-market-snapshots` hides thin trend rows until enough snapshots exist
- `--recommendation-changed-only` shows only clusters whose recommendation moved between the first and latest score snapshot
- `--series-status` filters lifecycle states such as `new`, `active`, `sparse`, `disappeared`, and `reappeared`
- `--score-coverage-status` filters whether the latest row is `scored`, `market_only`, or `market_absent`

Trend rows are now tracked per `cluster_id + source_name + query` market series. That prevents snapshots from different queries for the same cluster from being merged into one misleading trend line.
Score movement is also tracked against the same query-aware series, so recommendation-change views are materially cleaner.
Trend rows now expose both `series_status` and `score_coverage_status`, which makes sparse runs, disappearances, and reappearances easier to review directly from the CLI.

## Useful Support Commands

Run summary:

```bash
docker compose run --rm openclaw python -m app.cli runs
```

Table counts:

```bash
docker compose run --rm openclaw python -m app.cli stats
```

Cluster summary:

```bash
docker compose run --rm openclaw python -m app.cli clusters
```

Research signal summary:

```bash
docker compose run --rm openclaw python -m app.cli show-signals --limit 20
```

Side-by-side comparison:

```bash
docker compose run --rm openclaw python -m app.cli compare-products 1 2 3
```

Comparison rows now include structured supplier and competitor sub-scores in addition to the main economics and scoring fields.

Web shell startup:

```bash
python -m app.cli serve-web --host 0.0.0.0 --port 8000
```

## How To Read The Outputs

### Ingestion

`collect-ebay` returns:

- `inserted`: number of raw listings written
- `duplicates_skipped`: duplicate listings ignored within the same run
- `mode`: `demo` or `api`
- `marketplace_id`: active eBay marketplace

`collect-amazon` returns:

- `inserted`: number of raw listings written
- `duplicates_skipped`: duplicate listings ignored within the same run
- `mode`: currently always `demo`
- `source_name`: `amazon`

### Clusters

The cluster output is useful when:

- `listing_count` is not too thin
- `seller_count` shows more than one seller
- `median_total_price` stays inside the workable high-ticket range

### Scores

The main score fields are:

- `total_score`: overall opportunity score
- `recommendation`: usually `test`, `watch`, or `avoid`
- `gross_profit_estimate`: estimated unit gross profit
- `max_cpa`: estimated paid acquisition headroom

### Research Signals

These do not replace the main score. They add directional context around:

- supplier availability
- ad-friendliness
- competitive saturation
- cross-market potential
- trend suitability

### Review Pack

`export-review-pack` creates a handoff-oriented artifact that combines:

- core economics and recommendation
- supplier and competitor sub-signals
- latest trend status and coverage fields
- a compact deterministic review summary per row

## Troubleshooting

### `doctor` says eBay credentials are missing

Add `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` to `/home/favas/.config/openclaw/.env`, then rerun:

```bash
docker compose run --rm openclaw python -m app.cli doctor
```

### `collect-ebay --api` fails

Check:

- credentials are present
- `EBAY_ENV` matches the key type you have
- outbound network access is available from the container
- the marketplace ID is valid, usually `EBAY_GB`

### `collect-amazon` is not live

That is expected today. The Amazon path is a source-specific scout command with built-in demo data, not a live API integration.

### `enrich-clusters` fails

Check:

- Ollama container is running
- the model named in `OLLAMA_MODEL` is available
- `OLLAMA_BASE_URL` points to the container endpoint

### A new table is missing after pulling changes

Run:

```bash
docker compose run --rm openclaw python -m app.cli initdb
```

### The web shell does not start

Check:

- FastAPI, Uvicorn, and Jinja2 dependencies are installed in the current environment
- `WEB_HOST`, `WEB_PORT`, and `WEB_BASE_URL` are set correctly
- port `8000` is available, or start with a different `--port`
- the mounted `/data` directory exists if you expect reviewer pages to show database-backed content

### Outputs look empty

Check the pipeline order. `top-products` and `shortlist-products` require scoring to be completed first.

## Operator Guidance

- Treat OpenClaw as a ranking assistant, not an autopilot
- Review raw evidence before acting on a top-ranked cluster
- Compare several clusters side by side before deciding what to test
- Use repeated snapshots if you care about trend movement
- Prefer live API data over demo mode for real research decisions
