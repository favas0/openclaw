from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repo import (
    get_ingestion_run,
    get_latest_completed_run,
    get_latest_market_snapshot_rows_for_query,
    get_run_cluster_market_rows,
    get_score_summary,
    insert_score_snapshot,
    upsert_cluster_market_snapshot,
)


def capture_trend_snapshots(
    db: Session,
    *,
    run_id: int | None = None,
    source_name: str = "ebay",
) -> dict:
    active_run = get_ingestion_run(db, run_id) if run_id is not None else get_latest_completed_run(db, source_name=source_name)
    snapshot_run_info = {
        "snapshot_run_id": active_run.id if active_run else None,
        "snapshot_query": active_run.query if active_run else None,
        "snapshot_source_name": active_run.source_name if active_run else None,
    }

    if run_id is not None and not active_run:
        return {
            "status": "not_found",
            "message": "No ingestion run found for the provided run_id",
            "run_id": run_id,
        }

    if active_run and active_run.status != "completed":
        return {
            "status": "invalid_run",
            "message": "Trend snapshots require a completed ingestion run",
            "run_id": active_run.id,
            "run_status": active_run.status,
        }

    rows = get_score_summary(db, limit=None)
    score_snapshots_written = 0
    for row in rows:
        insert_score_snapshot(
            db,
            cluster_id=row["cluster_id"],
            total_score=row.get("total_score") or 0.0,
            recommendation=row.get("recommendation"),
            gross_profit_estimate=row.get("gross_profit_estimate"),
            max_cpa=row.get("max_cpa"),
            auto_commit=False,
        )
        score_snapshots_written += 1

    market_snapshots_written = 0
    if active_run:
        market_rows = get_run_cluster_market_rows(db, run_id=active_run.id)
        previous_rows = get_latest_market_snapshot_rows_for_query(
            db,
            source_name=active_run.source_name,
            query=active_run.query,
            exclude_run_id=active_run.id,
        )
        current_cluster_ids = {row["cluster_id"] for row in market_rows}

        for row in market_rows:
            upsert_cluster_market_snapshot(
                db,
                cluster_id=row["cluster_id"],
                run_id=active_run.id,
                source_name=row["source_name"],
                query=row["query"],
                listing_count=row["listing_count"],
                seller_count=row["seller_count"],
                min_total_price=row["min_total_price"],
                max_total_price=row["max_total_price"],
                avg_total_price=row["avg_total_price"],
                median_total_price=row["median_total_price"],
                external_ids_json=row["external_ids_json"],
                seller_names_json=row["seller_names_json"],
                auto_commit=False,
            )
            market_snapshots_written += 1

        for previous in previous_rows:
            if previous.cluster_id in current_cluster_ids:
                continue
            upsert_cluster_market_snapshot(
                db,
                cluster_id=previous.cluster_id,
                run_id=active_run.id,
                source_name=active_run.source_name,
                query=active_run.query,
                listing_count=0,
                seller_count=0,
                min_total_price=None,
                max_total_price=None,
                avg_total_price=None,
                median_total_price=None,
                external_ids_json="[]",
                seller_names_json="[]",
                auto_commit=False,
            )
            market_snapshots_written += 1

    db.commit()
    return {
        "status": "completed",
        "score_snapshots_written": score_snapshots_written,
        "market_snapshots_written": market_snapshots_written,
        **snapshot_run_info,
    }
