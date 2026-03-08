import json
from pathlib import Path

import typer
from rich import print

from app.config import settings
from app.db.database import Base, SessionLocal, engine
from app.db.repo import (
    count_normalized_listings,
    count_raw_listings,
    create_ingestion_run,
    finish_ingestion_run,
    get_raw_listings,
    get_run_summary,
    insert_raw_listing,
    upsert_normalized_listing,
)
from app.normalize.processor import normalize_raw_listing
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


@app.command()
def doctor():
    """Check config, mounts, and basic runtime state."""
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
    """Create database tables."""
    db_path = Path(settings.openclaw_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"[green]Database tables ready:[/green] {db_path}")


@app.command("seed-demo")
def seed_demo(query: str = "walking pad"):
    """Insert one demo ingestion run and one demo raw listing."""
    with SessionLocal() as db:
        run = create_ingestion_run(
            db,
            source_name="ebay",
            query=query,
            status="started",
        )

        insert_raw_listing(
            db,
            run_id=run.id,
            source_name="ebay",
            query=query,
            external_id="demo-001",
            title="Under Desk Walking Pad Treadmill 2.5HP Remote Control LED Display",
            price=189.99,
            shipping_cost=0.0,
            currency="GBP",
            seller_name="demo_seller_uk",
            item_url="https://example.com/item/demo-001",
            image_url="https://example.com/item/demo-001.jpg",
            category="Fitness Equipment",
            condition="New",
            is_sold_signal=False,
            raw_payload={"demo": True},
        )

        finish_ingestion_run(
            db,
            run_id=run.id,
            status="completed",
            listings_found=1,
            notes="Demo seed inserted",
        )

    print("[green]Inserted demo run and listing.[/green]")


@app.command("collect-ebay")
def collect_ebay(
    query: str = typer.Argument(..., help="Search query, e.g. 'walking pad'"),
    limit: int = typer.Option(20, "--limit", "-l", min=1, max=100),
    use_demo: bool = typer.Option(False, "--demo", help="Use built-in demo data"),
):
    """Collect eBay listings into raw_listings."""
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
    """Normalize raw listings into normalized_listings."""
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


@app.command()
def runs():
    """Show ingestion runs."""
    with SessionLocal() as db:
        print_json({"runs": get_run_summary(db)})


@app.command()
def stats():
    """Show basic database stats."""
    with SessionLocal() as db:
        print_json(
            {
                "raw_listings": count_raw_listings(db),
                "normalized_listings": count_normalized_listings(db),
            }
        )


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    app()
