"""
Unit tests for the application tracker and follow-up logic.
"""

from datetime import datetime, timedelta, timezone

from db.models import (
    Application, ApplicationStage, ApplicationStatus,
    Job, JobType, Followup,
)
from core.tracker.application import (
    add_manual_application,
    get_applications,
    get_application_by_id,
    update_stage,
    update_status,
    update_notes,
    set_followup_date,
    get_summary_stats,
)
from core.tracker.followup import (
    get_due_followups,
    mark_followup_sent,
    suggest_followup_date,
)


def _make_job(db, company="TestCorp", role="ML Intern"):
    job = Job(company=company, role=role, type=JobType.INDUSTRY)
    db.add(job)
    db.flush()
    return job


def _make_app(db, job, stage=ApplicationStage.APPLIED, status=ApplicationStatus.ACTIVE):
    app = Application(
        job_id=job.id,
        stage=stage,
        status=status,
        applied_date=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
    )
    db.add(app)
    db.flush()
    return app


# ── Application CRUD ───────────────────────────────────────────────────────────

def test_add_manual_application(db_session):
    app = add_manual_application(
        db_session,
        company="Google",
        role="SWE Intern",
        job_type="industry",
        stage="applied",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.ACTIVE
    assert app.stage == ApplicationStage.APPLIED


def test_add_manual_application_deduplicates_job(db_session):
    app1 = add_manual_application(db_session, company="Meta", role="Research Intern")
    app2 = add_manual_application(db_session, company="Meta", role="Research Intern")
    assert app1.job_id == app2.job_id


def test_get_applications_returns_results(db_session):
    job = _make_job(db_session)
    _make_app(db_session, job)
    results = get_applications(db_session)
    assert len(results) >= 1


def test_get_applications_filter_by_status(db_session):
    job = _make_job(db_session, company="FilterCorp")
    _make_app(db_session, job, status=ApplicationStatus.REJECTED)
    results = get_applications(db_session, status="rejected")
    assert all(a.status == ApplicationStatus.REJECTED for a, _ in results)


def test_get_applications_filter_by_stage(db_session):
    job = _make_job(db_session, company="StageCorp")
    _make_app(db_session, job, stage=ApplicationStage.INTERVIEW)
    results = get_applications(db_session, stage="interview")
    assert all(a.stage == ApplicationStage.INTERVIEW for a, _ in results)


def test_get_application_by_id(db_session):
    job = _make_job(db_session)
    app = _make_app(db_session, job)
    result = get_application_by_id(db_session, app.id)
    assert result is not None
    found_app, found_job = result
    assert found_app.id == app.id


def test_get_application_by_id_not_found(db_session):
    result = get_application_by_id(db_session, 999999)
    assert result is None


def test_update_stage(db_session):
    job = _make_job(db_session)
    app = _make_app(db_session, job)
    updated = update_stage(db_session, app.id, "interview")
    assert updated.stage == ApplicationStage.INTERVIEW


def test_update_status(db_session):
    job = _make_job(db_session)
    app = _make_app(db_session, job)
    updated = update_status(db_session, app.id, "rejected")
    assert updated.status == ApplicationStatus.REJECTED


def test_update_notes(db_session):
    job = _make_job(db_session)
    app = _make_app(db_session, job)
    updated = update_notes(db_session, app.id, "Spoke to recruiter on Monday")
    assert updated.notes == "Spoke to recruiter on Monday"


def test_get_summary_stats(db_session):
    stats = get_summary_stats(db_session)
    assert "total" in stats
    assert "active" in stats
    assert "interviews" in stats
    assert stats["total"] >= 0


# ── Follow-up logic ────────────────────────────────────────────────────────────

def test_get_due_followups_overdue(db_session):
    job = _make_job(db_session, company="OverdueCorp")
    app = _make_app(db_session, job, stage=ApplicationStage.APPLIED)
    # Set follow-up date to yesterday
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    set_followup_date(db_session, app.id, yesterday)

    due = get_due_followups(db_session)
    due_ids = [a.id for a, _, _ in due]
    assert app.id in due_ids


def test_mark_followup_sent(db_session):
    job = _make_job(db_session, company="FollowupCorp")
    app = _make_app(db_session, job)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    set_followup_date(db_session, app.id, yesterday)

    fu = mark_followup_sent(db_session, app.id, notes="Sent follow-up email")
    assert fu.status == "sent"
    assert fu.notes == "Sent follow-up email"


def test_suggest_followup_date_applied(db_session):
    suggested = suggest_followup_date(ApplicationStage.APPLIED)
    assert suggested is not None
    diff = suggested - datetime.now(timezone.utc)
    assert 13 <= diff.days <= 14   # 14-day window
