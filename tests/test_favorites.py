import pytest

from app import create_app, db
from app.models import Bookmark


@pytest.fixture
def bookmark_id(app):
    with app.app_context():
        bookmark = Bookmark(title="Python notes", url="https://example.com/python",
                            category="Research", description="Helpful references")
        untouched = Bookmark(title="Other bookmark", url="https://example.org/")
        db.session.add_all([bookmark, untouched])
        db.session.commit()
        return bookmark.id


def test_favorite_toggle_and_persistence(app, client, csrf_token, bookmark_id):
    path = f"/bookmarks/{bookmark_id}/favorite"
    headers = {"Accept": "application/json"}
    response = client.post(path, data={"csrf_token": csrf_token()}, headers=headers)
    assert response.status_code == 200
    assert response.json == {"id": bookmark_id, "is_favorite": True}
    restarted = create_app({"TESTING": True, "SECRET_KEY": "test-only-secret-key",
                            "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"]})
    with restarted.app_context():
        assert db.session.get(Bookmark, bookmark_id).is_favorite is True
        other = db.session.execute(db.select(Bookmark).where(Bookmark.id != bookmark_id)).scalar_one()
        assert other.is_favorite is False
    dashboard = client.get("/").data
    assert b'data-favorite="true"' in dashboard
    assert b'aria-label="Remove Python notes from favorites"' in dashboard
    response = client.post(path, data={"csrf_token": csrf_token()}, headers=headers)
    assert response.json["is_favorite"] is False
    with app.app_context():
        assert db.session.get(Bookmark, bookmark_id).is_favorite is False


def test_favorite_without_javascript(client, csrf_token, bookmark_id):
    response = client.post(f"/bookmarks/{bookmark_id}/favorite",
                           data={"csrf_token": csrf_token()})
    assert response.status_code == 303
    assert response.location == "/"
    assert b"Added to favorites." in client.get("/").data


@pytest.mark.parametrize("token", [None, "invalid"])
def test_favorite_csrf(app, client, bookmark_id, token):
    data = {} if token is None else {"csrf_token": token}
    response = client.post(f"/bookmarks/{bookmark_id}/favorite", data=data,
                           headers={"Accept": "application/json"})
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(Bookmark, bookmark_id).is_favorite is False


def test_missing_favorite_and_get_is_not_allowed(client, csrf_token, bookmark_id):
    response = client.post("/bookmarks/999999/favorite", data={"csrf_token": csrf_token()},
                           headers={"Accept": "application/json"})
    assert response.status_code == 404
    assert client.get(f"/bookmarks/{bookmark_id}/favorite").status_code == 405


def test_dashboard_filter_markup_escapes_input(app, client, bookmark_id):
    with app.app_context():
        bookmark = db.session.get(Bookmark, bookmark_id)
        bookmark.description = '\"><script>alert(1)</script>'
        db.session.commit()
    html = client.get("/").data
    assert b'id="bookmark-search"' in html
    assert b'data-category-filter="Research"' in html
    assert b'data-view="favorites"' in html
    assert b'id="no-results"' in html
    assert b'&lt;script&gt;' in html
    assert b'<script>alert(1)</script>' not in html
