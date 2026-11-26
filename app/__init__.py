from flask import Flask

from app.extensions import db, migrate


def create_app():
    app = Flask(__name__)

    app.config.from_object("config.Config")

    db.init_app(app)

    from app import models

    migrate.init_app(app, db)

    from app.routes.main import main_bp

    app.register_blueprint(main_bp)

    return app