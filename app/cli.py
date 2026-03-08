import json
from pathlib import Path

import typer
from rich import print

from app.config import settings

app = typer.Typer(help="OpenClaw V1 CLI")


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
        "db_parent_exists": db_path.parent.exists(),
        "ebay_env": settings.ebay_env,
        "has_ebay_app_id": bool(settings.ebay_app_id),
    }

    print_json(result)


@app.command()
def initdb():
    """Create an empty SQLite file if it does not exist yet."""
    db_path = Path(settings.openclaw_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.touch(exist_ok=True)
    print(f"[green]Database ready:[/green] {db_path}")


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    app()
