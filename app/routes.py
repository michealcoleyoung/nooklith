from ipaddress import ip_address
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Bookmark, Category, category_names

main = Blueprint("main", __name__)


def normalize_url(value):
    """Validate HTTP(S) syntax without fetching or resolving the destination."""
    if not value or len(value) > 4096:
        raise ValueError("Enter a URL of at most 4,096 characters.")
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127
           for character in value) or "\\" in value:
        raise ValueError("URLs cannot contain spaces, control characters, or backslashes.")
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
            raise ValueError
        if parts.username is not None or parts.password is not None:
            raise ValueError
        port = parts.port
        host = parts.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        try:
            address = ip_address(host)
        except ValueError:
            if len(host) > 253 or not all(
                re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in host.split(".")
            ) or re.fullmatch(r"[0-9.]+", host):
                raise ValueError
        else:
            host = f"[{address.compressed}]" if address.version == 6 else str(address)
        if port == 0 or parts.netloc.endswith(":"):
            raise ValueError
    except (ValueError, UnicodeError):
        raise ValueError("Enter a valid HTTP or HTTPS URL without embedded credentials.") from None

    scheme = parts.scheme.lower()
    if port is not None and (scheme, port) not in (("http", 80), ("https", 443)):
        host = f"{host}:{port}"
    return urlunsplit((scheme, host, parts.path or "/", parts.query, parts.fragment))


def bookmark_values():
    values = {field: request.form.get(field, "").strip()
              for field in ("title", "url", "description", "category")}
    errors = {}
    if not values["title"]:
        errors["title"] = "Give your bookmark a title."
    elif len(values["title"]) > 255:
        errors["title"] = "Keep the title to 255 characters or fewer."
    try:
        normalized_url = normalize_url(values["url"])
    except ValueError as error:
        errors["url"] = str(error)
    else:
        values["url"] = normalized_url
    values["category"] = values["category"] or "Other"
    if values["category"] not in category_names():
        errors["category"] = "Choose one of the listed categories."
    if len(values["description"]) > 5000:
        errors["description"] = "Keep the description to 5,000 characters or fewer."
    return values, errors


def render_form(values, errors=None, bookmark=None):
    return render_template(
        "bookmark_form.html", values=values, errors=errors or {},
        bookmark=bookmark, categories=category_names(),
    )


@main.get("/")
def index():
    bookmarks = db.session.execute(
        db.select(Bookmark).order_by(Bookmark.created_at.desc(), Bookmark.id.desc())
    ).scalars().all()
    return render_template(
        "index.html", bookmarks=bookmarks, categories=category_names(),
        domain=lambda url: urlsplit(url).netloc,
    )


@main.get("/bookmarks/new")
def new_bookmark():
    return render_form({"title": "", "url": "", "description": "", "category": "Other"})


@main.post("/bookmarks")
def create_bookmark():
    values, errors = bookmark_values()
    if errors:
        return render_form(values, errors), 422
    db.session.add(Bookmark(**values))
    db.session.commit()
    flash("Bookmark saved. A new find for your nook.", "success")
    return redirect(url_for("main.index"), code=303)


@main.route("/bookmarks/<int:bookmark_id>/edit", methods=["GET", "POST"])
def edit_bookmark(bookmark_id):
    bookmark = db.get_or_404(Bookmark, bookmark_id)
    if request.method == "GET":
        values = {field: getattr(bookmark, field) or ""
                  for field in ("title", "url", "description", "category")}
        return render_form(values, bookmark=bookmark)
    values, errors = bookmark_values()
    if errors:
        return render_form(values, errors, bookmark), 422
    for field, value in values.items():
        setattr(bookmark, field, value)
    db.session.commit()
    flash("Bookmark updated.", "success")
    return redirect(url_for("main.index"), code=303)


@main.post("/bookmarks/<int:bookmark_id>/delete")
def delete_bookmark(bookmark_id):
    bookmark = db.get_or_404(Bookmark, bookmark_id)
    # A server-rendered confirmation keeps deletion safe when JavaScript is off.
    if request.form.get("confirmed") != "yes":
        return render_template("bookmark_delete.html", bookmark=bookmark)
    db.session.delete(bookmark)
    db.session.commit()
    flash("Bookmark deleted.", "success")
    return redirect(url_for("main.index"), code=303)


@main.post("/bookmarks/<int:bookmark_id>/favorite")
def toggle_favorite(bookmark_id):
    bookmark = db.get_or_404(Bookmark, bookmark_id)
    bookmark.is_favorite = not bookmark.is_favorite
    db.session.commit()
    if request.accept_mimetypes.best == "application/json":
        return jsonify(id=bookmark.id, is_favorite=bookmark.is_favorite)
    flash("Added to favorites." if bookmark.is_favorite else "Removed from favorites.", "success")
    return redirect(url_for("main.index"), code=303)


def render_categories(name="", error=None):
    categories = db.session.execute(db.select(Category).order_by(Category.id)).scalars().all()
    return render_template("categories.html", categories=categories, name=name, error=error)


@main.get("/categories")
def manage_categories():
    return render_categories()


@main.post("/categories")
def create_category():
    raw_name = request.form.get("name", "")
    name = " ".join(raw_name.split())
    if not name or len(name) > 50:
        return render_categories(name, "Enter a category name between 1 and 50 characters."), 422
    if any(unicodedata.category(character).startswith("C") for character in raw_name):
        return render_categories(name, "Category names cannot contain control characters."), 422
    db.session.add(Category(name=name, name_key=name.casefold()))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return render_categories(name, "That category already exists. Choose a different name."), 422
    flash(f'Category “{name}” added.', "success")
    return redirect(url_for("main.manage_categories"), code=303)


@main.post("/categories/<int:category_id>/delete")
def delete_category(category_id):
    category = db.get_or_404(Category, category_id)
    if category.name == "Other":
        abort(400, description="Other is the fallback category and cannot be deleted.")
    if request.form.get("confirmed") != "yes":
        return render_template("category_delete.html", category=category)
    db.session.execute(
        db.update(Bookmark).where(Bookmark.category == category.name).values(category="Other")
    )
    name = category.name
    db.session.delete(category)
    db.session.commit()
    flash(f'Category “{name}” deleted. Its bookmarks are now in Other.', "success")
    return redirect(url_for("main.manage_categories"), code=303)
