"""
ApplyCopilot CLI
Run: applycopilot --help
"""

import typer
from rich.console import Console

from cli.commands import init, sync, jobs, resume, followups

app = typer.Typer(
    name="applycopilot",
    help="🚀 Local-first AI job & internship tracker",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

# Register sub-commands
app.add_typer(init.app,      name="init",      help="Initialize ApplyCopilot for the first time")
app.add_typer(sync.app,      name="sync",      help="Sync emails and classify job-related threads")
app.add_typer(jobs.app,      name="jobs",      help="List and manage job applications")
app.add_typer(resume.app,    name="resume",    help="Generate tailored resumes")
app.add_typer(followups.app, name="followups", help="View and manage follow-up reminders")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """ApplyCopilot — your local AI job tracker."""
    if ctx.invoked_subcommand is None:
        console.print(
            "\n[bold cyan]ApplyCopilot[/bold cyan] 🚀  [dim]v0.1.0[/dim]\n"
            "Run [bold]applycopilot --help[/bold] to see available commands.\n"
        )


if __name__ == "__main__":
    app()
