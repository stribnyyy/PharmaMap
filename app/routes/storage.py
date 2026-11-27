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
    update_location,
    delete_location,
    get_move_targets,
    move_location,
    reorder_location,
    create_slots,
    ALLOWED_CHILDREN,
    LOCATION_TYPES
)

from flask import abort
from sqlalchemy.exc import IntegrityError

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

@storage_bp.route(
    "/<int:location_id>/edit",
    methods=["GET", "POST"]
)
def edit(location_id):

    location = db.get_or_404(
        Location,
        location_id
    )

    if request.method == "POST":

        name = request.form.get("name", "")
        description = request.form.get(
            "description", ""
        )

        try:
            update_location(
                location,
                name,
                description
            )

            flash(
                "Изменения успешно сохранены.",
                "success"
            )

            return redirect(
                url_for(
                    "storage.detail",
                    location_id=location_id
                ),
                code=303
            )

        except ValueError as error:
            flash(str(error), "error")

            return redirect(
                url_for(
                    "storage.edit",
                    location_id=location_id
                ),
                code=303
            )

    return render_template(
        "storage/edit.html",
        location=location
    )

@storage_bp.post("/<int:location_id>/delete")
def delete(location_id):

    location = db.get_or_404(
        Location,
        location_id
    )

    parent_id = location.parent_id

    try:
        delete_location(location)

        flash(
            "Место хранения успешно удалено.",
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

    if parent_id is None:

        return redirect(
            url_for("storage.index"),
            code=303
        )

    return redirect(
        url_for(
            "storage.detail",
            location_id=parent_id
        ),
        code=303
    )

@storage_bp.route(
    "/<int:location_id>/move",
    methods=["GET", "POST"]
)
def move(location_id):

    location = db.get_or_404(
        Location,
        location_id
    )

    if request.method == "POST":

        parent_id = request.form.get(
            "parent_id",
            type=int
        )

        new_parent = None

        if parent_id is not None and 0 < parent_id <= 2**63 - 1:
            new_parent = db.session.get(
                Location,
                parent_id
            )

        try:
            if new_parent is None:
                raise ValueError(
                    "Выбранное место хранения не существует."
                )

            move_location(location, new_parent)

            flash(
                "Место хранения успешно перемещено.",
                "success"
            )

            return redirect(
                url_for(
                    "storage.detail",
                    location_id=location_id
                ),
                code=303
            )

        except ValueError as error:
            flash(str(error), "error")

            return redirect(
                url_for(
                    "storage.move",
                    location_id=location_id
                ),
                code=303
            )

    return render_template(
        "storage/move.html",
        location=location,
        path=get_location_path(location),
        targets=get_move_targets(location)
    )

@storage_bp.get("/<int:location_id>/layout")
def layout(location_id):

    cabinet = db.get_or_404(
        Location,
        location_id
    )

    if cabinet.type != "cabinet":
        abort(404)

    focus_id = request.args.get("focus", type=int)

    selected_id = None
    focus_path_ids = set()

    if focus_id is not None and 0 < focus_id <= 2**63 - 1:

        target = db.session.get(Location, focus_id)

        if target is not None:

            path = get_location_path(target)

            if path[0].id == cabinet.id:

                selected_id = target.id
                focus_path_ids = {
                    item.id for item in path
                }
    edit_mode = request.args.get("edit") == "1"
    return render_template(
        "storage/layout.html",
        cabinet=cabinet,
        selected_id=selected_id,
        focus_path_ids=focus_path_ids,
        location_types=LOCATION_TYPES,
        edit_mode=edit_mode,
        allowed_children=ALLOWED_CHILDREN
    )

@storage_bp.post("/<int:location_id>/layout/reorder")
def layout_reorder(location_id):

    location = db.get_or_404(
        Location, location_id
    )

    cabinet = get_location_path(location)[0]

    if cabinet.type != "cabinet":
        abort(404)

    direction = request.form.get(
        "direction", ""
    )

    try:
        reorder_location(location, direction)

        flash("Порядок изменён.", "success")

    except ValueError as error:
        flash(str(error), "error")

    except IntegrityError:
        db.session.rollback()
        flash("Не удалось изменить порядок.", "error")

    return redirect(
        url_for(
            "storage.layout",
            location_id=cabinet.id,
            edit=1,
            focus=location_id
        ),
        code=303
    )

@storage_bp.post("/<int:location_id>/layout/add")
def layout_add(location_id):

    parent = db.get_or_404(
        Location, location_id
    )

    cabinet = get_location_path(parent)[0]

    if cabinet.type != "cabinet":
        abort(404)

    action = request.form.get("action", "")
    focus_id = parent.id

    try:

        if action == "single":

            child = create_child_location(
                parent,
                request.form.get("name", ""),
                request.form.get("type", "")
            )

            focus_id = child.id

            flash(
                "Место хранения успешно создано.",
                "success"
            )

        elif action == "batch":

            count = request.form.get(
                "count",
                type=int
            )

            slots = create_slots(parent, count)

            flash(
                f"Создано ячеек: {len(slots)}.",
                "success"
            )

        else:
            raise ValueError(
                "Неизвестная операция."
            )

    except ValueError as error:
        flash(str(error), "error")

    except IntegrityError:
        db.session.rollback()

        flash(
            "Не удалось создать места хранения.",
            "error"
        )

    return redirect(
        url_for(
            "storage.layout",
            location_id=cabinet.id,
            edit=1,
            focus=focus_id
        ),
        code=303
    )