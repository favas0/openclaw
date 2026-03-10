from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from app.config import settings
from app.db.database import SessionLocal, engine, ensure_additive_schema
from app.db.repo import (
    count_cluster_scores,
    count_normalized_listings,
    count_product_clusters,
    count_raw_listings,
    get_reporting_summary,
)


WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenClaw Web Shell",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/", response_class=HTMLResponse)
    def homepage(request: Request) -> HTMLResponse:
        return _render(
            request,
            "home.html",
            page_title="OpenClaw",
            oauth_routes=_oauth_routes(),
        )

    @app.get("/privacy", response_class=HTMLResponse)
    def privacy(request: Request) -> HTMLResponse:
        return _render(
            request,
            "privacy.html",
            page_title="Privacy Policy",
        )

    @app.get("/terms", response_class=HTMLResponse)
    def terms(request: Request) -> HTMLResponse:
        return _render(
            request,
            "terms.html",
            page_title="Terms of Service",
        )

    @app.get("/support", response_class=HTMLResponse)
    def support(request: Request) -> HTMLResponse:
        return _render(
            request,
            "support.html",
            page_title="Support",
            oauth_routes=_oauth_routes(),
        )

    @app.get("/review", response_class=HTMLResponse)
    def review(request: Request) -> HTMLResponse:
        return _render(
            request,
            "review.html",
            page_title="Reviewer Overview",
            review_data=_review_data(),
            oauth_routes=_oauth_routes(),
        )

    @app.get("/oauth/etsy/callback", response_class=HTMLResponse)
    def etsy_callback(
        request: Request,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ) -> HTMLResponse:
        return _oauth_callback_page(
            request=request,
            provider_name="Etsy",
            code=code,
            state=state,
            error=error,
        )

    @app.get("/oauth/tiktok/callback", response_class=HTMLResponse)
    def tiktok_callback(
        request: Request,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ) -> HTMLResponse:
        return _oauth_callback_page(
            request=request,
            provider_name="TikTok",
            code=code,
            state=state,
            error=error,
        )

    @app.get("/health")
    @app.get("/healthz")
    def health() -> dict[str, Any]:
        db_path = Path(settings.openclaw_db_path)
        db_exists = db_path.exists()
        db_parent_exists = db_path.parent.exists()
        database_ok = False
        database_error = None

        if db_exists and db_parent_exists:
            try:
                with SessionLocal() as db:
                    db.execute(text("SELECT 1"))
                database_ok = True
            except Exception as exc:  # pragma: no cover - defensive fallback
                database_error = str(exc)

        return {
            "status": "ok" if database_ok or not db_exists else "degraded",
            "app": "openclaw-web",
            "base_url": settings.web_base_url.rstrip("/"),
            "db_path": str(db_path),
            "db_exists": db_exists,
            "db_parent_exists": db_parent_exists,
            "database_ok": database_ok,
            "database_error": database_error,
        }

    return app


def _render(request: Request, template_name: str, **context: Any) -> HTMLResponse:
    page_context = {
        **_base_context(request),
        **context,
    }
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=page_context,
    )


def _base_context(request: Request) -> dict[str, Any]:
    return {
        "request": request,
        "app_name": "OpenClaw",
        "base_url": settings.web_base_url.rstrip("/"),
        "support_email": settings.web_support_email,
        "support_mailto": f"mailto:{settings.web_support_email}",
        "nav_items": (
            {"label": "Home", "href": "/"},
            {"label": "Review", "href": "/review"},
            {"label": "Privacy", "href": "/privacy"},
            {"label": "Terms", "href": "/terms"},
            {"label": "Support", "href": "/support"},
            {"label": "Health", "href": "/health"},
        ),
    }


def _oauth_routes() -> tuple[dict[str, str], ...]:
    base_url = settings.web_base_url.rstrip("/")
    return (
        {"provider": "Etsy", "url": f"{base_url}/oauth/etsy/callback"},
        {"provider": "TikTok", "url": f"{base_url}/oauth/tiktok/callback"},
    )


def _review_data() -> dict[str, Any]:
    db_path = Path(settings.openclaw_db_path)
    if not db_path.parent.exists():
        return {
            "database_ready": False,
            "message": "The configured database directory does not exist yet. Run initdb or mount /data before using reviewer data views.",
            "stats": (),
            "top_products": (),
        }

    try:
        ensure_additive_schema(engine)
        with SessionLocal() as db:
            stats = (
                {"label": "Raw listings", "value": count_raw_listings(db)},
                {"label": "Normalized listings", "value": count_normalized_listings(db)},
                {"label": "Product clusters", "value": count_product_clusters(db)},
                {"label": "Scored clusters", "value": count_cluster_scores(db)},
            )
            top_products = tuple(get_reporting_summary(db, limit=5))
    except Exception as exc:
        return {
            "database_ready": False,
            "message": (
                "Database is configured, but reviewer data is not available yet. "
                f"Run initdb to complete additive schema setup. Details: {exc.__class__.__name__}."
            ),
            "stats": (),
            "top_products": (),
        }

    if not top_products:
        message = "Database is reachable. Populate it through the CLI pipeline to show reviewer-facing opportunity examples here."
    else:
        message = "Database is reachable and reviewer examples are available from the existing CLI pipeline outputs."

    return {
        "database_ready": True,
        "message": message,
        "stats": stats,
        "top_products": top_products,
    }


def _oauth_callback_page(
    *,
    request: Request,
    provider_name: str,
    code: str | None,
    state: str | None,
    error: str | None,
) -> HTMLResponse:
    status = "received" if code else "waiting"
    if error:
        status = "error"

    return _render(
        request,
        "oauth_callback.html",
        page_title=f"{provider_name} OAuth Callback",
        provider_name=provider_name,
        callback_status=status,
        code_present=bool(code),
        state=state,
        error=error,
    )
