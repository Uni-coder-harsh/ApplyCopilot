from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Root of the project repo
BASE_DIR = Path(__file__).resolve().parent.parent

# User data lives here — never committed to git
DATA_DIR = BASE_DIR / ".applycopilot"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────
    app_name: str = "ApplyCopilot"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Database ───────────────────────────────────────────
    database_url: str = f"sqlite:///{DATA_DIR}/applycopilot.db"

    # ── Auth ───────────────────────────────────────────────
    secret_key: str = "change-me-before-first-run"   # overridden on init
    token_expire_hours: int = 720                     # 30 days

    # ── Ollama ─────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    model_classifier: str = "phi3:mini"
    model_reasoner: str = "mistral:7b-instruct-q4_0"
    model_embedder: str = "nomic-embed-text"

    # ── Email sync ─────────────────────────────────────────
    email_sync_batch_size: int = 200   # emails per sync run
    email_max_age_days: int = 365      # how far back to look

    # ── Paths ──────────────────────────────────────────────
    data_dir: Path = DATA_DIR
    resume_output_dir: Path = DATA_DIR / "resumes"
    attachment_dir: Path = DATA_DIR / "attachments"


# Single shared instance — import this everywhere
settings = Settings()


def ensure_data_dirs() -> None:
    """Create all local data directories if they don't exist yet."""
    for d in [
        settings.data_dir,
        settings.resume_output_dir,
        settings.attachment_dir,
    ]:
        d.mkdir(parents=True, exist_ok=True)
