from __future__ import annotations

import json
from datetime import datetime
from statistics import mean, median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ClusterMarketSnapshot,
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


def find_existing_raw_listing_in_run(
    db: Session,
    *,
    run_id: int,
    source_name: str,
    external_id: str | None = None,
    item_url: str | None = None,
    title: str | None = None,
    seller_name: str | None = None,
) -> RawListing | None:
    stmt = select(RawListing).where(
        RawListing.run_id == run_id,
        RawListing.source_name == source_name,
    )

    if external_id:
        stmt = stmt.where(RawListing.external_id == external_id)
    elif item_url:
        stmt = stmt.where(RawListing.item_url == item_url)
    elif title:
        stmt = stmt.where(RawListing.title == title)
        if seller_name:
            stmt = stmt.where(RawListing.seller_name == seller_name)
    else:
        return None

    return db.scalar(stmt.limit(1))


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
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = ClusterMarketSnapshot(**values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_ingestion_run(db: Session, run_id: int) -> IngestionRun | None:
    return db.get(IngestionRun, run_id)


def get_latest_completed_run(
    db: Session,
    *,
    source_name: str | None = None,
) -> IngestionRun | None:
    stmt = select(IngestionRun).where(IngestionRun.status == "completed")
    if source_name:
        stmt = stmt.where(IngestionRun.source_name == source_name)
    stmt = stmt.order_by(IngestionRun.finished_at.desc(), IngestionRun.id.desc())
    return db.scalar(stmt.limit(1))


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
    cluster_map = {cluster.id: cluster for cluster in get_product_clusters(db)}
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

    market_map: dict[int, list[ClusterMarketSnapshot]] = {}
    for snap in market_snaps:
        market_map.setdefault(snap.cluster_id, []).append(snap)

    score_map: dict[int, list[ClusterScoreSnapshot]] = {}
    for snap in score_snaps:
        score_map.setdefault(snap.cluster_id, []).append(snap)

    results: list[dict] = []

    for cluster_id, snaps in market_map.items():
        cluster = cluster_map.get(cluster_id)
        if not cluster or not snaps:
            continue

        first = snaps[0]
        latest = snaps[-1]
        previous = snaps[-2] if len(snaps) >= 2 else None

        latest_ids = set(json.loads(latest.external_ids_json or "[]"))
        previous_ids = set(json.loads(previous.external_ids_json or "[]")) if previous else set()

        score_series = score_map.get(cluster_id, [])
        score_first = score_series[0] if score_series else None
        score_latest = score_series[-1] if score_series else None

        median_price_delta = None
        if first.median_total_price is not None and latest.median_total_price is not None:
            median_price_delta = round(latest.median_total_price - first.median_total_price, 2)

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
                "new_items_since_last_snapshot": len(latest_ids - previous_ids) if previous else len(latest_ids),
                "removed_items_since_last_snapshot": len(previous_ids - latest_ids) if previous else 0,
                "score_snapshots": len(score_series),
                "first_score": score_first.total_score if score_first else None,
                "latest_score": score_latest.total_score if score_latest else None,
                "score_delta": round((score_latest.total_score or 0.0) - (score_first.total_score or 0.0), 2)
                if score_first and score_latest
                else None,
                "first_recommendation": score_first.recommendation if score_first else None,
                "latest_recommendation": score_latest.recommendation if score_latest else None,
                "latest_gross_profit_estimate": score_latest.gross_profit_estimate if score_latest else None,
                "latest_max_cpa": score_latest.max_cpa if score_latest else None,
                "latest_captured_at": latest.captured_at,
            }
        )

    results.sort(
        key=lambda row: (
            -abs(row["listing_count_delta"]),
            -abs(row["seller_count_delta"]),
            -(row["latest_listing_count"] or 0),
            row["cluster_id"],
        )
    )
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


def count_cluster_market_snapshots(db: Session) -> int:
    stmt = select(func.count()).select_from(ClusterMarketSnapshot)
    return db.execute(stmt).scalar_one()
