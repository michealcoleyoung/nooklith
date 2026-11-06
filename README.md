# Nooklith

**Your little corner of the internet.** Built by Cole.dev.

A lightweight personal bookmark manager built with Python, Flask, Flask-SQLAlchemy,
SQLite, and Jinja2, with custom responsive CSS. This repository currently contains
**Phase 1 — Foundation**.

## Available now

- Dark, responsive dashboard with Nooklith branding and a friendly empty state.
- Persistent Bookmark model with title, URL, description, category, favorite status,
  and automatic creation/update timestamps.
- Automatic database creation on application startup.
- Read-only display of existing database records, newest first.
- Accessible focus states, semantic markup, and a custom 404 page.

Bookmark creation, editing, deletion, interactive filters, search, favorites, and
title fetching are deliberately deferred to later phases. Disabled controls show
where future features will appear. Requests and BeautifulSoup4 are included as
specified dependencies, but no network-fetch endpoint exists.

## Install and run

Requires Python **3.12 or newer**. `.python-version` selects **3.13** for reproducible
local development; uv can install it if needed.

Install uv using the instructions at <https://docs.astral.sh/uv/getting-started/installation/>.
On macOS with Homebrew, run `brew install uv`.

From this project's directory:

```bash
uv sync
uv run python run.py
```

Open <http://127.0.0.1:5000>. No manual environment activation is needed.
Stop the server with Ctrl+C. The SQLite database is created automatically at
`instance/nooklith.db` and persists between restarts. This directory is ignored by Git.

The application binds to loopback and runs without debug mode. Version 1 is for
local, single-user use: it has no authentication and should not be exposed to an
untrusted network or the public internet.

## Tests

```bash
uv run pytest
```

Tests use temporary SQLite databases, separate from personal bookmarks. They check
the homepage, empty state, database defaults and persistence across app instances,
escaped rendering, safe link handling, and missing routes.

## Project layout

```text
app/                 Flask factory, model, routes, templates, CSS
tests/               pytest fixtures and foundation tests
config.py            Default configuration
run.py               Local entry point
pyproject.toml       Metadata and dependencies
uv.lock              Locked dependencies (keep in Git)
```

Use `uv add` for application dependencies and `uv add --dev` for development
dependencies. Commit both `pyproject.toml` and `uv.lock` when changing dependencies.
`.env.example` documents a future session secret; `.env` is not automatically read.
No secret is needed by the current read-only dashboard. CSRF protection will be
added with state-changing forms in Phase 2.

## Next phases

1. CRUD forms, URL/category validation, and CSRF protection.
2. Category filters, instant search, and persistent favorites.
3. Additional accessibility and responsive polish.
4. Full feature tests, screenshots, and GitHub portfolio publication.
5. Optional title retrieval only with robust SSRF protection.

`db.create_all()` creates missing tables but does not migrate existing schemas.
Screenshots and GitHub publication are deferred to the portfolio phase.
