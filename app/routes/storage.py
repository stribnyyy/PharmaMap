from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from app.extensions import db
from app.models import Location

from app.services.storage import (
    get_cabinets,
    create_cabinet,
    get_allowed_children,
    get_location_path,
    create_child_location,
    LOCATION_TYPES
)

storage_bp = Blueprint(
    "storage",
    __name__,
    url_prefix="/storage"
)


@storage_bp.get("/")
def index():
    cabinets = get_cabinets()

    return render_template(
        "storage/index.html",
        cabinets=cabinets
    )


@storage_bp.post("/create")
def create():
    name = request.form.get("name", "")

    try:
        create_cabinet(name)
        flash("Шкаф успешно создан.", "success")

    except ValueError as error:
        flash(str(error), "error")

    return redirect(
        url_for("storage.index"),
        code=303
    )

@storage_bp.get("/<int:location_id>")
def detail(location_id):

    location = db.get_or_404(
        Location,
        location_id
    )

    return render_template(
        "storage/detail.html",
        location=location,
        path=get_location_path(location),
        allowed_types=get_allowed_children(location),
        location_types=LOCATION_TYPES
    )

@storage_bp.post("/<int:location_id>/create")
def create_child(location_id):

    parent = db.get_or_404(
        Location,
        location_id
    )

    name = request.form.get("name", "")
    location_type = request.form.get("type", "")

    try:
        create_child_location(
            parent,
            name,
            location_type
        )

        flash(
            "Место хранения успешно создано.",
            "success"
        )

    except ValueError as error:
        flash(str(error), "error")

    return redirect(
        url_for(
            "storage.detail",
            location_id=location_id
        ),
        code=303
    )