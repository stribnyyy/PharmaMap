from flask import (
    Blueprint,
    render_template,
    current_app,
    request
)

from app.services.search import (
    search_medicines,
    MAX_QUERY_LENGTH
)

from app.services.storage import get_location_path


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():

    query = request.args.get("q", "").strip()

    results = []
    total = 0
    error = None

    if query:

        try:
            medicines, total = search_medicines(query)

            for medicine in medicines:

                paths = [
                    get_location_path(
                        placement.location
                    )
                    for placement in medicine.placements
                ]

                paths.sort(
                    key=lambda path: tuple(
                        (item.position, item.id)
                        for item in path
                    )
                )

                results.append({
                    "medicine": medicine,
                    "paths": paths
                })

        except ValueError as exc:
            error = str(exc)

    return render_template(
        "index.html",
        app_name=current_app.config["APP_NAME"],
        query=query,
        results=results,
        total=total,
        error=error,
        max_query_length=MAX_QUERY_LENGTH
    ), 400 if error else 200