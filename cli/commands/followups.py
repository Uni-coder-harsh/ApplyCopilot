"""Stub for followups command — implemented in Phase 3."""
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.callback(invoke_without_command=True)
def followups(ctx: typer.Context):
    """View and manage follow-up reminders."""
    if ctx.resilient_parsing:
        return
    console.print("[yellow]⚠ Follow-up tracker not implemented yet (Phase 3).[/yellow]")
