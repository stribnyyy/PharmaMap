from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from app.services.storage import (
    get_cabinets,
    create_cabinet
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