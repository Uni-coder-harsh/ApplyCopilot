"""
Shared pytest fixtures for ApplyCopilot tests.
Uses an in-memory SQLite DB so tests never touch real data.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base


@pytest.fixture(scope="session")
def test_engine():
    """In-memory SQLite engine for the entire test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Fresh database session per test, rolled back after each test."""
    TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_user(db_session):
    """A pre-created test user."""
    from db.models import User, Profile
    from argon2 import PasswordHasher

    ph = PasswordHasher()
    user = User(username="testuser", password_hash=ph.hash("testpass123"))
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id, full_name="Test User")
    db_session.add(profile)
    db_session.flush()

    return user
