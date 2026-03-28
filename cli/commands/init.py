"""
applycopilot init
Sets up the database, creates the local data directory,
and creates the first user account.
"""

import secrets
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def init(ctx: typer.Context):
    """Initialize ApplyCopilot — run this once after cloning."""
    if ctx.resilient_parsing:
        return
    _run_init()


def _run_init():
    console.print(
        Panel.fit(
            "[bold cyan]Welcome to ApplyCopilot[/bold cyan] 🚀\n"
            "[dim]Local-first AI job & internship tracker[/dim]",
            border_style="cyan",
        )
    )

    # ── Step 1: Data directories ───────────────────────────────────────────────
    console.print("\n[bold]Step 1/4[/bold] — Setting up local data directories...")
    from config.settings import ensure_data_dirs, settings
    ensure_data_dirs()
    console.print(f"  [green]✓[/green] Data directory: {settings.data_dir}")
    console.print(f"  [green]✓[/green] Resumes directory: {settings.resume_output_dir}")

    # ── Step 2: Database ───────────────────────────────────────────────────────
    console.print("\n[bold]Step 2/4[/bold] — Initializing database...")
    from db.session import init_db
    init_db()
    console.print("  [green]✓[/green] Database created with all 16 tables")

    # ── Step 3: Secret key ─────────────────────────────────────────────────────
    console.print("\n[bold]Step 3/4[/bold] — Generating secret key...")
    secret_key = secrets.token_hex(32)
    env_path = settings.data_dir / ".env.local"
    env_path.write_text(f"SECRET_KEY={secret_key}\n")
    console.print(f"  [green]✓[/green] Secret key saved to {env_path}")

    # ── Step 4: Create first user ──────────────────────────────────────────────
    console.print("\n[bold]Step 4/4[/bold] — Create your account\n")

    username = Prompt.ask("  Username")
    while True:
        password = Prompt.ask("  Password", password=True)
        confirm  = Prompt.ask("  Confirm password", password=True)
        if password == confirm:
            break
        console.print("  [red]Passwords do not match. Try again.[/red]")

    _create_user(username, password)

    # ── Done ───────────────────────────────────────────────────────────────────
    console.print(
        Panel(
            f"[bold green]✓ ApplyCopilot is ready![/bold green]\n\n"
            f"  Username : [cyan]{username}[/cyan]\n"
            f"  Data dir : [dim]{settings.data_dir}[/dim]\n\n"
            f"Next steps:\n"
            f"  [bold]applycopilot sync[/bold]      — connect an email account\n"
            f"  [bold]applycopilot jobs[/bold]      — view tracked applications\n"
            f"  [bold]applycopilot --help[/bold]   — see all commands",
            border_style="green",
        )
    )


def _create_user(username: str, password: str) -> None:
    """Hash password with Argon2 and persist the user."""
    from argon2 import PasswordHasher
    from db.session import db_session
    from db.models import User, Profile

    ph = PasswordHasher()
    password_hash = ph.hash(password)

    with db_session() as db:
        # Check if user already exists
        from sqlalchemy import select
        existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing:
            console.print(f"  [yellow]⚠ User '{username}' already exists. Skipping.[/yellow]")
            return

        user = User(username=username, password_hash=password_hash)
        db.add(user)
        db.flush()

        profile = Profile(user_id=user.id)
        db.add(profile)

    console.print(f"  [green]✓[/green] User [cyan]{username}[/cyan] created")
