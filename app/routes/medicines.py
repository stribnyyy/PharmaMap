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

    paths = [
        get_location_path(placement.location)
        for placement in medicine.placements
    ]

    return render_template(
        "medicines/detail.html",
        medicine=medicine,
        paths=paths
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