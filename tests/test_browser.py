"""Optional browser checks; every test uses a temporary database and browser profile."""

from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from app import db
from app.models import Bookmark

pytestmark = pytest.mark.browser

DEMO_BOOKMARKS = [
    ("Python documentation", "https://docs.python.org/3/", "The reference shelf for everyday Python. Tutorials, recipes, and the details worth remembering.", "Technology", True),
    ("Flask documentation", "https://flask.palletsprojects.com/", "Small building blocks for thoughtful web applications.", "Technology", True),
    ("A calmer soundtrack", "https://example.com/music", "A sample bookmark for music that makes a quiet afternoon feel a little better.", "Music", False),
    ("Notes from the reading room", "https://example.com/research", "Questions to return to, ideas to connect, and a few rabbit holes worth exploring.", "Research", True),
    ("The weekend list", "https://example.com/weekend", "A few places to go and things to make when there is room to slow down.", "Personal", False),
    ("A collection of little things", "https://example.com/discoveries", "Interesting corners of the web. Saved for another day.", "Other", False),
]


@pytest.fixture(scope="module")
def browser(request):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=request.config.getoption("--browser-channel"))
        yield browser
        browser.close()


@pytest.fixture
def live_server(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page
    context.close()
    assert not errors, f"Browser JavaScript errors: {errors}"


@pytest.fixture
def demo(app):
    with app.app_context():
        for title, url, description, category, favorite in DEMO_BOOKMARKS:
            db.session.add(Bookmark(title=title, url=url, description=description,
                                    category=category, is_favorite=favorite))
        db.session.commit()


def screenshot(page, request, name):
    if request.config.getoption("--screenshots"):
        destination = Path(__file__).resolve().parents[1] / "docs" / "screenshots" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(destination), full_page=True, animations="disabled")


def assert_no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Horizontal page overflow"


def test_responsive_dashboard_and_screenshots(page, live_server, demo, request):
    page.goto(live_server)
    expect(page.locator("[data-bookmark]")).to_have_count(6)
    expect(page.locator("#bookmark-search")).to_be_enabled()
    for width, height, name in [(1440, 1000, "desktop.png"), (768, 1024, None),
                                (390, 844, "mobile.png"), (320, 740, None)]:
        page.set_viewport_size({"width": width, "height": height})
        assert_no_overflow(page)
        # Every category remains keyboard/touch reachable at the narrowest width.
        for button in page.locator("[data-category-filter]").all():
            expect(button).to_be_visible()
            assert button.bounding_box()["height"] >= 44
        if name:
            screenshot(page, request, name)


def test_combined_filters_and_favorites(page, live_server, demo):
    page.goto(live_server)
    page.locator("#bookmark-search").fill("PYTHON")
    expect(page.locator("[data-bookmark]:visible")).to_have_count(1)
    page.locator('[data-category-filter="Technology"]').click()
    page.locator('[data-view="favorites"]').click()
    expect(page.locator("#result-count")).to_have_text("1 of 6 bookmarks")
    expect(page.locator("#filter-summary")).to_contain_text("Favorites · Technology")
    star = page.locator("[data-bookmark]:visible .favorite-button")
    star.focus()
    star.click()
    expect(page.locator("#favorite-feedback")).to_have_text("Removed from favorites.")
    expect(page.locator("#no-results")).to_be_visible()
    expect(page.locator("#bookmark-search")).to_be_focused()
    page.reload()
    card = page.locator('[data-bookmark][data-title="Python documentation"]')
    expect(card.locator(".favorite-button")).to_have_attribute("aria-pressed", "false")
    page.locator("#bookmark-search").fill("no such discovery")
    expect(page.locator("#no-results")).to_be_visible()
    page.locator("#clear-filters").click()
    expect(page.locator("[data-bookmark]:visible")).to_have_count(6)


