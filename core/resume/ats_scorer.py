"""
ATS scorer — checks keyword density between resume and job description.
Gives a score and highlights missing keywords so the user knows
what to add before submitting.
"""

import re
from dataclasses import dataclass

from core.resume.builder import ResumeData


# Common filler words to ignore when extracting keywords
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "are", "was", "were",
    "be", "been", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall",
    "we", "you", "they", "he", "she", "it", "this", "that", "which",
    "who", "what", "how", "when", "where", "why", "our", "your",
    "their", "its", "all", "any", "both", "each", "more", "also",
    "as", "if", "so", "than", "then", "not", "no", "nor",
}


@dataclass
class ATSResult:
    overall_score: float          # 0–100
    keyword_score: float          # keyword overlap score
    matched_keywords: list[str]   # keywords found in resume
    missing_keywords: list[str]   # important JD keywords not in resume
    suggestions: list[str]        # actionable tips


def score_resume(resume_data: ResumeData, job_description: str) -> ATSResult:
    """
    Score the resume against a job description.
    Returns an ATSResult with score and actionable feedback.
    """
    resume_text = _build_resume_text(resume_data)
    jd_keywords = _extract_keywords(job_description)
    resume_keywords = _extract_keywords(resume_text)

    matched = [kw for kw in jd_keywords if kw in resume_keywords]
    missing = [kw for kw in jd_keywords if kw not in resume_keywords]

    keyword_score = (len(matched) / len(jd_keywords) * 100) if jd_keywords else 0

    # Bonus points for having key sections populated
    section_score = 0
    if resume_data.summary or resume_data.tailored_summary:
        section_score += 10
    if resume_data.skill_groups:
        section_score += 10
    if resume_data.projects:
        section_score += 10
    if resume_data.education:
        section_score += 10

    overall = min(100, keyword_score * 0.6 + section_score)

    suggestions = _generate_suggestions(
        resume_data, missing, keyword_score, overall
    )

    return ATSResult(
        overall_score=round(overall, 1),
        keyword_score=round(keyword_score, 1),
        matched_keywords=matched[:20],
        missing_keywords=missing[:15],
        suggestions=suggestions,
    )


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text."""
    text = text.lower()
    # Extract words and common tech abbreviations (e.g. "ml", "nlp", "api")
    words = re.findall(r"\b[a-z][a-z0-9+#._-]{1,30}\b", text)
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _build_resume_text(resume_data: ResumeData) -> str:
    """Flatten all resume content into a single string for keyword matching."""
    parts = [
        resume_data.full_name,
        resume_data.tailored_summary or resume_data.summary or "",
    ]

    for group in resume_data.skill_groups:
        parts.append(group.category)
        parts.extend(group.skills)

    projects = resume_data.tailored_projects or resume_data.projects
    for project in projects:
        parts.append(project.name)
        parts.append(project.description or "")
        parts.extend(project.tech_stack or [])
        parts.append(project.impact or "")

    for edu in resume_data.education:
        parts.extend([edu.institution, edu.degree, edu.field])

    return " ".join(filter(None, parts))


def _generate_suggestions(
    resume_data: ResumeData,
    missing_keywords: list[str],
    keyword_score: float,
    overall_score: float,
) -> list[str]:
    suggestions = []

    if not resume_data.summary and not resume_data.tailored_summary:
        suggestions.append("Add a professional summary — many ATS systems require it")

    if not resume_data.skill_groups:
        suggestions.append("Add your skills — ATS systems scan for keyword matches")

    if not resume_data.projects:
        suggestions.append("Add projects — they are a key differentiator for student applications")

    if keyword_score < 40:
        top_missing = missing_keywords[:5]
        if top_missing:
            suggestions.append(
                f"Low keyword match. Consider adding: {', '.join(top_missing)}"
            )

    if keyword_score >= 70:
        suggestions.append("Good keyword coverage — resume is ATS-friendly")

    if not suggestions:
        suggestions.append("Resume looks well-optimised for this job description")

    return suggestions
