from app.extensions import db
from app.models import Location
from sqlalchemy.exc import IntegrityError

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

def update_location(
    location: Location,
    name: str,
    description: str = ""
) -> Location:

    name = name.strip()
    description = description.strip()

    if not name:
        raise ValueError(
            "Название не может быть пустым."
        )

    if len(name) > 150:
        raise ValueError(
            "Название слишком длинное."
        )

    if len(description) > 1000:
        raise ValueError(
            "Описание слишком длинное."
        )

    if location.parent_id is None:
        siblings = get_cabinets()
    else:
        siblings = location.parent.children

    if any(
        sibling.id != location.id
        and sibling.name.casefold() == name.casefold()
        for sibling in siblings
    ):
        raise ValueError(
            "Объект с таким названием уже существует."
        )

    location.name = name
    location.description = description or None

    db.session.commit()

    return location

def delete_location(location: Location) -> None:

    if location.children:
        raise ValueError(
            "Нельзя удалить объект, "
            "содержащий вложенные места хранения."
        )

    if location.placements:
        raise ValueError(
            "Нельзя удалить объект, "
            "в котором размещены лекарства."
        )

    try:
        db.session.delete(location)
        db.session.commit()

    except IntegrityError as error:
        db.session.rollback()

        raise ValueError(
            "Удаление невозможно: "
            "объект связан с другими записями."
        ) from error

def validate_move(
    location: Location,
    new_parent: Location
) -> None:

    if location.type == "cabinet":
        raise ValueError(
            "Шкаф нельзя переместить внутрь другого объекта."
        )

    if location.id == new_parent.id:
        raise ValueError(
            "Нельзя переместить объект внутрь самого себя."
        )

    parent_path = get_location_path(new_parent)

    if any(item.id == location.id for item in parent_path):
        raise ValueError(
            "Нельзя переместить объект внутрь его потомка."
        )

    if location.parent_id == new_parent.id:
        raise ValueError(
            "Объект уже находится в этом месте."
        )

    if location.type not in get_allowed_children(new_parent):
        raise ValueError(
            "Недопустимый тип нового родителя."
        )

    if any(
        child.id != location.id
        and child.name.casefold() == location.name.casefold()
        for child in new_parent.children
    ):
        raise ValueError(
            "В новом месте уже существует объект "
            "с таким названием."
        )

def get_move_targets(location: Location):

    if location.type == "cabinet":
        return []

    statement = db.select(Location).order_by(
        Location.position,
        Location.id
    )

    candidates = db.session.scalars(statement).all()

    targets = []

    for candidate in candidates:

        try:
            validate_move(location, candidate)

        except ValueError:
            continue

        path = get_location_path(candidate)

        label = " → ".join(
            item.name for item in path
        )

        targets.append((candidate, label))

    return sorted(
        targets,
        key=lambda item: item[1].casefold()
    )

def move_location(
    location: Location,
    new_parent: Location
) -> Location:

    validate_move(location, new_parent)

    new_position = max(
        (child.position for child in new_parent.children),
        default=0
    ) + 1

    try:
        location.parent = new_parent
        location.position = new_position

        db.session.commit()

    except IntegrityError as error:
        db.session.rollback()

        raise ValueError(
            "Не удалось переместить место хранения."
        ) from error

    return location

from sqlalchemy.exc import IntegrityError

def reorder_location(
    location: Location,
    direction: str
) -> None:

    if direction not in ("earlier", "later"):
        raise ValueError(
            "Недопустимое направление перемещения."
        )

    if location.parent is None:
        raise ValueError(
            "Нельзя изменить порядок корневого объекта."
        )

    siblings = sorted(
        location.parent.children,
        key=lambda item: (item.position, item.id)
    )

    index = siblings.index(location)

    offset = -1 if direction == "earlier" else 1

    new_index = index + offset

    if not 0 <= new_index < len(siblings):
        raise ValueError(
            "Объект уже находится на границе списка."
        )

    siblings[index], siblings[new_index] = (
        siblings[new_index],
        siblings[index]
    )

    for position, item in enumerate(siblings, start=1):
        item.position = position

    db.session.commit()

def create_slots(
    parent: Location,
    count: int
) -> list[Location]:

    if "slot" not in get_allowed_children(parent):
        raise ValueError(
            "В этом объекте нельзя создавать ячейки."
        )

    if not isinstance(count, int) or not 1 <= count <= 50:
        raise ValueError(
            "Количество ячеек должно быть от 1 до 50."
        )

    children = list(parent.children)

    used_names = {
        child.name.casefold()
        for child in children
    }

    position = max(
        (child.position for child in children),
        default=0
    )

    number = 1
    slots = []

    for _ in range(count):

        while f"Место {number}".casefold() in used_names:
            number += 1

        name = f"Место {number}"

        position += 1

        slot = Location(
            name=name,
            type="slot",
            position=position,
            parent=parent
        )

        slots.append(slot)

        used_names.add(name.casefold())
        number += 1

    db.session.add_all(slots)
    db.session.commit()

    return slots

