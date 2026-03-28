"""Stub for sync command — implemented in Phase 2."""
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.callback(invoke_without_command=True)
def sync(ctx: typer.Context):
    """Sync emails and classify job-related threads."""
    if ctx.resilient_parsing:
        return
    console.print("[yellow]⚠ Email sync not implemented yet (Phase 2).[/yellow]")
