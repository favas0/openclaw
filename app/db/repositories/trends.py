from __future__ import annotations

import json
from statistics import mean, median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ClusterMarketSnapshot, ClusterScoreSnapshot, NormalizedListing, ProductCluster, RawListing
from app.db.repositories._common import persist_row
from app.db.repositories.catalog import get_product_clusters


def clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def upsert_cluster_market_snapshot(
    db: Session,
    *,
    cluster_id: int,
    run_id: int,
    source_name: str,
    query: str,
    listing_count: int,
    seller_count: int,
    min_total_price: float | None,
    max_total_price: float | None,
    avg_total_price: float | None,
    median_total_price: float | None,
    external_ids_json: str | None = None,
    seller_names_json: str | None = None,
    auto_commit: bool = True,
) -> ClusterMarketSnapshot:
    stmt = select(ClusterMarketSnapshot).where(
        ClusterMarketSnapshot.cluster_id == cluster_id,
        ClusterMarketSnapshot.run_id == run_id,
    )
    existing = db.scalar(stmt)

    values = {
        "cluster_id": cluster_id,
        "run_id": run_id,
        "source_name": source_name,
        "query": query,
        "listing_count": listing_count,
        "seller_count": seller_count,
        "min_total_price": min_total_price,
        "max_total_price": max_total_price,
        "avg_total_price": avg_total_price,
        "median_total_price": median_total_price,
        "external_ids_json": external_ids_json,
        "seller_names_json": seller_names_json,
    }

    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        return persist_row(db, existing, auto_commit=auto_commit)

    row = ClusterMarketSnapshot(**values)
    return persist_row(db, row, auto_commit=auto_commit)


def get_run_cluster_market_rows(db: Session, *, run_id: int) -> list[dict]:
    stmt = (
        select(ProductCluster, NormalizedListing, RawListing)
        .join(NormalizedListing, NormalizedListing.cluster_id == ProductCluster.id)
        .join(RawListing, RawListing.id == NormalizedListing.raw_listing_id)
        .where(RawListing.run_id == run_id)
        .order_by(ProductCluster.id.asc(), RawListing.id.asc())
    )

    grouped: dict[int, dict] = {}
    for cluster, normalized, raw in db.execute(stmt).all():
        bucket = grouped.setdefault(
            cluster.id,
            {
                "cluster_id": cluster.id,
                "source_name": raw.source_name,
                "query": raw.query,
                "listing_count": 0,
                "seller_names": set(),
                "external_ids": set(),
                "total_prices": [],
            },
        )
        bucket["listing_count"] += 1

        if raw.seller_name:
            bucket["seller_names"].add(raw.seller_name)
        if raw.external_id:
            bucket["external_ids"].add(raw.external_id)
        if normalized.total_price is not None:
            bucket["total_prices"].append(normalized.total_price)

    results: list[dict] = []
    for row in grouped.values():
        total_prices = row["total_prices"]
        seller_names = sorted(row["seller_names"])
        external_ids = sorted(row["external_ids"])

        results.append(
            {
                "cluster_id": row["cluster_id"],
                "source_name": row["source_name"],
                "query": row["query"],
                "listing_count": row["listing_count"],
                "seller_count": len(seller_names),
                "min_total_price": min(total_prices) if total_prices else None,
                "max_total_price": max(total_prices) if total_prices else None,
                "avg_total_price": round(mean(total_prices), 2) if total_prices else None,
                "median_total_price": round(median(total_prices), 2) if total_prices else None,
                "external_ids_json": json.dumps(external_ids, ensure_ascii=False),
                "seller_names_json": json.dumps(seller_names, ensure_ascii=False),
            }
        )

    results.sort(key=lambda item: (-(item["listing_count"]), item["cluster_id"]))
    return results


def get_latest_market_snapshot_rows_for_query(
    db: Session,
    *,
    source_name: str,
    query: str,
    exclude_run_id: int | None = None,
) -> list[ClusterMarketSnapshot]:
    run_id_stmt = select(ClusterMarketSnapshot.run_id).where(
        ClusterMarketSnapshot.source_name == source_name,
        ClusterMarketSnapshot.query == query,
    )
    if exclude_run_id is not None:
        run_id_stmt = run_id_stmt.where(ClusterMarketSnapshot.run_id != exclude_run_id)

    latest_run_id = db.scalar(
        run_id_stmt.order_by(ClusterMarketSnapshot.captured_at.desc(), ClusterMarketSnapshot.run_id.desc()).limit(1)
    )
    if latest_run_id is None:
        return []

    stmt = (
        select(ClusterMarketSnapshot)
        .where(
            ClusterMarketSnapshot.source_name == source_name,
            ClusterMarketSnapshot.query == query,
            ClusterMarketSnapshot.run_id == latest_run_id,
        )
        .order_by(ClusterMarketSnapshot.cluster_id.asc())
    )
    return list(db.scalars(stmt).all())


