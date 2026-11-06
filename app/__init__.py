from pathlib import Path

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    from app import models
    from app.routes import main

    app.register_blueprint(main)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    with app.app_context():
        db.create_all()

    return app
