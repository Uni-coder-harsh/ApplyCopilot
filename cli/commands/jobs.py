"""
applycopilot jobs
List, filter, and manage job applications.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import box
from typing import Optional

app = typer.Typer()
console = Console()

# Stage display labels
STAGE_LABELS = {
    "cold_email_sent":  ("📧", "Cold email"),
    "applied":          ("📝", "Applied"),
    "awaiting_reply":   ("⏳", "Awaiting"),
    "shortlisted":      ("⭐", "Shortlisted"),
    "oa":               ("💻", "Online test"),
    "interview":        ("🎯", "Interview"),
    "final_round":      ("🔥", "Final round"),
    "offer":            ("🎉", "Offer"),
}

STATUS_COLORS = {
    "active":   "green",
    "rejected": "red",
    "closed":   "dim",
    "offer":    "bold yellow",
}

PRIORITY_LABELS = {0: "", 1: "[yellow]●[/yellow]", 2: "[red]●●[/red]"}

VALID_STAGES = [
    "cold_email_sent", "applied", "awaiting_reply", "shortlisted",
    "oa", "interview", "final_round", "offer",
]
VALID_STATUSES = ["active", "rejected", "closed", "offer"]
VALID_TYPES = ["research", "industry", "fellowship", "ra", "open_source"]


@app.callback(invoke_without_command=True)
def jobs(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status: active|rejected|closed|offer"),
    stage: Optional[str] = typer.Option(None, "--stage", help="Filter by stage: applied|interview|oa|offer..."),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type: research|industry|fellowship|ra"),
    score: Optional[float] = typer.Option(None, "--score", help="Minimum match score (0-100)"),
    search: Optional[str] = typer.Option(None, "--search", "-q", help="Search company or role name"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results to show"),
):
    """List and manage job applications."""
    if ctx.invoked_subcommand is not None:
        return
    _list_jobs(status=status, stage=stage, job_type=type, min_score=score, search=search, limit=limit)


@app.command("update")
def update_application(
    app_id: int = typer.Argument(..., help="Application ID to update"),
    stage: Optional[str] = typer.Option(None, "--stage", help="New stage"),
    status: Optional[str] = typer.Option(None, "--status", help="New status"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Add/update notes"),
    priority: Optional[int] = typer.Option(None, "--priority", help="Priority: 0=normal, 1=high, 2=urgent"),
    followup: Optional[str] = typer.Option(None, "--followup", help="Follow-up date (YYYY-MM-DD)"),
):
    """Update an application's stage, status, notes, or priority."""
    from db.session import db_session
    from core.tracker.application import (
        update_stage, update_status, update_notes,
        set_followup_date, set_priority, get_application_by_id,
    )
    from datetime import datetime, timezone

    with db_session() as db:
        result = get_application_by_id(db, app_id)
        if not result:
            console.print(f"[red]✗ Application #{app_id} not found.[/red]")
            raise typer.Exit(1)

        app_obj, job = result
        changed = False

        if stage:
            if stage not in VALID_STAGES:
                console.print(f"[red]✗ Invalid stage. Choose from: {', '.join(VALID_STAGES)}[/red]")
                raise typer.Exit(1)
            update_stage(db, app_id, stage)
            console.print(f"  [green]✓[/green] Stage → {stage}")
            changed = True

        if status:
            if status not in VALID_STATUSES:
                console.print(f"[red]✗ Invalid status. Choose from: {', '.join(VALID_STATUSES)}[/red]")
                raise typer.Exit(1)
            update_status(db, app_id, status)
            console.print(f"  [green]✓[/green] Status → {status}")
            changed = True

        if notes:
            update_notes(db, app_id, notes)
            console.print("  [green]✓[/green] Notes updated")
            changed = True

        if priority is not None:
            set_priority(db, app_id, priority)
            console.print(f"  [green]✓[/green] Priority → {priority}")
            changed = True

        if followup:
            try:
                dt = datetime.strptime(followup, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                set_followup_date(db, app_id, dt)
                console.print(f"  [green]✓[/green] Follow-up date → {followup}")
                changed = True
            except ValueError:
                console.print("[red]✗ Invalid date format. Use YYYY-MM-DD.[/red]")
                raise typer.Exit(1)

        if not changed:
            console.print("[yellow]No changes specified. Use --stage, --status, --notes, --priority, or --followup.[/yellow]")


@app.command("add")
def add_application(
    company: str = typer.Option(..., "--company", "-c", prompt="Company name"),
    role: str = typer.Option(..., "--role", "-r", prompt="Role / position"),
    type: str = typer.Option("industry", "--type", "-t", prompt="Type (research/industry/fellowship/ra)"),
    stage: str = typer.Option("applied", "--stage", prompt="Stage"),
    url: Optional[str] = typer.Option(None, "--url", help="Job posting URL"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Notes"),
):
    """Manually add a job application."""
    from db.session import db_session
    from core.tracker.application import add_manual_application

    with db_session() as db:
        application = add_manual_application(
            db, company=company, role=role,
            job_type=type, stage=stage, url=url, notes=notes,
        )
        console.print(
            f"\n[green]✓[/green] Added: [bold]{company}[/bold] — {role} "
            f"(ID: #{application.id})"
        )


@app.command("stats")
def show_stats():
    """Show a summary of your application pipeline."""
    from db.session import db_session
    from core.tracker.application import get_summary_stats

    with db_session() as db:
        stats = get_summary_stats(db)

    console.print(Panel(
        f"  Total applications : [bold]{stats['total']}[/bold]\n"
        f"  Active             : [green]{stats['active']}[/green]\n"
        f"  At interview stage : [cyan]{stats['interviews']}[/cyan]\n"
        f"  Offers received    : [bold yellow]{stats['offers']}[/bold yellow]\n"
        f"  Rejections         : [red]{stats['rejections']}[/red]",
        title="[bold]Application Pipeline[/bold]",
        border_style="cyan",
    ))


# ── Internal ───────────────────────────────────────────────────────────────────

def _list_jobs(
    status=None, stage=None, job_type=None,
    min_score=None, search=None, limit=50,
):
    from db.session import db_session
    from core.tracker.application import get_applications, get_summary_stats

    with db_session() as db:
        results = get_applications(
            db,
            status=status,
            stage=stage,
            job_type=job_type,
            min_score=min_score,
            search=search,
            limit=limit,
        )
        stats = get_summary_stats(db)

    if not results:
        console.print("\n[dim]No applications found.[/dim]")
        console.print("Run [bold]applycopilot sync[/bold] to import from email, or")
        console.print("[bold]applycopilot jobs add[/bold] to add one manually.\n")
        return

    # Summary line
    console.print(
        f"\n[dim]Showing {len(results)} of {stats['total']} applications "
        f"— {stats['active']} active, {stats['interviews']} interviews, "
        f"{stats['offers']} offers[/dim]\n"
    )

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold",
        padding=(0, 1),
    )
    table.add_column("ID", style="dim", width=4, justify="right")
    table.add_column("Company", min_width=18)
    table.add_column("Role", min_width=20)
    table.add_column("Type", width=10)
    table.add_column("Stage", width=14)
    table.add_column("Status", width=9)
    table.add_column("Score", width=6, justify="right")
    table.add_column("Applied", width=11)
    table.add_column("P", width=2)

    for app_obj, job in results:
        stage_val = app_obj.stage.value if app_obj.stage else "—"
        icon, label = STAGE_LABELS.get(stage_val, ("", stage_val))
        stage_str = f"{icon} {label}"

        status_val = app_obj.status.value if app_obj.status else "active"
        status_color = STATUS_COLORS.get(status_val, "white")
        status_str = f"[{status_color}]{status_val}[/{status_color}]"

        score_str = f"{app_obj.match_score:.0f}" if app_obj.match_score else "—"

        applied_str = (
            app_obj.applied_date.strftime("%Y-%m-%d")
            if app_obj.applied_date else "—"
        )

        type_str = job.type.value if job.type else "—"
        priority_str = PRIORITY_LABELS.get(app_obj.priority or 0, "")

        table.add_row(
            f"#{app_obj.id}",
            job.company or "—",
            job.role or "—",
            type_str,
            stage_str,
            status_str,
            score_str,
            applied_str,
            priority_str,
        )

    console.print(table)
    console.print(
        "\n[dim]Commands:[/dim]\n"
        "  [bold]applycopilot jobs update <ID> --stage interview[/bold]   update stage\n"
        "  [bold]applycopilot jobs update <ID> --status rejected[/bold]   mark rejected\n"
        "  [bold]applycopilot jobs add[/bold]                             add manually\n"
        "  [bold]applycopilot jobs stats[/bold]                           pipeline summary\n"
        "  [bold]applycopilot followups[/bold]                            see what needs follow-up\n"
    )
