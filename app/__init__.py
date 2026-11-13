from pathlib import Path
import os
import secrets

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        key_path = Path(app.instance_path) / "secret_key"
        try:
            descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "w") as key_file:
                key_file.write(secrets.token_hex(32))
        app.config["SECRET_KEY"] = key_path.read_text().strip()
    db.init_app(app)
    csrf.init_app(app)

    from app import models
    from app.routes import main

    app.register_blueprint(main)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template("errors/csrf.html"), 400

    with app.app_context():
        db.create_all()

    return app
