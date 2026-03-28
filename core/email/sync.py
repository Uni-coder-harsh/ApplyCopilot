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
    Contact, ContactType, Email, EmailAccount,
    EmailCategory, EmailDirection, Job, JobType,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Summary returned after a sync run."""
    total_fetched: int = 0
    new_emails: int = 0
    already_seen: int = 0
    job_related: int = 0
    classified: int = 0
    applications_created: int = 0
    errors: int = 0


def get_existing_message_ids(db: Session, account_id: int) -> set[str]:
    """Fetch all message_ids already stored for this account."""
    rows = db.query(Email.message_id).filter(Email.account_id == account_id).all()
    return {r[0] for r in rows}


def persist_emails(
    db: Session,
    account: EmailAccount,
    parsed_emails,
    classification_results: dict,
) -> tuple[list[Email], int]:
    """
    Save parsed + classified emails to the database.
    Returns (list of new Email ORM objects, count of job-related).
    """
    saved = []
    job_count = 0

    for pe in parsed_emails:
        clf = classification_results.get(pe.message_id)
        is_job = clf.is_job_related if clf else False
        category = clf.category if clf else "other"

        if is_job:
            job_count += 1

        email_record = Email(
            account_id=account.id,
            message_id=pe.message_id,
            thread_id=pe.thread_id,
            subject=pe.subject,
            sender=f"{pe.sender_name} <{pe.sender_email}>".strip(),
            recipients=pe.recipients,
            body=pe.body[:50_000],   # cap at 50k chars
            snippet=pe.snippet,
            timestamp=pe.timestamp,
            direction=EmailDirection.OUTGOING if pe.direction == "outgoing" else EmailDirection.INCOMING,
            category=_map_category(category),
            is_job_related=is_job,
            ai_classified=clf is not None,
        )
        db.add(email_record)
        saved.append(email_record)

    db.flush()  # assign IDs without committing
    return saved, job_count


def create_application_from_email(
    db: Session,
    email_record: Email,
    classification,
) -> bool:
    """
    For job-related emails, try to extract job details and create
    a Job + Application record if one doesn't already exist.
    Returns True if a new application was created.
    """
    if not email_record.body:
        return False

    snippet = f"Subject: {email_record.subject}\n{email_record.body[:800]}"
    job_details = extract_job_details(snippet)

    if not job_details:
        return False

    # Check if we already have a job record for this company + role
    existing_job = (
        db.query(Job)
        .filter(
            Job.company == job_details.company,
            Job.role == job_details.role,
        )
        .first()
    )

    if not existing_job:
        job = Job(
            company=job_details.company,
            role=job_details.role,
            location=job_details.location,
            remote=job_details.remote,
            type=_map_job_type(job_details.type),
            domain=job_details.domain,
            url=job_details.url,
        )
        db.add(job)
        db.flush()
    else:
        job = existing_job

    # Check if an application for this job already exists
    existing_app = (
        db.query(Application)
        .filter(Application.job_id == job.id)
        .first()
    )

    if existing_app:
        return False

    # Determine stage from category
    stage = _category_to_stage(email_record.category.value if email_record.category else "other")

    app = Application(
        job_id=job.id,
        email_thread_id=email_record.id,
        status=ApplicationStatus.ACTIVE,
        stage=stage,
        source="email",
        applied_date=email_record.timestamp,
    )
    db.add(app)
    return True


def run_sync(
    db: Session,
    account: EmailAccount,
    adapter: EmailAdapter,
    progress_callback=None,
) -> SyncResult:
    """
    Full sync pipeline for one email account.

    1. Fetch emails from adapter
    2. Filter out already-seen message_ids
    3. Parse new emails
    4. Run AI classification
    5. Persist to DB
    6. Create Job + Application records for job-related emails
    7. Update account.last_sync timestamp
    """
    result = SyncResult()

    # Step 1: Fetch
    logger.info(f"Fetching emails for {account.email}")
    raw_emails = adapter.fetch_emails(
        max_count=settings.email_sync_batch_size,
        since_days=settings.email_max_age_days,
    )
    result.total_fetched = len(raw_emails)

    if not raw_emails:
        logger.info("No emails fetched")
        return result

    # Step 2: Deduplicate
    existing_ids = get_existing_message_ids(db, account.id)
    new_raws = [r for r in raw_emails if r.message_id not in existing_ids]
    result.already_seen = result.total_fetched - len(new_raws)
    result.new_emails = len(new_raws)

    if not new_raws:
        logger.info("No new emails to process")
        return result

    logger.info(f"{result.new_emails} new emails to process")

    # Step 3: Parse
    parsed = parse_batch(new_raws, account.email)

    # Step 4: AI classification
    logger.info("Running AI classification...")
    snippets = [(p.message_id, p.raw_snippet) for p in parsed]

    def _progress(current, total):
        if progress_callback:
            progress_callback("classify", current, total)

    classifications = classify_batch(snippets, progress_callback=_progress)
    result.classified = len(classifications)

    # Step 5: Persist emails
    saved_emails, job_count = persist_emails(db, account, parsed, classifications)
    result.job_related = job_count

    # Step 6: Create applications for job-related emails
    for email_record in saved_emails:
        if email_record.is_job_related:
            try:
                created = create_application_from_email(
                    db, email_record, classifications.get(email_record.message_id)
                )
                if created:
                    result.applications_created += 1
            except Exception as e:
                logger.warning(f"Failed to create application from email {email_record.message_id}: {e}")
                result.errors += 1

    # Step 7: Update last_sync
    account.last_sync = datetime.now(timezone.utc)

    logger.info(
        f"Sync complete: {result.new_emails} new, "
        f"{result.job_related} job-related, "
        f"{result.applications_created} applications created"
    )
    return result


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def _map_job_type(type_str: str) -> JobType:
    mapping = {
        "research": JobType.RESEARCH,
        "industry": JobType.INDUSTRY,
        "fellowship": JobType.FELLOWSHIP,
        "ra": JobType.RA,
        "open_source": JobType.OPEN_SOURCE,
    }
    return mapping.get(type_str, JobType.INDUSTRY)


def _category_to_stage(category: str):
    from db.models import ApplicationStage
    mapping = {
        "cold_email": ApplicationStage.COLD_EMAIL_SENT,
        "application_confirmation": ApplicationStage.APPLIED,
        "oa": ApplicationStage.OA,
        "interview": ApplicationStage.INTERVIEW,
        "offer": ApplicationStage.OFFER,
        "professor_reply": ApplicationStage.AWAITING_REPLY,
    }
    return mapping.get(category, ApplicationStage.AWAITING_REPLY)
