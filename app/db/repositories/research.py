from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ClusterResearchSignal, ProductCluster
from app.db.repositories._common import persist_row
from app.db.repositories.scoring import get_scored_clusters


def upsert_cluster_research_signal(
    db: Session,
    *,
    auto_commit: bool = True,
    **kwargs,
) -> ClusterResearchSignal:
    cluster_id = kwargs["cluster_id"]
    stmt = select(ClusterResearchSignal).where(ClusterResearchSignal.cluster_id == cluster_id)
    existing = db.scalar(stmt)

    if existing:
        for key, value in kwargs.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        return persist_row(db, existing, auto_commit=auto_commit)

    row = ClusterResearchSignal(**kwargs)
    return persist_row(db, row, auto_commit=auto_commit)


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
