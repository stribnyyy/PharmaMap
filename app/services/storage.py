from app.extensions import db
from app.models import Location

LOCATION_TYPES = {
    "cabinet": "Шкаф",
    "shelf": "Полка",
    "drawer": "Ящик",
    "slot": "Ячейка"
}


ALLOWED_CHILDREN = {
    "cabinet": ("shelf", "drawer", "slot"),
    "shelf": ("drawer", "slot"),
    "drawer": ("slot",),
    "slot": ()
}

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

def get_allowed_children(location: Location):
    return ALLOWED_CHILDREN.get(location.type, ())

def get_location_path(location: Location):
    path = []
    visited = set()

    current = location

    while current is not None:

        if current.id in visited:
            raise ValueError(
                "Обнаружен цикл в структуре хранения."
            )

        visited.add(current.id)
        path.append(current)

        current = current.parent

    return list(reversed(path))

def create_child_location(
    parent: Location,
    name: str,
    location_type: str
) -> Location:

    name = name.strip()

    if not name:
        raise ValueError(
            "Название не может быть пустым."
        )

    if len(name) > 150:
        raise ValueError(
            "Название слишком длинное."
        )

    allowed_types = get_allowed_children(parent)

    if location_type not in allowed_types:
        raise ValueError(
            "Недопустимый тип вложенного объекта."
        )

    if any(
        child.name.casefold() == name.casefold()
        for child in parent.children
    ):
        raise ValueError(
            "Объект с таким названием уже существует."
        )

    position = max(
        (child.position for child in parent.children),
        default=0
    ) + 1

    child = Location(
        name=name,
        type=location_type,
        position=position,
        parent=parent
    )

    db.session.add(child)
    db.session.commit()

    return child