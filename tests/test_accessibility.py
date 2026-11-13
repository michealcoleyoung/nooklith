from html.parser import HTMLParser


class PageMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_error_summary_links_to_invalid_fields(client, csrf_token):
    response = client.post("/bookmarks", data={
        "csrf_token": csrf_token(), "title": " ", "url": "invalid",
    })
    assert response.status_code == 422
    elements = PageMarkup(response.get_data(as_text=True)).elements
    summary = next(attrs for tag, attrs in elements if attrs.get("class") == "form-summary")
    assert summary["tabindex"] == "-1"
    assert summary["role"] == "alert"
    targets = {attrs["href"] for tag, attrs in elements if tag == "a" and attrs.get("href", "").startswith("#")}
    for field in ("title", "url"):
        assert f"#{field}" in targets
        control = next(attrs for tag, attrs in elements if attrs.get("id") == field)
        assert control["aria-invalid"] == "true"
        assert control["aria-describedby"] == f"{field}-error"


def test_form_help_and_skip_target(client):
    elements = PageMarkup(client.get("/bookmarks/new").get_data(as_text=True)).elements
    main = next(attrs for tag, attrs in elements if tag == "main")
    assert main["id"] == "main"
    assert main["tabindex"] == "-1"
    description = next(attrs for tag, attrs in elements if tag == "textarea")
    assert description["aria-describedby"] == "description-hint"
    assert any(attrs.get("id") == "description-hint" for tag, attrs in elements)
