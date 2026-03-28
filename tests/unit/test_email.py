"""
Unit tests for email parser and classifier logic.
Classifier tests mock Ollama — no real model needed.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from core.email.base import RawEmail
from core.email.parser import (
    parse_sender,
    detect_direction,
    build_classification_snippet,
    parse_raw_email,
)


# ── Parser tests ───────────────────────────────────────────────────────────────

def test_parse_sender_full():
    name, email = parse_sender("John Doe <john@example.com>")
    assert name == "John Doe"
    assert email == "john@example.com"


def test_parse_sender_email_only():
    name, email = parse_sender("john@example.com")
    assert name == ""
    assert email == "john@example.com"


def test_parse_sender_quoted_name():
    name, email = parse_sender('"Prof. Sharma" <sharma@iit.ac.in>')
    assert "Sharma" in name
    assert email == "sharma@iit.ac.in"


def test_detect_direction_incoming():
    direction = detect_direction("hr@company.com", "me@gmail.com")
    assert direction == "incoming"


def test_detect_direction_outgoing():
    direction = detect_direction("me@gmail.com", "me@gmail.com")
    assert direction == "outgoing"


def test_detect_direction_case_insensitive():
    direction = detect_direction("ME@GMAIL.COM", "me@gmail.com")
    assert direction == "outgoing"


def test_parse_raw_email_basic():
    raw = RawEmail(
        message_id="<test123@example.com>",
        subject="Research Internship Opportunity",
        sender="Prof. Kumar <kumar@iitb.ac.in>",
        recipients=["harsh@gmail.com"],
        body_text="Dear Harsh, I am looking for a research intern...",
        body_html="",
        timestamp=datetime(2025, 1, 15, tzinfo=timezone.utc),
        thread_id=None,
    )
    parsed = parse_raw_email(raw, "harsh@gmail.com")
    assert parsed.message_id == "<test123@example.com>"
    assert parsed.sender_email == "kumar@iitb.ac.in"
    assert parsed.sender_name == "Prof. Kumar"
    assert parsed.direction == "incoming"
    assert parsed.is_job_related is False  # set by classifier, not parser
    assert len(parsed.snippet) <= 200


def test_parse_raw_email_outgoing():
    raw = RawEmail(
        message_id="<out456@example.com>",
        subject="Application for ML Intern Position",
        sender="Harsh <harsh@gmail.com>",
        recipients=["hr@company.com"],
        body_text="Dear Hiring Manager, I am writing to apply...",
        body_html="",
        timestamp=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )
    parsed = parse_raw_email(raw, "harsh@gmail.com")
    assert parsed.direction == "outgoing"


def test_build_classification_snippet():
    raw = RawEmail(
        message_id="<x>",
        subject="Interview Invitation",
        sender="hr@google.com",
        recipients=["harsh@gmail.com"],
        body_text="We would like to invite you for a technical interview...",
        body_html="",
        timestamp=datetime.now(timezone.utc),
    )
    snippet = build_classification_snippet(raw)
    assert "Interview Invitation" in snippet
    assert "interview" in snippet.lower()


# ── Classifier tests (mocked) ──────────────────────────────────────────────────

def test_classify_email_job_related():
    mock_result = {
        "is_job_related": True,
        "category": "interview",
        "confidence": 0.95,
        "company": "Google",
        "role": "ML Intern",
    }
    with patch("ai.classifier.ollama_client") as mock_client:
        mock_client.generate_json.return_value = mock_result
        from ai.classifier import classify_email
        result = classify_email("Subject: Interview at Google\nWe'd like to schedule...")
        assert result.is_job_related is True
        assert result.category == "interview"
        assert result.company == "Google"


def test_classify_email_not_job_related():
    mock_result = {
        "is_job_related": False,
        "category": "other",
        "confidence": 0.9,
        "company": None,
        "role": None,
    }
    with patch("ai.classifier.ollama_client") as mock_client:
        mock_client.generate_json.return_value = mock_result
        from ai.classifier import classify_email
        result = classify_email("Subject: Your Amazon order has shipped\nHi, your package...")
        assert result.is_job_related is False
        assert result.category == "other"


def test_classify_email_bad_json_fallback():
    with patch("ai.classifier.ollama_client") as mock_client:
        mock_client.generate_json.return_value = None
        from ai.classifier import classify_email
        result = classify_email("Subject: Some email")
        assert result.is_job_related is False
        assert result.category == "other"
        assert result.confidence == 0.0


def test_classify_email_invalid_category_normalised():
    mock_result = {
        "is_job_related": True,
        "category": "totally_made_up_category",
        "confidence": 0.7,
    }
    with patch("ai.classifier.ollama_client") as mock_client:
        mock_client.generate_json.return_value = mock_result
        from ai.classifier import classify_email
        result = classify_email("Subject: Some job email")
        assert result.category == "other"   # invalid → normalised to "other"
