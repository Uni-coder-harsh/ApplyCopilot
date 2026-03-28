"""Stub for resume command — implemented in Phase 4."""
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.callback(invoke_without_command=True)
def resume(ctx: typer.Context):
    """Generate tailored resumes."""
    if ctx.resilient_parsing:
        return
    console.print("[yellow]⚠ Resume generator not implemented yet (Phase 4).[/yellow]")
