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


def placement_count():

    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Placement)
    )


@pytest.fixture()
def placement_data(app):

    with app.app_context():

        cabinet = Location(
            name="Шкаф 1",
            type="cabinet"
        )

        shelf = Location(
            name="Полка 1",
            type="shelf",
            parent=cabinet
        )

        slot1 = Location(
            name="Место 1",
            type="slot",
            position=1,
            parent=shelf
        )

        slot2 = Location(
            name="Место 2",
            type="slot",
            position=2,
            parent=shelf
        )

        medicine1 = Medicine(
            name="Но-шпа",
            dosage="40 мг"
        )

        medicine2 = Medicine(
            name="Парацетамол",
            dosage="500 мг"
        )

        placement = Placement(
            medicine=medicine1,
            location=slot1
        )

        db.session.add_all([
            cabinet,
            shelf,
            slot1,
            slot2,
            medicine1,
            medicine2,
            placement
        ])

        db.session.commit()

        return {
            "cabinet": cabinet.id,
            "shelf": shelf.id,
            "slot1": slot1.id,
            "slot2": slot2.id,
            "medicine1": medicine1.id,
            "medicine2": medicine2.id,
            "placement": placement.id
        }

def test_assign_from_catalog(
    client, app, placement_data
):

    d = placement_data

    response = post_form(
        client,
        f"/medicines/{d['medicine1']}/placements/add",
        {"location_id": d["slot2"]}
    )

    assert response.status_code == 200

    assert "Место хранения назначено" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        medicine = db.session.get(
            Medicine, d["medicine1"]
        )

        assert {
            p.location_id for p in medicine.placements
        } == {
            d["slot1"],
            d["slot2"]
        }

        assert placement_count() == 2

def test_assign_from_storage(
    client, app, placement_data
):

    d = placement_data

    response = post_form(
        client,
        f"/storage/{d['slot1']}/medicines/add",
        {"medicine_id": d["medicine2"]}
    )

    assert response.status_code == 200

    assert "Лекарство назначено" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        location = db.session.get(
            Location, d["slot1"]
        )

        assert {
            p.medicine_id for p in location.placements
        } == {
            d["medicine1"],
            d["medicine2"]
        }

        assert placement_count() == 2

@pytest.mark.parametrize(
    "source",
    ["catalog", "storage"]
)
def test_duplicate_placement(
    client, app, placement_data, source
):

    d = placement_data

    if source == "catalog":

        url = (
            f"/medicines/{d['medicine1']}"
            "/placements/add"
        )

        data = {"location_id": d["slot1"]}

    else:

        url = (
            f"/storage/{d['slot1']}"
            "/medicines/add"
        )

        data = {"medicine_id": d["medicine1"]}

    response = post_form(
        client, url, data
    )

    assert "уже назначено" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        assert placement_count() == 1

@pytest.mark.parametrize(
    "location_id",
    ["", "abc", 999999, "9223372036854775808"]
)
def test_invalid_placement_location(
    client, app, placement_data, location_id
):

    d = placement_data

    response = post_form(
        client,
        f"/medicines/{d['medicine1']}/placements/add",
        {"location_id": location_id}
    )

    assert "Место хранения не существует" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        assert placement_count() == 1


def test_invalid_placement_medicine(
    client, app, placement_data
):

    d = placement_data

    response = post_form(
        client,
        f"/storage/{d['slot1']}/medicines/add",
        {"medicine_id": 999999}
    )

    assert "Лекарство не существует" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        assert placement_count() == 1

def test_move_placement(
    client, app, placement_data
):

    d = placement_data

    response = post_form(
        client,
        f"/medicines/{d['medicine1']}"
        f"/placements/{d['placement']}/move",
        {"location_id": d["slot2"]}
    )

    assert response.status_code == 200

    assert "Размещение успешно изменено" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        placement = db.session.get(
            Placement, d["placement"]
        )

        assert placement is not None

        assert placement.medicine_id == d["medicine1"]

        assert placement.location_id == d["slot2"]

        old_location = db.session.get(
            Location, d["slot1"]
        )

        assert len(old_location.placements) == 0

        assert placement_count() == 1

    layout = client.get(
        f"/storage/{d['cabinet']}/layout"
        f"?focus={d['slot2']}"
    )

    assert layout.status_code == 200
    assert "Но-шпа" in layout.get_data(as_text=True)
    assert "is-selected" in layout.get_data(as_text=True)

@pytest.mark.parametrize(
    "target, expected",
    [
        ("slot1", "уже находится"),
        ("slot2", "уже назначено")
    ]
)
def test_invalid_move_placement(
    client, app, placement_data,
    target, expected
):

    d = placement_data

    if target == "slot2":

        response = post_form(
            client,
            f"/medicines/{d['medicine1']}/placements/add",
            {"location_id": d["slot2"]}
        )

        assert "Место хранения назначено" in (
            response.get_data(as_text=True)
        )

    response = post_form(
        client,
        f"/medicines/{d['medicine1']}"
        f"/placements/{d['placement']}/move",
        {"location_id": d[target]}
    )

    assert expected in response.get_data(as_text=True)

    with app.app_context():

        placement = db.session.get(
            Placement, d["placement"]
        )

        assert placement.location_id == d["slot1"]

        assert placement_count() == (
            2 if target == "slot2" else 1
        )

