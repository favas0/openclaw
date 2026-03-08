import json
from pathlib import Path

import typer
from rich import print

from app.config import settings
from app.db.database import Base, SessionLocal, engine
from app.db.repo import (
    count_raw_listings,
    create_ingestion_run,
    finish_ingestion_run,
    get_run_summary,
    insert_raw_listing,
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
        "has_ebay_app_id": bool(settings.ebay_app_id),
    }

    print_json(result)


@app.command()
def initdb():
    """Create database tables."""
    db_path = Path(settings.openclaw_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"[green]Database tables ready:[/green] {db_path}")


@app.command()
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
            raw_payload='{"demo": true}',
        )

        finish_ingestion_run(
            db,
            run_id=run.id,
            status="completed",
            listings_found=1,
            notes="Demo seed inserted",
        )

    print("[green]Inserted demo run and listing.[/green]")


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
            }
        )


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    app()
