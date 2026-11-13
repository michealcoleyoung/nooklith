import os


class Config:
    # Relative SQLite paths are resolved inside Flask's instance directory.
    SQLALCHEMY_DATABASE_URI = "sqlite:///nooklith.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
    MAX_CONTENT_LENGTH = 64 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
