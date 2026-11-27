import re
import unicodedata

from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Medicine, Placement


MAX_QUERY_LENGTH = 200
MAX_RESULTS = 100

SEARCH_FIELDS = (
    "name",
    "dosage",
    "form",
    "package_size"
)

DASHES = str.maketrans({
    char: " "
    for char in "-‐‑‒–—−"
})


def normalize_search_text(value: str | None) -> str:

    text = unicodedata.normalize(
        "NFKC", value or ""
    )

    text = text.casefold()
    text = text.replace("ё", "е")
    text = text.translate(DASHES)

    return " ".join(text.split())


def matches_term(term, fields):

    if re.fullmatch(r"\d+(?:[.,]\d+)?", term):

        for field in fields:

            numbers = re.findall(
                r"\d+(?:[.,]\d+)?",
                field
            )

            if term in numbers:
                return True

        return False

    return any(
        term in field
        for field in fields
    )


def search_medicines(query: str):

    query = query.strip()

    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(
            "Поисковый запрос слишком длинный."
        )

    normalized_query = normalize_search_text(query)

    if not normalized_query:
        return [], 0

    terms = normalized_query.split()

    medicines = db.session.scalars(
        db.select(Medicine)
    ).all()

    matches = []

    for medicine in medicines:

        fields = [
            normalize_search_text(
                getattr(medicine, field)
            )
            for field in SEARCH_FIELDS
        ]

        name = fields[0]

        barcode_match = (
            medicine.barcode is not None
            and medicine.barcode == query
        )

        text_match = all(
            matches_term(term, fields)
            for term in terms
        )

        if not barcode_match and not text_match:
            continue

        if barcode_match:
            rank = 0

        elif name == normalized_query:
            rank = 1

        elif name.startswith(normalized_query):
            rank = 2

        else:
            rank = 3

        matches.append((rank, medicine))

    matches.sort(
        key=lambda item: (
            item[0],
            normalize_search_text(item[1].name),
            normalize_search_text(item[1].dosage),
            item[1].id
        )
    )

    total = len(matches)

    ids = [
        medicine.id
        for _, medicine in matches[:MAX_RESULTS]
    ]

    if not ids:
        return [], total

    statement = (
        db.select(Medicine)
        .where(Medicine.id.in_(ids))
        .options(
            selectinload(Medicine.placements)
            .joinedload(Placement.location)
        )
    )

    loaded = db.session.scalars(statement).all()

    by_id = {
        medicine.id: medicine
        for medicine in loaded
    }

    return [
        by_id[medicine_id]
        for medicine_id in ids
    ], total