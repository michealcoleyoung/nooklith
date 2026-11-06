from urllib.parse import urlsplit

from flask import Blueprint, render_template

from app import db
from app.models import Bookmark, CATEGORIES

main = Blueprint("main", __name__)


@main.get("/")
def index():
    bookmarks = db.session.execute(
        db.select(Bookmark).order_by(Bookmark.created_at.desc(), Bookmark.id.desc())
    ).scalars().all()
    return render_template(
        "index.html", bookmarks=bookmarks, categories=CATEGORIES,
        domain=lambda url: urlsplit(url).netloc,
    )
