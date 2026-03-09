from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ClusterScore, ClusterScoreSnapshot, ProductCluster
from app.db.repositories._common import persist_row


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
    auto_commit: bool = True,
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
        return persist_row(db, existing, auto_commit=auto_commit)

    row = ClusterScore(**values)
    return persist_row(db, row, auto_commit=auto_commit)


def insert_score_snapshot(
    db: Session,
    *,
    cluster_id: int,
    source_name: str | None = None,
    query: str | None = None,
    total_score: float,
    recommendation: str | None,
    gross_profit_estimate: float | None,
    max_cpa: float | None,
    auto_commit: bool = True,
) -> ClusterScoreSnapshot:
    row = ClusterScoreSnapshot(
        cluster_id=cluster_id,
        source_name=source_name,
        query=query,
        total_score=total_score,
        recommendation=recommendation,
        gross_profit_estimate=gross_profit_estimate,
        max_cpa=max_cpa,
    )
    return persist_row(db, row, auto_commit=auto_commit)


def get_scored_clusters(
    db: Session,
    *,
    recommendation: str | None = None,
    source_name: str | None = None,
    query: str | None = None,
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
        results.append(
            {
                "cluster_id": cluster.id,
                "cluster_title": cluster.cluster_title,
                "source_name": cluster.source_name,
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
        )

    if recommendation:
        recommendation = recommendation.strip().lower()
        results = [
            row
            for row in results
            if str(row.get("recommendation", "")).strip().lower() == recommendation
        ]

    if source_name:
        normalized_source_name = source_name.strip().lower()
        results = [
            row
            for row in results
            if str(row.get("source_name", "")).strip().lower() == normalized_source_name
        ]

    if query:
        normalized_query = query.strip().lower()
        results = [
            row
            for row in results
            if str(row.get("query", "")).strip().lower() == normalized_query
        ]

    if limit is not None:
        results = results[:limit]

    return results


def get_score_summary(
    db: Session,
    *,
    recommendation: str | None = None,
    source_name: str | None = None,
    query: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    return get_scored_clusters(
        db,
        recommendation=recommendation,
        source_name=source_name,
        query=query,
        limit=limit,
    )


def count_cluster_scores(db: Session) -> int:
    stmt = select(func.count()).select_from(ClusterScore)
    return db.execute(stmt).scalar_one()