def test_crud_validation_keyboard_and_empty_screenshot(page, live_server, request):
    page.goto(live_server)
    expect(page.locator("#empty-title")).to_be_visible()
    screenshot(page, request, "empty-state.png")
    page.keyboard.press("Tab")
    expect(page.locator(".skip-link")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("main")).to_be_focused()
    page.locator(".header .add-button").click()
    screenshot(page, request, "bookmark-form.png")
    for width in (768, 390, 320):
        page.set_viewport_size({"width": width, "height": 844})
        assert_no_overflow(page)
    page.locator("#url").fill("ftp://example.com")
    page.locator("#title").fill("A test bookmark")
    page.get_by_role("button", name="Save bookmark", exact=True).click()
    expect(page.locator(".form-summary")).to_be_focused()
    page.locator('.form-summary a[href="#url"]').click()
    expect(page.locator("#url")).to_be_focused()
    page.locator("#url").fill("https://example.com")
    page.get_by_role("button", name="Save bookmark", exact=True).click()
    expect(page.locator("[data-bookmark]")).to_have_count(1)
    page.get_by_role("link", name="Edit A test bookmark", exact=True).click()
    expect(page.locator("#title")).to_have_value("A test bookmark")
    page.locator("#title").fill("Updated bookmark")
    page.get_by_role("button", name="Save changes", exact=True).click()
    expect(page.locator("[data-bookmark] h3")).to_contain_text("Updated bookmark")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Delete Updated bookmark", exact=True).click()
    expect(page.locator("[data-bookmark]")).to_have_count(1)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete Updated bookmark", exact=True).click()
    expect(page.locator("#empty-title")).to_be_visible()


def test_failed_favorite_request_preserves_star(page, live_server, demo):
    page.goto(live_server)
    button = page.locator('[data-title="Python documentation"] .favorite-button')
    page.route("**/bookmarks/*/favorite", lambda route: route.abort())
    button.click()
    expect(page.locator("#favorite-feedback")).to_contain_text("Refresh the page")
    expect(button).to_have_attribute("aria-pressed", "true")
    expect(button).to_be_enabled()


def test_without_javascript(browser, live_server, demo):
    context = browser.new_context(java_script_enabled=False)
    try:
        page = context.new_page()
        page.goto(live_server)
        card = page.locator('[data-title="Python documentation"]')
        card.locator(".favorite-button").click()
        expect(page.locator('[data-title="Python documentation"] .favorite-button')).to_have_attribute("aria-pressed", "false")
        page.get_by_role("button", name="Delete Python documentation", exact=True).click()
        expect(page.get_by_role("heading", name="Delete this bookmark?")).to_be_visible()
        page.get_by_role("link", name="Keep bookmark").click()
        expect(page.locator('[data-title="Python documentation"]')).to_be_visible()
    finally:
        context.close()


def test_manage_custom_categories(page, live_server):
    page.goto(live_server)
    page.get_by_role("link", name="Manage categories", exact=True).click()
    category = "Design" * 8
    page.locator("#name").fill(category)
    page.get_by_role("button", name="Add category", exact=True).click()
    expect(page.locator(".flash-messages")).to_contain_text("added")
    page.get_by_role("link", name="Back to your collection").click()
    page.set_viewport_size({"width": 320, "height": 740})
    assert_no_overflow(page)
    expect(page.locator(f'[data-category-filter="{category}"]')).to_be_visible()
    page.locator(".header .add-button").click()
    page.locator("#title").fill("A design bookmark")
    page.locator("#url").fill("https://example.com")
    page.locator("#category").select_option(category)
    page.get_by_role("button", name="Save bookmark", exact=True).click()
    page.locator(f'[data-category-filter="{category}"]').click()
    expect(page.locator("[data-bookmark]:visible")).to_have_count(1)
    page.get_by_role("link", name="Manage categories", exact=True).click()
    assert_no_overflow(page)
    page.get_by_role("button", name=f"Delete category {category}", exact=True).click()
    expect(page.get_by_role("heading", name="Delete this category?")).to_be_visible()
    page.get_by_role("link", name="Keep category").click()
    expect(page.get_by_role("button", name=f"Delete category {category}", exact=True)).to_be_visible()
    page.get_by_role("button", name=f"Delete category {category}", exact=True).click()
    page.get_by_role("button", name="Delete category", exact=True).click()
    page.get_by_role("link", name="Back to your collection").click()
    expect(page.locator("[data-bookmark] .category-pill")).to_have_text("Other")
    expect(page.locator(f'[data-category-filter="{category}"]')).to_have_count(0)
