import pytest

from app import db
from app.models import Bookmark


def submit(client, csrf_token, path="/bookmarks", **overrides):
    data = {"title": "A discovery", "url": "https://example.com", "description": "A note",
            "category": "Research", "csrf_token": csrf_token()}
    data.update(overrides)
    return client.post(path, data=data)


def test_create_and_show_bookmark(app, client, csrf_token):
    response = submit(client, csrf_token, title="  My discovery  ",
                      url="  HTTPS://EXAMPLE.COM:443?topic=python#intro  ")
    assert response.status_code == 303
    assert response.location == "/"
    with app.app_context():
        bookmark = db.session.execute(db.select(Bookmark)).scalar_one()
        assert bookmark.title == "My discovery"
        assert bookmark.url == "https://example.com/?topic=python#intro"
        assert bookmark.description == "A note"
        assert bookmark.category == "Research"
        assert bookmark.is_favorite is False
    dashboard = client.get("/")
    assert b"My discovery" in dashboard.data
    assert b"Bookmark saved" in dashboard.data
    assert b'rel="noopener noreferrer"' in dashboard.data


@pytest.mark.parametrize("url", [
    "", "example.com", "ftp://example.com", "javascript:alert(1)", "https://",
    "https://exa mple.com", "https://example.com:bad", "https://example.com:70000",
    "https://example.com:0", "https://example.com:", "https://[bad]",
    "https://user:password@example.com", "https://-bad.example", "https://bad_.example",
    "https://example.com\\@evil.example", "https://example.com/\npath", "https://999.999.999.999",
])
def test_invalid_urls_rejected(app, client, csrf_token, url):
    response = submit(client, csrf_token, url=url)
    assert response.status_code == 422
    assert b'aria-invalid="true"' in response.data
    with app.app_context():
        assert db.session.execute(db.select(Bookmark)).scalars().all() == []


@pytest.mark.parametrize("url, expected", [
    ("HTTP://Example.COM:80", "http://example.com/"),
    ("https://example.com:8443/Path?q=A#B", "https://example.com:8443/Path?q=A#B"),
    ("https://bücher.example", "https://xn--bcher-kva.example/"),
    ("http://[::1]:8080", "http://[::1]:8080/"),
])
def test_normalization(app, client, csrf_token, url, expected):
    assert submit(client, csrf_token, url=url).status_code == 303
    with app.app_context():
        assert db.session.execute(db.select(Bookmark)).scalar_one().url == expected


@pytest.mark.parametrize("overrides, error", [
    ({"title": "   "}, b"Give your bookmark a title"),
    ({"title": "x" * 256}, b"255 characters"),
    ({"description": "x" * 5001}, b"5,000 characters"),
    ({"category": "Unknown"}, b"listed categories"),
])
def test_validation_preserves_input(app, client, csrf_token, overrides, error):
    response = submit(client, csrf_token, **overrides)
    assert response.status_code == 422
    assert error in response.data
    assert b"https://example.com/" in response.data
    with app.app_context():
        assert db.session.execute(db.select(Bookmark)).scalars().all() == []


def test_optional_fields_default(app, client, csrf_token):
    assert client.post("/bookmarks", data={
        "title": "Minimal", "url": "https://example.com", "csrf_token": csrf_token(),
    }).status_code == 303
    with app.app_context():
        bookmark = db.session.execute(db.select(Bookmark)).scalar_one()
        assert bookmark.category == "Other"
        assert bookmark.description == ""


