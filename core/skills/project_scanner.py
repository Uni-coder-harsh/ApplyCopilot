"""
Project scanner — walks local directories and git repos,
extracts project metadata, and prepares it for skill inference.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# File extensions mapped to technology names
EXT_TO_TECH = {
    ".py":    "Python",
    ".js":    "JavaScript",
    ".ts":    "TypeScript",
    ".jsx":   "React",
    ".tsx":   "React/TypeScript",
    ".java":  "Java",
    ".kt":    "Kotlin",
    ".cpp":   "C++",
    ".c":     "C",
    ".cs":    "C#",
    ".go":    "Go",
    ".rs":    "Rust",
    ".rb":    "Ruby",
    ".php":   "PHP",
    ".swift": "Swift",
    ".dart":  "Dart/Flutter",
    ".r":     "R",
    ".m":     "MATLAB",
    ".scala": "Scala",
    ".ipynb": "Jupyter/Python",
    ".sql":   "SQL",
    ".sh":    "Shell/Bash",
    ".yaml":  "YAML/DevOps",
    ".yml":   "YAML/DevOps",
    ".tf":    "Terraform",
    ".proto": "Protocol Buffers",
}

# Config files that hint at frameworks/tools
CONFIG_HINTS = {
    "requirements.txt":     "Python",
    "pyproject.toml":       "Python",
    "package.json":         "Node.js",
    "Dockerfile":           "Docker",
    "docker-compose.yml":   "Docker Compose",
    "docker-compose.yaml":  "Docker Compose",
    ".github":              "GitHub Actions",
    "kubernetes":           "Kubernetes",
    "terraform.tf":         "Terraform",
    "Makefile":             "Make/Build",
    "CMakeLists.txt":       "CMake/C++",
    "setup.py":             "Python Package",
    "cargo.toml":           "Rust",
    "go.mod":               "Go Modules",
    "pom.xml":              "Maven/Java",
    "build.gradle":         "Gradle/Java",
    "pubspec.yaml":         "Flutter/Dart",
    ".env.example":         "Environment Config",
}

# Directories to always skip
SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".pytest_cache", "dist", "build",
    ".idea", ".vscode", "target", ".cache", "vendor",
}


@dataclass
class ScannedProject:
    name: str
    path: str
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    readme_snippet: str = ""
    is_git_repo: bool = False
    file_count: int = 0
    description: Optional[str] = None


def scan_directory(root_path: str, max_depth: int = 3) -> list[ScannedProject]:
    """
    Scan a directory for projects. Each immediate subdirectory
    that contains code files is treated as a project.
    """
    root = Path(root_path).expanduser().resolve()
    if not root.exists():
        logger.warning(f"Directory does not exist: {root}")
        return []

    projects = []

    # Check if root itself is a project
    if _looks_like_project(root):
        project = _scan_project(root)
        if project:
            projects.append(project)
        return projects

    # Otherwise scan subdirectories
    try:
        for child in sorted(root.iterdir()):
            if child.is_dir() and child.name not in SKIP_DIRS:
                if _looks_like_project(child):
                    project = _scan_project(child)
                    if project:
                        projects.append(project)
    except PermissionError:
        logger.warning(f"Permission denied: {root}")

    return projects


def _looks_like_project(path: Path) -> bool:
    """Check if a directory looks like a code project."""
    if not path.is_dir():
        return False

    # Has a git repo
    if (path / ".git").exists():
        return True

    # Has common project files
    indicators = [
        "requirements.txt", "pyproject.toml", "package.json",
        "Cargo.toml", "go.mod", "pom.xml", "Dockerfile",
        "setup.py", "main.py", "index.js", "main.go",
    ]
    return any((path / f).exists() for f in indicators)


def _scan_project(path: Path) -> Optional[ScannedProject]:
    """Extract metadata from a single project directory."""
    try:
        languages: dict[str, int] = {}
        frameworks = set()
        file_count = 0

        for dirpath, dirnames, filenames in os.walk(path):
            # Prune skip dirs in-place
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

            # Limit depth
            depth = len(Path(dirpath).relative_to(path).parts)
            if depth > 3:
                dirnames.clear()
                continue

            for filename in filenames:
                file_count += 1
                ext = Path(filename).suffix.lower()
                if ext in EXT_TO_TECH:
                    tech = EXT_TO_TECH[ext]
                    languages[tech] = languages.get(tech, 0) + 1

                if filename in CONFIG_HINTS:
                    frameworks.add(CONFIG_HINTS[filename])

        # Sort languages by file count
        sorted_langs = [
            lang for lang, _ in sorted(languages.items(), key=lambda x: x[1], reverse=True)
        ]

        # README snippet
        readme_snippet = _read_readme(path)

        # Git check
        is_git = (path / ".git").exists()

        # Description from README first line
        description = None
        if readme_snippet:
            lines = [l.strip() for l in readme_snippet.split("\n") if l.strip() and not l.startswith("#")]
            if lines:
                description = lines[0][:200]

        return ScannedProject(
            name=path.name,
            path=str(path),
            languages=sorted_langs[:8],
            frameworks=list(frameworks)[:8],
            readme_snippet=readme_snippet[:800],
            is_git_repo=is_git,
            file_count=file_count,
            description=description,
        )

    except Exception as e:
        logger.warning(f"Failed to scan {path}: {e}")
        return None


def _read_readme(path: Path) -> str:
    """Read the first 800 chars of the README file if it exists."""
    for name in ["README.md", "README.txt", "README.rst", "README"]:
        readme = path / name
        if readme.exists():
            try:
                return readme.read_text(errors="replace")[:800]
            except Exception:
                pass
    return ""
