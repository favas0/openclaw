from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ClusterResearchSignal, ProductCluster
from app.db.repositories._common import persist_row
from app.db.repositories.scoring import get_scored_clusters


def _safe_json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except Exception:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _safe_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except Exception:
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item).strip() for item in decoded if str(item).strip()]


def _flatten_signal_row(cluster: ProductCluster, signal: ClusterResearchSignal) -> dict[str, Any]:
    supplier_breakdown = _safe_json_dict(signal.supplier_breakdown_json)
    competitor_breakdown = _safe_json_dict(signal.competitor_breakdown_json)

    return {
        "cluster_id": cluster.id,
        "cluster_title": cluster.cluster_title,
        "source_name": cluster.source_name,
        "query": cluster.query,
        "supplier_intelligence_score": signal.supplier_intelligence_score,
        "ad_signal_score": signal.ad_signal_score,
        "competitor_saturation_score": signal.competitor_saturation_score,
        "multi_market_score": signal.multi_market_score,
        "trend_score": signal.trend_score,
        "handling_complexity_score": signal.handling_complexity_score,
        "supplier_search_query": signal.supplier_search_query,
        "supplier_terms_json": signal.supplier_terms_json,
        "supplier_terms": _safe_json_list(signal.supplier_terms_json),
        "supplier_breakdown_json": signal.supplier_breakdown_json,
        "supplier_breakdown": supplier_breakdown,
        "supplier_catalog_fit_score": supplier_breakdown.get("catalog_fit_score"),
        "supplier_shipping_profile_score": supplier_breakdown.get("shipping_profile_score"),
        "supplier_margin_support_score": supplier_breakdown.get("margin_support_score"),
        "supplier_evidence_score": supplier_breakdown.get("evidence_score"),
        "supplier_confidence_score": supplier_breakdown.get("confidence_score"),
        "supplier_strengths": supplier_breakdown.get("strengths") or [],
        "supplier_risks": supplier_breakdown.get("risks") or [],
        "supplier_notes": signal.supplier_notes,
        "ad_notes": signal.ad_notes,
        "competitor_breakdown_json": signal.competitor_breakdown_json,
        "competitor_breakdown": competitor_breakdown,
        "competitor_seller_pressure_score": competitor_breakdown.get("seller_pressure_score"),
        "competitor_listing_pressure_score": competitor_breakdown.get("listing_pressure_score"),
        "competitor_price_pressure_score": competitor_breakdown.get("price_pressure_score"),
        "competitor_market_maturity_score": competitor_breakdown.get("market_maturity_score"),
        "competitor_strengths": competitor_breakdown.get("strengths") or [],
        "competitor_risks": competitor_breakdown.get("risks") or [],
        "competitor_notes": signal.competitor_notes,
        "trend_notes": signal.trend_notes,
        "score_adjustment": signal.score_adjustment,
    }


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
    results = [_flatten_signal_row(cluster, signal) for cluster, signal in rows]
    if limit is not None:
        results = results[:limit]
    return results


def get_reporting_summary(
    db: Session,
    *,
    recommendation: str | None = None,
    source_name: str | None = None,
    query: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    scored_rows = get_scored_clusters(
        db,
        recommendation=recommendation,
        source_name=source_name,
        query=query,
        limit=None,
    )
    signal_rows = {row["cluster_id"]: row for row in get_research_signal_summary(db, limit=None)}

    results = [{**row, **signal_rows.get(row["cluster_id"], {})} for row in scored_rows]
    if limit is not None:
        results = results[:limit]
    return results


def get_cluster_comparison_rows(db: Session, cluster_ids: list[int]) -> list[dict]:
    reporting_rows = {row["cluster_id"]: row for row in get_reporting_summary(db, limit=None)}

    rows: list[dict] = []
    for cluster_id in cluster_ids:
        score_row = reporting_rows.get(cluster_id)
        if score_row:
            rows.append(score_row)
    return rows
