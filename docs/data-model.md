# OpenClaw Data Model

## Overview

OpenClaw stores pipeline state in SQLite. The schema is additive and stage-oriented: each pipeline stage writes a table that can be reused by later stages and reporting commands.

## Core Tables

### `ingestion_runs`

Tracks each collection run.

Important fields:

- `source_name`
- `query`
- `status`
- `listings_found`
- `notes`
- `started_at`
- `finished_at`

Use cases:

- operational audit trail
- debugging failed runs
- selecting runs for trend snapshots

### `raw_listings`

Stores source-native listing data in a shared downstream-compatible shape.

Important fields:

- `run_id`
- `source_name`
- `external_id`
- `query`
- `title`
- `price`
- `shipping_cost`
- `currency`
- `seller_name`
- `item_url`
- `image_url`
- `category`
- `condition`
- `is_sold_signal`
- `raw_payload`

Notes:

- `raw_payload` preserves provider-specific traceability
- downstream stages should not depend on arbitrary provider JSON outside mapping logic

### `normalized_listings`

Stores cleaned and derived listing features.

Important fields:

- `raw_listing_id`
- `normalized_title`
- `canonical_tokens`
- `total_price`
- `token_count`
- `has_brand_risk`
- `is_high_ticket_candidate`
- `cluster_id`

Invariant:

- one normalized row per raw listing

### `product_clusters`

Stores grouped product opportunities.

Important fields:

- `cluster_key`
- `cluster_title`
- `source_name`
- `query`
- `listing_count`
- `seller_count`
- `min_total_price`
- `max_total_price`
- `avg_total_price`
- `median_total_price`
- `high_ticket_count`
- `brand_risk_count`

Invariant:

- `cluster_key` is unique

### `cluster_enrichments`

Stores Ollama-generated structured product intelligence.

Important fields:

- `cluster_id`
- `product_type`
- `category_hint`
- `attributes_json`
- `buyer_intent`
- `visual_hook_score`
- `fragility_risk`
- `assembly_complexity`
- `supplier_search_terms_json`
- `confidence_score`
- `model_name`

Invariant:

- one enrichment row per cluster

### `cluster_scores`

Stores deterministic scoring and economics.

Important fields:

- `cluster_id`
- `demand_score`
- `sales_signal_score`
- `competition_score`
- `supplier_fit_score`
- `risk_score`
- `sell_price_estimate`
- `supplier_cost_estimate`
- `shipping_cost_estimate`
- `fees_estimate`
- `gross_profit_estimate`
- `max_cpa`
- `total_score`
- `recommendation`
- `notes`

Invariant:

- one score row per cluster

### `cluster_research_signals`

Stores secondary heuristic research signals.

Important fields:

- `supplier_intelligence_score`
- `ad_signal_score`
- `competitor_saturation_score`
- `multi_market_score`
- `trend_score`
- `handling_complexity_score`
- `supplier_search_query`
- `supplier_terms_json`
- `supplier_breakdown_json`
- `supplier_notes`
- `ad_notes`
- `competitor_breakdown_json`
- `competitor_notes`
- `trend_notes`
- `score_adjustment`

Invariant:

- one research signal row per cluster

### `cluster_score_snapshots`

Stores point-in-time score snapshots.

Important fields:

- `cluster_id`
- `source_name`
- `query`
- `total_score`
- `recommendation`
- `gross_profit_estimate`
- `max_cpa`

Use cases:

- score trend reporting
- tracking changes in recommendation and economics over time
- preserving query-series continuity even when the latest market snapshot has no active listings

### `cluster_market_snapshots`

Stores point-in-time market state snapshots tied to a specific ingestion run.

Important fields:

- `cluster_id`
- `run_id`
- `source_name`
- `query`
- `listing_count`
- `seller_count`
- `min_total_price`
- `max_total_price`
- `avg_total_price`
- `median_total_price`
- `external_ids_json`
- `seller_names_json`

Invariant:

- one market snapshot row per `cluster_id` and `run_id`

Use cases:

- real trend monitoring
- appearance/disappearance detection
- reappearance detection after zero-listing snapshots
- listing count drift
- seller count drift
- median price drift

## Relationship Flow

The main pipeline relationship is:

`ingestion_runs` -> `raw_listings` -> `normalized_listings` -> `product_clusters`

Then cluster-level outputs fan out into:

- `cluster_enrichments`
- `cluster_scores`
- `cluster_research_signals`
- `cluster_score_snapshots`
- `cluster_market_snapshots`

## Why The Shared Raw Shape Matters

Provider-specific ingestion stays isolated in source modules, but the rest of the pipeline depends on the same raw listing contract. That is what allows new sources to be added without redesigning normalization, clustering, scoring, and reporting.

## Operational Notes

- rerun `initdb` after additive schema changes
- current additive schema changes include query-aware score snapshots and structured research breakdown fields
- snapshot tables only become useful after repeated runs
- trend reports depend on both score snapshots and market snapshots