def _normalized_filter(value: str | None) -> str | None:
    text = (value or "").strip().lower()
    return text or None


def _trend_sort_key(sort_by: str, row: dict) -> tuple:
    if sort_by == "recommendation-change":
        return (
            -(1 if row.get("recommendation_changed") else 0),
            -abs(row.get("score_delta") or 0.0),
            -abs(row.get("listing_count_delta") or 0),
            row["cluster_id"],
            row["query"],
        )

    if sort_by == "stable-supply-price":
        return (
            -(row.get("supply_stability_score") or 0.0),
            -abs(row.get("median_price_delta") or 0.0),
            -(row.get("market_snapshots") or 0),
            row["cluster_id"],
            row["query"],
        )

    if sort_by == "score":
        return (
            -abs(row.get("score_delta") or 0.0),
            -abs(row.get("listing_count_delta") or 0),
            -(row.get("latest_score") or 0.0),
            row["cluster_id"],
            row["query"],
        )

    if sort_by == "price":
        return (
            -abs(row.get("median_price_delta") or 0.0),
            -abs(row.get("listing_count_delta") or 0),
            -(row.get("latest_median_total_price") or 0.0),
            row["cluster_id"],
            row["query"],
        )

    if sort_by == "new-items":
        return (
            -(row.get("new_items_since_last_snapshot") or 0),
            -(row.get("removed_items_since_last_snapshot") or 0),
            -(row.get("latest_listing_count") or 0),
            row["cluster_id"],
            row["query"],
        )

    return (
        -abs(row.get("listing_count_delta") or 0),
        -abs(row.get("seller_count_delta") or 0),
        -(row.get("latest_listing_count") or 0),
        row["cluster_id"],
        row["query"],
    )


def _score_snapshot_series_key(
    snap: ClusterScoreSnapshot,
    cluster: ProductCluster | None,
) -> tuple[int, str, str]:
    source_name = _normalized_filter(getattr(snap, "source_name", None)) or _normalized_filter(
        getattr(cluster, "source_name", None)
    ) or ""
    query = _normalized_filter(getattr(snap, "query", None)) or _normalized_filter(
        getattr(cluster, "query", None)
    ) or ""
    return snap.cluster_id, source_name, query


def _supply_stability_score(
    *,
    first_listing_count: int,
    latest_listing_count: int,
    first_seller_count: int,
    latest_seller_count: int,
    new_items_since_last_snapshot: int,
    removed_items_since_last_snapshot: int,
) -> float:
    baseline_listing_count = max(first_listing_count, latest_listing_count, 1)
    turnover_ratio = (new_items_since_last_snapshot + removed_items_since_last_snapshot) / baseline_listing_count
    score = 10.0
    score -= min(abs(latest_listing_count - first_listing_count) * 1.2, 4.0)
    score -= min(abs(latest_seller_count - first_seller_count) * 1.5, 3.0)
    score -= min(turnover_ratio * 3.0, 3.0)
    return round(clamp(score, 0.0, 10.0), 2)