def test_remove_from_catalog(
    client, app, placement_data
):

    d = placement_data

    response = post_form(
        client,
        f"/medicines/{d['medicine1']}"
        f"/placements/{d['placement']}/delete"
    )

    assert response.status_code == 200

    assert "Размещение удалено" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        assert db.session.get(
            Placement, d["placement"]
        ) is None

        assert db.session.get(
            Medicine, d["medicine1"]
        ) is not None

        assert db.session.get(
            Location, d["slot1"]
        ) is not None

        assert placement_count() == 0


def test_remove_from_storage(
    client, app, placement_data
):

    d = placement_data

    response = post_form(
        client,
        f"/storage/{d['slot1']}"
        f"/medicines/{d['placement']}/delete"
    )

    assert response.status_code == 200

    assert "Лекарство убрано" in (
        response.get_data(as_text=True)
    )

    with app.app_context():

        assert db.session.get(
            Placement, d["placement"]
        ) is None

        assert db.session.get(
            Medicine, d["medicine1"]
        ) is not None

        assert db.session.get(
            Location, d["slot1"]
        ) is not None

        assert placement_count() == 0

@pytest.mark.parametrize(
    "source",
    ["catalog", "storage"]
)
def test_placement_scope(
    client, app, placement_data, source
):

    d = placement_data

    if source == "catalog":

        url = (
            f"/medicines/{d['medicine2']}"
            f"/placements/{d['placement']}/delete"
        )

    else:

        url = (
            f"/storage/{d['slot2']}"
            f"/medicines/{d['placement']}/delete"
        )

    response = post_form(client, url)

    assert response.status_code == 404

    with app.app_context():

        placement = db.session.get(
            Placement, d["placement"]
        )

        assert placement is not None
        assert placement.medicine_id == d["medicine1"]
        assert placement.location_id == d["slot1"]

def test_layout_placement_management(
    client, app, placement_data
):

    d = placement_data

    cabinet_id = d["cabinet"]
    slot_id = d["slot1"]

    view = client.get(
        f"/storage/{cabinet_id}/layout"
        f"?focus={slot_id}"
    )

    edit = client.get(
        f"/storage/{cabinet_id}/layout"
        f"?edit=1&focus={slot_id}"
    )

    assert view.status_code == 200
    assert edit.status_code == 200

    assert 'id="placement-editor"' not in (
        view.get_data(as_text=True)
    )

    assert 'id="placement-editor"' in (
        edit.get_data(as_text=True)
    )

    response = post_form(
        client,
        f"/storage/{slot_id}/medicines/add",
        {
            "medicine_id": d["medicine2"],
            "return_to": "layout"
        }
    )

    assert response.status_code == 200

    assert response.request.path == (
        f"/storage/{cabinet_id}/layout"
    )

    assert response.request.args.get("edit") == "1"

    assert response.request.args.get(
        "focus"
    ) == str(slot_id)

    with app.app_context():

        location = db.session.get(
            Location, slot_id
        )

        assert {
            p.medicine_id for p in location.placements
        } == {
            d["medicine1"],
            d["medicine2"]
        }

    response = post_form(
        client,
        f"/storage/{slot_id}"
        f"/medicines/{d['placement']}/delete",
        {"return_to": "layout"}
    )

    assert response.status_code == 200
    assert response.request.args.get("edit") == "1"

    with app.app_context():

        location = db.session.get(
            Location, slot_id
        )

        assert {
            p.medicine_id for p in location.placements
        } == {d["medicine2"]}

@pytest.mark.parametrize(
    "action",
    [
        "catalog_add",
        "catalog_move",
        "catalog_delete",
        "storage_add",
        "storage_delete"
    ]
)
def test_placement_requires_csrf(
    client, app, placement_data, action
):

    d = placement_data

    catalog = f"/medicines/{d['medicine1']}"
    storage = f"/storage/{d['slot1']}"
    placement_id = d["placement"]

    requests = {
        "catalog_add": (
            f"{catalog}/placements/add",
            {"location_id": d["slot2"]}
        ),
        "catalog_move": (
            f"{catalog}/placements/{placement_id}/move",
            {"location_id": d["slot2"]}
        ),
        "catalog_delete": (
            f"{catalog}/placements/{placement_id}/delete",
            {}
        ),
        "storage_add": (
            f"{storage}/medicines/add",
            {"medicine_id": d["medicine2"]}
        ),
        "storage_delete": (
            f"{storage}/medicines/{placement_id}/delete",
            {}
        )
    }

    url, data = requests[action]

    response = client.post(
        url,
        data=data
    )

    assert response.status_code == 400

    with app.app_context():

        assert placement_count() == 1

        placement = db.session.get(
            Placement, placement_id
        )

        assert placement is not None
        assert placement.location_id == d["slot1"]
        assert placement.medicine_id == d["medicine1"]

