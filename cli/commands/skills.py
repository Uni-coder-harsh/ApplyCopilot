"""
applycopilot skills
Scan local project folders and infer skills using AI.
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box
from typing import Optional

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def skills(ctx: typer.Context):
    """Scan projects and infer skills."""
    if ctx.invoked_subcommand is None:
        console.print(
            "\n[bold]applycopilot skills[/bold] commands:\n"
            "  [cyan]applycopilot skills scan[/cyan]    scan a folder and infer skills\n"
            "  [cyan]applycopilot skills list[/cyan]    show all your skills\n"
            "  [cyan]applycopilot skills add[/cyan]     manually add a skill\n"
        )


@app.command("scan")
def scan(
    path: Optional[str] = typer.Argument(None, help="Directory to scan (default: ~/Desktop/CodeNova or ~/Projects)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be added without saving"),
):
    """Scan a local directory for projects and infer your skills."""
    from db.session import db_session
    from db.models import User
    from core.skills.project_scanner import scan_directory
    from core.skills.inferrer import (
        infer_skills_from_projects,
        persist_inferred_skills,
        persist_scanned_projects,
    )

    # Resolve scan path
    if not path:
        candidates = [
            Path.home() / "Desktop" / "CodeNova",
            Path.home() / "Projects",
            Path.home() / "projects",
            Path.home() / "code",
            Path.home() / "dev",
        ]
        found = [p for p in candidates if p.exists()]
        if found:
            path = str(found[0])
            console.print(f"[dim]Auto-detected project folder: {path}[/dim]")
        else:
            path = Prompt.ask("  Enter path to your projects folder")

    scan_path = Path(path).expanduser().resolve()
    if not scan_path.exists():
        console.print(f"[red]✗ Directory not found: {scan_path}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Scanning[/bold] {scan_path}...\n")

    # Scan
    with console.status("Discovering projects..."):
        projects = scan_directory(str(scan_path))

    if not projects:
        console.print("[yellow]⚠ No projects found in that directory.[/yellow]")
        raise typer.Exit(0)

    # Show what was found
    console.print(f"Found [bold]{len(projects)}[/bold] projects:\n")
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Project", min_width=20)
    table.add_column("Languages", min_width=30)
    table.add_column("Files", width=6, justify="right")
    table.add_column("Git", width=4)

    for p in projects:
        table.add_row(
            p.name,
            ", ".join(p.languages[:4]) or "—",
            str(p.file_count),
            "✓" if p.is_git_repo else "—",
        )
    console.print(table)

    if dry_run:
        console.print("\n[dim]Dry run — nothing saved.[/dim]")
        return

    if not Confirm.ask(f"\nInfer skills from these {len(projects)} projects?", default=True):
        return

    # AI skill inference with progress
    progress_state = {"task": None, "progress": None}

    def _progress(current, total):
        if progress_state["progress"] and progress_state["task"] is not None:
            progress_state["progress"].update(
                progress_state["task"],
                completed=current,
                total=total,
                description=f"[cyan]Inferring skills[/cyan] {current}/{total}",
            )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running AI inference...[/cyan]", total=len(projects))
        progress_state["task"] = task
        progress_state["progress"] = progress
        inferred = infer_skills_from_projects(projects, progress_callback=_progress)

    console.print(f"\n[bold]{len(inferred)}[/bold] unique skills inferred")

    # Preview top skills
    console.print("\n[bold]Top inferred skills:[/bold]")
    top = sorted(inferred, key=lambda s: s["confidence"], reverse=True)[:15]
    for skill in top:
        bar = "█" * int(skill["confidence"] * 10)
        console.print(
            f"  [cyan]{skill['name']:<20}[/cyan] "
            f"[dim]{skill['category'].value:<12}[/dim] "
            f"[green]{bar}[/green] {skill['confidence']:.0%}"
        )

    if not Confirm.ask("\nSave these skills and projects to your profile?", default=True):
        return

    # Persist
    with db_session() as db:
        user = db.query(User).first()
        if not user or not user.profile:
            console.print("[red]✗ No profile found. Run applycopilot resume profile first.[/red]")
            raise typer.Exit(1)

        profile_id = user.profile.id
        added_skills, skipped_skills = persist_inferred_skills(db, profile_id, inferred)
        added_projects = persist_scanned_projects(db, profile_id, projects)

    console.print(
        f"\n[green]✓[/green] Saved {added_skills} new skills "
        f"({skipped_skills} already existed)\n"
        f"[green]✓[/green] Saved {added_projects} new projects"
    )
    console.print(
        "\nRun [bold]applycopilot resume generate[/bold] to create a resume "
        "with your updated skill profile."
    )


@app.command("list")
def list_skills():
    """Show all your skills grouped by category."""
    from db.session import db_session
    from db.models import User, Skill, SkillCategory

    with db_session() as db:
        user = db.query(User).first()
        if not user or not user.profile:
            console.print("[red]✗ No profile found.[/red]")
            raise typer.Exit(1)

        skills_by_cat: dict[str, list[Skill]] = {}
        for skill in sorted(user.profile.skills, key=lambda s: s.confidence or 0, reverse=True):
            cat = skill.category.value if skill.category else "other"
            skills_by_cat.setdefault(cat, []).append(skill)

    if not skills_by_cat:
        console.print("[dim]No skills yet. Run applycopilot skills scan.[/dim]")
        return

    for cat, skill_list in skills_by_cat.items():
        console.print(f"\n[bold]{cat.upper()}[/bold]")
        names = [
            f"[cyan]{s.name}[/cyan]"
            + (f" [dim]({s.confidence:.0%})[/dim]" if s.confidence else "")
            for s in skill_list
        ]
        console.print("  " + "  ·  ".join(names))


@app.command("add")
def add_skill(
    name: str = typer.Argument(..., help="Skill name"),
    category: str = typer.Option("other", "--category", "-c", help="programming/ml/devops/research/tools/other"),
    level: str = typer.Option("intermediate", "--level", "-l", help="beginner/intermediate/expert"),
):
    """Manually add a skill to your profile."""
    from db.session import db_session
    from db.models import User, Skill, SkillCategory, SkillSource

    cat_map = {
        "programming": SkillCategory.PROGRAMMING,
        "ml": SkillCategory.ML,
        "devops": SkillCategory.DEVOPS,
        "research": SkillCategory.RESEARCH,
        "tools": SkillCategory.TOOLS,
        "other": SkillCategory.OTHER,
    }

    with db_session() as db:
        user = db.query(User).first()
        if not user or not user.profile:
            console.print("[red]✗ No profile found. Run applycopilot resume profile first.[/red]")
            raise typer.Exit(1)

        existing = next(
            (s for s in user.profile.skills if s.name.lower() == name.lower()), None
        )
        if existing:
            console.print(f"[yellow]⚠ Skill '{name}' already exists.[/yellow]")
            return

        skill = Skill(
            profile_id=user.profile.id,
            name=name,
            category=cat_map.get(category.lower(), SkillCategory.OTHER),
            level=level,
            source=SkillSource.MANUAL,
            confidence=1.0,
        )
        db.add(skill)
        db.commit()
        console.print(f"[green]✓[/green] Added skill: [cyan]{name}[/cyan] ({category})")
