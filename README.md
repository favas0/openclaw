# OpenClaw

OpenClaw is a self-hosted Python research agent for UK high-ticket dropshipping product discovery. It collects listing data, normalizes it, clusters similar products, enriches clusters with local LLM output, scores opportunities, and produces reports for human review.

The stack is intentionally light:

- Python CLI application
- SQLite database
- Docker-friendly local runtime
- Ollama for local enrichment

## Documentation

- User guide: [docs/user-guide.md](/home/favas/projects/openclaw/docs/user-guide.md)
- Operator workflows: [docs/operator-workflows.md](/home/favas/projects/openclaw/docs/operator-workflows.md)
- Technical architecture: [docs/technical-architecture.md](/home/favas/projects/openclaw/docs/technical-architecture.md)
- Data model: [docs/data-model.md](/home/favas/projects/openclaw/docs/data-model.md)
- Development workflow: [docs/development-workflow.md](/home/favas/projects/openclaw/docs/development-workflow.md)

## Local Paths

- Repo: `~/projects/openclaw`
- Secrets: `~/.config/openclaw/.env`
- Data: `~/data/openclaw`

## Quickstart

Build the image:

```bash
docker compose build
```

Check config and paths:

```bash
docker compose run --rm openclaw python -m app.cli doctor
```

Create database tables:

```bash
docker compose run --rm openclaw python -m app.cli initdb
```

Run a demo pipeline:

```bash
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --demo --limit 5
docker compose run --rm openclaw python -m app.cli normalize-listings
docker compose run --rm openclaw python -m app.cli cluster-products
docker compose run --rm openclaw python -m app.cli enrich-clusters
docker compose run --rm openclaw python -m app.cli score-products
docker compose run --rm openclaw python -m app.cli research-signals
docker compose run --rm openclaw python -m app.cli top-products --limit 10
```

## eBay API Usage

Once credentials are configured in `~/.config/openclaw/.env`:

```bash
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --api --limit 20 --marketplace-id EBAY_GB
```

Supported env vars:

```env
EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=
EBAY_ENV=production
EBAY_MARKETPLACE_ID=EBAY_GB
```

Legacy aliases also work:

- `EBAY_APP_ID`
- `EBAY_CERT_ID`

## Trend Monitoring

Capture a snapshot after a scoring run:

```bash
docker compose run --rm openclaw python -m app.cli snapshot-trends
```

View trend movement:

```bash
docker compose run --rm openclaw python -m app.cli trend-report --limit 20
```

Filter trend output by query and ranking mode when reviewing a specific market:

```bash
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --source-name ebay --sort-by new-items --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by recommendation-change --recommendation-changed-only --min-market-snapshots 2 --limit 20
```

If you already have a database, rerun `initdb` after pulling schema updates so additive tables and columns such as `cluster_market_snapshots`, structured research breakdowns, and query-aware score snapshots are created.

## Tests

```bash
python3 -m compileall app tests
docker compose run --rm openclaw python -m unittest discover -s tests -v
```
