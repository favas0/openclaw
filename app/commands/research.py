import typer

from app.commands.shared import print_json
from app.db.database import SessionLocal
from app.db.repo import (
    get_cluster_trends,
    get_research_signal_summary,
)
from app.research.trend_snapshots import capture_trend_snapshots


def register_research_commands(app: typer.Typer) -> None:
    trend_sort_modes = (
        "movement",
        "score",
        "price",
        "new-items",
        "coverage",
        "recommendation-change",
        "stable-supply-price",
    )

    @app.command("show-signals")
    def show_signals(
        limit: int = typer.Option(20, "--limit", "-l", min=1, max=200),
    ):
        with SessionLocal() as db:
            rows = get_research_signal_summary(db, limit=limit)
        print_json({"count": len(rows), "signals": rows})

    @app.command("snapshot-trends")
    def snapshot_trends(
        run_id: int | None = typer.Option(
            None,
            "--run-id",
            help="Optional ingestion run ID to snapshot for market trends; defaults to latest completed run",
        ),
    ):
        with SessionLocal() as db:
            result = capture_trend_snapshots(db, run_id=run_id)

        print_json(result)
        if result.get("status") != "completed":
            raise typer.Exit(code=1)

    @app.command("trend-report")
    def trend_report(
        limit: int = typer.Option(20, "--limit", "-l", min=1, max=200),
        query: str | None = typer.Option(
            None,
            "--query",
            help="Optional exact query filter for trend rows, e.g. 'walking pad'",
        ),
        source_name: str | None = typer.Option(
            None,
            "--source-name",
            help="Optional source filter, e.g. 'ebay'",
        ),
        sort_by: str = typer.Option(
            "movement",
            "--sort-by",
            help="Sort mode: movement | score | price | new-items | coverage | recommendation-change | stable-supply-price",
        ),
        min_market_snapshots: int = typer.Option(
            1,
            "--min-market-snapshots",
            min=1,
            help="Only include trend rows with at least this many market snapshots",
        ),
        recommendation_changed_only: bool = typer.Option(
            False,
            "--recommendation-changed-only",
            help="Only include rows where recommendation changed between first and latest score snapshot",
        ),
        series_status: str | None = typer.Option(
            None,
            "--series-status",
            help="Optional filter: new | active | sparse | disappeared | reappeared",
        ),
        score_coverage_status: str | None = typer.Option(
            None,
            "--score-coverage-status",
            help="Optional filter: scored | market_only | market_absent",
        ),
    ):
        sort_by = sort_by.strip().lower()
        if sort_by not in trend_sort_modes:
            raise typer.BadParameter(
                f"sort-by must be one of: {', '.join(trend_sort_modes)}"
            )

        with SessionLocal() as db:
            rows = get_cluster_trends(
                db,
                limit=limit,
                query=query,
                source_name=source_name,
                sort_by=sort_by,
                min_market_snapshots=min_market_snapshots,
                recommendation_changed_only=recommendation_changed_only,
                series_status=series_status,
                score_coverage_status=score_coverage_status,
            )
        print_json(
            {
                "count": len(rows),
                "filters": {
                    "query": query,
                    "source_name": source_name,
                    "sort_by": sort_by,
                    "min_market_snapshots": min_market_snapshots,
                    "recommendation_changed_only": recommendation_changed_only,
                    "series_status": series_status,
                    "score_coverage_status": score_coverage_status,
                    "limit": limit,
                },
                "trends": rows,
            }
        )
