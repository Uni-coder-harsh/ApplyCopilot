"""
Email classifier — uses phi3:mini to determine if an email is
job-related and what category it belongs to.

Designed for speed: phi3:mini is fast enough to classify
200 emails in a few minutes on 6GB VRAM.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ai.client import ollama_client
from ai.prompts import EMAIL_CLASSIFICATION_PROMPT, JOB_EXTRACTION_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    is_job_related: bool
    category: str
    confidence: float
    company: Optional[str] = None
    role: Optional[str] = None


@dataclass
class JobExtractionResult:
    company: str
    role: str
    location: Optional[str] = None
    remote: bool = False
    type: str = "industry"
    domain: Optional[str] = None
    deadline: Optional[str] = None
    url: Optional[str] = None


# Valid categories — fallback to "other" if model returns something unexpected
VALID_CATEGORIES = {
    "cold_email", "professor_reply", "application_confirmation",
    "rejection", "oa", "interview", "offer", "opportunity", "other",
}


def classify_email(email_snippet: str) -> ClassificationResult:
    """
    Classify a single email snippet.
    Returns a ClassificationResult with is_job_related, category, and confidence.

    Falls back to a safe default if the model fails or returns bad JSON.
    """
    prompt = EMAIL_CLASSIFICATION_PROMPT.format(email_snippet=email_snippet[:800])

    result = ollama_client.generate_json(
        model=settings.model_classifier,
        prompt=prompt,
        temperature=0.05,   # very low — we want deterministic classification
        max_tokens=256,
    )

    if not result or not isinstance(result, dict):
        logger.warning("Classifier returned invalid JSON — defaulting to not job-related")
        return ClassificationResult(
            is_job_related=False,
            category="other",
            confidence=0.0,
        )

    category = result.get("category", "other")
    if category not in VALID_CATEGORIES:
        category = "other"

    return ClassificationResult(
        is_job_related=bool(result.get("is_job_related", False)),
        category=category,
        confidence=float(result.get("confidence", 0.5)),
        company=result.get("company"),
        role=result.get("role"),
    )


def classify_batch(
    snippets: list[tuple[str, str]],   # list of (message_id, snippet)
    progress_callback=None,
) -> dict[str, ClassificationResult]:
    """
    Classify a batch of emails.
    Returns a dict mapping message_id → ClassificationResult.

    progress_callback(current, total) is called after each classification
    so the CLI can show a progress bar.
    """
    results = {}
    total = len(snippets)

    for i, (message_id, snippet) in enumerate(snippets):
        try:
            results[message_id] = classify_email(snippet)
        except Exception as e:
            logger.error(f"Failed to classify {message_id}: {e}")
            results[message_id] = ClassificationResult(
                is_job_related=False,
                category="other",
                confidence=0.0,
            )

        if progress_callback:
            progress_callback(i + 1, total)

    return results


def extract_job_details(email_snippet: str) -> Optional[JobExtractionResult]:
    """
    For job-related emails, extract structured job info.
    Called after classify_email confirms is_job_related=True.
    Uses mistral:7b for better extraction quality.
    """
    prompt = JOB_EXTRACTION_PROMPT.format(email_snippet=email_snippet[:1200])

    result = ollama_client.generate_json(
        model=settings.model_reasoner,
        prompt=prompt,
        temperature=0.1,
        max_tokens=512,
    )

    if not result or not isinstance(result, dict):
        return None

    return JobExtractionResult(
        company=result.get("company", "Unknown"),
        role=result.get("role", "Unknown"),
        location=result.get("location"),
        remote=bool(result.get("remote", False)),
        type=result.get("type", "industry"),
        domain=result.get("domain"),
        deadline=result.get("deadline"),
        url=result.get("url"),
    )
