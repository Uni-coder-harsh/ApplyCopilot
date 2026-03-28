"""
Database engine and session management.
Import `get_db` for FastAPI dependency injection.
Import `SessionLocal` for CLI/script usage.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from db.models import Base


# ── Engine ─────────────────────────────────────────────────────────────────────

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # needed for SQLite
    echo=settings.debug,
)


# Enable WAL mode for SQLite — better concurrent read performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ── Session factory ────────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables. Called once on `applycopilot init`."""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables. For dev/testing only."""
    Base.metadata.drop_all(bind=engine)


# ── FastAPI dependency ─────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """Yield a database session. Use as FastAPI Depends()."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── CLI / script context manager ───────────────────────────────────────────────

@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for CLI commands and scripts."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
