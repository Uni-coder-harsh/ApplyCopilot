"""
applycopilot followups
Show and manage follow-up reminders.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def followups(ctx: typer.Context):
    """View and manage follow-up reminders."""
    if ctx.resilient_parsing:
        return
    _show_followups()


def _show_followups():
    from db.session import db_session
    from core.tracker.followup import get_due_followups, get_upcoming_followups

    with db_session() as db:
        due = get_due_followups(db)
        upcoming = get_upcoming_followups(db, days=7)

    # ── Due now ────────────────────────────────────────────────────────────────
    if due:
        console.print(f"\n[bold red]⚠ {len(due)} follow-up(s) due now[/bold red]\n")

        table = Table(box=box.SIMPLE_HEAD, header_style="bold", padding=(0, 1))
        table.add_column("ID", style="dim", width=4, justify="right")
        table.add_column("Company", min_width=18)
        table.add_column("Role", min_width=18)
        table.add_column("Stage", width=14)
        table.add_column("Last updated", width=12)
        table.add_column("Last follow-up", width=14)

        for app_obj, job, last_fu in due:
            stage_val = app_obj.stage.value if app_obj.stage else "—"
            last_updated = (
                app_obj.last_updated.strftime("%Y-%m-%d")
                if app_obj.last_updated else "—"
            )
            last_fu_str = (
                last_fu.date.strftime("%Y-%m-%d") if last_fu and last_fu.date else "[dim]never[/dim]"
            )
            table.add_row(
                f"#{app_obj.id}",
                job.company or "—",
                job.role or "—",
                stage_val,
                last_updated,
                last_fu_str,
            )

        console.print(table)

        # Interactive mark-as-sent
        if Confirm.ask("\nMark any as sent?", default=False):
            _interactive_mark_sent(due)
    else:
        console.print("\n[green]✓ No follow-ups due right now.[/green]")

    # ── Upcoming ───────────────────────────────────────────────────────────────
    if upcoming:
        console.print("\n[bold]Upcoming follow-ups (next 7 days)[/bold]\n")
        table2 = Table(box=box.SIMPLE_HEAD, header_style="bold", padding=(0, 1))
        table2.add_column("ID", style="dim", width=4, justify="right")
        table2.add_column("Company", min_width=18)
        table2.add_column("Role", min_width=18)
        table2.add_column("Follow-up date", width=14)

        for app_obj, job in upcoming:
            fu_date = (
                app_obj.followup_date.strftime("%Y-%m-%d")
                if app_obj.followup_date else "—"
            )
            table2.add_row(f"#{app_obj.id}", job.company or "—", job.role or "—", fu_date)

        console.print(table2)

    if not due and not upcoming:
        console.print("[dim]Run [bold]applycopilot sync[/bold] to import emails and auto-detect follow-up needs.[/dim]\n")


def _interactive_mark_sent(due_list):
    from db.session import db_session
    from core.tracker.followup import mark_followup_sent, mark_followup_skipped

    ids_str = Prompt.ask(
        "Enter application IDs to mark as sent (comma-separated, e.g. 1,3)"
    )
    try:
        ids = [int(x.strip().lstrip("#")) for x in ids_str.split(",") if x.strip()]
    except ValueError:
        console.print("[red]✗ Invalid IDs.[/red]")
        return

    due_ids = {app_obj.id for app_obj, job, _ in due_list}

    with db_session() as db:
        for app_id in ids:
            if app_id not in due_ids:
                console.print(f"  [yellow]⚠ #{app_id} not in due list, skipping.[/yellow]")
                continue
            mark_followup_sent(db, app_id)
            console.print(f"  [green]✓[/green] #{app_id} marked as sent")
