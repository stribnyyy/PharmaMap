import re
import pytest
from app.extensions import db
from app.models import Location


def get_csrf_token(client):
    response = client.get("/storage/")

    assert response.status_code == 200

    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"',
        response.data
    )

    assert match is not None

    return match.group(1).decode()

def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200

    assert "Найдите нужное лекарство" in (
        response.get_data(as_text=True)
    )


def test_storage_page(client):
    response = client.get("/storage/")

    assert response.status_code == 200

    assert "Моя аптека" in (
        response.get_data(as_text=True)
    )

def test_create_cabinet(client, app):
    token = get_csrf_token(client)

    response = client.post(
        "/storage/create",
        data={
            "name": "Шкаф 1",
            "csrf_token": token
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    assert "Шкаф успешно создан" in (
        response.get_data(as_text=True)
    )

    with app.app_context():
        cabinets = db.session.scalars(
            db.select(Location)
        ).all()

        assert len(cabinets) == 1
        assert cabinets[0].name == "Шкаф 1"
        assert cabinets[0].type == "cabinet"
        assert cabinets[0].parent_id is None

def test_duplicate_cabinet(client, app):
    token = get_csrf_token(client)

    for name in ("Шкаф 1", "шкаф 1"):
        response = client.post(
            "/storage/create",
            data={
                "name": name,
                "csrf_token": token
            },
            follow_redirects=True
        )

    assert "уже существует" in (
        response.get_data(as_text=True)
    )

    with app.app_context():
        cabinets = db.session.scalars(
            db.select(Location)
        ).all()

        assert len(cabinets) == 1

@pytest.mark.parametrize(
    "name, expected_error",
    [
        ("", "не может быть пустым"),
        ("   ", "не может быть пустым"),
        ("А" * 151, "Название слишком длинное"),
    ]
)
def test_invalid_cabinet_name(
    client, app, name, expected_error
):
    token = get_csrf_token(client)

    response = client.post(
        "/storage/create",
        data={
            "name": name,
            "csrf_token": token
        },
        follow_redirects=True
    )

    assert expected_error in (
        response.get_data(as_text=True)
    )

    with app.app_context():
        cabinets = db.session.scalars(
            db.select(Location)
        ).all()

        assert len(cabinets) == 0

def test_missing_csrf_token(client, app):
    response = client.post(
        "/storage/create",
        data={"name": "Шкаф 1"}
    )

    assert response.status_code == 400

    with app.app_context():
        cabinets = db.session.scalars(
            db.select(Location)
        ).all()

        assert len(cabinets) == 0