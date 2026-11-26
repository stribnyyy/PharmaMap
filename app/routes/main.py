from flask import Blueprint, render_template, current_app, request

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    query = request.args.get("q", "").strip()

    return render_template(
        "index.html",
        app_name=current_app.config["APP_NAME"],
        query=query
    )