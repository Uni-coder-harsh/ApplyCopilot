"""
applycopilot sync
Connects an email account and syncs job-related emails.
"""

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def sync(ctx: typer.Context):
    """Sync emails and classify job-related threads."""
    if ctx.resilient_parsing:
        return
    _run_sync()


def _run_sync():
    from db.session import db_session
    from db.models import User, EmailAccount
    from ai.client import ollama_client
    from config.settings import settings

    # ── Check Ollama ───────────────────────────────────────────────────────────
    if not ollama_client.is_available():
        console.print(
            "[red]✗ Ollama is not running.[/red]\n"
            "  Start it with: [bold]ollama serve[/bold]"
        )
        raise typer.Exit(1)

    available_models = ollama_client.list_models()
    for model in [settings.model_classifier, settings.model_reasoner]:
        model_name = model.split(":")[0]
        if not any(model_name in m for m in available_models):
            console.print(f"[yellow]⚠ Model [bold]{model}[/bold] not found locally.[/yellow]")
            if Confirm.ask(f"  Pull {model} now?"):
                import ollama as ol
                with console.status(f"Pulling {model}..."):
                    ol.pull(model)
            else:
                console.print("[red]✗ Cannot proceed without required models.[/red]")
                raise typer.Exit(1)

    # ── Step 1: resolve account — open session then CLOSE it ──────────────────
    # We only save account_id (a plain int) so no ORM object crosses sessions.
    account_id = None

    with db_session() as db:
        user = db.query(User).first()
        if not user:
            console.print("[red]✗ No user found. Run [bold]applycopilot init[/bold] first.[/red]")
            raise typer.Exit(1)

        accounts = db.query(EmailAccount).filter(EmailAccount.user_id == user.id).all()
        if accounts:
            console.print("\n[bold]Connected email accounts:[/bold]")
            for acc in accounts:
                status = "[green]active[/green]" if acc.active else "[dim]inactive[/dim]"
                last = acc.last_sync.strftime("%Y-%m-%d %H:%M") if acc.last_sync else "never"
                console.print(f"  • {acc.email} ({acc.provider}) — {status} — last sync: {last}")
            console.print()

        action = "sync"
        if not accounts or Confirm.ask("Add a new email account?", default=False):
            action = "add"

        if action == "add":
            account_id = _add_email_account(db, user)
            if not account_id:
                return
        else:
            if len(accounts) == 1:
                account_id = accounts[0].id
            else:
                choices = {str(i + 1): acc for i, acc in enumerate(accounts)}
                for k, acc in choices.items():
                    console.print(f"  [{k}] {acc.email}")
                choice = Prompt.ask("Select account", choices=list(choices.keys()))
                account_id = choices[choice].id
    # ── outer session closes here — SQLite write lock released ─────────────────

    # ── Step 2: run sync in a completely fresh session ─────────────────────────
    with db_session() as sync_db:
        _do_sync(sync_db, account_id)


def _add_email_account(db, user) -> int | None:
    """Add a new email account. Returns the saved account_id or None on failure."""
    from db.models import EmailAccount
    from core.email.imap_adapter import IMAPAdapter

    console.print("\n[bold]Add email account[/bold]")
    console.print("[dim]For Gmail use an App Password — myaccount.google.com/apppasswords[/dim]\n")

    email_addr = Prompt.ask("  Email address")
    password = Prompt.ask("  Password / App Password", password=True)

    try:
        adapter = IMAPAdapter.from_email(email_addr, password)
    except ValueError as e:
        console.print(f"  [yellow]⚠ {e}[/yellow]")
        imap_host = Prompt.ask("  IMAP host (e.g. imap.gmail.com)")
        imap_port = int(Prompt.ask("  IMAP port", default="993"))
        adapter = IMAPAdapter(
            host=imap_host, port=imap_port,
            email_address=email_addr, password=password,
        )

    console.print("\n  Testing connection...")
    with console.status("Connecting..."):
        ok = adapter.test_connection()

    if not ok:
        console.print("  [red]✗ Connection failed. Check your credentials.[/red]")
        return None

    console.print("  [green]✓ Connection successful[/green]")
    encrypted = _encrypt_password(password)

    account = EmailAccount(
        user_id=user.id,
        email=email_addr,
        provider="imap",
        imap_host=adapter.host,
        imap_port=adapter.port,
        token_encrypted=encrypted,
        active=True,
    )
    db.add(account)
    db.commit()
    console.print(f"  [green]✓ Account {email_addr} saved[/green]\n")
    return account.id


def _do_sync(db, account_id: int):
    from core.email.imap_adapter import IMAPAdapter
    from core.email.sync import run_sync
    from db.models import EmailAccount

    # Load account details fresh in this session
    account = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if not account:
        console.print("[red]✗ Account not found.[/red]")
        raise typer.Exit(1)

    password = _decrypt_password(account.token_encrypted)
    adapter = IMAPAdapter(
        host=account.imap_host,
        port=account.imap_port,
        email_address=account.email,
        password=password,
    )

    console.print(f"\n[bold]Syncing[/bold] {account.email}...\n")
    progress_state = {"task": None, "progress": None}

    def _progress(stage, current, total):
        if progress_state["progress"] and progress_state["task"] is not None:
            progress_state["progress"].update(
                progress_state["task"],
                completed=current,
                total=total,
                description=f"[cyan]Classifying emails[/cyan] {current}/{total}",
            )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Fetching emails...[/cyan]", total=None)
        progress_state["task"] = task
        progress_state["progress"] = progress

        try:
            with adapter:
                # Pass account_id (int), not the ORM object
                result = run_sync(db, account_id, adapter, progress_callback=_progress)
        except Exception as e:
            console.print(f"\n[red]✗ Sync failed: {e}[/red]")
            import traceback
            traceback.print_exc()
            raise typer.Exit(1)

        progress.update(task, completed=100, total=100, description="[green]Done[/green]")

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Emails fetched",       str(result.total_fetched))
    table.add_row("Already in database",  str(result.already_seen))
    table.add_row("New emails saved",     str(result.new_emails))
    table.add_row("Job-related found",    f"[cyan]{result.job_related}[/cyan]")
    table.add_row("Applications created", f"[green]{result.applications_created}[/green]")
    if result.errors:
        table.add_row("Errors", f"[red]{result.errors}[/red]")

    console.print("\n[bold]Sync results[/bold]")
    console.print(table)

    if result.job_related > 0:
        console.print("\nRun [bold]applycopilot jobs[/bold] to see your tracked applications.")


def _encrypt_password(password: str) -> str:
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from config.settings import settings
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key).encrypt(password.encode()).decode()


def _decrypt_password(encrypted: str) -> str:
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from config.settings import settings
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key).decrypt(encrypted.encode()).decode()
