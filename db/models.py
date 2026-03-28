"""
SQLAlchemy ORM models for ApplyCopilot.
All 16 tables defined here. Alembic reads this file for migrations.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ── Base ───────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Enums ──────────────────────────────────────────────────────────────────────

class EmailDirection(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class EmailCategory(str, enum.Enum):
    COLD_EMAIL = "cold_email"
    PROFESSOR_REPLY = "professor_reply"
    APPLICATION_CONFIRM = "application_confirmation"
    REJECTION = "rejection"
    OA = "oa"
    INTERVIEW = "interview"
    OFFER = "offer"
    OPPORTUNITY = "opportunity"
    OTHER = "other"


class ContactType(str, enum.Enum):
    PROFESSOR = "professor"
    HR = "hr"
    RECRUITER = "recruiter"
    RESEARCHER = "researcher"


class JobType(str, enum.Enum):
    RESEARCH = "research"
    INDUSTRY = "industry"
    FELLOWSHIP = "fellowship"
    RA = "ra"
    OPEN_SOURCE = "open_source"


class ApplicationStatus(str, enum.Enum):
    ACTIVE = "active"
    REJECTED = "rejected"
    CLOSED = "closed"
    OFFER = "offer"


class ApplicationStage(str, enum.Enum):
    COLD_EMAIL_SENT = "cold_email_sent"
    APPLIED = "applied"
    AWAITING_REPLY = "awaiting_reply"
    SHORTLISTED = "shortlisted"
    OA = "oa"
    INTERVIEW = "interview"
    FINAL_ROUND = "final_round"
    OFFER = "offer"


class SkillSource(str, enum.Enum):
    MANUAL = "manual"
    INFERRED_FS = "inferred_from_projects"
    INFERRED_RESUME = "inferred_from_resume"


class SkillCategory(str, enum.Enum):
    PROGRAMMING = "programming"
    ML = "ml"
    DEVOPS = "devops"
    RESEARCH = "research"
    TOOLS = "tools"
    OTHER = "other"


class AttachmentType(str, enum.Enum):
    JOB_DESCRIPTION = "job_description"
    RESUME = "resume"
    EMAIL_ATTACHMENT = "email_attachment"


class ResumeSectionName(str, enum.Enum):
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"
    ACHIEVEMENTS = "achievements"


# ── 1. User ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    profile: Mapped[Optional["Profile"]] = relationship(back_populates="user", uselist=False)
    email_accounts: Mapped[List["EmailAccount"]] = relationship(back_populates="user")


# ── 2. Profile ─────────────────────────────────────────────────────────────────

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(128))
    first_name: Mapped[Optional[str]] = mapped_column(String(64))
    last_name: Mapped[Optional[str]] = mapped_column(String(64))
    primary_email: Mapped[Optional[str]] = mapped_column(String(256))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    location: Mapped[Optional[str]] = mapped_column(String(128))
    university: Mapped[Optional[str]] = mapped_column(String(256))
    degree: Mapped[Optional[str]] = mapped_column(String(128))
    branch: Mapped[Optional[str]] = mapped_column(String(128))
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer)
    cgpa: Mapped[Optional[float]] = mapped_column(Float)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    preferred_roles: Mapped[Optional[list]] = mapped_column(JSON)      # ["SWE", "ML Engineer"]
    preferred_domains: Mapped[Optional[list]] = mapped_column(JSON)    # ["AI", "Data Science"]
    preferred_locations: Mapped[Optional[list]] = mapped_column(JSON)  # ["Remote", "Bangalore"]
    remote_preference: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")
    social_links: Mapped[List["SocialLink"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    skills: Mapped[List["Skill"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    education: Mapped[List["Education"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    resumes: Mapped[List["Resume"]] = relationship(back_populates="profile")


# ── 3. SocialLink ──────────────────────────────────────────────────────────────

class SocialLink(Base):
    __tablename__ = "social_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(64))   # "GitHub", "LinkedIn", etc.
    url: Mapped[str] = mapped_column(String(512))
    username: Mapped[Optional[str]] = mapped_column(String(128))

    profile: Mapped["Profile"] = relationship(back_populates="social_links")


# ── 4. Skill ───────────────────────────────────────────────────────────────────

class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[SkillCategory] = mapped_column(Enum(SkillCategory), default=SkillCategory.OTHER)
    level: Mapped[Optional[str]] = mapped_column(String(32))       # beginner/intermediate/expert
    confidence: Mapped[Optional[float]] = mapped_column(Float)     # 0.0–1.0 when AI-inferred
    source: Mapped[SkillSource] = mapped_column(Enum(SkillSource), default=SkillSource.MANUAL)

    profile: Mapped["Profile"] = relationship(back_populates="skills")


# ── 5. Project ─────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tech_stack: Mapped[Optional[list]] = mapped_column(JSON)   # ["Python", "FastAPI", ...]
    repo_url: Mapped[Optional[str]] = mapped_column(String(512))
    live_url: Mapped[Optional[str]] = mapped_column(String(512))
    start_date: Mapped[Optional[str]] = mapped_column(String(16))
    end_date: Mapped[Optional[str]] = mapped_column(String(16))
    impact: Mapped[Optional[str]] = mapped_column(Text)

    profile: Mapped["Profile"] = relationship(back_populates="projects")


# ── 6. Education ───────────────────────────────────────────────────────────────

class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    institution: Mapped[str] = mapped_column(String(256), nullable=False)
    degree: Mapped[Optional[str]] = mapped_column(String(128))
    field: Mapped[Optional[str]] = mapped_column(String(128))
    start_year: Mapped[Optional[int]] = mapped_column(Integer)
    end_year: Mapped[Optional[int]] = mapped_column(Integer)
    cgpa: Mapped[Optional[float]] = mapped_column(Float)

    profile: Mapped["Profile"] = relationship(back_populates="education")


# ── 7. EmailAccount ────────────────────────────────────────────────────────────

class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    provider: Mapped[str] = mapped_column(String(64))    # "imap", "gmail", "outlook"
    imap_host: Mapped[Optional[str]] = mapped_column(String(256))
    imap_port: Mapped[Optional[int]] = mapped_column(Integer, default=993)
    token_encrypted: Mapped[Optional[str]] = mapped_column(Text)   # encrypted password/token
    last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="email_accounts")
    emails: Mapped[List["Email"]] = relationship(back_populates="account", cascade="all, delete-orphan")


# ── 8. Email ───────────────────────────────────────────────────────────────────

class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("email_accounts.id"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String(512), index=True)
    subject: Mapped[Optional[str]] = mapped_column(String(1024))
    sender: Mapped[Optional[str]] = mapped_column(String(512))
    recipients: Mapped[Optional[list]] = mapped_column(JSON)
    body: Mapped[Optional[str]] = mapped_column(Text)
    snippet: Mapped[Optional[str]] = mapped_column(String(512))
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    direction: Mapped[EmailDirection] = mapped_column(Enum(EmailDirection), default=EmailDirection.INCOMING)
    category: Mapped[EmailCategory] = mapped_column(Enum(EmailCategory), default=EmailCategory.OTHER)
    is_job_related: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ai_classified: Mapped[bool] = mapped_column(Boolean, default=False)

    account: Mapped["EmailAccount"] = relationship(back_populates="emails")
    applications: Mapped[List["Application"]] = relationship(back_populates="email_thread")


# ── 9. Contact ─────────────────────────────────────────────────────────────────

class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(256))
    email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    organization: Mapped[Optional[str]] = mapped_column(String(256))
    role: Mapped[Optional[str]] = mapped_column(String(256))
    type: Mapped[ContactType] = mapped_column(Enum(ContactType), default=ContactType.HR)
    linkedin: Mapped[Optional[str]] = mapped_column(String(512))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    applications: Mapped[List["Application"]] = relationship(back_populates="contact")


# ── 10. Job ────────────────────────────────────────────────────────────────────

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(256))
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    type: Mapped[JobType] = mapped_column(Enum(JobType), default=JobType.INDUSTRY)
    domain: Mapped[Optional[str]] = mapped_column(String(128))   # "AI", "SWE", "Data Science"
    source: Mapped[Optional[str]] = mapped_column(String(128))   # "cold_email", "portal", "referral"
    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    url: Mapped[Optional[str]] = mapped_column(String(1024))

    applications: Mapped[List["Application"]] = relationship(back_populates="job")
    resumes: Mapped[List["Resume"]] = relationship(back_populates="job")


# ── 11. Application ────────────────────────────────────────────────────────────

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    email_thread_id: Mapped[Optional[int]] = mapped_column(ForeignKey("emails.id"), nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.ACTIVE, index=True)
    stage: Mapped[ApplicationStage] = mapped_column(Enum(ApplicationStage), default=ApplicationStage.APPLIED, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(128))
    applied_via: Mapped[Optional[str]] = mapped_column(String(256))
    applied_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_updated: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    followup_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    match_score: Mapped[Optional[float]] = mapped_column(Float)
    priority: Mapped[int] = mapped_column(Integer, default=0)   # 0=normal, 1=high, 2=urgent
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="applications")
    contact: Mapped[Optional["Contact"]] = relationship(back_populates="applications")
    email_thread: Mapped[Optional["Email"]] = relationship(back_populates="applications")
    resumes: Mapped[List["Resume"]] = relationship(back_populates="application")
    match_scores: Mapped[List["MatchScore"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    followups: Mapped[List["Followup"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    attachments: Mapped[List["Attachment"]] = relationship(back_populates="application", cascade="all, delete-orphan")


# ── 12. Resume ─────────────────────────────────────────────────────────────────

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    application_id: Mapped[Optional[int]] = mapped_column(ForeignKey("applications.id"), nullable=True)
    version_name: Mapped[str] = mapped_column(String(256), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024))
    score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    profile: Mapped["Profile"] = relationship(back_populates="resumes")
    job: Mapped[Optional["Job"]] = relationship(back_populates="resumes")
    application: Mapped[Optional["Application"]] = relationship(back_populates="resumes")
    sections: Mapped[List["ResumeSection"]] = relationship(back_populates="resume", cascade="all, delete-orphan")


# ── 13. ResumeSection ──────────────────────────────────────────────────────────

class ResumeSection(Base):
    __tablename__ = "resume_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), nullable=False)
    section_name: Mapped[ResumeSectionName] = mapped_column(Enum(ResumeSectionName))
    content: Mapped[Optional[str]] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, default=0)

    resume: Mapped["Resume"] = relationship(back_populates="sections")


# ── 14. MatchScore ─────────────────────────────────────────────────────────────

class MatchScore(Base):
    __tablename__ = "match_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False)
    overall_score: Mapped[Optional[float]] = mapped_column(Float)
    skill_score: Mapped[Optional[float]] = mapped_column(Float)
    experience_score: Mapped[Optional[float]] = mapped_column(Float)
    keyword_score: Mapped[Optional[float]] = mapped_column(Float)
    project_score: Mapped[Optional[float]] = mapped_column(Float)
    analysis: Mapped[Optional[str]] = mapped_column(Text)   # AI explanation text
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    application: Mapped["Application"] = relationship(back_populates="match_scores")


# ── 15. Followup ───────────────────────────────────────────────────────────────

class Followup(Base):
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False)
    date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(64), default="pending")   # pending/sent/skipped
    notes: Mapped[Optional[str]] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="followups")


# ── 16. Attachment ─────────────────────────────────────────────────────────────

class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False)
    type: Mapped[AttachmentType] = mapped_column(Enum(AttachmentType))
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    application: Mapped["Application"] = relationship(back_populates="attachments")
