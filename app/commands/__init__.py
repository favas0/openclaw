from app.commands.pipeline import register_pipeline_commands
from app.commands.reporting import register_reporting_commands
from app.commands.research import register_research_commands
from app.commands.system import register_system_commands
from app.commands.web import register_web_commands

__all__ = [
    "register_pipeline_commands",
    "register_reporting_commands",
    "register_research_commands",
    "register_system_commands",
    "register_web_commands",
]
