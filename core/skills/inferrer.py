"""
Skill inferrer — takes scanned project metadata and uses
phi3:mini to infer skill names, categories, and confidence scores.
Also merges inferred skills with manually added ones without duplicates.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from ai.client import ollama_client
from ai.prompts import SKILL_INFERENCE_PROMPT
from config.settings import settings
from core.skills.project_scanner import ScannedProject
from db.models import Profile, Project, Skill, SkillCategory, SkillSource

logger = logging.getLogger(__name__)


def infer_skills_from_projects(
    scanned_projects: list[ScannedProject],
    progress_callback=None,
) -> list[dict]:
    """
    Run AI skill inference on a list of scanned projects.
    Returns a list of skill dicts with name, category, level, confidence.
    """
    all_skills = []
    total = len(scanned_projects)

    for i, project in enumerate(scanned_projects):
        try:
            skills = _infer_single_project(project)
            all_skills.extend(skills)
        except Exception as e:
            logger.warning(f"Skill inference failed for {project.name}: {e}")

        if progress_callback:
            progress_callback(i + 1, total)

    return _deduplicate_skills(all_skills)


def _infer_single_project(project: ScannedProject) -> list[dict]:
    """Infer skills from one project using phi3:mini."""
    file_ext_summary = ", ".join(project.languages[:6]) if project.languages else "unknown"

    prompt = SKILL_INFERENCE_PROMPT.format(
        project_name=project.name,
        description=project.description or "No description available",
        file_extensions=file_ext_summary,
        readme_snippet=project.readme_snippet[:400] if project.readme_snippet else "No README",
    )

    result = ollama_client.generate_json(
        model=settings.model_classifier,
        prompt=prompt,
        temperature=0.1,
        max_tokens=512,
    )

    if not result or not isinstance(result, list):
        # Fallback: use detected languages directly
        return _fallback_skills_from_scan(project)

    skills = []
    for item in result:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "").strip()
        if not name:
            continue
        skills.append({
            "name": name,
            "category": _map_category(item.get("category", "other")),
            "level": item.get("level", "intermediate"),
            "confidence": float(item.get("confidence", 0.7)),
            "source": SkillSource.INFERRED_FS,
        })

    # Always add detected languages as skills too
    skills.extend(_fallback_skills_from_scan(project))
    return skills


def _fallback_skills_from_scan(project: ScannedProject) -> list[dict]:
    """Create basic skill entries directly from file extension detection."""
    skills = []
    for lang in project.languages[:5]:
        skills.append({
            "name": lang,
            "category": _guess_category(lang),
            "level": "intermediate",
            "confidence": 0.6,
            "source": SkillSource.INFERRED_FS,
        })
    for framework in project.frameworks[:3]:
        skills.append({
            "name": framework,
            "category": SkillCategory.TOOLS,
            "level": "intermediate",
            "confidence": 0.5,
            "source": SkillSource.INFERRED_FS,
        })
    return skills


def persist_inferred_skills(
    db: Session,
    profile_id: int,
    inferred_skills: list[dict],
) -> tuple[int, int]:
    """
    Save inferred skills to the DB, skipping duplicates.
    Returns (added_count, skipped_count).
    """
    existing_names = {
        s.name.lower() for s in db.query(Skill).filter(Skill.profile_id == profile_id).all()
    }

    added = 0
    skipped = 0

    for skill_data in inferred_skills:
        name = skill_data["name"]
        if name.lower() in existing_names:
            skipped += 1
            continue

        skill = Skill(
            profile_id=profile_id,
            name=name,
            category=skill_data["category"],
            level=skill_data.get("level"),
            confidence=skill_data.get("confidence"),
            source=skill_data["source"],
        )
        db.add(skill)
        existing_names.add(name.lower())
        added += 1

    db.commit()
    return added, skipped


def persist_scanned_projects(
    db: Session,
    profile_id: int,
    scanned_projects: list[ScannedProject],
) -> int:
    """Save scanned projects to the DB Project table. Returns count added."""
    from db.models import Project

    existing_names = {
        p.name.lower() for p in db.query(Project).filter(Project.profile_id == profile_id).all()
    }

    added = 0
    for sp in scanned_projects:
        if sp.name.lower() in existing_names:
            continue
        project = Project(
            profile_id=profile_id,
            name=sp.name,
            description=sp.description or sp.readme_snippet[:300] if sp.readme_snippet else None,
            tech_stack=sp.languages + sp.frameworks,
            repo_url=None,
        )
        db.add(project)
        existing_names.add(sp.name.lower())
        added += 1

    db.commit()
    return added


def _deduplicate_skills(skills: list[dict]) -> list[dict]:
    """Merge duplicate skill names, keeping highest confidence."""
    seen: dict[str, dict] = {}
    for skill in skills:
        name = skill["name"].lower()
        if name not in seen or skill["confidence"] > seen[name]["confidence"]:
            seen[name] = skill
    return list(seen.values())


def _map_category(raw: str) -> SkillCategory:
    mapping = {
        "programming": SkillCategory.PROGRAMMING,
        "ml": SkillCategory.ML,
        "devops": SkillCategory.DEVOPS,
        "research": SkillCategory.RESEARCH,
        "tools": SkillCategory.TOOLS,
    }
    return mapping.get(str(raw).lower(), SkillCategory.OTHER)


def _guess_category(lang: str) -> SkillCategory:
    lang_lower = lang.lower()
    if any(x in lang_lower for x in ["python", "java", "c++", "go", "rust", "javascript", "typescript"]):
        return SkillCategory.PROGRAMMING
    if any(x in lang_lower for x in ["pytorch", "tensorflow", "ml", "jupyter", "r"]):
        return SkillCategory.ML
    if any(x in lang_lower for x in ["docker", "kubernetes", "terraform", "yaml", "shell"]):
        return SkillCategory.DEVOPS
    return SkillCategory.TOOLS
