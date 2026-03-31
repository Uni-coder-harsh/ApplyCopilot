"""
Match scorer — scores how well a candidate's profile matches a job.
Uses a hybrid approach:
  - mistral:7b for qualitative reasoning and explanation
  - nomic-embed-text for semantic similarity
  - keyword overlap for ATS-style scoring
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ai.client import ollama_client
from ai.embedder import semantic_similarity
from ai.prompts import MATCH_SCORE_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class MatchScoreResult:
    overall_score: float
    skill_score: float
    experience_score: float
    keyword_score: float
    project_score: float
    semantic_score: float
    analysis: str


def score_match(
    job_description: str,
    skills: list[str],
    projects: list[str],
    degree: str,
    branch: str,
    cgpa: Optional[float],
) -> MatchScoreResult:
    """
    Score how well a candidate matches a job description.
    Combines AI reasoning with semantic similarity.
    """
    skills_str = ", ".join(skills[:30]) if skills else "None listed"
    projects_str = "\n".join(f"- {p}" for p in projects[:5]) if projects else "None listed"
    cgpa_str = str(cgpa) if cgpa else "Not provided"

    # ── AI reasoning score ─────────────────────────────────────────────────────
    ai_result = _get_ai_scores(
        job_description=job_description,
        skills_str=skills_str,
        projects_str=projects_str,
        degree=degree,
        branch=branch,
        cgpa_str=cgpa_str,
    )

    # ── Semantic similarity score ──────────────────────────────────────────────
    profile_text = f"{degree} {branch} skills: {skills_str} projects: {projects_str}"
    semantic = semantic_similarity(profile_text, job_description[:2000])
    semantic_score = round(semantic * 100, 1)

    # ── Blend scores ───────────────────────────────────────────────────────────
    if ai_result:
        overall = round(
            ai_result["overall_score"] * 0.5
            + semantic_score * 0.3
            + ai_result["keyword_score"] * 0.2,
            1,
        )
        return MatchScoreResult(
            overall_score=min(100, overall),
            skill_score=ai_result["skill_score"],
            experience_score=ai_result["experience_score"],
            keyword_score=ai_result["keyword_score"],
            project_score=ai_result["project_score"],
            semantic_score=semantic_score,
            analysis=ai_result["analysis"],
        )
    else:
        # Fallback: semantic only
        return MatchScoreResult(
            overall_score=semantic_score,
            skill_score=0,
            experience_score=0,
            keyword_score=0,
            project_score=0,
            semantic_score=semantic_score,
            analysis="AI scoring unavailable — showing semantic similarity only.",
        )


def _get_ai_scores(
    job_description: str,
    skills_str: str,
    projects_str: str,
    degree: str,
    branch: str,
    cgpa_str: str,
) -> Optional[dict]:
    """Call mistral:7b with the match scoring prompt."""
    prompt = MATCH_SCORE_PROMPT.format(
        job_description=job_description[:1500],
        skills=skills_str,
        projects=projects_str,
        degree=degree,
        branch=branch,
        cgpa=cgpa_str,
    )

    result = ollama_client.generate_json(
        model=settings.model_reasoner,
        prompt=prompt,
        temperature=0.1,
        max_tokens=512,
    )

    if not result or not isinstance(result, dict):
        return None

    return {
        "overall_score": float(result.get("overall_score", 0)),
        "skill_score": float(result.get("skill_score", 0)),
        "experience_score": float(result.get("experience_score", 0)),
        "keyword_score": float(result.get("keyword_score", 0)),
        "project_score": float(result.get("project_score", 0)),
        "analysis": str(result.get("analysis", "")),
    }


def score_and_persist(
    db,
    application_id: int,
    job_description: str,
    skills: list[str],
    projects: list[str],
    degree: str,
    branch: str,
    cgpa: Optional[float],
) -> MatchScoreResult:
    """
    Score a match and save the result to the MatchScore table.
    Also updates Application.match_score for quick filtering.
    """
    from db.models import Application, MatchScore

    result = score_match(
        job_description=job_description,
        skills=skills,
        projects=projects,
        degree=degree,
        branch=branch,
        cgpa=cgpa,
    )

    # Persist to MatchScore table
    score_record = MatchScore(
        application_id=application_id,
        overall_score=result.overall_score,
        skill_score=result.skill_score,
        experience_score=result.experience_score,
        keyword_score=result.keyword_score,
        project_score=result.project_score,
        analysis=result.analysis,
    )
    db.add(score_record)

    # Update the denormalised match_score on Application for fast filtering
    app = db.query(Application).filter(Application.id == application_id).first()
    if app:
        app.match_score = result.overall_score

    db.commit()
    return result
