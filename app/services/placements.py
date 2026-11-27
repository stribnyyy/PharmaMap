from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Medicine, Location, Placement
from app.services.storage import get_location_path


def require_object(model, object_id, error_message):

    if (
        not isinstance(object_id, int)
        or not 1 <= object_id <= 2**63 - 1
    ):
        raise ValueError(error_message)

    obj = db.session.get(model, object_id)

    if obj is None:
        raise ValueError(error_message)

    return obj


def get_available_locations(medicine: Medicine):

    statement = db.select(Location).where(
        ~Location.placements.any(
            Placement.medicine_id == medicine.id
        )
    )

    locations = db.session.scalars(statement).all()

    choices = []

    for location in locations:

        path = get_location_path(location)

        if path[0].type != "cabinet":
            continue

        label = " → ".join(
            item.name for item in path
        )

        choices.append((location, label))

    return sorted(
        choices,
        key=lambda item: (
            item[1].casefold(),
            item[0].id
        )
    )


def get_available_medicines(location: Location):

    statement = db.select(Medicine).where(
        ~Medicine.placements.any(
            Placement.location_id == location.id
        )
    )

    medicines = db.session.scalars(statement).all()

    return sorted(
        medicines,
        key=lambda item: (
            item.name.casefold(),
            (item.dosage or "").casefold(),
            item.id
        )
    )


def validate_placement(medicine_id, location_id):

    existing = db.session.scalar(
        db.select(Placement).where(
            Placement.medicine_id == medicine_id,
            Placement.location_id == location_id
        )
    )

    if existing is not None:

        raise ValueError(
            "Лекарство уже назначено этому месту."
        )


def commit_placement():

    try:
        db.session.commit()

    except IntegrityError as error:

        db.session.rollback()

        raise ValueError(
            "Не удалось сохранить изменение размещения."
        ) from error


def create_placement(
    medicine: Medicine,
    location: Location
) -> Placement:

    validate_placement(
        medicine.id,
        location.id
    )

    placement = Placement(
        medicine=medicine,
        location=location
    )

    db.session.add(placement)

    commit_placement()

    return placement


def move_placement(
    placement: Placement,
    new_location: Location
) -> Placement:

    if placement.location_id == new_location.id:

        raise ValueError(
            "Лекарство уже находится в этом месте."
        )

    validate_placement(
        placement.medicine_id,
        new_location.id
    )

    placement.location = new_location

    commit_placement()

    return placement


def delete_placement(placement: Placement) -> None:

    db.session.delete(placement)

    commit_placement()