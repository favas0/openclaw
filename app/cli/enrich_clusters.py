from __future__ import annotations

import json

from sqlalchemy import text

from app.enrichment.cluster_enricher import ClusterEnricher


def run_enrich_clusters(session) -> dict:
    enricher = ClusterEnricher()

    rows = session.execute(
        text(
            """
            SELECT
                pc.id,
                pc.cluster_title,
                pc.median_total_price,
                pc.seller_count,
                pc.listing_count
            FROM product_clusters pc
            ORDER BY pc.id
            """
        )
    ).fetchall()

    processed = 0

    for row in rows:
        cluster_id = row.id
        cluster_title = row.cluster_title
        median_total_price = row.median_total_price
        seller_count = row.seller_count
        listing_count = row.listing_count

        sample_rows = session.execute(
            text(
                """
                SELECT nl.normalized_title
                FROM normalized_listings nl
                WHERE nl.cluster_id = :cluster_id
                LIMIT 5
                """
            ),
            {"cluster_id": cluster_id},
        ).fetchall()

        sample_titles = [r.normalized_title for r in sample_rows if r.normalized_title]

        result = enricher.enrich_cluster(
            cluster_title=cluster_title,
            median_price=median_total_price,
            seller_count=seller_count,
            listing_count=listing_count,
            sample_titles=sample_titles,
        )

        session.execute(
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
                "cluster_id": cluster_id,
                "product_type": result["product_type"],
                "category_hint": result["category_hint"],
                "attributes_json": json.dumps(result["attributes"], ensure_ascii=False, sort_keys=True),
                "buyer_intent": result["buyer_intent"],
                "visual_hook_score": result["visual_hook_score"],
                "fragility_risk": result["fragility_risk"],
                "assembly_complexity": result["assembly_complexity"],
                "supplier_search_terms_json": json.dumps(result["supplier_search_terms"], ensure_ascii=False, sort_keys=True),
                "confidence_score": result["confidence_score"],
                "model_name": "llama3.1:8b",
            },
        )

        processed += 1

    session.commit()
    return {"status": "completed", "clusters_enriched": processed}
