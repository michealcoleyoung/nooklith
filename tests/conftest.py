import pytest
import re

from app import create_app


def pytest_addoption(parser):
    parser.addoption("--browser", action="store_true", help="Run real browser tests.")
    parser.addoption("--browser-channel", default="chrome", help="Playwright browser channel.")
    parser.addoption("--screenshots", action="store_true", help="Refresh demo screenshots.")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--screenshots") and not config.getoption("--browser"):
        raise pytest.UsageError("--screenshots requires --browser")
    if not config.getoption("--browser"):
        for item in items:
            if "browser" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Run with --browser to enable Chrome tests."))


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf_token(client):
    def get_token():
        response = client.get("/bookmarks/new")
        return re.search(rb'name="csrf_token" value="([^"]+)"', response.data)[1].decode()
    return get_token
