# OpenClaw Operator Workflows

## Workflow 1: Smoke Test The Stack

Use this when setting up a new machine or after pulling changes.

```bash
docker compose build
docker compose run --rm openclaw python -m app.cli doctor
docker compose run --rm openclaw python -m app.cli initdb
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --demo --limit 5
docker compose run --rm openclaw python -m app.cli normalize-listings
docker compose run --rm openclaw python -m app.cli cluster-products
docker compose run --rm openclaw python -m app.cli enrich-clusters
docker compose run --rm openclaw python -m app.cli score-products
docker compose run --rm openclaw python -m app.cli research-signals
docker compose run --rm openclaw python -m app.cli top-products --limit 10
```

Expected outcome:

- commands complete without errors
- `top-products` returns at least one scored cluster

## Workflow 2: Live eBay Research Run

Use this once eBay API credentials are configured.

```bash
docker compose run --rm openclaw python -m app.cli doctor
docker compose run --rm openclaw python -m app.cli collect-ebay "standing desk" --api --limit 20 --marketplace-id EBAY_GB
docker compose run --rm openclaw python -m app.cli normalize-listings
docker compose run --rm openclaw python -m app.cli cluster-products
docker compose run --rm openclaw python -m app.cli enrich-clusters
docker compose run --rm openclaw python -m app.cli score-products
docker compose run --rm openclaw python -m app.cli research-signals
docker compose run --rm openclaw python -m app.cli shortlist-products --min-profit 60 --min-cpa 30 --min-listings 2 --limit 10
```

Recommended follow-up:

- inspect the shortlist
- run `explain-product` on the best few clusters
- export the results

## Workflow 3: Compare Candidate Clusters

Review the top clusters first:

```bash
docker compose run --rm openclaw python -m app.cli top-products --limit 10
```

Then compare likely candidates:

```bash
docker compose run --rm openclaw python -m app.cli compare-products 1 2 3
```

Then inspect individual reasoning:

```bash
docker compose run --rm openclaw python -m app.cli explain-product 1
docker compose run --rm openclaw python -m app.cli explain-product 2
docker compose run --rm openclaw python -m app.cli explain-product 3
```

Use this when the score gap is small and you want more context before deciding what to test.

The comparison output now includes supplier and competitor sub-scores, which makes it easier to distinguish margin-friendly but crowded markets from cleaner supplier paths with lighter competition.

## Workflow 4: Track Trend Movement Across Runs

Run the full pipeline for a query, then snapshot:

```bash
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --api --limit 20
docker compose run --rm openclaw python -m app.cli normalize-listings
docker compose run --rm openclaw python -m app.cli cluster-products
docker compose run --rm openclaw python -m app.cli score-products
docker compose run --rm openclaw python -m app.cli snapshot-trends
```

Repeat later with the same query, then snapshot again:

```bash
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --api --limit 20
docker compose run --rm openclaw python -m app.cli normalize-listings
docker compose run --rm openclaw python -m app.cli cluster-products
docker compose run --rm openclaw python -m app.cli score-products
docker compose run --rm openclaw python -m app.cli snapshot-trends
docker compose run --rm openclaw python -m app.cli trend-report --limit 20
```

Use this when you want to observe:

- listing volume increasing or falling
- seller count shifts
- median price drift
- products appearing or disappearing

For a cleaner operator view, prefer filtering the report to the active query:

```bash
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --source-name ebay --sort-by movement --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by new-items --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by recommendation-change --recommendation-changed-only --min-market-snapshots 2 --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by stable-supply-price --min-market-snapshots 2 --limit 20
docker compose run --rm openclaw python -m app.cli trend-report --query "walking pad" --sort-by coverage --series-status disappeared --score-coverage-status market_absent --limit 20
```

Sort modes:

- `movement`: biggest listing and seller swings first
- `score`: biggest score changes first
- `price`: biggest median price moves first
- `new-items`: clusters with the most newly seen items first
- `coverage`: scored and continuity-rich rows first
- `recommendation-change`: rows where recommendation changed, ranked by score movement
- `stable-supply-price`: the most stable supply series with meaningful price movement first

Lifecycle filters:

- `--series-status disappeared` isolates clusters that vanished from the latest run
- `--series-status reappeared` isolates clusters that came back after a zero-listing snapshot
- `--score-coverage-status market_only` isolates rows with market evidence but missing current scoring coverage

## Workflow 5: Export A Review Pack

Export a ranked overview:

```bash
docker compose run --rm openclaw python -m app.cli export-products --format both
```

Export a filtered shortlist:

```bash
docker compose run --rm openclaw python -m app.cli export-shortlist --format both --min-profit 60 --min-cpa 30 --min-listings 2 --limit 10
```

Files are written under:

`/data/reports`

Use this when you want a handoff artifact for manual product review.

## Workflow 6: Inspect System Health

```bash
docker compose run --rm openclaw python -m app.cli doctor
docker compose run --rm openclaw python -m app.cli runs
docker compose run --rm openclaw python -m app.cli stats
docker compose run --rm openclaw python -m app.cli clusters
docker compose run --rm openclaw python -m app.cli show-signals --limit 20
```

Use this when troubleshooting, validating a deployment, or checking whether the last research run completed correctly.

## Workflow Notes

- The intended order is still collect -> normalize -> cluster -> enrich -> score -> research signals -> report
- `enrich-clusters` requires Ollama availability
- `trend-report` becomes meaningful only after multiple snapshots
- `collect-ebay` stays eBay-specific by design; future sources should get separate commands
