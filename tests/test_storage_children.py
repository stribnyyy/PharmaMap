import re
import pytest

from app.extensions import db
from app.models import Location


def get_token(client, url):

    response = client.get(url)

    assert response.status_code == 200

    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"',
        response.data
    )

    assert match is not None

    return match.group(1).decode()


def add_child(client, parent_id, name, kind):

    token = get_token(
        client,
        f"/storage/{parent_id}"
    )

    return client.post(
        f"/storage/{parent_id}/create",
        data={
            "name": name,
            "type": kind,
            "csrf_token": token
        },
        follow_redirects=True
    )


@pytest.fixture()
def cabinet_id(app):

    with app.app_context():

        cabinet = Location(
            name="Шкаф 1",
            type="cabinet"
        )

        db.session.add(cabinet)
        db.session.commit()

        return cabinet.id

def test_location_detail(client, cabinet_id):

    response = client.get(
        f"/storage/{cabinet_id}"
    )

    assert response.status_code == 200

    assert "Шкаф 1" in response.get_data(
        as_text=True
    )

def test_create_shelf(client, app, cabinet_id):

    response = add_child(
        client,
        cabinet_id,
        "Полка 1",
        "shelf"
    )

    assert response.status_code == 200

    assert "Место хранения успешно создано" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        shelf = db.session.scalar(
            db.select(Location).where(
                Location.type == "shelf"
            )
        )

        assert shelf is not None
        assert shelf.name == "Полка 1"
        assert shelf.parent_id == cabinet_id

def test_nested_hierarchy(client, app, cabinet_id):

    add_child(
        client, cabinet_id,
        "Полка 1", "shelf"
    )

    with app.app_context():

        shelf = db.session.scalar(
            db.select(Location).where(
                Location.type == "shelf"
            )
        )

        shelf_id = shelf.id

    add_child(
        client, shelf_id,
        "Место 1", "slot"
    )

    with app.app_context():

        slot = db.session.scalar(
            db.select(Location).where(
                Location.type == "slot"
            )
        )

        assert slot is not None
        assert slot.parent.name == "Полка 1"
        assert slot.parent.parent.name == "Шкаф 1"

@pytest.mark.parametrize(
    "kind",
    ["cabinet", "unknown", ""]
)
def test_invalid_child_type(
    client, app, cabinet_id, kind
):

    response = add_child(
        client,
        cabinet_id,
        "Новый объект",
        kind
    )

    assert "Недопустимый тип" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        cabinet = db.session.get(
            Location, cabinet_id
        )

        assert len(cabinet.children) == 0

def test_duplicate_child(client, app, cabinet_id):

    add_child(
        client, cabinet_id,
        "Полка 1", "shelf"
    )

    response = add_child(
        client, cabinet_id,
        "полка 1", "shelf"
    )

    assert "уже существует" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        cabinet = db.session.get(
            Location, cabinet_id
        )

        assert len(cabinet.children) == 1

def test_location_not_found(client):

    response = client.get("/storage/999999")

    assert response.status_code == 404

def test_slot_cannot_have_children(
    client, app, cabinet_id
):

    add_child(
        client, cabinet_id,
        "Место 1", "slot"
    )

    with app.app_context():

        slot = db.session.scalar(
            db.select(Location).where(
                Location.type == "slot"
            )
        )

        slot_id = slot.id

    token = get_token(client, "/storage/")

    response = client.post(
        f"/storage/{slot_id}/create",
        data={
            "name": "Место 2",
            "type": "slot",
            "csrf_token": token
        },
        follow_redirects=True
    )

    assert "Недопустимый тип" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        slot = db.session.get(
            Location, slot_id
        )

        assert len(slot.children) == 0

