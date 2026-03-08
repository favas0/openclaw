import json
from pathlib import Path

import typer
from rich import print

from app.cluster.cluster_products import build_clusters
from app.config import settings
from app.db.database import Base, SessionLocal, engine
from app.db.repo import (
    assign_listing_to_cluster,
    count_cluster_scores,
    count_normalized_listings,
    count_product_clusters,
    count_raw_listings,
    create_ingestion_run,
    finish_ingestion_run,
    get_cluster_summary,
    get_normalized_listings,
    get_product_clusters,
    get_raw_listings,
    get_run_summary,
    get_score_summary,
    insert_raw_listing,
    upsert_cluster_score,
    upsert_normalized_listing,
    upsert_product_cluster,
)
from app.normalize.processor import normalize_raw_listing
from app.reporting.rankings import write_ranked_csv, write_ranked_markdown
from app.scoring.cluster_scoring import score_cluster
from app.sources.ebay import (
    EbayClient,
    extract_item_summaries,
    get_demo_items,
    map_item_summary_to_raw_listing,
)

app = typer.Typer(
    help="OpenClaw V1 CLI",
    rich_markup_mode=None,
    no_args_is_help=True,
    add_completion=False,
)


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


@app.command()
def doctor():
    data_dir = Path(settings.openclaw_data_dir)
    db_path = Path(settings.openclaw_db_path)
    ebay = EbayClient()

    result = {
        "app_env": settings.app_env,
        "log_level": settings.log_level,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "data_dir": str(data_dir),
        "data_dir_exists": data_dir.exists(),
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
        "db_parent_exists": db_path.parent.exists(),
        "ebay_env": settings.ebay_env,
        "ebay_marketplace_id": settings.ebay_marketplace_id,
        "has_ebay_app_id": bool(settings.ebay_app_id),
        "has_ebay_client_secret": bool(settings.ebay_client_secret),
        "ebay_credentials_ready": ebay.has_credentials(),
    }
    print_json(result)


@app.command()
def initdb():
    db_path = Path(settings.openclaw_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"[green]Database tables ready:[/green] {db_path}")


@app.command("seed-demo")
def seed_demo(query: str = "walking pad"):
    with SessionLocal() as db:
        run = create_ingestion_run(
            db,
            source_name="ebay",
            query=query,
            status="started",
        )

        demo_rows = [
            {
                "external_id": "demo-001",
                "title": "Under Desk Walking Pad Treadmill 2.5HP Remote Control LED Display",
                "price": 179.99,
                "shipping_cost": 0.0,
                "seller_name": "demo_seller_uk_1",
            },
            {
                "external_id": "demo-002",
                "title": "Walking Pad Treadmill Under Desk 2.5HP LED Display Remote Control",
                "price": 189.99,
                "shipping_cost": 0.0,
                "seller_name": "demo_seller_uk_2",
            },
            {
                "external_id": "demo-003",
                "title": "Compact Under Desk Walking Pad Treadmill Home Office Remote",
                "price": 199.99,
                "shipping_cost": 0.0,
                "seller_name": "demo_seller_uk_3",
            },
            {
                "external_id": "demo-004",
                "title": "2.5HP Walking Pad for Home Office Under Desk Treadmill",
                "price": 209.99,
                "shipping_cost": 0.0,
                "seller_name": "demo_seller_uk_2",
            },
        ]

        for item in demo_rows:
            insert_raw_listing(
                db,
                run_id=run.id,
                source_name="ebay",
                query=query,
                external_id=item["external_id"],
                title=item["title"],
                price=item["price"],
                shipping_cost=item["shipping_cost"],
                currency="GBP",
                seller_name=item["seller_name"],
                item_url=f"https://example.com/item/{item['external_id']}",
                image_url=f"https://example.com/item/{item['external_id']}.jpg",
                category="Fitness Equipment",
                condition="New",
                is_sold_signal=False,
                raw_payload={"demo": True},
            )

        finish_ingestion_run(
            db,
            run_id=run.id,
            status="completed",
            listings_found=len(demo_rows),
            notes="Demo seed inserted",
        )
        print("[green]Inserted demo run and listings.[/green]")


