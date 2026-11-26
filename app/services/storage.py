from app.extensions import db
from app.models import Location


def get_cabinets():
    statement = (
        db.select(Location)
        .where(
            Location.parent_id.is_(None),
            Location.type == "cabinet"
        )
        .order_by(Location.position, Location.id)
    )

    return db.session.scalars(statement).all()


def create_cabinet(name: str) -> Location:
    name = name.strip()

    if not name:
        raise ValueError("Название шкафа не может быть пустым.")

    if len(name) > 150:
        raise ValueError("Название слишком длинное.")

    cabinets = get_cabinets()

    if any(
        cabinet.name.casefold() == name.casefold()
        for cabinet in cabinets
    ):
        raise ValueError("Шкаф с таким названием уже существует.")

    position = max(
        (cabinet.position for cabinet in cabinets),
        default=0
    ) + 1

    cabinet = Location(
        name=name,
        type="cabinet",
        position=position
    )

    db.session.add(cabinet)
    db.session.commit()

    return cabinet