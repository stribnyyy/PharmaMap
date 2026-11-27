import pytest

from app.extensions import db
from app.models import Medicine, Location, Placement
from app.services.search import search_medicines


@pytest.fixture()
def search_data(app):

    with app.app_context():

        cabinet1 = Location(
            name="Шкаф 1",
            type="cabinet"
        )

        cabinet2 = Location(
            name="Шкаф 2",
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
            parent=cabinet2
        )

        slot = Location(
            name="Место 1",
            type="slot",
            parent=shelf
        )

        medicines = {
            "no_shpa": Medicine(
                name="Но-шпа",
                dosage="40 мг",
                form="Таблетки",
                package_size="24 таблетки",
                barcode="0012345678905"
            ),
            "forte": Medicine(
                name="Но-шпа форте",
                dosage="80 мг"
            ),
            "ibu200": Medicine(
                name="Ибупрофен",
                dosage="200 мг",
                form="Таблетки",
                package_size="20 таблеток"
            ),
            "ibu400": Medicine(
                name="Ибупрофен",
                dosage="400 мг",
                form="Таблетки",
                package_size="20 таблеток"
            ),
            "para": Medicine(
                name="Парацетамол",
                dosage="500 мг"
            ),
            "green": Medicine(
                name="Зелёнка",
                form="Раствор"
            ),
            "vitamin": Medicine(
                name="Vitamin C",
                dosage="100 мг"
            )
        }

        placements = [
            Placement(
                medicine=medicines["no_shpa"],
                location=slot
            ),
            Placement(
                medicine=medicines["no_shpa"],
                location=drawer
            )
        ]

        db.session.add_all([
            *medicines.values(),
            *placements
        ])

        db.session.commit()

        return {
            **{
                key: medicine.id
                for key, medicine in medicines.items()
            },
            "cabinet1": cabinet1.id,
            "cabinet2": cabinet2.id,
            "slot": slot.id,
            "drawer": drawer.id
        }

@pytest.mark.parametrize(
    "query, expected",
    [
        ("НО-ШПА", {"no_shpa", "forte"}),
        ("шпа", {"no_shpa", "forte"}),
        ("Но шпа", {"no_shpa", "forte"}),
        ("Но‑шпа", {"no_shpa", "forte"}),
        ("400 ИБУПРОФЕН", {"ibu400"}),
        ("40", {"no_shpa"}),
        ("500 мг", {"para"}),
        ("зеленка", {"green"}),
        ("VITAMIN", {"vitamin"}),
        ("0012345678905", {"no_shpa"}),
        ("0012345", set()),
        ("ибупрофен 20 таблеток", {"ibu200", "ibu400"}),
        ("раствор", {"green"}),
        ("%", set()),
        ("несуществующий", set()),
        ("", set()),
        ("   ", set()),
        ("---", set())
    ]
)
def test_search_matches(
    app, search_data, query, expected
):

    with app.app_context():

        medicines, total = search_medicines(query)

        actual_ids = {
            medicine.id
            for medicine in medicines
        }

        expected_ids = {
            search_data[key]
            for key in expected
        }

        assert actual_ids == expected_ids

        assert total == len(expected_ids)

def test_search_ranking(app, search_data):

    with app.app_context():

        medicines, total = search_medicines(
            "Но-шпа"
        )

        assert total == 2

        assert [
            medicine.id
            for medicine in medicines
        ] == [
            search_data["no_shpa"],
            search_data["forte"]
        ]

def test_search_empty_page(client):

    response = client.get("/")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Введите поисковый запрос" in html
    assert 'name="q"' in html

def test_search_location_links(client, search_data):

    response = client.get(
        "/",
        query_string={"q": "НО-ШПА 40"}
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Но-шпа" in html
    assert "40 мг" in html
    assert "Шкаф 1" in html
    assert "Шкаф 2" in html
    assert "Полка 1" in html
    assert "Ящик 1" in html

    d = search_data

    first_url = (
        f"/storage/{d['cabinet1']}"
        f"/layout?focus={d['slot']}"
        f"#location-{d['slot']}"
    )

    second_url = (
        f"/storage/{d['cabinet2']}"
        f"/layout?focus={d['drawer']}"
        f"#location-{d['drawer']}"
    )

    assert f'href="{first_url}"' in html
    assert f'href="{second_url}"' in html

    layout = client.get(second_url)

    assert layout.status_code == 200
    assert "is-selected" in layout.get_data(as_text=True)

def test_search_unplaced_medicine(
    client, search_data
):

    response = client.get(
        "/",
        query_string={"q": "ибупрофен 200"}
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Ибупрофен" in html

    assert "Место хранения не назначено" in html

    assert "Показать на схеме" not in html

def test_search_no_results(client):

    response = client.get(
        "/",
        query_string={"q": "несуществующий"}
    )

    assert response.status_code == 200

    assert "Ничего не найдено" in (
        response.get_data(as_text=True)
    )

def test_search_query_limit(client):

    response = client.get(
        "/",
        query_string={"q": "А" * 201}
    )

    assert response.status_code == 400

    assert "Поисковый запрос слишком длинный" in (
        response.get_data(as_text=True)
    )

def test_search_result_limit(client, app):

    with app.app_context():

        medicines = [
            Medicine(name=f"Тестовый препарат {i}")
            for i in range(101)
        ]

        db.session.add_all(medicines)
        db.session.commit()

        results, total = search_medicines(
            "Тестовый препарат"
        )

        assert total == 101
        assert len(results) == 100

    response = client.get(
        "/",
        query_string={"q": "Тестовый препарат"}
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Найдено препаратов: 101" in html
    assert "Показано первых 100" in html
    assert html.count('class="search-result"') == 100

