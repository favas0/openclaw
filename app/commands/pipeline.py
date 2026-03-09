import json
from types import SimpleNamespace

import typer
from sqlalchemy import text

from app.cluster.cluster_products import build_clusters
from app.commands.shared import print_json
from app.db.database import SessionLocal
from app.db.repo import (
    assign_listing_to_cluster,
    create_ingestion_run,
    find_existing_raw_listing_in_run,
    finish_ingestion_run,
    get_normalized_listings,
    get_product_clusters,
    get_raw_listings,
    insert_raw_listing,
    upsert_cluster_research_signal,
    upsert_cluster_score,
    upsert_normalized_listing,
    upsert_product_cluster,
)
from app.enrichment.cluster_enricher import ClusterEnricher
from app.normalize.processor import normalize_raw_listing
from app.research.signals import build_research_signal
from app.scoring.cluster_scoring import score_cluster
from app.sources.ebay import get_demo_items, map_demo_item_to_raw_listing
from app.sources.ebay_api import EbayBrowseApiClient, extract_item_summaries, map_api_item_to_raw_listing


def register_pipeline_commands(app: typer.Typer) -> None:
    @app.command("collect-ebay")
    def collect_ebay(
        query: str = typer.Argument(..., help="Search query, e.g. 'walking pad'"),
        limit: int = typer.Option(20, "--limit", "-l", min=1, max=100),
        use_demo: bool = typer.Option(False, "--demo", help="Use built-in demo data"),
        use_api: bool = typer.Option(False, "--api", help="Use the official eBay Browse API"),
        marketplace_id: str | None = typer.Option(
            None,
            "--marketplace-id",
            help="Optional eBay marketplace ID override, e.g. EBAY_GB",
        ),
    ):
        if use_demo and use_api:
            raise typer.BadParameter("Use either --demo or --api, not both")

        client = EbayBrowseApiClient()
        active_marketplace_id = client.resolve_marketplace_id(marketplace_id)

        with SessionLocal() as db:
            run = create_ingestion_run(
                db,
                source_name="ebay",
                query=query,
                status="started",
            )

            try:
                if use_demo:
                    items = get_demo_items(query)[:limit]
                    notes = "Demo mode used"
                    mode = "demo"
                elif use_api:
                    payload = client.search_items(
                        query=query,
                        limit=limit,
                        marketplace_id=active_marketplace_id,
                    )
                    items = extract_item_summaries(payload)
                    notes = f"Official eBay Browse API used (marketplace={active_marketplace_id})"
                    mode = "api"
                elif client.has_credentials():
                    payload = client.search_items(
                        query=query,
                        limit=limit,
                        marketplace_id=active_marketplace_id,
                    )
                    items = extract_item_summaries(payload)
                    notes = f"Official eBay Browse API used (marketplace={active_marketplace_id})"
                    mode = "api"
                else:
                    items = get_demo_items(query)[:limit]
                    notes = "Demo mode used (missing eBay API credentials)"
                    mode = "demo"

                inserted = 0
                duplicates_skipped = 0
                for item in items:
                    if mode == "api":
                        mapped = map_api_item_to_raw_listing(
                            item,
                            query=query,
                            marketplace_id=active_marketplace_id,
                        )
                    else:
                        mapped = map_demo_item_to_raw_listing(item, query=query)

                    existing = find_existing_raw_listing_in_run(
                        db,
                        run_id=run.id,
                        source_name=mapped["source_name"],
                        external_id=mapped.get("external_id"),
                        item_url=mapped.get("item_url"),
                        title=mapped.get("title"),
                        seller_name=mapped.get("seller_name"),
                    )
                    if existing:
                        duplicates_skipped += 1
                        continue

                    insert_raw_listing(
                        db,
                        run_id=run.id,
                        source_name=mapped["source_name"],
                        query=mapped["query"],
                        title=mapped["title"],
                        item_url=mapped["item_url"],
                        external_id=mapped["external_id"],
                        price=mapped["price"],
                        shipping_cost=mapped["shipping_cost"],
                        currency=mapped["currency"],
                        seller_name=mapped["seller_name"],
                        seller_url=mapped["seller_url"],
                        image_url=mapped["image_url"],
                        category=mapped["category"],
                        condition=mapped["condition"],
                        is_sold_signal=mapped["is_sold_signal"],
                        raw_payload=mapped["raw_payload"],
                        auto_commit=False,
                    )
                    inserted += 1

                db.commit()

                finish_ingestion_run(
                    db,
                    run_id=run.id,
                    status="completed",
                    listings_found=inserted,
                    notes=f"{notes}; duplicates_skipped={duplicates_skipped}",
                    auto_commit=True,
                )

                print_json(
                    {
                        "status": "completed",
                        "query": query,
                        "inserted": inserted,
                        "duplicates_skipped": duplicates_skipped,
                        "mode": mode,
                        "marketplace_id": active_marketplace_id,
                        "notes": notes,
                    }
                )
            except Exception as exc:
                db.rollback()
                finish_ingestion_run(
                    db,
                    run_id=run.id,
                    status="failed",
                    listings_found=0,
                    notes=str(exc),
                )
                raise typer.Exit(code=1) from exc

    @app.command("normalize-listings")
    def normalize_listings():
        with SessionLocal() as db:
            raw_listings = get_raw_listings(db)
            processed = 0

            for raw in raw_listings:
                norm = normalize_raw_listing(raw)
                upsert_normalized_listing(db, auto_commit=False, **norm)
                processed += 1

            db.commit()

            print_json(
                {
                    "status": "completed",
                    "raw_seen": len(raw_listings),
                    "normalized_written": processed,
                }
            )

    @app.command("cluster-products")
    def cluster_products():
        with SessionLocal() as db:
            normalized_rows = get_normalized_listings(db)
            clusters = build_clusters(normalized_rows)

            for cluster in clusters:
                cluster_row = upsert_product_cluster(
                    db,
                    cluster_key=cluster["cluster_key"],
                    cluster_title=cluster["cluster_title"],
                    source_name=cluster["source_name"],
                    query=cluster["query"],
                    listing_count=cluster["listing_count"],
                    seller_count=cluster["seller_count"],
                    min_total_price=cluster["min_total_price"],
                    max_total_price=cluster["max_total_price"],
                    avg_total_price=cluster["avg_total_price"],
                    median_total_price=cluster["median_total_price"],
                    high_ticket_count=cluster["high_ticket_count"],
                    brand_risk_count=cluster["brand_risk_count"],
                    auto_commit=False,
                )

                for normalized_listing_id in cluster["normalized_listing_ids"]:
                    assign_listing_to_cluster(
                        db,
                        normalized_listing_id=normalized_listing_id,
                        cluster_id=cluster_row.id,
                        auto_commit=False,
                    )

            db.commit()

            print_json(
                {
                    "status": "completed",
                    "normalized_seen": len(normalized_rows),
                    "clusters_written": len(clusters),
                }
            )

    @app.command("score-products")
    def score_products():
        with SessionLocal() as db:
            clusters = get_product_clusters(db)

            enrichment_rows = db.execute(
                text(
                    """
                    SELECT
                        cluster_id,
                        visual_hook_score,
                        fragility_risk,
                        assembly_complexity,
                        confidence_score
                    FROM cluster_enrichments
                    """
                )
            ).fetchall()

            enrichment_map = {row.cluster_id: row for row in enrichment_rows}
            written = 0

            for cluster in clusters:
                enrichment = enrichment_map.get(cluster.id)

                cluster_payload = {
                    "id": getattr(cluster, "id", None),
                    "cluster_title": getattr(cluster, "cluster_title", ""),
                    "listing_count": getattr(cluster, "listing_count", 0),
                    "seller_count": getattr(cluster, "seller_count", 0),
                    "min_total_price": getattr(cluster, "min_total_price", None),
                    "max_total_price": getattr(cluster, "max_total_price", None),
                    "median_total_price": getattr(cluster, "median_total_price", None),
                    "brand_risk_count": getattr(cluster, "brand_risk_count", 0),
                    "visual_hook_score": getattr(enrichment, "visual_hook_score", 0) if enrichment else 0,
                    "fragility_risk": getattr(enrichment, "fragility_risk", 0) if enrichment else 0,
                    "assembly_complexity": getattr(enrichment, "assembly_complexity", 0) if enrichment else 0,
                    "confidence_score": getattr(enrichment, "confidence_score", 0) if enrichment else 0,
                }

                score = score_cluster(SimpleNamespace(**cluster_payload))
                upsert_cluster_score(
                    db,
                    cluster_id=cluster.id,
                    demand_score=score["demand_score"],
                    sales_signal_score=score["sales_signal_score"],
                    competition_score=score["competition_score"],
                    supplier_fit_score=score["supplier_fit_score"],
                    risk_score=score["risk_score"],
                    sell_price_estimate=score["sell_price_estimate"],
                    supplier_cost_estimate=score["supplier_cost_estimate"],
                    shipping_cost_estimate=score["shipping_cost_estimate"],
                    fees_estimate=score["fees_estimate"],
                    gross_profit_estimate=score["gross_profit_estimate"],
                    max_cpa=score["max_cpa"],
                    visual_hook_score=score.get("visual_hook_score", 0),
                    fragility_risk=score.get("fragility_risk", 0),
                    assembly_complexity=score.get("assembly_complexity", 0),
                    confidence_score=score.get("confidence_score", 0),
                    enrichment_adjustment=score.get("enrichment_adjustment", 0.0),
                    base_total_score=score.get("base_total_score", score["total_score"]),
                    total_score=score["total_score"],
                    recommendation=score["recommendation"],
                    notes=score["notes"],
                    auto_commit=False,
                )
                written += 1

            db.commit()
            print_json({"status": "completed", "clusters_scored": written})

    @app.command("enrich-clusters")
    def enrich_clusters(
        limit: int = typer.Option(0, "--limit", min=0, help="Optional limit of clusters to enrich"),
    ):
        with SessionLocal() as db:
            enricher = ClusterEnricher()

            query_sql = """
                SELECT
                    pc.id,
                    pc.cluster_title,
                    pc.median_total_price,
                    pc.seller_count,
                    pc.listing_count
                FROM product_clusters pc
                ORDER BY pc.id ASC
            """

            if limit and limit > 0:
                query_sql += " LIMIT :limit"
                rows = db.execute(text(query_sql), {"limit": limit}).fetchall()
            else:
                rows = db.execute(text(query_sql)).fetchall()

            processed = 0

            for row in rows:
                sample_rows = db.execute(
                    text(
                        """
                        SELECT nl.normalized_title
                        FROM normalized_listings nl
                        WHERE nl.cluster_id = :cluster_id
                        ORDER BY nl.id ASC
                        LIMIT 5
                        """
                    ),
                    {"cluster_id": row.id},
                ).fetchall()

                sample_titles = [r.normalized_title for r in sample_rows if r.normalized_title]

                result = enricher.enrich_cluster(
                    cluster_title=row.cluster_title,
                    median_price=row.median_total_price,
                    seller_count=row.seller_count,
                    listing_count=row.listing_count,
                    sample_titles=sample_titles,
                )

                db.execute(
                    text(
                        """
                        INSERT INTO cluster_enrichments (
                            cluster_id,
                            product_type,
                            category_hint,
                            attributes_json,
                            buyer_intent,
                            visual_hook_score,
                            fragility_risk,
                            assembly_complexity,
                            supplier_search_terms_json,
                            confidence_score,
                            model_name
                        )
                        VALUES (
                            :cluster_id,
                            :product_type,
                            :category_hint,
                            :attributes_json,
                            :buyer_intent,
                            :visual_hook_score,
                            :fragility_risk,
                            :assembly_complexity,
                            :supplier_search_terms_json,
                            :confidence_score,
                            :model_name
                        )
                        ON CONFLICT(cluster_id) DO UPDATE SET
                            product_type = excluded.product_type,
                            category_hint = excluded.category_hint,
                            attributes_json = excluded.attributes_json,
                            buyer_intent = excluded.buyer_intent,
                            visual_hook_score = excluded.visual_hook_score,
                            fragility_risk = excluded.fragility_risk,
                            assembly_complexity = excluded.assembly_complexity,
                            supplier_search_terms_json = excluded.supplier_search_terms_json,
                            confidence_score = excluded.confidence_score,
                            model_name = excluded.model_name
                        """
                    ),
                    {
                        "cluster_id": row.id,
                        "product_type": result["product_type"],
                        "category_hint": result["category_hint"],
                        "attributes_json": enricher.to_json_text(result["attributes"]),
                        "buyer_intent": result["buyer_intent"],
                        "visual_hook_score": result["visual_hook_score"],
                        "fragility_risk": result["fragility_risk"],
                        "assembly_complexity": result["assembly_complexity"],
                        "supplier_search_terms_json": enricher.to_json_text(result["supplier_search_terms"]),
                        "confidence_score": result["confidence_score"],
                        "model_name": enricher.ollama.model,
                    },
                )

                processed += 1

            db.commit()
            print_json({"status": "completed", "clusters_enriched": processed})

    @app.command("research-signals")
    def research_signals(
        limit: int = typer.Option(0, "--limit", min=0, help="Optional limit of clusters to analyse"),
    ):
        with SessionLocal() as db:
            clusters = get_product_clusters(db)

            enrichment_rows = db.execute(
                text(
                    """
                    SELECT
                        cluster_id,
                        category_hint,
                        buyer_intent,
                        visual_hook_score,
                        fragility_risk,
                        assembly_complexity,
                        supplier_search_terms_json,
                        confidence_score
                    FROM cluster_enrichments
                    """
                )
            ).fetchall()
            enrichment_map = {row.cluster_id: row for row in enrichment_rows}

            written = 0
            for cluster in clusters[: limit or None]:
                enrichment = enrichment_map.get(cluster.id)
                signal = build_research_signal(cluster, enrichment)
                upsert_cluster_research_signal(
                    db,
                    cluster_id=cluster.id,
                    supplier_intelligence_score=signal["supplier_intelligence_score"],
                    ad_signal_score=signal["ad_signal_score"],
                    competitor_saturation_score=signal["competitor_saturation_score"],
                    multi_market_score=signal["multi_market_score"],
                    trend_score=signal["trend_score"],
                    handling_complexity_score=signal["handling_complexity_score"],
                    supplier_search_query=signal["supplier_search_query"],
                    supplier_terms_json=json.dumps(signal["supplier_terms"], ensure_ascii=False),
                    supplier_breakdown_json=json.dumps(signal["supplier_breakdown"], ensure_ascii=False),
                    supplier_notes=signal["supplier_notes"],
                    ad_notes=signal["ad_notes"],
                    competitor_breakdown_json=json.dumps(signal["competitor_breakdown"], ensure_ascii=False),
                    competitor_notes=signal["competitor_notes"],
                    trend_notes=signal["trend_notes"],
                    score_adjustment=signal["score_adjustment"],
                    auto_commit=False,
                )
                written += 1

            db.commit()
            print_json({"status": "completed", "research_signals_written": written})
