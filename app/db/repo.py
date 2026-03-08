from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ClusterResearchSignal,
    ClusterScore,
    ClusterScoreSnapshot,
    IngestionRun,
    NormalizedListing,
    ProductCluster,
    RawListing,
)


def create_ingestion_run(
    db: Session,
    *,
    source_name: str,
    query: str,
    status: str = "started",
) -> IngestionRun:
    run = IngestionRun(
        source_name=source_name,
        query=query,
        status=status,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_ingestion_run(
    db: Session,
    *,
    run_id: int,
    status: str,
    listings_found: int = 0,
    notes: str | None = None,
) -> IngestionRun | None:
    run = db.get(IngestionRun, run_id)
    if not run:
        return None

    run.status = status
    run.listings_found = listings_found
    run.notes = notes
    run.finished_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def insert_raw_listing(
    db: Session,
    *,
    run_id: int,
    source_name: str,
    query: str,
    external_id: str,
    title: str,
    price: float | None = None,
    shipping_cost: float | None = None,
    currency: str | None = None,
    seller_name: str | None = None,
    seller_url: str | None = None,
    item_url: str | None = None,
    image_url: str | None = None,
    category: str | None = None,
    condition: str | None = None,
    is_sold_signal: bool = False,
    raw_payload: dict | str | None = None,
) -> RawListing:
    payload_text: str | None

    if raw_payload is None:
        payload_text = None
    elif isinstance(raw_payload, str):
        payload_text = raw_payload
    else:
        payload_text = json.dumps(raw_payload, ensure_ascii=False)

    row = RawListing(
        run_id=run_id,
        source_name=source_name,
        query=query,
        external_id=external_id,
        title=title,
        price=price,
        shipping_cost=shipping_cost,
        currency=currency,
        seller_name=seller_name,
        seller_url=seller_url,
        item_url=item_url,
        image_url=image_url,
        category=category,
        condition=condition,
        is_sold_signal=is_sold_signal,
        raw_payload=payload_text,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_raw_listings(db: Session) -> list[RawListing]:
    stmt = select(RawListing).order_by(RawListing.id.asc())
    return list(db.scalars(stmt).all())


def upsert_normalized_listing(db: Session, **kwargs) -> NormalizedListing:
    raw_listing_id = kwargs["raw_listing_id"]

    stmt = select(NormalizedListing).where(
        NormalizedListing.raw_listing_id == raw_listing_id
    )
    existing = db.scalar(stmt)

    if existing:
        for key, value in kwargs.items():
            setattr(existing, key, value)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = NormalizedListing(**kwargs)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_normalized_listings(db: Session) -> list[NormalizedListing]:
    stmt = select(NormalizedListing).order_by(NormalizedListing.id.asc())
    return list(db.scalars(stmt).all())


def upsert_product_cluster(db: Session, **kwargs) -> ProductCluster:
    cluster_key = kwargs["cluster_key"]

    stmt = select(ProductCluster).where(ProductCluster.cluster_key == cluster_key)
    existing = db.scalar(stmt)

    if existing:
        for key, value in kwargs.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = ProductCluster(**kwargs)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_product_clusters(db: Session) -> list[ProductCluster]:
    stmt = select(ProductCluster).order_by(
        ProductCluster.listing_count.desc(),
        ProductCluster.id.asc(),
    )
    return list(db.scalars(stmt).all())


def assign_listing_to_cluster(
    db: Session,
    *,
    normalized_listing_id: int,
    cluster_id: int,
) -> NormalizedListing | None:
    row = db.get(NormalizedListing, normalized_listing_id)
    if not row:
        return None

    row.cluster_id = cluster_id
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def upsert_cluster_score(
    db: Session,
    *,
    cluster_id: int,
    demand_score: float,
    sales_signal_score: float,
    competition_score: float,
    supplier_fit_score: float,
    risk_score: float,
    sell_price_estimate: float | None,
    supplier_cost_estimate: float | None,
    shipping_cost_estimate: float | None,
    fees_estimate: float | None,
    gross_profit_estimate: float | None,
    max_cpa: float | None,
    visual_hook_score: int = 0,
    fragility_risk: int = 0,
    assembly_complexity: int = 0,
    confidence_score: int = 0,
    enrichment_adjustment: float = 0.0,
    base_total_score: float = 0.0,
    total_score: float = 0.0,
    recommendation: str = "watch",
    notes: str | None = None,
) -> ClusterScore:
    stmt = select(ClusterScore).where(ClusterScore.cluster_id == cluster_id)
    existing = db.scalar(stmt)

    values = {
        "cluster_id": cluster_id,
        "demand_score": demand_score,
        "sales_signal_score": sales_signal_score,
        "competition_score": competition_score,
        "supplier_fit_score": supplier_fit_score,
        "risk_score": risk_score,
        "sell_price_estimate": sell_price_estimate,
        "supplier_cost_estimate": supplier_cost_estimate,
        "shipping_cost_estimate": shipping_cost_estimate,
        "fees_estimate": fees_estimate,
        "gross_profit_estimate": gross_profit_estimate,
        "max_cpa": max_cpa,
        "visual_hook_score": visual_hook_score,
        "fragility_risk": fragility_risk,
        "assembly_complexity": assembly_complexity,
        "confidence_score": confidence_score,
        "enrichment_adjustment": enrichment_adjustment,
        "base_total_score": base_total_score,
        "total_score": total_score,
        "recommendation": recommendation,
        "notes": notes,
    }

    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = ClusterScore(**values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def upsert_cluster_research_signal(db: Session, **kwargs) -> ClusterResearchSignal:
    cluster_id = kwargs["cluster_id"]
    stmt = select(ClusterResearchSignal).where(ClusterResearchSignal.cluster_id == cluster_id)
    existing = db.scalar(stmt)

    if existing:
        for key, value in kwargs.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = ClusterResearchSignal(**kwargs)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def insert_score_snapshot(
    db: Session,
    *,
    cluster_id: int,
    total_score: float,
    recommendation: str | None,
    gross_profit_estimate: float | None,
    max_cpa: float | None,
) -> ClusterScoreSnapshot:
    row = ClusterScoreSnapshot(
        cluster_id=cluster_id,
        total_score=total_score,
        recommendation=recommendation,
        gross_profit_estimate=gross_profit_estimate,
        max_cpa=max_cpa,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_run_summary(db: Session) -> list[dict]:
    stmt = select(IngestionRun).order_by(IngestionRun.id.desc())
    rows = db.scalars(stmt).all()

    return [
        {
            "id": row.id,
            "source_name": row.source_name,
            "query": row.query,
            "status": row.status,
            "listings_found": row.listings_found,
            "notes": row.notes,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
        }
        for row in rows
    ]


def get_cluster_summary(db: Session) -> list[dict]:
    stmt = select(ProductCluster).order_by(
        ProductCluster.listing_count.desc(),
        ProductCluster.id.asc(),
    )
    rows = db.scalars(stmt).all()

    return [
        {
            "id": row.id,
            "cluster_key": row.cluster_key,
            "cluster_title": row.cluster_title,
            "source_name": row.source_name,
            "query": row.query,
            "listing_count": row.listing_count,
            "seller_count": row.seller_count,
            "min_total_price": row.min_total_price,
            "max_total_price": row.max_total_price,
            "avg_total_price": row.avg_total_price,
            "median_total_price": row.median_total_price,
            "high_ticket_count": row.high_ticket_count,
            "brand_risk_count": row.brand_risk_count,
        }
        for row in rows
    ]


def get_scored_clusters(
    db: Session,
    *,
    recommendation: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    stmt = (
        select(ProductCluster, ClusterScore)
        .join(ClusterScore, ClusterScore.cluster_id == ProductCluster.id)
        .order_by(
            ClusterScore.total_score.desc(),
            ClusterScore.gross_profit_estimate.desc(),
            ProductCluster.listing_count.desc(),
            ProductCluster.id.asc(),
        )
    )

    rows = db.execute(stmt).all()

    results: list[dict] = []
    for cluster, score in rows:
        item = {
            "cluster_id": cluster.id,
            "cluster_title": cluster.cluster_title,
            "query": cluster.query,
            "listing_count": cluster.listing_count,
            "seller_count": cluster.seller_count,
            "median_total_price": cluster.median_total_price,
            "demand_score": score.demand_score,
            "sales_signal_score": score.sales_signal_score,
            "competition_score": score.competition_score,
            "supplier_fit_score": score.supplier_fit_score,
            "risk_score": score.risk_score,
            "sell_price_estimate": score.sell_price_estimate,
            "supplier_cost_estimate": score.supplier_cost_estimate,
            "shipping_cost_estimate": score.shipping_cost_estimate,
            "fees_estimate": score.fees_estimate,
            "gross_profit_estimate": score.gross_profit_estimate,
            "max_cpa": score.max_cpa,
            "visual_hook_score": score.visual_hook_score,
            "fragility_risk": score.fragility_risk,
            "assembly_complexity": score.assembly_complexity,
            "confidence_score": score.confidence_score,
            "enrichment_adjustment": score.enrichment_adjustment,
            "base_total_score": score.base_total_score,
            "total_score": score.total_score,
            "recommendation": score.recommendation,
            "notes": score.notes,
        }
        results.append(item)

    if recommendation:
        recommendation = recommendation.strip().lower()
        results = [
            row
            for row in results
            if str(row.get("recommendation", "")).strip().lower() == recommendation
        ]

    if limit is not None:
        results = results[:limit]

    return results


def get_research_signal_summary(db: Session, *, limit: int | None = None) -> list[dict]:
    stmt = (
        select(ProductCluster, ClusterResearchSignal)
        .join(ClusterResearchSignal, ClusterResearchSignal.cluster_id == ProductCluster.id)
        .order_by(
            ClusterResearchSignal.score_adjustment.desc(),
            ClusterResearchSignal.supplier_intelligence_score.desc(),
            ProductCluster.id.asc(),
        )
    )
    rows = db.execute(stmt).all()
    results = [
        {
            "cluster_id": cluster.id,
            "cluster_title": cluster.cluster_title,
            "query": cluster.query,
            "supplier_intelligence_score": signal.supplier_intelligence_score,
            "ad_signal_score": signal.ad_signal_score,
            "competitor_saturation_score": signal.competitor_saturation_score,
            "multi_market_score": signal.multi_market_score,
            "trend_score": signal.trend_score,
            "handling_complexity_score": signal.handling_complexity_score,
            "supplier_search_query": signal.supplier_search_query,
            "supplier_terms_json": signal.supplier_terms_json,
            "supplier_notes": signal.supplier_notes,
            "ad_notes": signal.ad_notes,
            "competitor_notes": signal.competitor_notes,
            "trend_notes": signal.trend_notes,
            "score_adjustment": signal.score_adjustment,
        }
        for cluster, signal in rows
    ]
    if limit is not None:
        results = results[:limit]
    return results


def get_cluster_comparison_rows(db: Session, cluster_ids: list[int]) -> list[dict]:
    scored = {row["cluster_id"]: row for row in get_scored_clusters(db, limit=None)}
    signals = {row["cluster_id"]: row for row in get_research_signal_summary(db, limit=None)}

    rows: list[dict] = []
    for cluster_id in cluster_ids:
        score_row = scored.get(cluster_id)
        if not score_row:
            continue
        signal_row = signals.get(cluster_id, {})
        rows.append({**score_row, **signal_row})
    return rows


def get_cluster_trends(db: Session, *, limit: int = 20) -> list[dict]:
    clusters = get_scored_clusters(db, limit=None)
    results: list[dict] = []

    for cluster in clusters:
        stmt = (
            select(ClusterScoreSnapshot)
            .where(ClusterScoreSnapshot.cluster_id == cluster["cluster_id"])
            .order_by(ClusterScoreSnapshot.captured_at.asc(), ClusterScoreSnapshot.id.asc())
        )
        snaps = list(db.scalars(stmt).all())
        if not snaps:
            continue

        first = snaps[0]
        latest = snaps[-1]
        results.append(
            {
                "cluster_id": cluster["cluster_id"],
                "cluster_title": cluster["cluster_title"],
                "snapshots": len(snaps),
                "first_score": first.total_score,
                "latest_score": latest.total_score,
                "score_delta": round((latest.total_score or 0.0) - (first.total_score or 0.0), 2),
                "first_recommendation": first.recommendation,
                "latest_recommendation": latest.recommendation,
                "latest_gross_profit_estimate": latest.gross_profit_estimate,
                "latest_max_cpa": latest.max_cpa,
                "latest_captured_at": latest.captured_at,
            }
        )

    results.sort(key=lambda row: (-(row["score_delta"]), -(row["latest_score"]), row["cluster_id"]))
    return results[:limit]


def get_score_summary(
    db: Session,
    *,
    recommendation: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    return get_scored_clusters(
        db,
        recommendation=recommendation,
        limit=limit,
    )


def count_raw_listings(db: Session) -> int:
    stmt = select(func.count()).select_from(RawListing)
    return db.execute(stmt).scalar_one()


def count_normalized_listings(db: Session) -> int:
    stmt = select(func.count()).select_from(NormalizedListing)
    return db.execute(stmt).scalar_one()


def count_product_clusters(db: Session) -> int:
    stmt = select(func.count()).select_from(ProductCluster)
    return db.execute(stmt).scalar_one()


def count_cluster_scores(db: Session) -> int:
    stmt = select(func.count()).select_from(ClusterScore)
    return db.execute(stmt).scalar_one()
