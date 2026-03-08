import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import (
    ClusterScore,
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
    notes: str | None = None,
) -> IngestionRun:
    run = IngestionRun(
        source_name=source_name,
        query=query,
        status=status,
        notes=notes,
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
    listings_found: int,
    notes: str | None = None,
) -> IngestionRun | None:
    run = db.get(IngestionRun, run_id)
    if not run:
        return None

    run.status = status
    run.listings_found = listings_found
    run.notes = notes
    run.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


def insert_raw_listing(
    db: Session,
    *,
    run_id: int,
    source_name: str,
    query: str,
    title: str,
    item_url: str,
    external_id: str | None = None,
    price: float | None = None,
    shipping_cost: float | None = None,
    currency: str | None = None,
    seller_name: str | None = None,
    seller_url: str | None = None,
    image_url: str | None = None,
    category: str | None = None,
    condition: str | None = None,
    is_sold_signal: bool = False,
    raw_payload: Any = None,
) -> RawListing:
    payload_text = None
    if raw_payload is not None:
        payload_text = json.dumps(raw_payload, ensure_ascii=False)

    listing = RawListing(
        run_id=run_id,
        source_name=source_name,
        external_id=external_id,
        query=query,
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
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def upsert_normalized_listing(
    db: Session,
    *,
    raw_listing_id: int,
    source_name: str,
    query: str,
    original_title: str,
    normalized_title: str,
    canonical_tokens: str,
    price: float | None,
    shipping_cost: float | None,
    total_price: float | None,
    currency: str | None,
    seller_name: str | None,
    category: str | None,
    condition: str | None,
    token_count: int,
    has_brand_risk: bool,
    is_high_ticket_candidate: bool,
) -> NormalizedListing:
    existing = db.execute(
        select(NormalizedListing).where(NormalizedListing.raw_listing_id == raw_listing_id)
    ).scalar_one_or_none()

    if existing:
        existing.source_name = source_name
        existing.query = query
        existing.original_title = original_title
        existing.normalized_title = normalized_title
        existing.canonical_tokens = canonical_tokens
        existing.price = price
        existing.shipping_cost = shipping_cost
        existing.total_price = total_price
        existing.currency = currency
        existing.seller_name = seller_name
        existing.category = category
        existing.condition = condition
        existing.token_count = token_count
        existing.has_brand_risk = has_brand_risk
        existing.is_high_ticket_candidate = is_high_ticket_candidate
        db.commit()
        db.refresh(existing)
        return existing

    row = NormalizedListing(
        raw_listing_id=raw_listing_id,
        source_name=source_name,
        query=query,
        original_title=original_title,
        normalized_title=normalized_title,
        canonical_tokens=canonical_tokens,
        price=price,
        shipping_cost=shipping_cost,
        total_price=total_price,
        currency=currency,
        seller_name=seller_name,
        category=category,
        condition=condition,
        token_count=token_count,
        has_brand_risk=has_brand_risk,
        is_high_ticket_candidate=is_high_ticket_candidate,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def upsert_product_cluster(
    db: Session,
    *,
    cluster_key: str,
    cluster_title: str,
    source_name: str,
    query: str,
    listing_count: int,
    seller_count: int,
    min_total_price: float | None,
    max_total_price: float | None,
    avg_total_price: float | None,
    median_total_price: float | None,
    high_ticket_count: int,
    brand_risk_count: int,
) -> ProductCluster:
    existing = db.execute(
        select(ProductCluster).where(ProductCluster.cluster_key == cluster_key)
    ).scalar_one_or_none()

    if existing:
        existing.cluster_title = cluster_title
        existing.source_name = source_name
        existing.query = query
        existing.listing_count = listing_count
        existing.seller_count = seller_count
        existing.min_total_price = min_total_price
        existing.max_total_price = max_total_price
        existing.avg_total_price = avg_total_price
        existing.median_total_price = median_total_price
        existing.high_ticket_count = high_ticket_count
        existing.brand_risk_count = brand_risk_count
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    row = ProductCluster(
        cluster_key=cluster_key,
        cluster_title=cluster_title,
        source_name=source_name,
        query=query,
        listing_count=listing_count,
        seller_count=seller_count,
        min_total_price=min_total_price,
        max_total_price=max_total_price,
        avg_total_price=avg_total_price,
        median_total_price=median_total_price,
        high_ticket_count=high_ticket_count,
        brand_risk_count=brand_risk_count,
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


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
    total_score: float,
    recommendation: str,
    notes: str | None,
) -> ClusterScore:
    existing = db.execute(
        select(ClusterScore).where(ClusterScore.cluster_id == cluster_id)
    ).scalar_one_or_none()

    if existing:
        existing.demand_score = demand_score
        existing.sales_signal_score = sales_signal_score
        existing.competition_score = competition_score
        existing.supplier_fit_score = supplier_fit_score
        existing.risk_score = risk_score
        existing.sell_price_estimate = sell_price_estimate
        existing.supplier_cost_estimate = supplier_cost_estimate
        existing.shipping_cost_estimate = shipping_cost_estimate
        existing.fees_estimate = fees_estimate
        existing.gross_profit_estimate = gross_profit_estimate
        existing.max_cpa = max_cpa
        existing.total_score = total_score
        existing.recommendation = recommendation
        existing.notes = notes
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    row = ClusterScore(
        cluster_id=cluster_id,
        demand_score=demand_score,
        sales_signal_score=sales_signal_score,
        competition_score=competition_score,
        supplier_fit_score=supplier_fit_score,
        risk_score=risk_score,
        sell_price_estimate=sell_price_estimate,
        supplier_cost_estimate=supplier_cost_estimate,
        shipping_cost_estimate=shipping_cost_estimate,
        fees_estimate=fees_estimate,
        gross_profit_estimate=gross_profit_estimate,
        max_cpa=max_cpa,
        total_score=total_score,
        recommendation=recommendation,
        notes=notes,
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_run_summary(db: Session) -> list[dict]:
    stmt = (
        select(
            IngestionRun.id,
            IngestionRun.source_name,
            IngestionRun.query,
            IngestionRun.status,
            IngestionRun.listings_found,
            IngestionRun.started_at,
            IngestionRun.finished_at,
        )
        .order_by(IngestionRun.id.desc())
    )

    rows = db.execute(stmt).all()
    return [
        {
            "id": row.id,
            "source_name": row.source_name,
            "query": row.query,
            "status": row.status,
            "listings_found": row.listings_found,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        }
        for row in rows
    ]


def get_raw_listings(db: Session) -> list[RawListing]:
    stmt = select(RawListing).order_by(RawListing.id.asc())
    return list(db.execute(stmt).scalars().all())


def get_normalized_listings(db: Session) -> list[NormalizedListing]:
    stmt = select(NormalizedListing).order_by(NormalizedListing.id.asc())
    return list(db.execute(stmt).scalars().all())


def get_product_clusters(db: Session) -> list[ProductCluster]:
    stmt = select(ProductCluster).order_by(ProductCluster.listing_count.desc(), ProductCluster.id.asc())
    return list(db.execute(stmt).scalars().all())


def get_cluster_summary(db: Session) -> list[dict]:
    stmt = select(ProductCluster).order_by(ProductCluster.listing_count.desc(), ProductCluster.id.asc())
    rows = db.execute(stmt).scalars().all()

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


def get_score_summary(db: Session) -> list[dict]:
    stmt = (
        select(ProductCluster, ClusterScore)
        .join(ClusterScore, ClusterScore.cluster_id == ProductCluster.id)
        .order_by(ClusterScore.total_score.desc(), ProductCluster.id.asc())
    )

    rows = db.execute(stmt).all()

    results = []
    for cluster, score in rows:
        results.append(
            {
                "cluster_id": cluster.id,
                "cluster_title": cluster.cluster_title,
                "listing_count": cluster.listing_count,
                "seller_count": cluster.seller_count,
                "median_total_price": cluster.median_total_price,
                "demand_score": score.demand_score,
                "sales_signal_score": score.sales_signal_score,
                "competition_score": score.competition_score,
                "supplier_fit_score": score.supplier_fit_score,
                "risk_score": score.risk_score,
                "gross_profit_estimate": score.gross_profit_estimate,
                "max_cpa": score.max_cpa,
                "total_score": score.total_score,
                "recommendation": score.recommendation,
                "notes": score.notes,
            }
        )
    return results


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
