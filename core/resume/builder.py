"""
Resume builder — assembles a structured resume dict from the user's
profile, skills, projects, and education stored in the DB.
This is the data layer. docx_writer.py handles the output.
"""

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from db.models import (
    Profile, Skill, Project, Education,
    SocialLink, SkillCategory,
)


@dataclass
class ResumeSkillGroup:
    category: str
    skills: list[str]


@dataclass
class ResumeProject:
    name: str
    description: str
    tech_stack: list[str]
    repo_url: Optional[str]
    impact: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]


@dataclass
class ResumeEducation:
    institution: str
    degree: str
    field: str
    start_year: Optional[int]
    end_year: Optional[int]
    cgpa: Optional[float]


@dataclass
class ResumeData:
    """Complete structured data for one resume."""
    full_name: str
    email: str
    phone: Optional[str]
    location: Optional[str]
    linkedin: Optional[str]
    github: Optional[str]
    portfolio: Optional[str]
    summary: Optional[str]
    skill_groups: list[ResumeSkillGroup]
    projects: list[ResumeProject]
    education: list[ResumeEducation]
    # Tailored content — set by tailorer.py
    tailored_summary: Optional[str] = None
    tailored_skills: Optional[str] = None
    tailored_projects: Optional[list[ResumeProject]] = None
    job_company: Optional[str] = None
    job_role: Optional[str] = None


CATEGORY_LABELS = {
    SkillCategory.PROGRAMMING: "Programming Languages",
    SkillCategory.ML: "ML / AI",
    SkillCategory.DEVOPS: "DevOps & Cloud",
    SkillCategory.RESEARCH: "Research",
    SkillCategory.TOOLS: "Tools & Frameworks",
    SkillCategory.OTHER: "Other",
}


def build_resume_data(db: Session, user_id: int) -> Optional[ResumeData]:
    """
    Pull all profile data from DB and return a ResumeData object.
    Returns None if no profile exists.
    """
    from db.models import User
    user = db.query(User).filter_by(id=user_id).first()
    if not user or not user.profile:
        return None

    profile: Profile = user.profile

    # Social links
    links = {sl.platform.lower(): sl.url for sl in profile.social_links}

    # Skills grouped by category
    skill_groups = _group_skills(profile.skills)

    # Projects — newest first
    projects = [
        ResumeProject(
            name=p.name,
            description=p.description or "",
            tech_stack=p.tech_stack or [],
            repo_url=p.repo_url,
            impact=p.impact,
            start_date=p.start_date,
            end_date=p.end_date,
        )
        for p in sorted(
            profile.projects,
            key=lambda p: p.end_date or "9999",
            reverse=True,
        )
    ]

    # Education — most recent first
    education = [
        ResumeEducation(
            institution=e.institution,
            degree=e.degree or "",
            field=e.field or "",
            start_year=e.start_year,
            end_year=e.end_year,
            cgpa=e.cgpa,
        )
        for e in sorted(
            profile.education,
            key=lambda e: e.end_year or 9999,
            reverse=True,
        )
    ]

    return ResumeData(
        full_name=profile.full_name or user.username,
        email=profile.primary_email or "",
        phone=profile.phone,
        location=profile.location,
        linkedin=links.get("linkedin"),
        github=links.get("github"),
        portfolio=links.get("portfolio"),
        summary=profile.bio,
        skill_groups=skill_groups,
        projects=projects,
        education=education,
    )


def _group_skills(skills: list[Skill]) -> list[ResumeSkillGroup]:
    """Group skills by category, sorted by confidence descending."""
    groups: dict[SkillCategory, list[str]] = {}

    for skill in sorted(skills, key=lambda s: s.confidence or 0, reverse=True):
        cat = skill.category or SkillCategory.OTHER
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(skill.name)

    # Maintain a logical order
    order = [
        SkillCategory.PROGRAMMING,
        SkillCategory.ML,
        SkillCategory.TOOLS,
        SkillCategory.DEVOPS,
        SkillCategory.RESEARCH,
        SkillCategory.OTHER,
    ]

    result = []
    for cat in order:
        if cat in groups:
            result.append(ResumeSkillGroup(
                category=CATEGORY_LABELS.get(cat, cat.value),
                skills=groups[cat],
            ))

    return result


def build_profile_setup_prompt() -> list[dict]:
    """
    Return a list of fields the user needs to fill in their profile
    before resume generation can work well.
    """
    return [
        {"field": "full_name",      "label": "Full name",          "required": True},
        {"field": "primary_email",  "label": "Email address",      "required": True},
        {"field": "phone",          "label": "Phone number",       "required": False},
        {"field": "location",       "label": "Location (city)",    "required": False},
        {"field": "university",     "label": "University",         "required": True},
        {"field": "degree",         "label": "Degree (e.g. B.Tech)", "required": True},
        {"field": "branch",         "label": "Branch / Major",     "required": True},
        {"field": "graduation_year","label": "Graduation year",    "required": True},
        {"field": "cgpa",           "label": "CGPA",               "required": False},
        {"field": "bio",            "label": "Professional summary (2-3 lines)", "required": False},
    ]
