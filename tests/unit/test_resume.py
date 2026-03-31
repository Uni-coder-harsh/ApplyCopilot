"""
Unit tests for resume builder, ATS scorer, and DOCX writer.
No Ollama or DB needed for most tests.
"""

from pathlib import Path
from core.resume.builder import ResumeData, ResumeSkillGroup, ResumeProject, ResumeEducation
from core.resume.ats_scorer import score_resume, ATSResult


def _sample_resume() -> ResumeData:
    return ResumeData(
        full_name="Harsh Kumar",
        email="harsh@example.com",
        phone="+91-9999999999",
        location="Bengaluru",
        linkedin="https://linkedin.com/in/harsh",
        github="https://github.com/harsh",
        portfolio=None,
        summary="ML engineer with experience in Python, PyTorch, and NLP.",
        skill_groups=[
            ResumeSkillGroup("Programming Languages", ["Python", "C++", "JavaScript"]),
            ResumeSkillGroup("ML / AI", ["PyTorch", "TensorFlow", "scikit-learn", "NLP"]),
            ResumeSkillGroup("Tools & Frameworks", ["FastAPI", "Docker", "Git"]),
        ],
        projects=[
            ResumeProject(
                name="ApplyCopilot",
                description="Local-first AI job tracker using FastAPI, SQLite, and Ollama",
                tech_stack=["Python", "FastAPI", "SQLite", "Ollama"],
                repo_url="https://github.com/harsh/ApplyCopilot",
                impact="Automated job tracking for 200+ emails",
                start_date="2025-01",
                end_date="2025-03",
            ),
            ResumeProject(
                name="NLP Sentiment Analyser",
                description="Fine-tuned BERT model for sentiment analysis on Twitter data",
                tech_stack=["Python", "PyTorch", "HuggingFace", "BERT"],
                repo_url=None,
                impact="Achieved 94% accuracy on benchmark dataset",
                start_date="2024-09",
                end_date="2024-12",
            ),
        ],
        education=[
            ResumeEducation(
                institution="VTU",
                degree="B.Tech",
                field="Computer Science",
                start_year=2021,
                end_year=2025,
                cgpa=8.5,
            )
        ],
    )


# ── ATS Scorer tests ───────────────────────────────────────────────────────────

def test_ats_score_returns_result():
    resume = _sample_resume()
    jd = "Looking for ML engineer with Python, PyTorch, NLP, and FastAPI experience."
    result = score_resume(resume, jd)
    assert isinstance(result, ATSResult)
    assert 0 <= result.overall_score <= 100
    assert isinstance(result.matched_keywords, list)
    assert isinstance(result.missing_keywords, list)
    assert isinstance(result.suggestions, list)


def test_ats_score_high_for_matching_resume():
    resume = _sample_resume()
    jd = "Python PyTorch NLP FastAPI ML engineer SQLite Docker Git scikit-learn"
    result = score_resume(resume, jd)
    assert result.keyword_score > 50


def test_ats_score_low_for_mismatched_resume():
    resume = _sample_resume()
    jd = "Java Spring Boot Kubernetes AWS microservices enterprise backend architect"
    result = score_resume(resume, jd)
    assert result.keyword_score < 40


def test_ats_missing_keywords_populated():
    resume = _sample_resume()
    jd = "Rust Go Kubernetes Terraform AWS Lambda serverless"
    result = score_resume(resume, jd)
    assert len(result.missing_keywords) > 0


def test_ats_suggestions_for_empty_profile():
    empty = ResumeData(
        full_name="Test User",
        email="test@test.com",
        phone=None, location=None, linkedin=None,
        github=None, portfolio=None, summary=None,
        skill_groups=[], projects=[], education=[],
    )
    result = score_resume(empty, "Python machine learning")
    assert any("summary" in s.lower() or "skills" in s.lower() for s in result.suggestions)


# ── DOCX Writer tests ──────────────────────────────────────────────────────────

def test_docx_generates_file(tmp_path):
    from core.resume.docx_writer import generate_docx
    resume = _sample_resume()
    output_path = tmp_path / "test_resume.docx"
    result_path = generate_docx(resume, output_path)
    assert result_path.exists()
    assert result_path.stat().st_size > 1000


def test_docx_filename_builder():
    from core.resume.docx_writer import build_output_filename
    resume = _sample_resume()
    resume.job_company = "Google"
    resume.job_role = "ML Intern"
    filename = build_output_filename(resume)
    assert "harsh" in filename.lower()
    assert "google" in filename.lower()
    assert filename.endswith(".docx")


def test_docx_general_resume(tmp_path):
    from core.resume.docx_writer import generate_docx
    resume = _sample_resume()
    # No tailoring — test base resume
    output_path = tmp_path / "general.docx"
    generate_docx(resume, output_path)
    assert output_path.exists()


# ── Builder tests ──────────────────────────────────────────────────────────────

def test_resume_data_fields():
    resume = _sample_resume()
    assert resume.full_name == "Harsh Kumar"
    assert len(resume.skill_groups) == 3
    assert len(resume.projects) == 2
    assert len(resume.education) == 1


def test_resume_skill_group_structure():
    resume = _sample_resume()
    for group in resume.skill_groups:
        assert group.category
        assert len(group.skills) > 0
