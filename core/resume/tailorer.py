"""
Resume tailorer — uses mistral:7b to rewrite resume sections
to better match a specific job description.
"""

import logging
from typing import Optional

from ai.client import ollama_client
from ai.prompts import RESUME_TAILOR_PROMPT
from config.settings import settings
from core.resume.builder import ResumeData, ResumeProject

logger = logging.getLogger(__name__)


def tailor_resume(
    resume_data: ResumeData,
    job_description: str,
    company: str,
    role: str,
) -> ResumeData:
    """
    Tailor a ResumeData object for a specific job.
    Rewrites the summary and re-ranks projects based on JD relevance.
    Returns a new ResumeData with tailored fields set.
    """
    resume_data.job_company = company
    resume_data.job_role = role

    # Build context strings for the prompt
    skills_str = _format_skills(resume_data)
    projects_str = _format_projects(resume_data)
    edu = resume_data.education[0] if resume_data.education else None

    # Tailor the summary
    resume_data.tailored_summary = _tailor_summary(
        resume_data=resume_data,
        job_description=job_description,
        skills_str=skills_str,
        projects_str=projects_str,
        edu=edu,
    )

    # Re-rank and tailor projects
    resume_data.tailored_projects = _rank_projects(
        resume_data=resume_data,
        job_description=job_description,
    )

    return resume_data


def _tailor_summary(
    resume_data: ResumeData,
    job_description: str,
    skills_str: str,
    projects_str: str,
    edu,
) -> str:
    """Rewrite the professional summary to match the JD."""
    prompt = RESUME_TAILOR_PROMPT.format(
        job_description=job_description[:1500],
        name=resume_data.full_name,
        degree=edu.degree if edu else "N/A",
        branch=edu.field if edu else "N/A",
        university=edu.institution if edu else "N/A",
        cgpa=edu.cgpa if edu else "N/A",
        skills=skills_str[:500],
        projects=projects_str[:800],
        section_name="Professional Summary",
        current_content=resume_data.summary or "No existing summary.",
    )

    try:
        result = ollama_client.generate(
            model=settings.model_reasoner,
            prompt=prompt,
            temperature=0.3,
            max_tokens=300,
        )
        return result.strip() if result else resume_data.summary or ""
    except Exception as e:
        logger.warning(f"Summary tailoring failed: {e}")
        return resume_data.summary or ""


def _rank_projects(
    resume_data: ResumeData,
    job_description: str,
) -> list[ResumeProject]:
    """
    Score each project against the JD using keyword overlap,
    then return them sorted by relevance (most relevant first).
    This is a fast heuristic — no extra AI call needed.
    """
    jd_lower = job_description.lower()
    jd_words = set(jd_lower.split())

    scored = []
    for project in resume_data.projects:
        score = 0
        text = f"{project.name} {project.description} {' '.join(project.tech_stack or [])}".lower()
        words = set(text.split())
        overlap = words & jd_words
        score = len(overlap)
        scored.append((score, project))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]


def _format_skills(resume_data: ResumeData) -> str:
    parts = []
    for group in resume_data.skill_groups:
        parts.append(f"{group.category}: {', '.join(group.skills)}")
    return "\n".join(parts)


def _format_projects(resume_data: ResumeData) -> str:
    parts = []
    for p in resume_data.projects[:4]:
        tech = ", ".join(p.tech_stack or [])
        parts.append(f"- {p.name} ({tech}): {p.description[:120] if p.description else ''}")
    return "\n".join(parts)
