from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import NormalizedListing, ProductCluster
from app.db.repositories._common import persist_row


def upsert_normalized_listing(
    db: Session,
    *,
    auto_commit: bool = True,
    **kwargs,
) -> NormalizedListing:
    raw_listing_id = kwargs["raw_listing_id"]
    stmt = select(NormalizedListing).where(
        NormalizedListing.raw_listing_id == raw_listing_id
    )
    existing = db.scalar(stmt)

    if existing:
        for key, value in kwargs.items():
            setattr(existing, key, value)
        return persist_row(db, existing, auto_commit=auto_commit)

    row = NormalizedListing(**kwargs)
    return persist_row(db, row, auto_commit=auto_commit)


def get_normalized_listings(db: Session) -> list[NormalizedListing]:
    stmt = select(NormalizedListing).order_by(NormalizedListing.id.asc())
    return list(db.scalars(stmt).all())


def upsert_product_cluster(
    db: Session,
    *,
    auto_commit: bool = True,
    **kwargs,
) -> ProductCluster:
    cluster_key = kwargs["cluster_key"]
    stmt = select(ProductCluster).where(ProductCluster.cluster_key == cluster_key)
    existing = db.scalar(stmt)

    if existing:
        for key, value in kwargs.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        return persist_row(db, existing, auto_commit=auto_commit)

    row = ProductCluster(**kwargs)
    return persist_row(db, row, auto_commit=auto_commit)


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
    auto_commit: bool = True,
) -> NormalizedListing | None:
    row = db.get(NormalizedListing, normalized_listing_id)
    if not row:
        return None

    row.cluster_id = cluster_id
    return persist_row(db, row, auto_commit=auto_commit)


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


def count_normalized_listings(db: Session) -> int:
    stmt = select(func.count()).select_from(NormalizedListing)
    return db.execute(stmt).scalar_one()


def count_product_clusters(db: Session) -> int:
    stmt = select(func.count()).select_from(ProductCluster)
    return db.execute(stmt).scalar_one()
