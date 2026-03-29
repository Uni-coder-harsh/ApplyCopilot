"""
Email sync pipeline.
Pulls emails from an adapter, parses them, deduplicates against the DB,
runs AI classification on new ones, and persists everything.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ai.classifier import classify_batch, extract_job_details
from core.email.base import EmailAdapter
from core.email.parser import parse_batch
from config.settings import settings
from db.models import (
    Application, ApplicationStage, ApplicationStatus,
    Email, EmailAccount,
    EmailCategory, EmailDirection, Job, JobType,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    total_fetched: int = 0
    new_emails: int = 0
    already_seen: int = 0
    job_related: int = 0
    classified: int = 0
    applications_created: int = 0
    errors: int = 0


def get_existing_message_ids(db: Session, account_id: int) -> set[str]:
    rows = db.query(Email.message_id).filter(Email.account_id == account_id).all()
    return {r[0] for r in rows}


def persist_emails(
    db: Session,
    account_id: int,
    parsed_emails,
    classification_results: dict,
) -> tuple[list[int], int]:
    """
    Save parsed + classified emails to the database.
    Returns (list of saved email IDs, count of job-related).
    Commits immediately so IDs are stable.
    """
    job_count = 0
    saved_ids = []

    for pe in parsed_emails:
        clf = classification_results.get(pe.message_id)
        is_job = clf.is_job_related if clf else False
        category = clf.category if clf else "other"

        if is_job:
            job_count += 1

        email_record = Email(
            account_id=account_id,
            message_id=pe.message_id,
            thread_id=pe.thread_id,
            subject=pe.subject,
            sender=f"{pe.sender_name} <{pe.sender_email}>".strip(),
            recipients=pe.recipients,
            body=pe.body[:50_000],
            snippet=pe.snippet,
            timestamp=pe.timestamp,
            direction=EmailDirection.OUTGOING if pe.direction == "outgoing" else EmailDirection.INCOMING,
            category=_map_category(category),
            is_job_related=is_job,
            ai_classified=clf is not None,
        )
        db.add(email_record)

    # Commit all emails in one shot
    db.commit()

    # Now fetch back the IDs of job-related emails
    job_email_ids = (
        db.query(Email.id, Email.subject, Email.body, Email.category, Email.timestamp)
        .filter(
            Email.account_id == account_id,
            Email.is_job_related == True,
        )
        .order_by(Email.id.desc())
        .limit(len(parsed_emails))
        .all()
    )

    return job_email_ids, job_count


def create_application_from_email(db: Session, email_row) -> bool:
    """
    For job-related emails, extract job details and create
    Job + Application records. Uses savepoints for safety.
    """
    email_id, subject, body, category, timestamp = email_row

    if not body:
        return False

    snippet = f"Subject: {subject}\n{body[:800]}"
    job_details = extract_job_details(snippet)

    if not job_details:
        return False

    # Fallback for null role — use "Unknown Role" rather than skipping
    company = (job_details.company or "").strip() or "Unknown Company"
    role = (job_details.role or "").strip() or "Unknown Role"

    try:
        with db.begin_nested():
            existing_job = (
                db.query(Job)
                .filter(Job.company == company, Job.role == role)
                .first()
            )

            if not existing_job:
                job = Job(
                    company=company,
                    role=role,
                    location=job_details.location,
                    remote=bool(job_details.remote),
                    type=_map_job_type(job_details.type),
                    domain=job_details.domain,
                    url=_safe_url(job_details.url),
                )
                db.add(job)
                db.flush()
            else:
                job = existing_job

            existing_app = (
                db.query(Application)
                .filter(Application.job_id == job.id)
                .first()
            )
            if existing_app:
                return False

            stage = _category_to_stage(category.value if hasattr(category, "value") else str(category))
            app = Application(
                job_id=job.id,
                email_thread_id=email_id,
                status=ApplicationStatus.ACTIVE,
                stage=stage,
                source="email",
                applied_date=timestamp,
            )
            db.add(app)
            return True

    except Exception as e:
        logger.warning(f"Savepoint rolled back for email_id={email_id}: {e}")
        return False


def run_sync(
    db: Session,
    account_id: int,
    adapter: EmailAdapter,
    progress_callback=None,
) -> SyncResult:
    """
    Full sync pipeline for one email account.
    Takes account_id (int) instead of the ORM object to avoid
    cross-session tracking issues with SQLAlchemy.
    """
    result = SyncResult()

    # Step 1: Fetch
    logger.info(f"Fetching emails for account_id={account_id}")
    raw_emails = adapter.fetch_emails(
        max_count=settings.email_sync_batch_size,
        since_days=settings.email_max_age_days,
    )
    result.total_fetched = len(raw_emails)

    if not raw_emails:
        return result

    # Step 2: Deduplicate
    existing_ids = get_existing_message_ids(db, account_id)
    new_raws = [r for r in raw_emails if r.message_id not in existing_ids]
    result.already_seen = result.total_fetched - len(new_raws)
    result.new_emails = len(new_raws)

    if not new_raws:
        return result

    # Step 3: Parse
    # We need the account email for direction detection — fetch it fresh
    account = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    account_email = account.email if account else ""
    parsed = parse_batch(new_raws, account_email)

    # Step 4: AI classification
    snippets = [(p.message_id, p.raw_snippet) for p in parsed]

    def _progress(current, total):
        if progress_callback:
            progress_callback("classify", current, total)

    classifications = classify_batch(snippets, progress_callback=_progress)
    result.classified = len(classifications)

    # Step 5: Persist emails + commit
    job_email_rows, job_count = persist_emails(db, account_id, parsed, classifications)
    result.job_related = job_count

    # Step 6: Create Job + Application records
    for email_row in job_email_rows:
        try:
            created = create_application_from_email(db, email_row)
            if created:
                result.applications_created += 1
        except Exception as e:
            logger.warning(f"Failed to create application: {e}")
            result.errors += 1

    # Commit applications
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Final commit failed: {e}")
        db.rollback()

    # Step 7: Update last_sync
    try:
        db.query(EmailAccount).filter(EmailAccount.id == account_id).update(
            {"last_sync": datetime.now(timezone.utc)}
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Could not update last_sync: {e}")

    logger.info(
        f"Sync complete: {result.new_emails} new, "
        f"{result.job_related} job-related, "
        f"{result.applications_created} applications created"
    )
    return result


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_url(url: str | None) -> str | None:
    """Strip angle brackets that models sometimes wrap URLs in."""
    if not url:
        return None
    return url.strip("<>").strip()


def _map_category(category: str) -> EmailCategory:
    mapping = {
        "cold_email": EmailCategory.COLD_EMAIL,
        "professor_reply": EmailCategory.PROFESSOR_REPLY,
        "application_confirmation": EmailCategory.APPLICATION_CONFIRM,
        "rejection": EmailCategory.REJECTION,
        "oa": EmailCategory.OA,
        "interview": EmailCategory.INTERVIEW,
        "offer": EmailCategory.OFFER,
        "opportunity": EmailCategory.OPPORTUNITY,
    }
    return mapping.get(category, EmailCategory.OTHER)


def _map_job_type(type_str: str | None) -> JobType:
    mapping = {
        "research": JobType.RESEARCH,
        "industry": JobType.INDUSTRY,
        "fellowship": JobType.FELLOWSHIP,
        "ra": JobType.RA,
        "open_source": JobType.OPEN_SOURCE,
    }
    return mapping.get(str(type_str).lower() if type_str else "", JobType.INDUSTRY)


def _category_to_stage(category: str) -> ApplicationStage:
    mapping = {
        "cold_email": ApplicationStage.COLD_EMAIL_SENT,
        "application_confirmation": ApplicationStage.APPLIED,
        "oa": ApplicationStage.OA,
        "interview": ApplicationStage.INTERVIEW,
        "offer": ApplicationStage.OFFER,
        "professor_reply": ApplicationStage.AWAITING_REPLY,
        "opportunity": ApplicationStage.AWAITING_REPLY,
    }
    return mapping.get(category.lower(), ApplicationStage.AWAITING_REPLY)
