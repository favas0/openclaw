import typer
import uvicorn

from app.config import settings


def register_web_commands(app: typer.Typer) -> None:
    @app.command("serve-web")
    def serve_web(
        host: str = typer.Option(
            settings.web_host,
            "--host",
            help="Host interface to bind the optional web shell to.",
        ),
        port: int = typer.Option(
            settings.web_port,
            "--port",
            min=1,
            max=65535,
            help="Port to bind the optional web shell to.",
        ),
        reload: bool = typer.Option(
            False,
            "--reload",
            help="Enable auto-reload for local web-shell development.",
        ),
    ) -> None:
        uvicorn.run(
            "app.web.app:create_app",
            factory=True,
            host=host,
            port=port,
            reload=reload,
        )
