import re
import pytest

from app.extensions import db
from app.models import Location, Medicine, Placement


def get_token(client):

    response = client.get("/storage/")

    assert response.status_code == 200

    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"',
        response.data
    )

    assert match is not None

    return match.group(1).decode()


def move_request(client, location_id, parent_id):

    return client.post(
        f"/storage/{location_id}/move",
        data={
            "parent_id": parent_id,
            "csrf_token": get_token(client)
        },
        follow_redirects=True
    )

@pytest.fixture()
def move_data(app):

    with app.app_context():

        cabinet1 = Location(
            name="Шкаф 1",
            type="cabinet"
        )

        cabinet2 = Location(
            name="Шкаф 2",
            type="cabinet"
        )

        cabinet3 = Location(
            name="Шкаф 3",
            type="cabinet"
        )

        shelf = Location(
            name="Полка 1",
            type="shelf",
            parent=cabinet1
        )

        drawer = Location(
            name="Ящик 1",
            type="drawer",
            parent=shelf
        )

        slot = Location(
            name="Место 1",
            type="slot",
            parent=drawer
        )

        other_shelf = Location(
            name="Полка 2",
            type="shelf",
            parent=cabinet2,
            position=4
        )

        duplicate_shelf = Location(
            name="полка 1",
            type="shelf",
            parent=cabinet3
        )

        medicine = Medicine(
            name="Но-шпа",
            dosage="40 мг"
        )

        placement = Placement(
            medicine=medicine,
            location=slot
        )

        db.session.add_all([
            cabinet1,
            cabinet2,
            cabinet3,
            shelf,
            drawer,
            slot,
            other_shelf,
            duplicate_shelf,
            placement
        ])

        db.session.commit()

        return {
            "cabinet1": cabinet1.id,
            "cabinet2": cabinet2.id,
            "cabinet3": cabinet3.id,
            "shelf": shelf.id,
            "drawer": drawer.id,
            "slot": slot.id,
            "other_shelf": other_shelf.id,
            "medicine": medicine.id,
            "placement": placement.id
        }

def test_move_page(client, move_data):

    shelf_id = move_data["shelf"]

    response = client.get(
        f"/storage/{shelf_id}/move"
    )

    assert response.status_code == 200

    text = response.get_data(as_text=True)

    assert "Перемещение места хранения" in text

    assert f'value="{move_data["cabinet2"]}"' in text

    assert f'value="{move_data["cabinet1"]}"' not in text

    assert f'value="{move_data["cabinet3"]}"' not in text

def test_move_location_with_contents(
    client, app, move_data
):

    shelf_id = move_data["shelf"]

    response = move_request(
        client,
        shelf_id,
        move_data["cabinet2"]
    )

    assert response.status_code == 200

    assert "успешно перемещено" in (
        response.get_data(as_text=True)
    )

    assert response.request.path == (
        f"/storage/{shelf_id}"
    )

    with app.app_context():

        shelf = db.session.get(
            Location, shelf_id
        )

        drawer = db.session.get(
            Location, move_data["drawer"]
        )

        slot = db.session.get(
            Location, move_data["slot"]
        )

        placement = db.session.get(
            Placement, move_data["placement"]
        )

        assert shelf.parent_id == move_data["cabinet2"]
        assert shelf.position == 5

        assert drawer.parent_id == shelf_id
        assert slot.parent_id == drawer.id

        assert placement.location_id == slot.id

        assert placement.medicine_id == (
            move_data["medicine"]
        )

        assert placement.medicine.name == "Но-шпа"

        old_cabinet = db.session.get(
            Location,
            move_data["cabinet1"]
        )

        assert len(old_cabinet.children) == 0

        from app.services.storage import get_location_path

        path = get_location_path(slot)

        assert [item.name for item in path] == [
            "Шкаф 2",
            "Полка 1",
            "Ящик 1",
            "Место 1"
        ]

@pytest.mark.parametrize(
    "source, target, expected",
    [
        (
            "shelf", "shelf",
            "внутрь самого себя"
        ),
        (
            "shelf", "drawer",
            "внутрь его потомка"
        ),
        (
            "shelf", "other_shelf",
            "Недопустимый тип"
        ),
        (
            "shelf", "cabinet1",
            "уже находится"
        ),
        (
            "cabinet1", "cabinet2",
            "Шкаф нельзя переместить"
        ),
        (
            "shelf", "cabinet3",
            "с таким названием"
        )
    ]
)
def test_invalid_move(
    client, app, move_data,
    source, target, expected
):

    location_id = move_data[source]

    with app.app_context():

        location = db.session.get(
            Location, location_id
        )

        old_parent_id = location.parent_id
        old_position = location.position

    response = move_request(
        client,
        location_id,
        move_data[target]
    )

    assert response.status_code == 200

    assert expected in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        location = db.session.get(
            Location, location_id
        )

        assert location.parent_id == old_parent_id
        assert location.position == old_position

@pytest.mark.parametrize(
    "parent_id",
    ["", "abc", 999999]
)
def test_invalid_parent_id(
    client, app, move_data, parent_id
):

    shelf_id = move_data["shelf"]

    response = move_request(
        client,
        shelf_id,
        parent_id
    )

    assert "не существует" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        shelf = db.session.get(
            Location, shelf_id
        )

        assert shelf.parent_id == move_data["cabinet1"]

def test_move_requires_csrf(
    client, app, move_data
):

    shelf_id = move_data["shelf"]

    response = client.post(
        f"/storage/{shelf_id}/move",
        data={
            "parent_id": move_data["cabinet2"]
        }
    )

    assert response.status_code == 400

    with app.app_context():

        shelf = db.session.get(
            Location, shelf_id
        )

        assert shelf.parent_id == move_data["cabinet1"]

def test_move_nonexistent_location(client):

    response = client.get(
        "/storage/999999/move"
    )

    assert response.status_code == 404

def test_cabinet_has_no_move_targets(
    client, move_data
):

    cabinet_id = move_data["cabinet1"]

    response = client.get(
        f"/storage/{cabinet_id}/move"
    )

    assert response.status_code == 200

    text = response.get_data(as_text=True)

    assert "Нет доступных мест" in text

    assert 'name="parent_id"' not in text

