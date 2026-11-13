# Nooklith — Project Requirements

**Tagline:** Your little corner of the internet.<br>
**Developer:** Cole.dev<br>
**Application:** Local, single-user personal bookmark manager<br>
**Stack:** Python 3.12+, Flask, Flask-SQLAlchemy, SQLite, Jinja2, HTML, CSS, vanilla JavaScript<br>
**Project/dependency manager:** uv

## 1. Purpose and scope

Build a clean, modern, responsive web application to save, organize, search, edit, and delete website bookmarks. Nooklith is both a useful personal utility and a polished GitHub portfolio project. Keep the implementation straightforward and maintainable; do not introduce enterprise infrastructure or unnecessary abstractions.

Version 1 is **local-only and single-user**. It does not include accounts or authentication. **Never expose the application directly to the public internet or an untrusted network.**

## 2. Technology and tooling

- Python 3.12 or newer, Flask, Flask-SQLAlchemy, SQLite.
- HTML5, CSS3, Jinja2, vanilla JavaScript. No React, Vue, Angular, Bootstrap, or Tailwind.
- `uv` exclusively for Python versions, environments, dependencies, and execution. Do not use pip, pipenv, Poetry, or Conda.
- Maintain `pyproject.toml`, committed `uv.lock`, and `.python-version`. Exclude `.venv/` and SQLite files from Git.
- Add dependencies using `uv add`; add test/development dependencies using `uv add --dev`; set up using `uv sync`; run using `uv run`.
- Use pytest and Flask's test client. No paid services or external API requirements.
- Do not introduce Docker, Redis, Celery, or message queues in the initial version.
- `requests` and `beautifulsoup4` are **optional Phase 6 dependencies**, not required for Phase 1.

## 3. Core functionality

### 3.1 Create bookmarks

Fields: required website URL and title; optional description and category; favorite defaults to false.

- Accept only valid HTTP/HTTPS URLs; normalize consistently.
- Reject blank titles and invalid URLs; provide clear validation feedback.
- Persist to SQLite and display new bookmarks on the dashboard.

### 3.2 Browse bookmarks

- Display bookmarks newest first.
- Each card shows title, URL/domain, optional description, category, favorite state, and edit/delete controls.
- Titles open external websites in a new tab with safe `rel` attributes.
- Show a friendly empty state when the collection is empty.

### 3.3 Edit bookmarks

- Allow edits to URL, title, description, and category.
- Prepopulate the form; validate edits; update the existing record; show confirmation.

### 3.4 Delete bookmarks

- Require user confirmation; delete the correct record; update the view and provide feedback.
- Use POST, never GET, for deletion.

### 3.5 Categories

Default options: **Technology, Music, Research, Personal, Other**.

- Select a category on create/edit; default to Other.
- Filter by category and offer an All Bookmarks view.
- Users can add and delete categories through a management page.
- Names must be 1–50 characters, whitespace-normalized, and unique without regard to case.
- Deletion requires confirmation and moves affected bookmarks to Other without deleting them.
- Other is the permanent fallback and cannot be deleted. Other starter categories may be removed.
- Preserve existing bookmarks when initializing category storage; do not recreate deleted categories on restart.
- Category renaming remains out of scope.

### 3.6 Instant search

- Case-insensitive client-side filtering by title, URL, and description.
- Search combines correctly with category and favorites filters.
- No page reload; show a no-results state when appropriate.

### 3.7 Favorites

- Toggle favorite status via an accessible star button.
- Persist to SQLite; update the interface after a successful server response.
- Offer a Favorites filter; state survives reloads.

## 4. Optional Phase 6: Website title retrieval

After core features are complete, optionally add a **Fetch Title** action that uses Requests and BeautifulSoup to extract a website's HTML title.

- Support HTTP/HTTPS only.
- Defend against server-side request forgery (SSRF): reject localhost, private, loopback, link-local, and otherwise non-public destinations; validate resolved addresses and every redirect destination; protect against DNS rebinding and unsafe redirects.
- Apply short timeouts, strict response-size limits, and graceful errors.
- Never silently overwrite an existing user-entered title.
- If safe network validation is not feasible, **defer the feature** rather than shipping an unsafe endpoint.

## 5. Data model

Create a SQLAlchemy `Bookmark` model:

| Field | Type | Rule |
| --- | --- | --- |
| `id` | Integer | Primary key |
| `title` | String(255) | Required |
| `url` | Text | Required |
| `description` | Text | Optional |
| `category` | String(50) | Default `Other` |
| `is_favorite` | Boolean | Default `False` |
| `created_at` | DateTime | Automatically set |
| `updated_at` | DateTime | Automatically updated |

Use Flask-SQLAlchemy and ORM queries. Initialize the database during local setup. Keep database files outside version control. Keep the model easy to extend.

Categories are stored in a `Category` table with an integer primary key, a unique
50-character name, and a unique case-folded name key. Keep `Bookmark.category` as
text so the existing database upgrades without rebuilding bookmark records.
Seed starter and existing bookmark categories only when first initializing the
category table. Delete categories and reassign their bookmarks in one transaction.