def get_cluster_trends(
    db: Session,
    *,
    limit: int = 20,
    source_name: str | None = None,
    query: str | None = None,
    sort_by: str = "movement",
    min_market_snapshots: int = 1,
    recommendation_changed_only: bool = False,
) -> list[dict]:
    cluster_map = {cluster.id: cluster for cluster in get_product_clusters(db)}
    normalized_source_name = _normalized_filter(source_name)
    normalized_query = _normalized_filter(query)
    market_snaps = list(
        db.scalars(
            select(ClusterMarketSnapshot).order_by(
                ClusterMarketSnapshot.cluster_id.asc(),
                ClusterMarketSnapshot.captured_at.asc(),
                ClusterMarketSnapshot.id.asc(),
            )
        ).all()
    )
    score_snaps = list(
        db.scalars(
            select(ClusterScoreSnapshot).order_by(
                ClusterScoreSnapshot.cluster_id.asc(),
                ClusterScoreSnapshot.captured_at.asc(),
                ClusterScoreSnapshot.id.asc(),
            )
        ).all()
    )

    market_map: dict[tuple[int, str, str], list[ClusterMarketSnapshot]] = {}
    for snap in market_snaps:
        snap_source_name = _normalized_filter(snap.source_name) or ""
        snap_query = _normalized_filter(snap.query) or ""

        if normalized_source_name and snap_source_name != normalized_source_name:
            continue
        if normalized_query and snap_query != normalized_query:
            continue

        market_map.setdefault((snap.cluster_id, snap_source_name, snap_query), []).append(snap)

    score_map: dict[tuple[int, str, str], list[ClusterScoreSnapshot]] = {}
    for snap in score_snaps:
        cluster = cluster_map.get(snap.cluster_id)
        score_map.setdefault(_score_snapshot_series_key(snap, cluster), []).append(snap)

    results: list[dict] = []
    for (cluster_id, _snap_source_name, _snap_query), snaps in market_map.items():
        cluster = cluster_map.get(cluster_id)
        if not cluster or not snaps:
            continue
        if len(snaps) < max(min_market_snapshots, 1):
            continue

        first = snaps[0]
        latest = snaps[-1]
        previous = snaps[-2] if len(snaps) >= 2 else None

        latest_ids = set(json.loads(latest.external_ids_json or "[]"))
        previous_ids = set(json.loads(previous.external_ids_json or "[]")) if previous else set()

        score_series = score_map.get((cluster_id, _snap_source_name, _snap_query), [])
        score_first = score_series[0] if score_series else None
        score_latest = score_series[-1] if score_series else None

        median_price_delta = None
        if first.median_total_price is not None and latest.median_total_price is not None:
            median_price_delta = round(latest.median_total_price - first.median_total_price, 2)

        new_items_since_last_snapshot = len(latest_ids - previous_ids) if previous else len(latest_ids)
        removed_items_since_last_snapshot = len(previous_ids - latest_ids) if previous else 0
        recommendation_changed = (
            bool(score_first and score_latest)
            and (score_first.recommendation or "") != (score_latest.recommendation or "")
        )
        if recommendation_changed_only and not recommendation_changed:
            continue

        supply_stability_score = _supply_stability_score(
            first_listing_count=first.listing_count,
            latest_listing_count=latest.listing_count,
            first_seller_count=first.seller_count,
            latest_seller_count=latest.seller_count,
            new_items_since_last_snapshot=new_items_since_last_snapshot,
            removed_items_since_last_snapshot=removed_items_since_last_snapshot,
        )

        results.append(
            {
                "cluster_id": cluster.id,
                "cluster_title": cluster.cluster_title,
                "source_name": latest.source_name,
                "query": latest.query,
                "market_snapshots": len(snaps),
                "first_run_id": first.run_id,
                "latest_run_id": latest.run_id,
                "first_listing_count": first.listing_count,
                "latest_listing_count": latest.listing_count,
                "listing_count_delta": latest.listing_count - first.listing_count,
                "first_seller_count": first.seller_count,
                "latest_seller_count": latest.seller_count,
                "seller_count_delta": latest.seller_count - first.seller_count,
                "first_median_total_price": first.median_total_price,
                "latest_median_total_price": latest.median_total_price,
                "median_price_delta": median_price_delta,
                "new_items_since_last_snapshot": new_items_since_last_snapshot,
                "removed_items_since_last_snapshot": removed_items_since_last_snapshot,
                "supply_stability_score": supply_stability_score,
                "score_snapshots": len(score_series),
                "first_score": score_first.total_score if score_first else None,
                "latest_score": score_latest.total_score if score_latest else None,
                "score_delta": round((score_latest.total_score or 0.0) - (score_first.total_score or 0.0), 2)
                if score_first and score_latest
                else None,
                "first_recommendation": score_first.recommendation if score_first else None,
                "latest_recommendation": score_latest.recommendation if score_latest else None,
                "recommendation_changed": recommendation_changed,
                "recommendation_change": (
                    f"{score_first.recommendation} -> {score_latest.recommendation}"
                    if recommendation_changed and score_first and score_latest
                    else None
                ),
                "latest_gross_profit_estimate": score_latest.gross_profit_estimate if score_latest else None,
                "latest_max_cpa": score_latest.max_cpa if score_latest else None,
                "latest_captured_at": latest.captured_at,
            }
        )

    results.sort(key=lambda row: _trend_sort_key(sort_by, row))
    return results[:limit]


def count_cluster_market_snapshots(db: Session) -> int:
    stmt = select(func.count()).select_from(ClusterMarketSnapshot)
    return db.execute(stmt).scalar_one()
