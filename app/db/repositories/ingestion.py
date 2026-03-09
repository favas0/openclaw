from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import IngestionRun, RawListing
from app.db.repositories._common import persist_row, serialize_payload


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
    return persist_row(db, run, auto_commit=True)


def finish_ingestion_run(
    db: Session,
    *,
    run_id: int,
    status: str,
    listings_found: int = 0,
    notes: str | None = None,
    auto_commit: bool = True,
) -> IngestionRun | None:
    run = db.get(IngestionRun, run_id)
    if not run:
        return None

    run.status = status
    run.listings_found = listings_found
    run.notes = notes
    run.finished_at = datetime.utcnow()
    return persist_row(db, run, auto_commit=auto_commit)


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
    auto_commit: bool = True,
) -> RawListing:
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
        raw_payload=serialize_payload(raw_payload),
    )
    return persist_row(db, row, auto_commit=auto_commit)


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


def count_raw_listings(db: Session) -> int:
    stmt = select(func.count()).select_from(RawListing)
    return db.execute(stmt).scalar_one()
