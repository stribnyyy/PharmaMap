from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Medicine


FIELD_LIMITS = {
    "name": 200,
    "dosage": 100,
    "form": 100,
    "package_size": 100,
    "barcode": 64
}

FIELD_LABELS = {
    "name": "Название",
    "dosage": "Дозировка",
    "form": "Лекарственная форма",
    "package_size": "Размер упаковки",
    "barcode": "Штрихкод"
}

IDENTITY_FIELDS = (
    "name",
    "dosage",
    "form",
    "package_size"
)


def get_medicines():

    statement = db.select(Medicine).options(
        selectinload(Medicine.placements)
    )

    medicines = db.session.scalars(
        statement
    ).all()

    return sorted(
        medicines,
        key=lambda item: (
            item.name.casefold(),
            (item.dosage or "").casefold(),
            item.id
        )
    )


def normalize_fields(data):

    values = {}

    for field, limit in FIELD_LIMITS.items():

        value = (data.get(field) or "").strip()

        if len(value) > limit:
            raise ValueError(
                f"{FIELD_LABELS[field]}: "
                f"максимум {limit} символов."
            )

        values[field] = value or None

    if not values["name"]:
        raise ValueError(
            "Название не может быть пустым."
        )

    return values


def medicine_identity(values):

    return tuple(
        (values.get(field) or "").casefold()
        for field in IDENTITY_FIELDS
    )


def validate_unique_medicine(
    values,
    exclude_id=None
):

    medicines = db.session.scalars(
        db.select(Medicine)
    ).all()

    new_identity = medicine_identity(values)

    for medicine in medicines:

        if medicine.id == exclude_id:
            continue

        existing_values = {
            field: getattr(medicine, field)
            for field in IDENTITY_FIELDS
        }

        if medicine_identity(
            existing_values
        ) == new_identity:

            raise ValueError(
                "Такой препарат уже существует."
            )

        if (
            values["barcode"]
            and medicine.barcode == values["barcode"]
        ):
            raise ValueError(
                "Такой штрихкод уже используется."
            )


def save_medicine(
    data,
    medicine: Medicine | None = None
) -> Medicine:

    values = normalize_fields(data)

    exclude_id = (
        medicine.id if medicine is not None
        else None
    )

    validate_unique_medicine(
        values,
        exclude_id
    )

    if medicine is None:
        medicine = Medicine()

    for field, value in values.items():
        setattr(medicine, field, value)

    try:
        db.session.add(medicine)
        db.session.commit()

    except IntegrityError as error:
        db.session.rollback()

        raise ValueError(
            "Не удалось сохранить лекарство."
        ) from error

    return medicine


def delete_medicine(medicine: Medicine) -> None:

    if medicine.placements:
        raise ValueError(
            "Нельзя удалить лекарство "
            "с назначенными местами хранения."
        )

    try:
        db.session.delete(medicine)
        db.session.commit()

    except IntegrityError as error:
        db.session.rollback()

        raise ValueError(
            "Лекарство связано с другими записями."
        ) from error