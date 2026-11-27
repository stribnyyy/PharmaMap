import re
import pytest


def get_token(client, url="/auth/login"):

    response = client.get(url)

    assert response.status_code == 200

    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"',
        response.data
    )

    assert match is not None

    return match.group(1).decode()


@pytest.mark.parametrize(
    "url",
    [
        "/",
        "/storage/",
        "/medicines/",
        "/storage/1/layout"
    ]
)
def test_requires_authentication(
    anonymous_client, url
):

    response = anonymous_client.get(url)

    assert response.status_code == 302

    assert response.headers["Location"] == (
        "/auth/login"
    )


def test_successful_login(anonymous_client):

    response = anonymous_client.post(
        "/auth/login",
        data={
            "username": "test-user",
            "password": "test-password",
            "csrf_token": get_token(
                anonymous_client
            )
        }
    )

    assert response.status_code == 303

    assert anonymous_client.get(
        "/"
    ).status_code == 200


@pytest.mark.parametrize(
    "username, password",
    [
        ("wrong-user", "test-password"),
        ("test-user", "wrong-password")
    ]
)
def test_invalid_credentials(
    anonymous_client, username, password
):

    response = anonymous_client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": get_token(
                anonymous_client
            )
        }
    )

    assert response.status_code == 401

    assert "Неверный логин или пароль" in (
        response.get_data(as_text=True)
    )

    assert anonymous_client.get(
        "/"
    ).status_code == 302


def test_logout(client):

    response = client.post(
        "/auth/logout",
        data={
            "csrf_token": get_token(
                client, "/storage/"
            )
        }
    )

    assert response.status_code == 303

    assert client.get(
        "/storage/"
    ).status_code == 302


def test_login_requires_csrf(anonymous_client):

    response = anonymous_client.post(
        "/auth/login",
        data={
            "username": "test-user",
            "password": "test-password"
        }
    )

    assert response.status_code == 400


def test_logout_requires_csrf(client):

    response = client.post("/auth/logout")

    assert response.status_code == 400

    assert client.get("/").status_code == 200


def test_anonymous_cannot_create_cabinet(
    anonymous_client
):

    response = anonymous_client.post(
        "/storage/create",
        data={
            "name": "Посторонний шкаф",
            "csrf_token": get_token(
                anonymous_client
            )
        }
    )

    assert response.status_code == 303

    assert response.headers["Location"] == (
        "/auth/login"
    )

    from app.extensions import db
    from app.models import Location

    with anonymous_client.application.app_context():

        locations = db.session.scalars(
            db.select(Location)
        ).all()

        assert locations == []


def test_unconfigured_account(
    app, anonymous_client
):

    app.config["AUTH_PASSWORD_HASH"] = None

    response = anonymous_client.post(
        "/auth/login",
        data={
            "username": "test-user",
            "password": "test-password",
            "csrf_token": get_token(
                anonymous_client
            )
        }
    )

    assert response.status_code == 503

