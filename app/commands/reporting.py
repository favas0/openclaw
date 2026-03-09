from pathlib import Path

import typer

from app.commands.shared import explain_row, print_json, shortlist_rows
from app.config import settings
from app.db.database import SessionLocal
from app.db.repo import get_cluster_comparison_rows, get_score_summary
from app.reporting.rankings import write_ranked_csv, write_ranked_markdown


def register_reporting_commands(app: typer.Typer) -> None:
    @app.command("top-products")
    def top_products(
        recommendation: str | None = typer.Option(
            None,
            "--recommendation",
            "-r",
            help="Optional filter, e.g. watch / shortlist / test",
        ),
        limit: int = typer.Option(
            20,
            "--limit",
            "-l",
            min=1,
            max=200,
            help="Maximum ranked products to show",
        ),
    ):
        with SessionLocal() as db:
            rows = get_score_summary(
                db,
                recommendation=recommendation,
                limit=limit,
            )

            print_json(
                {
                    "count": len(rows),
                    "recommendation_filter": recommendation,
                    "products": rows,
                }
            )

    @app.command("shortlist-products")
    def shortlist_products(
        recommendation: str | None = typer.Option(
            None,
            "--recommendation",
            "-r",
            help="Optional filter, e.g. watch / test",
        ),
        limit: int = typer.Option(
            10,
            "--limit",
            "-l",
            min=1,
            max=100,
            help="Maximum shortlisted products to show",
        ),
        min_profit: float = typer.Option(
            60.0,
            "--min-profit",
            help="Minimum gross profit estimate",
        ),
        min_cpa: float = typer.Option(
            30.0,
            "--min-cpa",
            help="Minimum max CPA",
        ),
        min_listings: int = typer.Option(
            2,
            "--min-listings",
            help="Minimum listing count",
        ),
    ):
        with SessionLocal() as db:
            rows = get_score_summary(
                db,
                recommendation=recommendation,
                limit=None,
            )

        filtered = shortlist_rows(
            rows=rows,
            min_profit=min_profit,
            min_cpa=min_cpa,
            min_listings=min_listings,
            limit=limit,
        )

        print_json(
            {
                "count": len(filtered),
                "filters": {
                    "recommendation": recommendation,
                    "min_profit": min_profit,
                    "min_cpa": min_cpa,
                    "min_listings": min_listings,
                    "limit": limit,
                },
                "products": filtered,
            }
        )

    @app.command("explain-product")
    def explain_product(
        cluster_id: int = typer.Argument(..., help="Cluster ID to explain"),
    ):
        with SessionLocal() as db:
            rows = get_score_summary(
                db,
                recommendation=None,
                limit=None,
            )

        match = next((row for row in rows if row.get("cluster_id") == cluster_id), None)

        if not match:
            print_json(
                {
                    "status": "not_found",
                    "cluster_id": cluster_id,
                    "message": "No scored product cluster found for that cluster_id",
                }
            )
            raise typer.Exit(code=1)

        explanation = explain_row(match)

        print_json(
            {
                "cluster_id": match.get("cluster_id"),
                "cluster_title": match.get("cluster_title"),
                "query": match.get("query"),
                "listing_count": match.get("listing_count"),
                "seller_count": match.get("seller_count"),
                "median_total_price": match.get("median_total_price"),
                "scores": {
                    "demand_score": match.get("demand_score"),
                    "sales_signal_score": match.get("sales_signal_score"),
                    "competition_score": match.get("competition_score"),
                    "supplier_fit_score": match.get("supplier_fit_score"),
                    "risk_score": match.get("risk_score"),
                    "total_score": match.get("total_score"),
                },
                "economics": {
                    "sell_price_estimate": match.get("sell_price_estimate"),
                    "supplier_cost_estimate": match.get("supplier_cost_estimate"),
                    "shipping_cost_estimate": match.get("shipping_cost_estimate"),
                    "fees_estimate": match.get("fees_estimate"),
                    "gross_profit_estimate": match.get("gross_profit_estimate"),
                    "max_cpa": match.get("max_cpa"),
                },
                "recommendation": match.get("recommendation"),
                "notes": match.get("notes"),
                "strengths": explanation["strengths"],
                "weaknesses": explanation["weaknesses"],
                "summary": explanation["summary"],
            }
        )

    @app.command("export-shortlist")
    def export_shortlist(
        recommendation: str | None = typer.Option(
            None,
            "--recommendation",
            "-r",
            help="Optional filter, e.g. watch / test",
        ),
        limit: int = typer.Option(
            10,
            "--limit",
            "-l",
            min=1,
            max=100,
            help="Maximum shortlisted products to export",
        ),
        min_profit: float = typer.Option(
            60.0,
            "--min-profit",
            help="Minimum gross profit estimate",
        ),
        min_cpa: float = typer.Option(
            30.0,
            "--min-cpa",
            help="Minimum max CPA",
        ),
        min_listings: int = typer.Option(
            2,
            "--min-listings",
            help="Minimum listing count",
        ),
        fmt: str = typer.Option(
            "csv",
            "--format",
            "-f",
            help="csv | md | both",
        ),
    ):
        fmt = fmt.strip().lower()
        if fmt not in {"csv", "md", "both"}:
            raise typer.BadParameter("format must be one of: csv, md, both")

        with SessionLocal() as db:
            rows = get_score_summary(
                db,
                recommendation=recommendation,
                limit=None,
            )

        filtered = shortlist_rows(
            rows=rows,
            min_profit=min_profit,
            min_cpa=min_cpa,
            min_listings=min_listings,
            limit=limit,
        )

        reports_dir = Path(settings.openclaw_data_dir) / "reports"
        rec_suffix = recommendation.strip().lower() if recommendation else "all"
        file_stem = (
            f"shortlist_{rec_suffix}"
            f"_profit{int(min_profit)}"
            f"_cpa{int(min_cpa)}"
            f"_listings{min_listings}"
            f"_top{limit}"
        )

        written: list[str] = []

        if fmt in {"csv", "both"}:
            csv_path = reports_dir / f"{file_stem}.csv"
            write_ranked_csv(csv_path, filtered)
            written.append(str(csv_path))

        if fmt in {"md", "both"}:
            md_path = reports_dir / f"{file_stem}.md"
            write_ranked_markdown(md_path, filtered)
            written.append(str(md_path))

        print_json(
            {
                "status": "completed",
                "exported_count": len(filtered),
                "filters": {
                    "recommendation": recommendation,
                    "min_profit": min_profit,
                    "min_cpa": min_cpa,
                    "min_listings": min_listings,
                    "limit": limit,
                },
                "files": written,
            }
        )

    @app.command("export-products")
    def export_products(
        recommendation: str | None = typer.Option(
            None,
            "--recommendation",
            "-r",
            help="Optional filter, e.g. watch / shortlist / test",
        ),
        limit: int | None = typer.Option(
            None,
            "--limit",
            "-l",
            min=1,
            max=1000,
            help="Optional maximum rows to export",
        ),
        fmt: str = typer.Option(
            "csv",
            "--format",
            "-f",
            help="csv | md | both",
        ),
    ):
        fmt = fmt.strip().lower()
        if fmt not in {"csv", "md", "both"}:
            raise typer.BadParameter("format must be one of: csv, md, both")

        with SessionLocal() as db:
            rows = get_score_summary(
                db,
                recommendation=recommendation,
                limit=limit,
            )

        reports_dir = Path(settings.openclaw_data_dir) / "reports"
        suffix = recommendation.strip().lower() if recommendation else "all"
        written: list[str] = []

        if fmt in {"csv", "both"}:
            csv_path = reports_dir / f"ranked_products_{suffix}.csv"
            write_ranked_csv(csv_path, rows)
            written.append(str(csv_path))

        if fmt in {"md", "both"}:
            md_path = reports_dir / f"ranked_products_{suffix}.md"
            write_ranked_markdown(md_path, rows)
            written.append(str(md_path))

        print_json(
            {
                "status": "completed",
                "exported_count": len(rows),
                "recommendation_filter": recommendation,
                "files": written,
            }
        )

    @app.command("compare-products")
    def compare_products(
        cluster_ids: list[int] = typer.Argument(..., help="Two or more cluster IDs to compare"),
    ):
        unique_ids: list[int] = []
        for cluster_id in cluster_ids:
            if cluster_id not in unique_ids:
                unique_ids.append(cluster_id)

        with SessionLocal() as db:
            rows = get_cluster_comparison_rows(db, unique_ids)

        print_json(
            {
                "count": len(rows),
                "cluster_ids": unique_ids,
                "comparison": rows,
            }
        )
