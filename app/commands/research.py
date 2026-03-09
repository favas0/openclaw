import typer

from app.commands.shared import print_json
from app.db.database import SessionLocal
from app.db.repo import (
    get_cluster_trends,
    get_research_signal_summary,
)
from app.research.trend_snapshots import capture_trend_snapshots


def register_research_commands(app: typer.Typer) -> None:
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
    ):
        with SessionLocal() as db:
            rows = get_cluster_trends(db, limit=limit)
        print_json({"count": len(rows), "trends": rows})