def test_edit_only_updates_selected_record(app, client, csrf_token):
    submit(client, csrf_token, title="First")
    submit(client, csrf_token, title="Second")
    with app.app_context():
        first, second = db.session.execute(db.select(Bookmark).order_by(Bookmark.id)).scalars()
        first_id, second_id = first.id, second.id
        created_at = first.created_at
        first.is_favorite = True
        db.session.commit()
    response = client.get(f"/bookmarks/{first_id}/edit")
    assert b'value="First"' in response.data
    assert b"A note</textarea>" in response.data
    response = submit(client, csrf_token, f"/bookmarks/{first_id}/edit", title="Updated",
                      url="https://updated.example", description="Changed", category="Music")
    assert response.status_code == 303
    with app.app_context():
        first = db.session.get(Bookmark, first_id)
        assert first.title == "Updated"
        assert first.url == "https://updated.example/"
        assert first.description == "Changed"
        assert first.category == "Music"
        assert first.is_favorite is True
        assert first.created_at == created_at
        assert first.updated_at >= created_at
        assert db.session.get(Bookmark, second_id).title == "Second"
        assert len(db.session.execute(db.select(Bookmark)).scalars().all()) == 2
    assert b"Bookmark updated" in client.get("/").data


def test_invalid_edit_does_not_change_record(app, client, csrf_token):
    submit(client, csrf_token)
    with app.app_context():
        bookmark_id = db.session.execute(db.select(Bookmark)).scalar_one().id
    assert submit(client, csrf_token, f"/bookmarks/{bookmark_id}/edit",
                  title="Changed", url="invalid").status_code == 422
    with app.app_context():
        assert db.session.get(Bookmark, bookmark_id).title == "A discovery"


def test_delete_confirmation_and_selected_record(app, client, csrf_token):
    submit(client, csrf_token, title="First")
    submit(client, csrf_token, title="Second")
    with app.app_context():
        first, second = db.session.execute(db.select(Bookmark).order_by(Bookmark.id)).scalars()
        first_id, second_id = first.id, second.id
    path = f"/bookmarks/{first_id}/delete"
    assert client.get(path).status_code == 405
    confirmation = client.post(path, data={"csrf_token": csrf_token()})
    assert confirmation.status_code == 200
    assert b"Delete this bookmark?" in confirmation.data
    with app.app_context():
        assert db.session.get(Bookmark, first_id) is not None
    assert client.post(path, data={"csrf_token": csrf_token(), "confirmed": "yes"}).status_code == 303
    with app.app_context():
        assert db.session.get(Bookmark, first_id) is None
        assert db.session.get(Bookmark, second_id).title == "Second"
    assert b"Bookmark deleted" in client.get("/").data


@pytest.mark.parametrize("path", ["/bookmarks/999/edit", "/bookmarks/999/delete"])
def test_missing_record(client, csrf_token, path):
    assert client.post(path, data={"csrf_token": csrf_token(), "confirmed": "yes"}).status_code == 404
    if path.endswith("edit"):
        assert client.get(path).status_code == 404


@pytest.mark.parametrize("action", ["create", "edit", "delete"])
@pytest.mark.parametrize("token", [None, "invalid"])
def test_csrf_rejection_leaves_database_unchanged(app, client, csrf_token, action, token):
    submit(client, csrf_token)
    with app.app_context():
        bookmark_id = db.session.execute(db.select(Bookmark)).scalar_one().id
    path = {"create": "/bookmarks", "edit": f"/bookmarks/{bookmark_id}/edit",
            "delete": f"/bookmarks/{bookmark_id}/delete"}[action]
    data = {"title": "Tampered", "url": "https://evil.example", "confirmed": "yes"}
    if token:
        data["csrf_token"] = token
    response = client.post(path, data=data)
    assert response.status_code == 400
    assert b"Nothing was changed" in response.data
    with app.app_context():
        bookmarks = db.session.execute(db.select(Bookmark)).scalars().all()
        assert len(bookmarks) == 1
        assert bookmarks[0].title == "A discovery"


def test_token_from_another_session_rejected(app, client, csrf_token):
    token = csrf_token()
    other_client = app.test_client()
    response = other_client.post("/bookmarks", data={
        "title": "Cross session", "url": "https://example.com", "csrf_token": token,
    })
    assert response.status_code == 400
