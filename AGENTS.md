# Nooklith — Coding Agent Instructions

## Project context

Nooklith is a **local-only, single-user bookmark manager** and Cole.dev portfolio project. Read [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) before planning or modifying code. That file is the authoritative source for features, architecture, phases, and acceptance criteria.

## Current scope

**Phases 1–5 are approved.** The core application is implemented; Phase 5 covers portfolio readiness, tests, screenshots, documentation, and GitHub publication. Do not implement optional Phase 6 title fetching unless the user explicitly approves it.

Custom category creation/deletion is also approved. Deletion must preserve bookmarks by moving them to the protected Other category.

## Stack and package management

- Python 3.12+, Flask, Flask-SQLAlchemy, SQLite, Jinja2, HTML, CSS, vanilla JavaScript.
- Use **uv exclusively** for Python version/environment/dependency management and execution.
- Keep project dependencies in `pyproject.toml`; commit `uv.lock`; maintain `.python-version`.
- Use `uv add <package>` for runtime dependencies and `uv add --dev <package>` for development dependencies.
- Use `uv sync` to set up and `uv run python run.py` to start the app.
- Run tests with `uv run pytest` when tests exist.
- **Do not** use pip, pipenv, Poetry, Conda, or `requirements.txt`.
- Do not add optional `requests`/`beautifulsoup4` dependencies until Phase 6 is approved.

## Engineering principles

- Prefer clear, minimal, maintainable code over abstractions and cleverness.
- Use a Flask application factory and Flask-SQLAlchemy ORM.
- Keep templates, CSS, and JavaScript separate.
- Do not introduce frontend frameworks, Docker, Redis, Celery, or external services.
- Preserve existing functionality when making changes.
- Avoid creating placeholder files for future phases unless necessary.
- Follow the feature specifications and route contracts in `docs/REQUIREMENTS.md`.

## Security and correctness

- Treat all user input as untrusted; validate server-side.
- Preserve Jinja2 escaping; never inject untrusted HTML.
- Use CSRF protection for state-changing routes when they are introduced.
- Never mutate records through GET routes.
- Keep secrets, `.venv/`, and SQLite database files out of Git.
- Do not expose the unauthenticated app to public/untrusted networks.
- Defer automatic URL fetching unless SSRF protections can be implemented robustly.

## Workflow for each phase

1. Read `docs/REQUIREMENTS.md` and identify the current phase.
2. **Before editing**, summarize the files to create/change and the intended approach.
3. Implement only the approved phase in small, understandable steps.
4. Run relevant checks/tests where possible; report commands and actual results.
5. Explain what changed, how to run it, and any limitations or follow-up work.
6. **Stop** and request approval before proceeding to the next phase.

Never claim a test passed or an application ran unless it was actually executed. Ask clarifying questions only when a decision materially affects implementation. Do not add features outside the specification without approval.

## Phase 1 acceptance criteria

- `uv sync` succeeds.
- `uv run python run.py` launches the local Flask app.
- SQLite initializes and the Bookmark model is available.
- `/` renders the Nooklith name, tagline, and an empty-state message.
- No CRUD, categories UI, search, favorites, or website title retrieval is implemented yet.

## GitHub expectations

Keep `README.md` focused on user-facing setup, features, screenshots (when available), tests, and limitations. Keep detailed requirements in `docs/REQUIREMENTS.md`. Make changes that are easy to review and suitable for a portfolio repository.
