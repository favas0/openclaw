from pathlib import Path

import typer
from rich import print

from app.commands.shared import print_json
from app.config import settings
from app.db.database import Base, SessionLocal, engine
from app.db.repo import (
    count_cluster_market_snapshots,
    count_cluster_scores,
    count_normalized_listings,
    count_product_clusters,
    count_raw_listings,
    create_ingestion_run,
    finish_ingestion_run,
    get_cluster_summary,
    get_run_summary,
    insert_raw_listing,
)
from app.sources.ebay_api import EbayBrowseApiClient


def register_system_commands(app: typer.Typer) -> None:
    @app.command()
    def doctor():
        data_dir = Path(settings.openclaw_data_dir)
        db_path = Path(settings.openclaw_db_path)
        ebay = EbayBrowseApiClient()

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
            "has_ebay_client_id": bool(settings.ebay_client_id),
            "has_ebay_client_secret": bool(settings.ebay_client_secret),
            "ebay_credentials_ready": ebay.has_credentials(),
            "ebay_default_collection_mode": "api" if ebay.has_credentials() else "demo",
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
                    "cluster_market_snapshots": count_cluster_market_snapshots(db),
                }
            )

    @app.command("clusters")
    def clusters_cmd():
        with SessionLocal() as db:
            print_json({"clusters": get_cluster_summary(db)})
