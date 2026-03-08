import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import IngestionRun, NormalizedListing, RawListing


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


def count_raw_listings(db: Session) -> int:
    stmt = select(func.count()).select_from(RawListing)
    return db.execute(stmt).scalar_one()


def count_normalized_listings(db: Session) -> int:
    stmt = select(func.count()).select_from(NormalizedListing)
    return db.execute(stmt).scalar_one()
