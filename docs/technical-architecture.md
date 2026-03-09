# OpenClaw Technical Architecture

## System Shape

OpenClaw is a single-process Python CLI application designed for local or self-hosted research workflows.

It intentionally keeps the stack light:

- Python backend
- SQLite database
- Docker-friendly local runtime
- Ollama for local LLM enrichment
- no microservices
- no queueing layer
- no remote orchestrator

## Runtime Components

### `openclaw` container

Runs the CLI commands and accesses:

- source ingestion code
- normalization and clustering logic
- scoring and reporting logic
- SQLite database mounted under `/data`

### `ollama` container

Provides local LLM inference for cluster enrichment.

## Active CLI Entry Point

The active CLI entry point is:

[app/cli.py](/home/favas/projects/openclaw/app/cli.py)

It registers command groups from:

- [app/commands/system.py](/home/favas/projects/openclaw/app/commands/system.py)
- [app/commands/pipeline.py](/home/favas/projects/openclaw/app/commands/pipeline.py)
- [app/commands/reporting.py](/home/favas/projects/openclaw/app/commands/reporting.py)
- [app/commands/research.py](/home/favas/projects/openclaw/app/commands/research.py)

## Pipeline Stages

### 1. Ingestion

Current real source support is eBay.

- demo source mapping lives in [app/sources/ebay.py](/home/favas/projects/openclaw/app/sources/ebay.py)
- official eBay Browse API integration lives in [app/sources/ebay_api.py](/home/favas/projects/openclaw/app/sources/ebay_api.py)

The collector command is eBay-specific by design:

- `collect-ebay`

The collector writes shared `raw_listings` records so downstream stages remain source-agnostic.

### 2. Normalization

[app/normalize/processor.py](/home/favas/projects/openclaw/app/normalize/processor.py) and [app/normalize/titles.py](/home/favas/projects/openclaw/app/normalize/titles.py) convert raw titles into:

- normalized titles
- canonical tokens
- total price
- brand-risk flags
- high-ticket candidate flags

### 3. Clustering

[app/cluster/cluster_products.py](/home/favas/projects/openclaw/app/cluster/cluster_products.py) groups normalized listings into product clusters using token overlap and fuzzy matching.

### 4. Enrichment

[app/enrichment/cluster_enricher.py](/home/favas/projects/openclaw/app/enrichment/cluster_enricher.py) calls [app/llm/ollama_client.py](/home/favas/projects/openclaw/app/llm/ollama_client.py) to produce structured product intelligence for each cluster.

### 5. Scoring

[app/scoring/cluster_scoring.py](/home/favas/projects/openclaw/app/scoring/cluster_scoring.py) computes deterministic opportunity scores and economics.

### 6. Research Signals

[app/research/signals.py](/home/favas/projects/openclaw/app/research/signals.py) adds secondary heuristic signals around supplier fit, ad potential, competition, multi-market expansion, and trend suitability.

The research layer now stores structured supplier and competitor breakdowns, not just top-line notes. That keeps the logic deterministic while giving operators clearer reasons behind supplier viability and market saturation.

### 7. Trend Snapshots

[app/research/trend_snapshots.py](/home/favas/projects/openclaw/app/research/trend_snapshots.py) captures:

- score snapshots
- market snapshots keyed to ingestion runs

This allows `trend-report` to show actual market movement, not just score history.

Trend reporting is query-aware at the market snapshot layer. Market series are interpreted per `cluster_id + source_name + query`, which avoids mixing snapshots from different ingestion queries into one trend line for the same underlying cluster.

Score snapshots are also now stamped with `source_name` and `query`, so recommendation and score movement can be interpreted against the correct market series instead of only the raw cluster id.

Snapshot capture also backfills continuity for missing clusters within the active query series. When a cluster disappears from the latest run, OpenClaw writes a zero-listing market snapshot and a placeholder score snapshot for that series so later trend reports can distinguish disappearance, reappearance, sparse evidence, and missing score coverage.

## Source Architecture

OpenClaw intentionally does not use a generic multi-provider `collect` command.

Current pattern:

- `collect-ebay` command
- `app/sources/ebay.py`
- `app/sources/ebay_api.py`

Expected future pattern:

- `collect-amazon`
- `collect-etsy`
- `collect-tiktok`

Each source should have its own module and mapping logic, but should still emit the shared raw listing shape so the downstream pipeline remains unchanged.

## Database Access Pattern

The repository layer is split by responsibility under [app/db/repositories/](/home/favas/projects/openclaw/app/db/repositories/__init__.py):

- `ingestion.py`
- `catalog.py`
- `scoring.py`
- `research.py`
- `trends.py`

[app/db/repo.py](/home/favas/projects/openclaw/app/db/repo.py) remains as a compatibility facade that re-exports the public repository functions used by commands.

## Transaction Model

Write-heavy stages now batch most writes per command rather than committing on every row.

Current pattern:

- repository functions accept `auto_commit`
- pipeline commands usually call repository writes with `auto_commit=False`
- commands commit once at the end of the stage

This keeps the code simple while reducing SQLite transaction churn.

## Configuration Model

Configuration is defined in [app/config.py](/home/favas/projects/openclaw/app/config.py) using `pydantic-settings`.

Notable configuration:

- Ollama base URL and model
- data directory and SQLite path
- eBay credentials and marketplace defaults

eBay credentials support both canonical and legacy names:

- `EBAY_CLIENT_ID` or `EBAY_APP_ID`
- `EBAY_CLIENT_SECRET` or `EBAY_CERT_ID`

## Design Constraints

The current architecture deliberately preserves:

- SQLite
- CLI-driven workflow
- Docker-friendly local development
- modular Python package layout
- deterministic downstream scoring
- source-specific integration modules
- stable downstream compatibility from `raw_listings`

## Current Technical Limits

- no migration framework yet; additive schema changes rely on rerunning `initdb`
- only eBay is implemented as a collection source
- no scheduler built into the app
- trend monitoring is manual unless an external scheduler invokes commands
- supplier and competitor signals are still heuristic

## Recommended Extension Points

If extending the system:

- add new providers as separate source modules and separate CLI commands
- preserve the raw listing contract
- keep economic scoring deterministic
- keep enrichment optional and additive
- add tests around new source mapping and trend behavior
