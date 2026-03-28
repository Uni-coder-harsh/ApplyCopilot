# Contributing to ApplyCopilot

Thanks for your interest in contributing. This is a open-source project — contributions are welcome but must meet the bar set below.

---

## Ground rules

- One concern per PR. Don't bundle unrelated changes.
- All code must pass `ruff check .` and `mypy .` before opening a PR.
- All new features must include tests in `tests/`.
- Never commit `.env`, `.applycopilot/`, or any user data.
- Keep dependencies minimal — open an issue before adding a new one.

---

## Setting up locally

```bash
git clone https://github.com/Uni-coder-harsh/ApplyCopilot.git
cd ApplyCopilot
bash setup.sh
source .venv/bin/activate
applycopilot init
```

---

## Branch strategy

| Branch | Purpose |
|---|---|
| `main` | Always stable, always passing CI |
| `dev` | Integration branch — PRs merge here first |
| `feature/your-feature` | Your work branch |

**Never push directly to `main`.**

Flow: `feature/x` → PR → `dev` → PR → `main`

---

## Commit message format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add IMAP sync for Gmail
fix: correct Argon2 hash comparison
chore: update dependencies
docs: add setup instructions for Windows
refactor: extract email parser into its own module
test: add unit tests for application stage machine
```

---

## Running tests

```bash
pytest                    # all tests
pytest tests/unit/        # unit only
pytest -v --cov=.         # with coverage
```

---

## Reporting bugs

Open an issue using the **Bug Report** template. Include:
- OS and Python version
- Ollama version and models pulled
- Full error output
- Steps to reproduce

---

## Suggesting features

Open an issue using the **Feature Request** template before writing any code. Features that don't align with the local-first, zero-cloud principle will be declined.
