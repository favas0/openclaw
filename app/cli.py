import typer

from app.commands import (
    register_pipeline_commands,
    register_reporting_commands,
    register_research_commands,
    register_system_commands,
    register_web_commands,
)

app = typer.Typer(
    help="OpenClaw V1 CLI",
    rich_markup_mode=None,
    no_args_is_help=True,
    add_completion=False,
)

register_system_commands(app)
register_pipeline_commands(app)
register_reporting_commands(app)
register_research_commands(app)
register_web_commands(app)


if __name__ == "__main__":
    app()
