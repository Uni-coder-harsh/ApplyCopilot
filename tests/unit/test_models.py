"""
Unit tests for SQLAlchemy models.
Verifies all 16 tables create correctly and relationships work.
"""

from db.models import (
    User, Profile, SocialLink, Skill, Project, Education,
    EmailAccount, Email, Contact, Job, Application,
    Resume, ResumeSection, MatchScore, Followup, Attachment,
    JobType, ApplicationStatus, ApplicationStage,
    EmailCategory, EmailDirection, SkillSource, SkillCategory,
)


def test_user_created(db_session):
    from argon2 import PasswordHasher
    ph = PasswordHasher()
    user = User(username="alice", password_hash=ph.hash("secret"))
    db_session.add(user)
    db_session.flush()
    assert user.id is not None
    assert user.username == "alice"


def test_profile_linked_to_user(db_session, sample_user):
    assert sample_user.profile is not None
    assert sample_user.profile.user_id == sample_user.id


def test_skill_created(db_session, sample_user):
    skill = Skill(
        profile_id=sample_user.profile.id,
        name="Python",
        category=SkillCategory.PROGRAMMING,
        level="expert",
        source=SkillSource.MANUAL,
    )
    db_session.add(skill)
    db_session.flush()
    assert skill.id is not None


def test_job_and_application(db_session, sample_user):
    job = Job(company="Anthropic", role="ML Intern", type=JobType.INDUSTRY)
    db_session.add(job)
    db_session.flush()

    app = Application(
        job_id=job.id,
        status=ApplicationStatus.ACTIVE,
        stage=ApplicationStage.APPLIED,
    )
    db_session.add(app)
    db_session.flush()

    assert app.id is not None
    assert app.job.company == "Anthropic"


def test_all_tables_exist(test_engine):
    """Verify all 16 tables are present in the schema."""
    from sqlalchemy import inspect
    inspector = inspect(test_engine)
    tables = set(inspector.get_table_names())
    expected = {
        "users", "profiles", "social_links", "skills", "projects",
        "education", "email_accounts", "emails", "contacts", "jobs",
        "applications", "resumes", "resume_sections", "match_scores",
        "followups", "attachments",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"
