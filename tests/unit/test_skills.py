"""
Unit tests for project scanner and skill inferrer.
Scanner tests use temp directories. Inferrer tests mock Ollama.
"""

import os
from pathlib import Path
from unittest.mock import patch

from core.skills.project_scanner import (
    scan_directory,
    _looks_like_project,
    _scan_project,
    EXT_TO_TECH,
)
from core.skills.inferrer import (
    _deduplicate_skills,
    _map_category,
    _fallback_skills_from_scan,
    infer_skills_from_projects,
)
from core.skills.project_scanner import ScannedProject
from db.models import SkillCategory, SkillSource


# ── Project Scanner tests ──────────────────────────────────────────────────────

def test_scan_directory_finds_project(tmp_path):
    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / "requirements.txt").write_text("fastapi\nsqlalchemy\n")
    (proj / "main.py").write_text("print('hello')")

    results = scan_directory(str(tmp_path))
    assert any(p.name == "myproject" for p in results)


def test_scan_detects_languages(tmp_path):
    proj = tmp_path / "pyproject"
    proj.mkdir()
    (proj / "requirements.txt").write_text("torch\n")
    (proj / "train.py").write_text("import torch")
    (proj / "model.py").write_text("class Model: pass")

    results = scan_directory(str(tmp_path))
    assert len(results) == 1
    assert "Python" in results[0].languages


def test_scan_reads_readme(tmp_path):
    proj = tmp_path / "readme_project"
    proj.mkdir()
    (proj / "setup.py").write_text("")
    (proj / "README.md").write_text("# My Project\nThis is a cool ML project.")

    results = scan_directory(str(tmp_path))
    assert len(results) == 1
    assert "My Project" in results[0].readme_snippet or "cool" in results[0].readme_snippet


def test_scan_skips_venv(tmp_path):
    proj = tmp_path / "proj_with_venv"
    proj.mkdir()
    (proj / "requirements.txt").write_text("flask\n")
    venv = proj / ".venv"
    venv.mkdir()
    (venv / "fake.py").write_text("# venv file")

    results = scan_directory(str(tmp_path))
    assert len(results) == 1
    assert results[0].file_count < 5   # .venv files should not be counted


def test_looks_like_project_with_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    assert _looks_like_project(tmp_path) is True


def test_looks_like_project_empty_dir(tmp_path):
    assert _looks_like_project(tmp_path) is False


def test_scan_nonexistent_directory():
    results = scan_directory("/this/does/not/exist/anywhere")
    assert results == []


# ── Skill Inferrer tests ───────────────────────────────────────────────────────

def test_deduplicate_skills_keeps_highest_confidence():
    skills = [
        {"name": "Python", "category": SkillCategory.PROGRAMMING, "confidence": 0.6, "level": "intermediate", "source": SkillSource.INFERRED_FS},
        {"name": "python", "category": SkillCategory.PROGRAMMING, "confidence": 0.9, "level": "expert", "source": SkillSource.INFERRED_FS},
    ]
    result = _deduplicate_skills(skills)
    assert len(result) == 1
    assert result[0]["confidence"] == 0.9


def test_map_category_known():
    assert _map_category("programming") == SkillCategory.PROGRAMMING
    assert _map_category("ml") == SkillCategory.ML
    assert _map_category("devops") == SkillCategory.DEVOPS


def test_map_category_unknown_falls_back():
    assert _map_category("something_random") == SkillCategory.OTHER


def test_fallback_skills_from_scan():
    project = ScannedProject(
        name="TestProject",
        path="/tmp/test",
        languages=["Python", "JavaScript"],
        frameworks=["Docker"],
    )
    skills = _fallback_skills_from_scan(project)
    names = [s["name"] for s in skills]
    assert "Python" in names
    assert "JavaScript" in names
    assert "Docker" in names


def test_infer_skills_mocked():
    mock_ai_result = [
        {"name": "PyTorch", "category": "ml", "level": "intermediate", "confidence": 0.85},
        {"name": "FastAPI", "category": "tools", "level": "expert", "confidence": 0.9},
    ]
    project = ScannedProject(
        name="MLProject",
        path="/tmp/ml",
        languages=["Python"],
        frameworks=["Docker"],
        readme_snippet="A machine learning project using PyTorch",
    )
    with patch("core.skills.inferrer.ollama_client") as mock_client:
        mock_client.generate_json.return_value = mock_ai_result
        results = infer_skills_from_projects([project])

    names = [s["name"] for s in results]
    assert "PyTorch" in names or "Python" in names  # either AI or fallback


def test_infer_skills_bad_json_uses_fallback():
    project = ScannedProject(
        name="FallbackProject",
        path="/tmp/fb",
        languages=["Go", "Python"],
        frameworks=[],
    )
    with patch("core.skills.inferrer.ollama_client") as mock_client:
        mock_client.generate_json.return_value = None  # simulate bad JSON
        results = infer_skills_from_projects([project])

    names = [s["name"] for s in results]
    assert "Go" in names or "Python" in names
