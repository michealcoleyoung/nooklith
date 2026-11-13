from app import create_app, db
from app.models import Bookmark


def test_dashboard_empty_state(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Your little corner of the internet." in response.data
    assert b"Great finds deserve a little home." in response.data
    assert b"0 bookmarks" in response.data


def test_database_persistence_and_defaults(app):
    with app.app_context():
        bookmark = Bookmark(title="Flask", url="https://flask.palletsprojects.com/")
        db.session.add(bookmark)
        db.session.commit()
        assert bookmark.category == "Other"
        assert bookmark.is_favorite is False
        assert bookmark.created_at is not None
        assert bookmark.updated_at is not None

    restarted_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret-key",
        "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
    })
    with restarted_app.app_context():
        assert db.session.execute(db.select(Bookmark)).scalar_one().title == "Flask"
    assert b"Flask" in restarted_app.test_client().get("/").data


def test_dashboard_escapes_saved_content(app, client):
    with app.app_context():
        db.session.add(Bookmark(title="<script>alert(1)</script>", url="javascript:alert(1)"))
        db.session.commit()
    response = client.get("/")
    assert b"&lt;script&gt;" in response.data
    assert b'href="javascript:' not in response.data


def test_missing_page(client):
    assert client.get("/missing").status_code == 404


def test_creation_requires_csrf(client):
    assert client.post("/bookmarks").status_code == 400
