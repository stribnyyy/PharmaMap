from flask import (
    Flask,
    request,
    redirect,
    url_for
)

from flask_login import current_user

from app.extensions import (
    db,
    migrate,
    csrf,
    login_manager
)


def create_app(test_config=None):

    app = Flask(__name__)

    app.config.from_object("config.Config")

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    from app import models

    migrate.init_app(app, db)

    login_manager.init_app(app)

    from app.routes.main import main_bp
    from app.routes.storage import storage_bp
    from app.routes.medicines import medicines_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(storage_bp)
    app.register_blueprint(medicines_bp)
    app.register_blueprint(auth_bp)

    @app.before_request
    def require_authentication():

        public_endpoints = {
            "auth.login",
            "static"
        }

        if request.endpoint in public_endpoints:
            return None

        if not current_user.is_authenticated:

            return redirect(
                url_for("auth.login"),
                code=302 if request.method == "GET"
                else 303
            )

    csrf.init_app(app)

    return app