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


def edit_location(client, location_id, name,
                  description=""):

    return client.post(
        f"/storage/{location_id}/edit",
        data={
            "name": name,
            "description": description,
            "csrf_token": get_token(client)
        },
        follow_redirects=True
    )


def delete_location(client, location_id):

    return client.post(
        f"/storage/{location_id}/delete",
        data={
            "csrf_token": get_token(client)
        },
        follow_redirects=True
    )

@pytest.fixture()
def storage_data(app):

    with app.app_context():

        cabinet = Location(
            name="Шкаф 1",
            type="cabinet"
        )

        empty_cabinet = Location(
            name="Шкаф 2",
            type="cabinet"
        )

        shelf1 = Location(
            name="Полка 1",
            type="shelf",
            parent=cabinet
        )

        shelf2 = Location(
            name="Полка 2",
            type="shelf",
            parent=cabinet
        )

        db.session.add_all([
            cabinet,
            empty_cabinet,
            shelf1,
            shelf2
        ])

        db.session.commit()

        return {
            "cabinet": cabinet.id,
            "empty_cabinet": empty_cabinet.id,
            "shelf1": shelf1.id,
            "shelf2": shelf2.id
        }

def test_edit_page(client, storage_data):

    location_id = storage_data["cabinet"]

    response = client.get(
        f"/storage/{location_id}/edit"
    )

    assert response.status_code == 200

    text = response.get_data(as_text=True)

    assert "Редактирование места хранения" in text
    assert 'value="Шкаф 1"' in text

def test_update_location(
    client, app, storage_data
):

    location_id = storage_data["cabinet"]

    response = edit_location(
        client,
        location_id,
        "Основной шкаф",
        "Рядом с кассой"
    )

    assert "успешно сохранены" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        location = db.session.get(
            Location, location_id
        )

        assert location.name == "Основной шкаф"
        assert location.description == "Рядом с кассой"
        assert len(location.children) == 2

    response = edit_location(
        client,
        location_id,
        "Основной шкаф",
        "Новое описание"
    )

    assert "успешно сохранены" in (
        response.get_data(as_text=True)
    )

    with app.app_context():
        location = db.session.get(
            Location, location_id
        )

        assert location.description == "Новое описание"

def test_rename_to_duplicate(
    client, app, storage_data
):

    location_id = storage_data["shelf1"]

    response = edit_location(
        client,
        location_id,
        "полка 2"
    )

    assert "уже существует" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        location = db.session.get(
            Location, location_id
        )

        assert location.name == "Полка 1"

@pytest.mark.parametrize(
    "name, description, expected",
    [
        ("   ", "", "не может быть пустым"),
        ("А" * 151, "", "Название слишком длинное"),
        ("Полка 1", "А" * 1001, "Описание слишком длинное")
    ]
)
def test_invalid_update(
    client, app, storage_data,
    name, description, expected
):

    location_id = storage_data["shelf1"]

    response = edit_location(
        client,
        location_id,
        name,
        description
    )

    assert expected in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        location = db.session.get(
            Location, location_id
        )

        assert location.name == "Полка 1"
        assert location.description is None

def test_delete_empty_shelf(
    client, app, storage_data
):

    location_id = storage_data["shelf1"]

    response = delete_location(
        client, location_id
    )

    assert response.status_code == 200

    assert "успешно удалено" in (
        response.get_data(as_text=True)
    )

    assert response.request.path == (
        f"/storage/{storage_data['cabinet']}"
    )

    with app.app_context():

        assert db.session.get(
            Location, location_id
        ) is None

        cabinet = db.session.get(
            Location,
            storage_data["cabinet"]
        )

        assert len(cabinet.children) == 1

def test_delete_empty_cabinet(
    client, app, storage_data
):

    location_id = storage_data["empty_cabinet"]

    response = delete_location(
        client, location_id
    )

    assert response.status_code == 200
    assert response.request.path == "/storage/"

    with app.app_context():

        assert db.session.get(
            Location, location_id
        ) is None

def test_cannot_delete_with_children(
    client, app, storage_data
):

    location_id = storage_data["cabinet"]

    response = delete_location(
        client, location_id
    )

    assert "вложенные места хранения" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        cabinet = db.session.get(
            Location, location_id
        )

        assert cabinet is not None
        assert len(cabinet.children) == 2

def test_cannot_delete_with_medicine(
    client, app, storage_data
):

    location_id = storage_data["shelf1"]

    with app.app_context():

        medicine = Medicine(
            name="Но-шпа",
            dosage="40 мг"
        )

        placement = Placement(
            medicine=medicine,
            location_id=location_id
        )

        db.session.add(placement)
        db.session.commit()

        medicine_id = medicine.id
        placement_id = placement.id

    response = delete_location(
        client, location_id
    )

    assert "размещены лекарства" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        assert db.session.get(
            Location, location_id
        ) is not None

        assert db.session.get(
            Medicine, medicine_id
        ) is not None

        assert db.session.get(
            Placement, placement_id
        ) is not None

@pytest.mark.parametrize(
    "action",
    ["edit", "delete"]
)
def test_management_requires_csrf(
    client, app, storage_data, action
):

    location_id = storage_data["shelf1"]

    response = client.post(
        f"/storage/{location_id}/{action}",
        data={"name": "Изменённое название"}
    )

    assert response.status_code == 400

    with app.app_context():

        location = db.session.get(
            Location, location_id
        )

        assert location is not None
        assert location.name == "Полка 1"

def test_edit_nonexistent_location(client):

    response = client.get(
        "/storage/999999/edit"
    )

    assert response.status_code == 404

