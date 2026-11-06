import os


class Config:
    # Relative SQLite paths are resolved inside Flask's instance directory.
    SQLALCHEMY_DATABASE_URI = "sqlite:///nooklith.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
