"""
Application tracker — CRUD and query logic.
All business logic lives here. CLI commands call these functions.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.models import (
    Application, ApplicationStage, ApplicationStatus,
    Job, JobType, Contact,
)


# ── Read ───────────────────────────────────────────────────────────────────────

def get_applications(
    db: Session,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    job_type: Optional[str] = None,
    min_score: Optional[float] = None,
    search: Optional[str] = None,
    limit: int = 100,
) -> list[tuple[Application, Job]]:
    """
    Return applications with their associated job, filtered by any combination
    of status, stage, job_type, min_score, and free-text search.
    """
    query = (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
    )

    if status:
        try:
            query = query.filter(Application.status == ApplicationStatus(status.lower()))
        except ValueError:
            pass

    if stage:
        try:
            query = query.filter(Application.stage == ApplicationStage(stage.lower()))
        except ValueError:
            pass

    if job_type:
        try:
            query = query.filter(Job.type == JobType(job_type.lower()))
        except ValueError:
            pass

    if min_score is not None:
        query = query.filter(Application.match_score >= min_score)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Job.company.ilike(term),
                Job.role.ilike(term),
                Job.domain.ilike(term),
                Application.notes.ilike(term),
            )
        )

    return (
        query
        .order_by(Application.last_updated.desc())
        .limit(limit)
        .all()
    )


def get_application_by_id(db: Session, app_id: int) -> Optional[tuple[Application, Job]]:
    """Fetch a single application + job by application ID."""
    return (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.id == app_id)
        .first()
    )


# ── Update ─────────────────────────────────────────────────────────────────────

def update_stage(db: Session, app_id: int, new_stage: str) -> Optional[Application]:
    """Update the stage of an application."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        return None
    try:
        app.stage = ApplicationStage(new_stage.lower())
        app.last_updated = datetime.now(timezone.utc)
        db.commit()
        return app
    except ValueError:
        return None


def update_status(db: Session, app_id: int, new_status: str) -> Optional[Application]:
    """Update the status of an application (active/rejected/closed/offer)."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        return None
    try:
        app.status = ApplicationStatus(new_status.lower())
        app.last_updated = datetime.now(timezone.utc)
        db.commit()
        return app
    except ValueError:
        return None


def update_notes(db: Session, app_id: int, notes: str) -> Optional[Application]:
    """Update notes on an application."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        return None
    app.notes = notes
    app.last_updated = datetime.now(timezone.utc)
    db.commit()
    return app


def set_followup_date(db: Session, app_id: int, followup_date: datetime) -> Optional[Application]:
    """Set or update the follow-up date for an application."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        return None
    app.followup_date = followup_date
    app.last_updated = datetime.now(timezone.utc)
    db.commit()
    return app


def set_priority(db: Session, app_id: int, priority: int) -> Optional[Application]:
    """Set priority: 0=normal, 1=high, 2=urgent."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        return None
    app.priority = max(0, min(2, priority))
    db.commit()
    return app


# ── Create ─────────────────────────────────────────────────────────────────────

def add_manual_application(
    db: Session,
    company: str,
    role: str,
    job_type: str = "industry",
    stage: str = "applied",
    source: str = "manual",
    url: Optional[str] = None,
    notes: Optional[str] = None,
    domain: Optional[str] = None,
    location: Optional[str] = None,
) -> Application:
    """Manually add a job application."""
    # Find or create job
    job = (
        db.query(Job)
        .filter(Job.company == company, Job.role == role)
        .first()
    )
    if not job:
        job = Job(
            company=company,
            role=role,
            type=JobType(job_type.lower()) if job_type else JobType.INDUSTRY,
            url=url,
            domain=domain,
            location=location,
        )
        db.add(job)
        db.flush()

    app = Application(
        job_id=job.id,
        status=ApplicationStatus.ACTIVE,
        stage=ApplicationStage(stage.lower()) if stage else ApplicationStage.APPLIED,
        source=source,
        applied_date=datetime.now(timezone.utc),
        notes=notes,
    )
    db.add(app)
    db.commit()
    return app


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_summary_stats(db: Session) -> dict:
    """Return a summary of application statistics."""
    total = db.query(Application).count()
    active = db.query(Application).filter(
        Application.status == ApplicationStatus.ACTIVE
    ).count()
    interviews = db.query(Application).filter(
        Application.stage == ApplicationStage.INTERVIEW
    ).count()
    offers = db.query(Application).filter(
        Application.status == ApplicationStatus.OFFER
    ).count()
    rejections = db.query(Application).filter(
        Application.status == ApplicationStatus.REJECTED
    ).count()

    return {
        "total": total,
        "active": active,
        "interviews": interviews,
        "offers": offers,
        "rejections": rejections,
    }
