# OpenClaw User Guide

## Purpose

OpenClaw is a local product research agent for UK high-ticket dropshipping research. It collects marketplace listings, normalizes them, clusters similar products, enriches clusters with LLM-generated product intelligence, scores opportunities, and produces reports for operator review.

OpenClaw is not a storefront, order system, or auto-publisher. It is a research and decision-support tool.

## What OpenClaw Can Do

- Collect eBay listing data in demo mode or through the official eBay Browse API
- Normalize raw listing titles into cleaner comparable forms
- Cluster similar listings into product groups
- Enrich clusters with structured product intelligence using Ollama
- Score clusters with deterministic economics and research heuristics
- Snapshot score and market trend data across repeated runs
- Export ranked products and shortlists

## Current Limits

- Only eBay is a real source today
- Amazon, Etsy, and TikTok collectors do not exist yet
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

If you already have a database and have pulled newer schema changes, run `initdb` again. It creates missing additive tables such as `cluster_market_snapshots`.

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

### 7. Review Results

Top products:

```bash
docker compose run --rm openclaw python -m app.cli top-products --limit 20
```

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

Then review trend movement:

```bash
docker compose run --rm openclaw python -m app.cli trend-report --limit 20
```

The trend report includes:

- listing count change
- seller count change
- median price change
- items appearing since the previous snapshot
- items disappearing since the previous snapshot
- score movement over time

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

## How To Read The Outputs

### Ingestion

`collect-ebay` returns:

- `inserted`: number of raw listings written
- `duplicates_skipped`: duplicate listings ignored within the same run
- `mode`: `demo` or `api`
- `marketplace_id`: active eBay marketplace

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

### Outputs look empty

Check the pipeline order. `top-products` and `shortlist-products` require scoring to be completed first.

## Operator Guidance

- Treat OpenClaw as a ranking assistant, not an autopilot
- Review raw evidence before acting on a top-ranked cluster
- Compare several clusters side by side before deciding what to test
- Use repeated snapshots if you care about trend movement
- Prefer live API data over demo mode for real research decisions
