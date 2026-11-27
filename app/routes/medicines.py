from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from app.extensions import db
from app.models import Medicine

from app.services.medicines import (
    get_medicines,
    save_medicine,
    delete_medicine,
    FIELD_LABELS,
    FIELD_LIMITS
)

from app.services.storage import get_location_path

from flask import abort

from app.models import Location, Placement

from app.services.placements import (
    require_object,
    get_available_locations,
    create_placement,
    move_placement,
    delete_placement
)

medicines_bp = Blueprint(
    "medicines",
    __name__,
    url_prefix="/medicines"
)


@medicines_bp.get("/")
def index():

    return render_template(
        "medicines/index.html",
        medicines=get_medicines()
    )


@medicines_bp.route(
    "/create",
    methods=["GET", "POST"]
)
def create():

    values = {}

    if request.method == "POST":

        values = request.form.to_dict()

        try:
            medicine = save_medicine(values)

        except ValueError as error:

            flash(str(error), "error")

            return render_template(
                "medicines/form.html",
                medicine=None,
                values=values,
                fields=FIELD_LABELS,
                limits=FIELD_LIMITS
            ), 400

        flash("Лекарство успешно создано.", "success")

        return redirect(
            url_for(
                "medicines.detail",
                medicine_id=medicine.id
            ),
            code=303
        )

    return render_template(
        "medicines/form.html",
        medicine=None,
        values=values,
        fields=FIELD_LABELS,
        limits=FIELD_LIMITS
    )


@medicines_bp.get("/<int:medicine_id>")
def detail(medicine_id):

    medicine = db.get_or_404(
        Medicine, medicine_id
    )

    placement_rows = [
        (
            placement,
            get_location_path(placement.location)
        )
        for placement in medicine.placements
    ]

    return render_template(
        "medicines/detail.html",
        medicine=medicine,
        placement_rows=placement_rows,
        available_locations=get_available_locations(
            medicine
        )
    )


@medicines_bp.route(
    "/<int:medicine_id>/edit",
    methods=["GET", "POST"]
)
def edit(medicine_id):

    medicine = db.get_or_404(
        Medicine, medicine_id
    )

    values = {
        field: getattr(medicine, field) or ""
        for field in FIELD_LABELS
    }

    if request.method == "POST":

        values = request.form.to_dict()

        try:
            save_medicine(values, medicine)

        except ValueError as error:

            flash(str(error), "error")

            return render_template(
                "medicines/form.html",
                medicine=medicine,
                values=values,
                fields=FIELD_LABELS,
                limits=FIELD_LIMITS
            ), 400

        flash("Изменения успешно сохранены.", "success")

        return redirect(
            url_for(
                "medicines.detail",
                medicine_id=medicine_id
            ),
            code=303
        )

    return render_template(
        "medicines/form.html",
        medicine=medicine,
        values=values,
        fields=FIELD_LABELS,
        limits=FIELD_LIMITS
    )


@medicines_bp.post("/<int:medicine_id>/delete")
def delete(medicine_id):

    medicine = db.get_or_404(
        Medicine, medicine_id
    )

    try:
        delete_medicine(medicine)

    except ValueError as error:

        flash(str(error), "error")

        return redirect(
            url_for(
                "medicines.detail",
                medicine_id=medicine_id
            ),
            code=303
        )

    flash("Лекарство успешно удалено.", "success")

    return redirect(
        url_for("medicines.index"),
        code=303
    )

def get_medicine_placement_or_404(
    medicine_id,
    placement_id
):

    placement = db.get_or_404(
        Placement, placement_id
    )

    if placement.medicine_id != medicine_id:
        abort(404)

    return placement

@medicines_bp.post(
    "/<int:medicine_id>/placements/add"
)
def add_placement(medicine_id):

    medicine = db.get_or_404(
        Medicine, medicine_id
    )

    try:

        location = require_object(
            Location,
            request.form.get(
                "location_id", type=int
            ),
            "Место хранения не существует."
        )

        create_placement(medicine, location)

        flash(
            "Место хранения назначено.",
            "success"
        )

    except ValueError as error:
        flash(str(error), "error")

    return redirect(
        url_for(
            "medicines.detail",
            medicine_id=medicine_id
        ),
        code=303
    )

@medicines_bp.post(
    "/<int:medicine_id>"
    "/placements/<int:placement_id>/move"
)
def relocate_placement(medicine_id, placement_id):

    placement = get_medicine_placement_or_404(
        medicine_id,
        placement_id
    )

    try:

        location = require_object(
            Location,
            request.form.get(
                "location_id", type=int
            ),
            "Место хранения не существует."
        )

        move_placement(placement, location)

        flash(
            "Размещение успешно изменено.",
            "success"
        )

    except ValueError as error:
        flash(str(error), "error")

    return redirect(
        url_for(
            "medicines.detail",
            medicine_id=medicine_id
        ),
        code=303
    )

@medicines_bp.post(
    "/<int:medicine_id>"
    "/placements/<int:placement_id>/delete"
)
def remove_placement(medicine_id, placement_id):

    placement = get_medicine_placement_or_404(
        medicine_id,
        placement_id
    )

    try:

        delete_placement(placement)

        flash(
            "Размещение удалено.",
            "success"
        )

    except ValueError as error:
        flash(str(error), "error")

    return redirect(
        url_for(
            "medicines.detail",
            medicine_id=medicine_id
        ),
        code=303
    )