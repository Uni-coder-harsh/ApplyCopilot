"""
Follow-up tracker — logic for scheduling and querying follow-ups.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from db.models import Application, ApplicationStage, ApplicationStatus, Followup, Job


# Default follow-up windows by stage (days)
FOLLOWUP_WINDOWS = {
    ApplicationStage.COLD_EMAIL_SENT: 7,
    ApplicationStage.APPLIED: 14,
    ApplicationStage.AWAITING_REPLY: 7,
    ApplicationStage.OA: 3,
    ApplicationStage.INTERVIEW: 5,
    ApplicationStage.FINAL_ROUND: 7,
}
def _make_aware(dt: datetime) -> datetime:
    """Add UTC timezone to a naive datetime from SQLite."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_due_followups(db: Session) -> list[tuple[Application, Job, Optional[Followup]]]:
    now = datetime.now(timezone.utc)

    results = (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.status == ApplicationStatus.ACTIVE)
        .all()
    )

    due = []
    for app, job in results:
        # Explicit follow-up date set
        if app.followup_date:
            fu_date = _make_aware(app.followup_date)
            if fu_date <= now:
                last_followup = _get_last_followup(db, app.id)
                due.append((app, job, last_followup))
                continue

        # Stage-based automatic follow-up window
        window = FOLLOWUP_WINDOWS.get(app.stage)
        if window and app.last_updated:
            last_updated = _make_aware(app.last_updated)
            cutoff = last_updated + timedelta(days=window)
            if cutoff <= now:
                last_followup = _get_last_followup(db, app.id)
                due.append((app, job, last_followup))

    return due


def get_upcoming_followups(db: Session, days: int = 7) -> list[tuple[Application, Job]]:
    """Return applications with follow-ups due within the next N days."""
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=days)

    return (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(
            Application.status == ApplicationStatus.ACTIVE,
            Application.followup_date.isnot(None),
            Application.followup_date > now,
            Application.followup_date <= soon,
        )
        .order_by(Application.followup_date.asc())
        .all()
    )


def mark_followup_sent(db: Session, app_id: int, notes: Optional[str] = None) -> Followup:
    """Record that a follow-up was sent for an application."""
    followup = Followup(
        application_id=app_id,
        date=datetime.now(timezone.utc),
        status="sent",
        notes=notes,
    )
    db.add(followup)

    # Clear the followup_date so it doesn't keep showing as due
    app = db.query(Application).filter(Application.id == app_id).first()
    if app:
        app.followup_date = None

    db.commit()
    return followup


def mark_followup_skipped(db: Session, app_id: int, notes: Optional[str] = None) -> Followup:
    """Record that a follow-up was skipped."""
    followup = Followup(
        application_id=app_id,
        date=datetime.now(timezone.utc),
        status="skipped",
        notes=notes,
    )
    db.add(followup)

    app = db.query(Application).filter(Application.id == app_id).first()
    if app:
        app.followup_date = None

    db.commit()
    return followup


def suggest_followup_date(stage: ApplicationStage) -> Optional[datetime]:
    """Suggest a follow-up date based on the current application stage."""
    window = FOLLOWUP_WINDOWS.get(stage)
    if not window:
        return None
    return datetime.now(timezone.utc) + timedelta(days=window)


def _get_last_followup(db: Session, app_id: int) -> Optional[Followup]:
    """Get the most recent follow-up record for an application."""
    return (
        db.query(Followup)
        .filter(Followup.application_id == app_id)
        .order_by(Followup.date.desc())
        .first()
    )
