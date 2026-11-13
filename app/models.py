from datetime import datetime, timezone

from app import db

DEFAULT_CATEGORIES = ("Technology", "Music", "Research", "Personal", "Other")


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    name_key = db.Column(db.String(150), nullable=False, unique=True)


def initialize_categories():
    """Seed once, including existing bookmark categories when upgrading."""
    if db.session.execute(db.select(Category.id).limit(1)).first() is not None:
        return
    existing = db.session.execute(db.select(Bookmark.category).distinct()).scalars().all()
    names = dict.fromkeys((*DEFAULT_CATEGORIES, *existing))
    for name in names:
        if name:
            db.session.add(Category(name=name, name_key=name.casefold()))
    db.session.commit()


def category_names():
    return db.session.execute(db.select(Category.name).order_by(Category.id)).scalars().all()


def utc_now():
    return datetime.now(timezone.utc)


class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default="Other")
    is_favorite = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