## 6. Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Dashboard |
| GET | `/categories` | Manage categories |
| POST | `/categories` | Create category |
| POST | `/categories/<id>/delete` | Confirm and delete category; move bookmarks to Other |
| GET | `/bookmarks/new` | New bookmark form |
| POST | `/bookmarks` | Create bookmark |
| GET | `/bookmarks/<id>/edit` | Edit form |
| POST | `/bookmarks/<id>/edit` | Save changes |
| POST | `/bookmarks/<id>/delete` | Delete bookmark |
| POST | `/bookmarks/<id>/favorite` | Toggle favorite |
| POST | `/bookmarks/fetch-title` | Optional title retrieval (Phase 6) |

Use correct status codes and 404s for missing records. Redirect after successful form submissions; use JSON for asynchronous interactions where appropriate. Protect state-changing routes against CSRF.

## 7. UI and accessibility

**Brand:** Nooklith — *Your little corner of the internet.* — Built by Cole.dev.

- Minimal, modern dark theme with restrained accents, clean typography, subtle borders, rounded cards, and clear hover/focus states.
- Header: app wordmark and Add Bookmark action.
- Sidebar/navigation: All Bookmarks, Favorites, and categories.
- Main area: search, bookmark count, and responsive cards.
- Desktop: sidebar and multi-column grid; tablet: reduced columns; mobile: accessible navigation and one-column layout.
- Semantic HTML, explicit input labels, visible keyboard focus, accessible icon-button names, sufficient contrast, and keyboard operability.
- Keep JavaScript in a separate file; handle failed requests; do not inject untrusted HTML.

## 8. Security and operational constraints

- Validate URLs, titles, categories, and bookmark IDs server-side.
- Preserve Jinja2 autoescaping; never mark user content as trusted HTML.
- CSRF-protect all state-changing forms and JavaScript requests.
- Use ORM parameterization and safe external links (`target="_blank"` with `rel="noopener noreferrer"`).
- Keep secrets out of Git; never enable Flask debug mode in production.
- Do not show raw stack traces to users.
- No authentication in v1 means the app must remain local-only.

## 9. Suggested repository layout

```text
nooklith/
├── AGENTS.md
├── README.md
├── docs/
│   └── REQUIREMENTS.md
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── bookmark_form.html
│   │   └── errors/
│   │       └── 404.html
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
├── tests/
│   ├── conftest.py
│   └── test_bookmarks.py
├── config.py
├── run.py
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
└── .gitignore
```

Create files as needed per phase; the layout is a target, not a mandate to generate placeholders prematurely.

## 10. Testing

Use pytest with an isolated temporary SQLite database and Flask's test client. Verify:

1. Homepage returns success.
2. Creating a bookmark works.
3. Invalid URLs and blank titles are rejected.
4. Data persists.
5. Editing updates the intended record.
6. Deleting removes the intended record.
7. Favorites toggle and persist.
8. Missing IDs return 404.
9. Requests without valid CSRF tokens are rejected.
10. Search and filters work together (browser/manual or suitable automated tests).

Run tests with `uv run pytest`. Never claim tests passed without executing them.

## 11. GitHub and README

Use repository name `nooklith`. Include overview, features, stack, screenshots, setup/usage instructions, test commands, limitations, and possible improvements.

### Setup example

```bash
git clone <repository-url>
cd nooklith
uv sync
uv run python run.py
```

Document how to install uv and the supported Python version. No manual virtual environment activation should be necessary.

## 12. Development phases

**Phase 1 — Foundation**
- Initialize the uv project, Python version, `pyproject.toml`, and lockfile.
- Add only the dependencies needed for the foundation.
- Implement Flask app factory, SQLite configuration, Bookmark model, database initialization, and basic dashboard.
- Show branding and a friendly empty state. Verify the app starts locally.

**Phase 2 — CRUD**
- Add create, edit, delete, and validation flows.

**Phase 3 — Organization**
- Implement category filtering, instant search, and persistent favorites.

**Phase 4 — Polish**
- Refine visual design, mobile responsiveness, feedback, and accessibility.

**Phase 5 — Portfolio readiness**
- Complete automated tests, README, screenshots, cleanup, and GitHub publication.

**Phase 6 — Optional enhancement**
- Add secure website title retrieval only if it can be implemented safely.

Finish and verify each phase before starting the next.

## 13. Definition of done

- [ ] `uv sync` succeeds and `uv run python run.py` starts the app.
- [ ] `pyproject.toml` and `uv.lock` are committed; `.venv/` and database files are ignored.
- [ ] Bookmark creation, viewing, editing, and deletion work.
- [ ] Category filtering, instant search, and favorites work.
- [ ] Bookmarks and favorites persist after restart.
- [ ] Desktop/mobile layouts are usable and accessible.
- [ ] CSRF protection and server-side validation are in place.
- [ ] `uv run pytest` passes.
- [ ] README accurately explains installation, usage, tests, and limitations.
- [ ] Repository is presentable as a Cole.dev portfolio project.

## 14. Initial instruction to the coding assistant

**Implement Phase 1 only.** First summarize the files you intend to create or change. Set up Nooklith with uv, Flask, Flask-SQLAlchemy, SQLite, the Bookmark model, and an empty dashboard displaying the Nooklith name and tagline. Do **not** implement CRUD, search, filters, favorites, or title retrieval yet. Run available checks and provide exact `uv` commands to launch the application. Stop and wait for approval before Phase 2.
