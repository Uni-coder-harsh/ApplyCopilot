"""
applycopilot resume
Generate a tailored resume for a specific job application.
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich import box
from typing import Optional

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def resume(ctx: typer.Context):
    """Generate tailored resumes."""
    if ctx.invoked_subcommand is None:
        console.print(
            "\n[bold]applycopilot resume[/bold] commands:\n"
            "  [cyan]applycopilot resume generate --job <ID>[/cyan]   generate for a job\n"
            "  [cyan]applycopilot resume profile[/cyan]               set up your profile\n"
            "  [cyan]applycopilot resume list[/cyan]                  list generated resumes\n"
        )


@app.command("generate")
def generate(
    job_id: Optional[int] = typer.Option(None, "--job", "-j", help="Job ID to tailor resume for"),
    no_tailor: bool = typer.Option(False, "--no-tailor", help="Skip AI tailoring (faster)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
):
    """Generate a tailored resume for a specific job."""
    from db.session import db_session
    from db.models import User, Job, Application, Resume
    from core.resume.builder import build_resume_data
    from core.resume.tailorer import tailor_resume
    from core.resume.docx_writer import generate_docx, build_output_filename
    from core.resume.ats_scorer import score_resume
    from config.settings import settings

    with db_session() as db:
        user = db.query(User).first()
        if not user:
            console.print("[red]✗ No user found. Run applycopilot init first.[/red]")
            raise typer.Exit(1)

        # Build resume data from profile
        resume_data = build_resume_data(db, user.id)
        if not resume_data:
            console.print(
                "[yellow]⚠ Your profile is empty.[/yellow]\n"
                "Run [bold]applycopilot resume profile[/bold] to set it up first."
            )
            raise typer.Exit(1)

        # Resolve job
        job = None
        job_description = ""

        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                console.print(f"[red]✗ Job #{job_id} not found.[/red]")
                raise typer.Exit(1)
            job_description = job.description or ""
        else:
            # Show available jobs and let user pick
            jobs = db.query(Job).all()
            if not jobs:
                console.print("[yellow]No jobs found. Generating a general resume.[/yellow]")
            else:
                console.print("\n[bold]Available jobs:[/bold]")
                for j in jobs[:20]:
                    console.print(f"  #{j.id}  {j.company} — {j.role}")
                choice = Prompt.ask("\nEnter job ID (or press Enter for general resume)", default="")
                if choice.strip():
                    job = db.query(Job).filter(Job.id == int(choice)).first()
                    job_description = job.description or "" if job else ""

        # Determine output directory
        out_dir = output or settings.resume_output_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        # AI tailoring
        if job and job_description and not no_tailor:
            console.print("\n[bold]Step 1/3[/bold] — Tailoring resume with AI...")
            from ai.client import ollama_client
            if ollama_client.is_available():
                with console.status("Running mistral:7b..."):
                    resume_data = tailor_resume(
                        resume_data,
                        job_description=job_description,
                        company=job.company,
                        role=job.role,
                    )
                console.print("  [green]✓[/green] Resume tailored to job description")
            else:
                console.print("  [yellow]⚠ Ollama not running — skipping AI tailoring[/yellow]")
        elif job:
            resume_data.job_company = job.company
            resume_data.job_role = job.role

        # ATS scoring
        if job_description:
            console.print("\n[bold]Step 2/3[/bold] — Running ATS check...")
            from core.resume.ats_scorer import score_resume
            ats = score_resume(resume_data, job_description)
            _show_ats_result(ats)
        else:
            console.print("\n[bold]Step 2/3[/bold] — Skipping ATS check (no job description)")

        # Generate DOCX
        console.print("\n[bold]Step 3/3[/bold] — Generating DOCX...")
        filename = build_output_filename(resume_data)
        output_path = Path(out_dir) / filename

        generate_docx(resume_data, output_path)

        # Save record to DB
        resume_record = Resume(
            profile_id=user.profile.id,
            job_id=job.id if job else None,
            version_name=filename,
            file_path=str(output_path),
        )
        db.add(resume_record)
        db.commit()

        console.print(Panel(
            f"[bold green]✓ Resume generated![/bold green]\n\n"
            f"  File : [cyan]{output_path}[/cyan]\n"
            f"  Job  : {job.company + ' — ' + job.role if job else 'General resume'}",
            border_style="green",
        ))


@app.command("profile")
def setup_profile():
    """Set up or update your profile for resume generation."""
    from db.session import db_session
    from db.models import User, Profile, Skill, Project, Education, SocialLink, SkillCategory, SkillSource
    from core.resume.builder import build_profile_setup_prompt

    with db_session() as db:
        user = db.query(User).first()
        if not user:
            console.print("[red]✗ Run applycopilot init first.[/red]")
            raise typer.Exit(1)

        profile = user.profile
        if not profile:
            profile = Profile(user_id=user.id)
            db.add(profile)
            db.flush()

        console.print("\n[bold]Profile Setup[/bold]\n[dim]Press Enter to keep existing value.[/dim]\n")

        fields = build_profile_setup_prompt()
        for f in fields:
            current = getattr(profile, f["field"], None)
            hint = f" [dim](current: {current})[/dim]" if current else ""
            required = " [red]*[/red]" if f["required"] else ""
            value = Prompt.ask(f"  {f['label']}{required}{hint}", default=str(current) if current else "")
            if value and value != str(current):
                # Handle type conversion
                if f["field"] == "graduation_year":
                    try:
                        setattr(profile, f["field"], int(value))
                    except ValueError:
                        pass
                elif f["field"] == "cgpa":
                    try:
                        setattr(profile, f["field"], float(value))
                    except ValueError:
                        pass
                else:
                    setattr(profile, f["field"], value)

        # Skills
        console.print("\n[bold]Skills[/bold] [dim](comma-separated, e.g. Python, PyTorch, Docker)[/dim]")
        skills_input = Prompt.ask("  Skills", default="")
        if skills_input.strip():
            skill_names = [s.strip() for s in skills_input.split(",") if s.strip()]
            for name in skill_names:
                existing = next((s for s in profile.skills if s.name.lower() == name.lower()), None)
                if not existing:
                    skill = Skill(
                        profile_id=profile.id,
                        name=name,
                        category=SkillCategory.OTHER,
                        source=SkillSource.MANUAL,
                    )
                    db.add(skill)

        # Social links
        console.print("\n[bold]Social Links[/bold]\n")
        for platform in ["LinkedIn", "GitHub", "Portfolio"]:
            existing = next((sl for sl in profile.social_links if sl.platform.lower() == platform.lower()), None)
            current_url = existing.url if existing else None
            hint = f" [dim](current: {current_url})[/dim]" if current_url else ""
            url = Prompt.ask(f"  {platform} URL{hint}", default=current_url or "")
            if url and url != current_url:
                if existing:
                    existing.url = url
                else:
                    db.add(SocialLink(profile_id=profile.id, platform=platform, url=url))

        db.commit()
        console.print("\n[green]✓ Profile saved.[/green]")
        console.print("Run [bold]applycopilot resume generate[/bold] to create your resume.")


@app.command("list")
def list_resumes():
    """List all generated resumes."""
    from db.session import db_session
    from db.models import Resume, Job

    with db_session() as db:
        resumes = (
            db.query(Resume)
            .order_by(Resume.created_at.desc())
            .limit(20)
            .all()
        )

    if not resumes:
        console.print("[dim]No resumes generated yet. Run applycopilot resume generate.[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAD, header_style="bold", padding=(0, 1))
    table.add_column("ID", style="dim", width=4)
    table.add_column("Version name", min_width=30)
    table.add_column("Score", width=6)
    table.add_column("Created", width=12)

    for r in resumes:
        table.add_row(
            f"#{r.id}",
            r.version_name or "—",
            f"{r.score:.0f}" if r.score else "—",
            r.created_at.strftime("%Y-%m-%d") if r.created_at else "—",
        )

    console.print(table)


def _show_ats_result(ats):
    color = "green" if ats.overall_score >= 70 else "yellow" if ats.overall_score >= 40 else "red"
    console.print(f"  ATS Score: [{color}]{ats.overall_score}/100[/{color}]")

    if ats.missing_keywords:
        console.print(f"  Missing keywords: [dim]{', '.join(ats.missing_keywords[:8])}[/dim]")

    for tip in ats.suggestions:
        console.print(f"  [dim]→ {tip}[/dim]")
