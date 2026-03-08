from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(50), index=True)
    query: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(30), default="started", index=True)
    listings_found: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    listings: Mapped[list["RawListing"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class RawListing(Base):
    __tablename__ = "raw_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"), index=True)

    source_name: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)

    query: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    shipping_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seller_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    item_url: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_sold_signal: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    run: Mapped["IngestionRun"] = relationship(back_populates="listings")
    normalized: Mapped["NormalizedListing | None"] = relationship(
        back_populates="raw_listing",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ProductCluster(Base):
    __tablename__ = "product_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cluster_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    cluster_title: Mapped[str] = mapped_column(Text, index=True)

    source_name: Mapped[str] = mapped_column(String(50), index=True)
    query: Mapped[str] = mapped_column(String(255), index=True)

    listing_count: Mapped[int] = mapped_column(Integer, default=0)
    seller_count: Mapped[int] = mapped_column(Integer, default=0)

    min_total_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_total_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_total_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_total_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    high_ticket_count: Mapped[int] = mapped_column(Integer, default=0)
    brand_risk_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    normalized_listings: Mapped[list["NormalizedListing"]] = relationship(
        back_populates="cluster"
    )


class NormalizedListing(Base):
    __tablename__ = "normalized_listings"
    __table_args__ = (
        UniqueConstraint("raw_listing_id", name="uq_normalized_raw_listing_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_listing_id: Mapped[int] = mapped_column(ForeignKey("raw_listings.id"), index=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("product_clusters.id"), index=True, nullable=True)

    source_name: Mapped[str] = mapped_column(String(50), index=True)
    query: Mapped[str] = mapped_column(String(255), index=True)

    original_title: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str] = mapped_column(Text, index=True)
    canonical_tokens: Mapped[str] = mapped_column(Text, index=True)

    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    shipping_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(100), nullable=True)

    token_count: Mapped[int] = mapped_column(Integer, default=0)
    has_brand_risk: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_high_ticket_candidate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    raw_listing: Mapped["RawListing"] = relationship(back_populates="normalized")
    cluster: Mapped["ProductCluster | None"] = relationship(back_populates="normalized_listings")
