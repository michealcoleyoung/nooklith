import pytest
from sqlalchemy import create_engine

from app import create_app, db
from app.models import Bookmark, Category, category_names


def category_id(app, name):
    with app.app_context():
        return db.session.execute(db.select(Category.id).where(Category.name == name)).scalar_one()


def test_custom_category_available_for_forms_and_filters(app, client, csrf_token):
    response = client.post("/categories", data={"name": "  Game   Design  ", "csrf_token": csrf_token()})
    assert response.status_code == 303
    with app.app_context():
        assert "Game Design" in category_names()
    assert b'value="Game Design"' in client.get("/bookmarks/new").data
    assert b'data-category-filter="Game Design"' in client.get("/").data
    response = client.post("/bookmarks", data={
        "title": "A game", "url": "https://example.com", "category": "Game Design",
        "csrf_token": csrf_token(),
    })
    assert response.status_code == 303
    with app.app_context():
        assert db.session.execute(db.select(Bookmark)).scalar_one().category == "Game Design"


@pytest.mark.parametrize("name", ["", "   ", "x" * 51, "Other", "oThEr", "Technology", "Bad\x00Name"])
def test_invalid_category_names(app, client, csrf_token, name):
    response = client.post("/categories", data={"name": name, "csrf_token": csrf_token()})
    assert response.status_code == 422
    with app.app_context():
        assert len(category_names()) == 5


def test_unicode_duplicate_and_escaping(app, client, csrf_token):
    assert client.post("/categories", data={"name": "Straße", "csrf_token": csrf_token()}).status_code == 303
    assert client.post("/categories", data={"name": "STRASSE", "csrf_token": csrf_token()}).status_code == 422
    client.post("/categories", data={"name": '<script>alert("x")</script>', "csrf_token": csrf_token()})
    assert b'<script>alert("x")</script>' not in client.get("/categories").data
    assert b'&lt;script&gt;' in client.get("/categories").data


def test_delete_confirmation_preserves_bookmarks_and_restart(app, client, csrf_token):
    with app.app_context():
        db.session.add_all([
            Bookmark(title="Keep me", url="https://example.com", category="Music", is_favorite=True),
            Bookmark(title="Unrelated", url="https://example.org", category="Research"),
        ])
        db.session.commit()
    path = f"/categories/{category_id(app, 'Music')}/delete"
    assert client.get(path).status_code == 405
    response = client.post(path, data={"csrf_token": csrf_token()})
    assert b"No bookmarks will be deleted" in response.data
    with app.app_context():
        assert "Music" in category_names()
    assert client.post(path, data={"csrf_token": csrf_token(), "confirmed": "yes"}).status_code == 303
    restarted = create_app({"TESTING": True, "SECRET_KEY": "test-only-secret-key",
                            "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"]})
    with restarted.app_context():
        assert "Music" not in category_names()
        bookmarks = db.session.execute(db.select(Bookmark).order_by(Bookmark.id)).scalars().all()
        assert len(bookmarks) == 2
        assert bookmarks[0].category == "Other"
        assert bookmarks[0].is_favorite is True
        assert bookmarks[0].title == "Keep me"
        assert bookmarks[1].category == "Research"
    # Stale forms must not recreate deleted categories.
    assert client.post("/bookmarks", data={"title": "Stale", "url": "https://example.com",
                       "category": "Music", "csrf_token": csrf_token()}).status_code == 422


def test_protected_other_and_missing_id(app, client, csrf_token):
    path = f"/categories/{category_id(app, 'Other')}/delete"
    assert client.post(path, data={"csrf_token": csrf_token(), "confirmed": "yes"}).status_code == 400
    assert client.post("/categories/99999/delete", data={"csrf_token": csrf_token()}).status_code == 404
    with app.app_context():
        assert "Other" in category_names()


@pytest.mark.parametrize("token", [None, "invalid"])
def test_category_csrf_protection(app, client, token):
    data = {"name": "Blocked", "confirmed": "yes"}
    if token:
        data["csrf_token"] = token
    assert client.post("/categories", data=data).status_code == 400
    path = f"/categories/{category_id(app, 'Music')}/delete"
    assert client.post(path, data=data).status_code == 400
    with app.app_context():
        assert "Blocked" not in category_names()
        assert "Music" in category_names()


def test_upgrade_existing_database(tmp_path):
    uri = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(uri)
    # Recreate the previous schema using model metadata, with no category table.
    Bookmark.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(Bookmark.__table__.insert().values(
            title="Existing", url="https://example.com", category="Legacy topic"))
    engine.dispose()
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only-secret-key",
                      "SQLALCHEMY_DATABASE_URI": uri})
    with app.app_context():
        assert "Legacy topic" in category_names()
        assert "Other" in category_names()
        assert db.session.execute(db.select(Bookmark)).scalar_one().title == "Existing"
