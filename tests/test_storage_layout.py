import re
import pytest

from app.extensions import db
from app.models import Location, Medicine, Placement


@pytest.fixture()
def layout_data(app):

    with app.app_context():

        cabinet = Location(
            name="Основной шкаф",
            type="cabinet"
        )

        other_cabinet = Location(
            name="Резервный шкаф",
            type="cabinet"
        )

        shelf = Location(
            name="Полка 1",
            type="shelf",
            parent=cabinet
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

        medicine = Medicine(
            name="Но-шпа",
            dosage="40 мг"
        )

        placement = Placement(
            medicine=medicine,
            location=slot
        )

        db.session.add_all([
            cabinet,
            other_cabinet,
            placement
        ])

        db.session.commit()

        return {
            "cabinet": cabinet.id,
            "other_cabinet": other_cabinet.id,
            "shelf": shelf.id,
            "drawer": drawer.id,
            "slot": slot.id
        }

def test_layout_renders_hierarchy(
    client, layout_data
):

    response = client.get(
        f"/storage/{layout_data['cabinet']}/layout"
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    for name in (
        "Основной шкаф",
        "Полка 1",
        "Ящик 1",
        "Место 1",
        "Но-шпа",
        "40 мг"
    ):
        assert name in html

    assert "Резервный шкаф" not in html

    for key in ("cabinet", "shelf", "drawer", "slot"):

        location_id = layout_data[key]

        assert f'id="location-{location_id}"' in html

    assert "css/layout.css" in html

    assert not re.search(
        r"<details\b[^>]*\bopen\b[^>]*>",
        html
    )

def test_empty_cabinet_layout(
    client, layout_data
):

    response = client.get(
        f"/storage/{layout_data['other_cabinet']}/layout"
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Резервный шкаф" in html
    assert "Пусто" in html
    assert "Но-шпа" not in html

def test_layout_requires_cabinet(
    client, layout_data
):

    response = client.get(
        f"/storage/{layout_data['shelf']}/layout"
    )

    assert response.status_code == 404

def test_layout_not_found(client):

    response = client.get(
        "/storage/999999/layout"
    )

    assert response.status_code == 404

def test_layout_focus(
    client, layout_data
):

    cabinet_id = layout_data["cabinet"]
    slot_id = layout_data["slot"]

    response = client.get(
        f"/storage/{cabinet_id}/layout?focus={slot_id}"
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    selected = re.search(
        rf'<article\s+id="location-{slot_id}"[^>]*>',
        html
    )

    assert selected is not None
    assert "is-selected" in selected.group(0)

    drawer_id = layout_data["drawer"]

    drawer = re.search(
        rf'<details\s+id="location-{drawer_id}"[^>]*>',
        html
    )

    assert drawer is not None

    assert re.search(
        r"\bopen\b",
        drawer.group(0)
    )

def test_layout_ignores_foreign_focus(
    client, layout_data
):

    cabinet_id = layout_data["cabinet"]
    foreign_id = layout_data["other_cabinet"]

    response = client.get(
        f"/storage/{cabinet_id}/layout?focus={foreign_id}"
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "is-selected" not in html

@pytest.mark.parametrize(
    "focus",
    ["abc", "999999"]
)
def test_layout_invalid_focus(
    client, layout_data, focus
):

    cabinet_id = layout_data["cabinet"]

    response = client.get(
        f"/storage/{cabinet_id}/layout?focus={focus}"
    )

    assert response.status_code == 200

    assert "is-selected" not in (
        response.get_data(as_text=True)
    )

def test_detail_links_to_layout(
    client, layout_data
):

    cabinet_id = layout_data["cabinet"]
    slot_id = layout_data["slot"]

    response = client.get(
        f"/storage/{slot_id}"
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    expected_url = (
        f"/storage/{cabinet_id}/layout?focus={slot_id}"
    )

    assert f'href="{expected_url}"' in html

