from flask import Flask

from app.extensions import db, migrate, csrf


def create_app(test_config=None):

    app = Flask(__name__)

    app.config.from_object("config.Config")

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    from app import models

    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.routes.main import main_bp
    from app.routes.storage import storage_bp
    from app.routes.medicines import medicines_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(storage_bp)
    app.register_blueprint(medicines_bp)

    return app