@app.command("collect-ebay")
def collect_ebay(
    query: str = typer.Argument(..., help="Search query, e.g. 'walking pad'"),
    limit: int = typer.Option(20, "--limit", "-l", min=1, max=100),
    use_demo: bool = typer.Option(False, "--demo", help="Use built-in demo data"),
):
    client = EbayClient()

    with SessionLocal() as db:
        run = create_ingestion_run(
            db,
            source_name="ebay",
            query=query,
            status="started",
        )

        try:
            if use_demo or not client.has_credentials():
                items = get_demo_items(query)
                notes = "Demo mode used"
            else:
                payload = client.search_items(query=query, limit=limit)
                items = extract_item_summaries(payload)
                notes = "Live eBay Browse API used"

            inserted = 0
            for item in items:
                mapped = map_item_summary_to_raw_listing(item, query)
                insert_raw_listing(
                    db,
                    run_id=run.id,
                    source_name=mapped["source_name"],
                    query=mapped["query"],
                    title=mapped["title"],
                    item_url=mapped["item_url"],
                    external_id=mapped["external_id"],
                    price=mapped["price"],
                    shipping_cost=mapped["shipping_cost"],
                    currency=mapped["currency"],
                    seller_name=mapped["seller_name"],
                    seller_url=mapped["seller_url"],
                    image_url=mapped["image_url"],
                    category=mapped["category"],
                    condition=mapped["condition"],
                    is_sold_signal=mapped["is_sold_signal"],
                    raw_payload=mapped["raw_payload"],
                )
                inserted += 1

            finish_ingestion_run(
                db,
                run_id=run.id,
                status="completed",
                listings_found=inserted,
                notes=notes,
            )

            print_json(
                {
                    "status": "completed",
                    "query": query,
                    "inserted": inserted,
                    "notes": notes,
                }
            )
        except Exception as exc:
            db.rollback()
            finish_ingestion_run(
                db,
                run_id=run.id,
                status="failed",
                listings_found=0,
                notes=str(exc),
            )
            raise typer.Exit(code=1) from exc


@app.command("normalize-listings")
def normalize_listings():
    with SessionLocal() as db:
        raw_listings = get_raw_listings(db)
        processed = 0

        for raw in raw_listings:
            norm = normalize_raw_listing(raw)
            upsert_normalized_listing(db, **norm)
            processed += 1

        print_json(
            {
                "status": "completed",
                "raw_seen": len(raw_listings),
                "normalized_written": processed,
            }
        )


@app.command("cluster-products")
def cluster_products():
    with SessionLocal() as db:
        normalized_rows = get_normalized_listings(db)
        clusters = build_clusters(normalized_rows)

        for cluster in clusters:
            cluster_row = upsert_product_cluster(
                db,
                cluster_key=cluster["cluster_key"],
                cluster_title=cluster["cluster_title"],
                source_name=cluster["source_name"],
                query=cluster["query"],
                listing_count=cluster["listing_count"],
                seller_count=cluster["seller_count"],
                min_total_price=cluster["min_total_price"],
                max_total_price=cluster["max_total_price"],
                avg_total_price=cluster["avg_total_price"],
                median_total_price=cluster["median_total_price"],
                high_ticket_count=cluster["high_ticket_count"],
                brand_risk_count=cluster["brand_risk_count"],
            )

            for normalized_listing_id in cluster["normalized_listing_ids"]:
                assign_listing_to_cluster(
                    db,
                    normalized_listing_id=normalized_listing_id,
                    cluster_id=cluster_row.id,
                )

        print_json(
            {
                "status": "completed",
                "normalized_seen": len(normalized_rows),
                "clusters_written": len(clusters),
            }
        )


@app.command("score-products")
def score_products():
    with SessionLocal() as db:
        clusters = get_product_clusters(db)
        written = 0

        for cluster in clusters:
            score = score_cluster(cluster)
            upsert_cluster_score(
                db,
                cluster_id=cluster.id,
                demand_score=score["demand_score"],
                sales_signal_score=score["sales_signal_score"],
                competition_score=score["competition_score"],
                supplier_fit_score=score["supplier_fit_score"],
                risk_score=score["risk_score"],
                sell_price_estimate=score["sell_price_estimate"],
                supplier_cost_estimate=score["supplier_cost_estimate"],
                shipping_cost_estimate=score["shipping_cost_estimate"],
                fees_estimate=score["fees_estimate"],
                gross_profit_estimate=score["gross_profit_estimate"],
                max_cpa=score["max_cpa"],
                total_score=score["total_score"],
                recommendation=score["recommendation"],
                notes=score["notes"],
            )
            written += 1

        print_json(
            {
                "status": "completed",
                "clusters_scored": written,
            }
        )


@app.command()
def runs():
    with SessionLocal() as db:
        print_json({"runs": get_run_summary(db)})


@app.command()
def stats():
    with SessionLocal() as db:
        print_json(
            {
                "raw_listings": count_raw_listings(db),
                "normalized_listings": count_normalized_listings(db),
                "product_clusters": count_product_clusters(db),
                "cluster_scores": count_cluster_scores(db),
            }
        )


@app.command("clusters")
def clusters_cmd():
    with SessionLocal() as db:
        print_json({"clusters": get_cluster_summary(db)})


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


if __name__ == "__main__":
    app()
