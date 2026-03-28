"""Stub for jobs command — implemented in Phase 3."""
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.callback(invoke_without_command=True)
def jobs(ctx: typer.Context):
    """List and manage job applications."""
    if ctx.resilient_parsing:
        return
    console.print("[yellow]⚠ Job tracker not implemented yet (Phase 3).[/yellow]")
