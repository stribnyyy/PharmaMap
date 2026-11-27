import re
import pytest

from app.extensions import db
from app.models import Medicine, Location, Placement


def get_token(client):

    response = client.get("/medicines/create")

    assert response.status_code == 200

    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"',
        response.data
    )

    assert match is not None

    return match.group(1).decode()


def post_form(client, url, data=None):

    return client.post(
        url,
        data={
            **(data or {}),
            "csrf_token": get_token(client)
        },
        follow_redirects=True
    )


def medicine_count():

    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Medicine)
    )


@pytest.fixture()
def catalog_data(app):

    with app.app_context():

        cabinet = Location(
            name="Шкаф 1",
            type="cabinet"
        )

        slot = Location(
            name="Место 1",
            type="slot",
            parent=cabinet
        )

        placed = Medicine(
            name="Но-шпа",
            dosage="40 мг",
            form="Таблетки",
            package_size="24 таблетки",
            barcode="0012345678905"
        )

        unplaced = Medicine(
            name="Парацетамол",
            dosage="500 мг"
        )

        placement = Placement(
            medicine=placed,
            location=slot
        )

        db.session.add_all([
            placement,
            unplaced
        ])

        db.session.commit()

        return {
            "placed": placed.id,
            "unplaced": unplaced.id,
            "cabinet": cabinet.id,
            "slot": slot.id,
            "placement": placement.id
        }

def test_catalog_page(client, catalog_data):

    response = client.get("/medicines/")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Каталог лекарств" in html
    assert "Но-шпа" in html
    assert "Парацетамол" in html


def test_medicine_detail(client, catalog_data):

    response = client.get(
        f"/medicines/{catalog_data['placed']}"
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Но-шпа" in html
    assert "40 мг" in html
    assert "Шкаф 1" in html
    assert "Место 1" in html

    layout_url = (
        f"/storage/{catalog_data['cabinet']}"
        f"/layout?focus={catalog_data['slot']}"
    )

    assert f'href="{layout_url}"' in html


def test_create_medicine_variants(client, app):

    for dosage in ("200 мг", "400 мг"):

        response = post_form(
            client,
            "/medicines/create",
            {
                "name": "  Ибупрофен  ",
                "dosage": dosage,
                "form": "Таблетки",
                "package_size": "20 таблеток",
                "barcode": (
                    "0012345" if dosage == "200 мг"
                    else ""
                )
            }
        )

        assert response.status_code == 200
        assert "успешно создано" in (
            response.get_data(as_text=True)
        )

    with app.app_context():

        medicines = db.session.scalars(
            db.select(Medicine)
        ).all()

        assert len(medicines) == 2

        assert all(
            m.name == "Ибупрофен"
            for m in medicines
        )

        assert {m.dosage for m in medicines} == {
            "200 мг",
            "400 мг"
        }

        assert {m.barcode for m in medicines} == {
            "0012345",
            None
        }

@pytest.mark.parametrize(
    "data, expected",
    [
        (
            {
                "name": "но-шпа",
                "dosage": "40 мг",
                "form": "таблетки",
                "package_size": "24 таблетки"
            },
            "Такой препарат уже существует"
        ),
        (
            {
                "name": "Ибупрофен",
                "barcode": "0012345678905"
            },
            "Такой штрихкод уже используется"
        )
    ]
)
def test_duplicate_medicine(
    client, app, catalog_data,
    data, expected
):

    response = post_form(
        client,
        "/medicines/create",
        data
    )

    assert response.status_code == 400
    assert expected in response.get_data(as_text=True)

    with app.app_context():
        assert medicine_count() == 2


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            {"name": "   "},
            "Название не может быть пустым"
        ),
        (
            {"name": "А" * 201},
            "максимум 200 символов"
        ),
        (
            {
                "name": "Ибупрофен",
                "barcode": "1" * 65
            },
            "максимум 64 символов"
        )
    ]
)
def test_invalid_medicine(
    client, app, data, expected
):

    response = post_form(
        client,
        "/medicines/create",
        data
    )

    assert response.status_code == 400
    assert expected in response.get_data(as_text=True)

    with app.app_context():
        assert medicine_count() == 0

def test_edit_medicine(
    client, app, catalog_data
):

    medicine_id = catalog_data["placed"]

    response = post_form(
        client,
        f"/medicines/{medicine_id}/edit",
        {
            "name": "Но-шпа (обновлено)",
            "dosage": "40 мг",
            "form": "Таблетки",
            "package_size": "24 таблетки",
            "barcode": "0012345678905"
        }
    )

    assert response.status_code == 200

    assert "успешно сохранены" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        medicine = db.session.get(
            Medicine, medicine_id
        )

        placement = db.session.get(
            Placement,
            catalog_data["placement"]
        )

        assert medicine.name == "Но-шпа (обновлено)"

        assert placement.medicine_id == medicine_id

        assert placement.location_id == (
            catalog_data["slot"]
        )

    layout = client.get(
        f"/storage/{catalog_data['cabinet']}/layout"
    )

    assert "Но-шпа (обновлено)" in (
        layout.get_data(as_text=True)
    )


def test_edit_to_duplicate(
    client, app, catalog_data
):

    medicine_id = catalog_data["unplaced"]

    response = post_form(
        client,
        f"/medicines/{medicine_id}/edit",
        {
            "name": "Но-шпа",
            "dosage": "40 мг",
            "form": "Таблетки",
            "package_size": "24 таблетки"
        }
    )

    assert response.status_code == 400

    assert "уже существует" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        medicine = db.session.get(
            Medicine, medicine_id
        )

        assert medicine.name == "Парацетамол"

def test_delete_unplaced_medicine(
    client, app, catalog_data
):

    medicine_id = catalog_data["unplaced"]

    response = post_form(
        client,
        f"/medicines/{medicine_id}/delete"
    )

    assert response.status_code == 200
    assert response.request.path == "/medicines/"

    with app.app_context():

        assert db.session.get(
            Medicine, medicine_id
        ) is None

        assert medicine_count() == 1


def test_cannot_delete_placed_medicine(
    client, app, catalog_data
):

    medicine_id = catalog_data["placed"]

    response = post_form(
        client,
        f"/medicines/{medicine_id}/delete"
    )

    assert "с назначенными местами хранения" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        assert db.session.get(
            Medicine, medicine_id
        ) is not None

        assert db.session.get(
            Placement,
            catalog_data["placement"]
        ) is not None

        assert db.session.get(
            Location,
            catalog_data["slot"]
        ) is not None

@pytest.mark.parametrize(
    "action",
    ["create", "edit", "delete"]
)
def test_medicine_requires_csrf(
    client, app, catalog_data, action
):

    medicine_id = catalog_data["placed"]

    if action == "create":
        url = "/medicines/create"
    else:
        url = f"/medicines/{medicine_id}/{action}"

    response = client.post(
        url,
        data={"name": "Новое название"}
    )

    assert response.status_code == 400

    with app.app_context():

        assert medicine_count() == 2

        medicine = db.session.get(
            Medicine, medicine_id
        )

        assert medicine.name == "Но-шпа"


def test_medicine_not_found(client):

    response = client.get(
        "/medicines/999999"
    )

    assert response.status_code == 404

