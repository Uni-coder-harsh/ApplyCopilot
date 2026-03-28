# ApplyCopilot 🚀

> **Local-first AI-powered job & research internship tracker.**  
> Runs entirely on your machine. No cloud. No subscription. Free and open-source.

---

## What it does

ApplyCopilot aggregates all your job applications, research internship outreach, and cold emails into one place — with AI running locally on your GPU/CPU via Ollama.

- **Email intelligence** — connects to your IMAP accounts, reads all job-related threads, and classifies them automatically
- **Application tracker** — tracks every application, its stage, contact, and follow-up date
- **Resume generator** — generates a tailored DOCX resume per job description using local AI
- **Match scoring** — scores your profile against each job and explains why
- **Skill inferrer** — scans your local project folders and git repos to build your skill profile
- **Follow-up reminders** — tells you when to follow up and with whom

Everything stays on your machine. Your data never leaves.

---

## Stack

| Layer | Tech |
|---|---|
| CLI | Python 3.13 + Typer + Rich |
| Backend | FastAPI + Uvicorn |
| Database | SQLite + SQLAlchemy + Alembic |
| AI | Ollama (`phi3:mini`, `mistral:7b-q4`, `nomic-embed-text`) |
| Resume | python-docx |
| Config | pydantic-settings |

---

## Requirements

- Python 3.12+
- [Ollama](https://ollama.com) installed and running
- 6GB+ VRAM recommended (CPU-only works, slower)
- Linux or Windows

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/Uni-coder-harsh/ApplyCopilot.git
cd ApplyCopilot

# 2. Run setup (installs deps + pulls AI models)
bash setup.sh          # Linux
# setup.bat            # Windows

# 3. Activate venv
source .venv/bin/activate

# 4. Initialize (creates DB + your account)
applycopilot init

# 5. You're ready
applycopilot --help
```

---

## CLI commands

```
applycopilot init           Set up database and create account
applycopilot sync           Connect email and sync job-related threads
applycopilot jobs           List all tracked applications
applycopilot jobs --type research     Filter by type
applycopilot jobs --score 80          Show high-match only
applycopilot followups      Show pending follow-ups
applycopilot resume --job 42          Generate resume for job #42
```

---

## Project structure

```
ApplyCopilot/
├── core/               Business logic (no framework deps)
│   ├── email/          IMAP adapter, parser, sync
│   ├── tracker/        Application, contact, follow-up
│   ├── resume/         Builder, tailorer, DOCX writer
│   └── skills/         Project scanner, skill inferrer
├── ai/                 Ollama client, classifier, embedder, scorer
├── db/                 SQLAlchemy models, session, Alembic migrations
├── api/                FastAPI routes and middleware
├── cli/                Typer CLI commands
├── dashboard/          Local web UI (served at localhost:8000)
├── config/             pydantic-settings
└── tests/
```

---

## Development

```bash
# Install with dev extras
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .

# Type check
mypy .
```

---

## Roadmap

- [x] Phase 1 — Scaffold, DB, Auth, CLI init
- [ ] Phase 2 — Email sync + AI classification
- [ ] Phase 3 — Application tracker + follow-ups
- [ ] Phase 4 — Resume generator (DOCX)
- [ ] Phase 5 — AI match scoring + skill inferrer
- [ ] Phase 6 — Local web dashboard
- [ ] Phase 7 — Gmail OAuth adapter

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

---

## License

MIT — see [LICENSE](LICENSE).
