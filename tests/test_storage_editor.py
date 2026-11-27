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


def editor_request(
    client, location_id, action, data
):

    return client.post(
        f"/storage/{location_id}/layout/{action}",
        data={
            **data,
            "csrf_token": get_token(client)
        },
        follow_redirects=True
    )


@pytest.fixture()
def editor_data(app):

    with app.app_context():

        cabinet = Location(
            name="Шкаф 1",
            type="cabinet"
        )

        shelf1 = Location(
            name="Полка 1",
            type="shelf",
            position=2,
            parent=cabinet
        )

        shelf2 = Location(
            name="Полка 2",
            type="shelf",
            position=7,
            parent=cabinet
        )

        slot1 = Location(
            name="Место 1",
            type="slot",
            position=1,
            parent=shelf1
        )

        slot3 = Location(
            name="Место 3",
            type="slot",
            position=3,
            parent=shelf1
        )

        medicine = Medicine(
            name="Но-шпа",
            dosage="40 мг"
        )

        placement = Placement(
            medicine=medicine,
            location=slot1
        )

        db.session.add_all([
            cabinet,
            shelf1,
            shelf2,
            placement,
            slot3
        ])

        db.session.commit()

        return {
            "cabinet": cabinet.id,
            "shelf1": shelf1.id,
            "shelf2": shelf2.id,
            "slot1": slot1.id,
            "slot3": slot3.id,
            "placement": placement.id,
            "medicine": medicine.id
        }

def test_editor_modes(client, editor_data):

    cabinet_id = editor_data["cabinet"]

    view = client.get(
        f"/storage/{cabinet_id}/layout"
    )

    edit = client.get(
        f"/storage/{cabinet_id}/layout?edit=1"
    )

    assert view.status_code == 200
    assert edit.status_code == 200

    view_html = view.get_data(as_text=True)
    edit_html = edit.get_data(as_text=True)

    assert 'class="editor-tools"' not in view_html
    assert 'name="direction"' not in view_html

    assert 'class="editor-tools"' in edit_html
    assert 'name="direction"' in edit_html
    assert "Несколько ячеек" in edit_html
    assert "js/layout.js" in edit_html

def test_reorder_shelves(
    client, app, editor_data
):

    response = editor_request(
        client,
        editor_data["shelf2"],
        "reorder",
        {"direction": "earlier"}
    )

    assert response.status_code == 200

    assert "Порядок изменён" in (
        response.get_data(as_text=True)
    )

    assert response.request.args.get("edit") == "1"

    with app.app_context():

        shelf1 = db.session.get(
            Location, editor_data["shelf1"]
        )

        shelf2 = db.session.get(
            Location, editor_data["shelf2"]
        )

        assert shelf2.position == 1
        assert shelf1.position == 2

        assert shelf1.parent_id == editor_data["cabinet"]
        assert shelf2.parent_id == editor_data["cabinet"]

def test_reorder_slots_preserves_medicine(
    client, app, editor_data
):

    response = editor_request(
        client,
        editor_data["slot1"],
        "reorder",
        {"direction": "later"}
    )

    assert "Порядок изменён" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        slot1 = db.session.get(
            Location, editor_data["slot1"]
        )

        slot3 = db.session.get(
            Location, editor_data["slot3"]
        )

        placement = db.session.get(
            Placement,
            editor_data["placement"]
        )

        assert slot1.position == 2
        assert slot3.position == 1

        assert slot1.parent_id == editor_data["shelf1"]

        assert placement.location_id == slot1.id

        assert placement.medicine_id == (
            editor_data["medicine"]
        )

        assert placement.medicine.name == "Но-шпа"

@pytest.mark.parametrize(
    "source, direction, expected",
    [
        (
            "cabinet",
            "earlier",
            "корневого объекта"
        ),
        (
            "shelf1",
            "earlier",
            "границе списка"
        ),
        (
            "shelf2",
            "sideways",
            "Недопустимое направление"
        )
    ]
)
def test_invalid_reorder(
    client, app, editor_data,
    source, direction, expected
):

    location_id = editor_data[source]

    with app.app_context():

        location = db.session.get(
            Location, location_id
        )

        old_position = location.position

    response = editor_request(
        client,
        location_id,
        "reorder",
        {"direction": direction}
    )

    assert expected in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        location = db.session.get(
            Location, location_id
        )

        assert location.position == old_position

def test_batch_create_slots(
    client, app, editor_data
):

    shelf_id = editor_data["shelf1"]

    response = editor_request(
        client,
        shelf_id,
        "add",
        {
            "action": "batch",
            "count": 3
        }
    )

    assert response.status_code == 200

    assert "Создано ячеек: 3" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        shelf = db.session.get(
            Location, shelf_id
        )

        children = sorted(
            shelf.children,
            key=lambda item: item.position
        )

        assert len(children) == 5

        assert [item.name for item in children] == [
            "Место 1",
            "Место 3",
            "Место 2",
            "Место 4",
            "Место 5"
        ]

        assert [item.position for item in children] == [
            1, 3, 4, 5, 6
        ]

        assert all(
            item.type == "slot"
            for item in children
        )

@pytest.mark.parametrize(
    "count",
    [0, 51, "abc", ""]
)
def test_invalid_batch_count(
    client, app, editor_data, count
):

    shelf_id = editor_data["shelf1"]

    response = editor_request(
        client,
        shelf_id,
        "add",
        {
            "action": "batch",
            "count": count
        }
    )

    assert "от 1 до 50" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        shelf = db.session.get(
            Location, shelf_id
        )

        assert len(shelf.children) == 2

def test_batch_invalid_parent(
    client, app, editor_data
):

    slot_id = editor_data["slot1"]

    response = editor_request(
        client,
        slot_id,
        "add",
        {
            "action": "batch",
            "count": 5
        }
    )

    assert "нельзя создавать ячейки" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        slot = db.session.get(
            Location, slot_id
        )

        assert len(slot.children) == 0

def test_editor_create_drawer(
    client, app, editor_data
):

    cabinet_id = editor_data["cabinet"]

    response = editor_request(
        client,
        cabinet_id,
        "add",
        {
            "action": "single",
            "name": "Ящик 1",
            "type": "drawer"
        }
    )

    assert response.status_code == 200

    assert "успешно создано" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        drawer = db.session.scalar(
            db.select(Location).where(
                Location.type == "drawer"
            )
        )

        assert drawer is not None
        assert drawer.name == "Ящик 1"
        assert drawer.parent_id == cabinet_id
        assert drawer.position == 8

def test_editor_invalid_child(
    client, app, editor_data
):

    shelf_id = editor_data["shelf1"]

    response = editor_request(
        client,
        shelf_id,
        "add",
        {
            "action": "single",
            "name": "Шкаф 2",
            "type": "cabinet"
        }
    )

    assert "Недопустимый тип" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        shelf = db.session.get(
            Location, shelf_id
        )

        assert len(shelf.children) == 2

@pytest.mark.parametrize(
    "action, data",
    [
        (
            "reorder",
            {"direction": "later"}
        ),
        (
            "add",
            {
                "action": "batch",
                "count": 5
            }
        )
    ]
)
def test_editor_requires_csrf(
    client, app, editor_data,
    action, data
):

    shelf_id = editor_data["shelf1"]

    response = client.post(
        f"/storage/{shelf_id}/layout/{action}",
        data=data
    )

    assert response.status_code == 400

    with app.app_context():

        shelf = db.session.get(
            Location, shelf_id
        )

        assert shelf.position == 2
        assert len(shelf.children) == 2

