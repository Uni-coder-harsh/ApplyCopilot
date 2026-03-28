"""
Converts RawEmail objects into structured dicts ready for DB insertion.
Also handles sender name/email extraction and direction detection.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.email.base import RawEmail


# Regex to extract name + email from "Name <email@domain.com>" format
_EMAIL_RE = re.compile(r"([^<]*)<([^>]+)>|([^\s]+@[^\s]+)")


@dataclass
class ParsedEmail:
    """Structured email record ready for DB insertion."""
    message_id: str
    thread_id: Optional[str]
    subject: str
    sender_name: str
    sender_email: str
    recipients: list[str]
    body: str
    snippet: str
    timestamp: datetime
    direction: str          # "incoming" | "outgoing"
    is_job_related: bool    # set to False initially, AI classifier updates this
    category: str           # set to "other" initially, AI classifier updates this
    raw_snippet: str        # first 500 chars for AI classification


def parse_sender(raw_sender: str) -> tuple[str, str]:
    """
    Extract (name, email) from a raw From header.
    'John Doe <john@example.com>' → ('John Doe', 'john@example.com')
    'john@example.com'            → ('', 'john@example.com')
    """
    raw_sender = raw_sender.strip()
    match = _EMAIL_RE.search(raw_sender)
    if not match:
        return ("", raw_sender)

    if match.group(2):
        name = match.group(1).strip().strip('"').strip("'")
        email_addr = match.group(2).strip().lower()
        return (name, email_addr)
    elif match.group(3):
        return ("", match.group(3).strip().lower())

    return ("", raw_sender)


def detect_direction(sender_email: str, account_email: str) -> str:
    """
    Determine if an email is incoming or outgoing based on the sender.
    Outgoing = sent by the account owner.
    """
    return "outgoing" if sender_email.lower() == account_email.lower() else "incoming"


def build_classification_snippet(raw: RawEmail) -> str:
    """
    Build a short text snippet for the AI classifier.
    Combines subject + first 400 chars of body.
    """
    subject_part = f"Subject: {raw.subject}\n"
    body_part = raw.body_text[:400] if raw.body_text else ""
    return (subject_part + body_part).strip()


def parse_raw_email(raw: RawEmail, account_email: str) -> ParsedEmail:
    """Convert a RawEmail into a ParsedEmail ready for DB insertion."""
    sender_name, sender_email = parse_sender(raw.sender)
    direction = detect_direction(sender_email, account_email)

    # Use plain text body; fall back to a stripped version of HTML if needed
    body = raw.body_text.strip() if raw.body_text else ""
    if not body and raw.body_html:
        # Very basic HTML strip — just remove tags
        body = re.sub(r"<[^>]+>", " ", raw.body_html)
        body = re.sub(r"\s+", " ", body).strip()

    snippet = body[:200].replace("\n", " ").strip()

    return ParsedEmail(
        message_id=raw.message_id,
        thread_id=raw.thread_id,
        subject=raw.subject,
        sender_name=sender_name,
        sender_email=sender_email,
        recipients=raw.recipients,
        body=body,
        snippet=snippet,
        timestamp=raw.timestamp,
        direction=direction,
        is_job_related=False,   # AI classifier sets this
        category="other",       # AI classifier sets this
        raw_snippet=build_classification_snippet(raw),
    )


def parse_batch(raws: list[RawEmail], account_email: str) -> list[ParsedEmail]:
    """Parse a batch of RawEmails."""
    parsed = []
    for raw in raws:
        try:
            parsed.append(parse_raw_email(raw, account_email))
        except Exception:
            continue
    return parsed
