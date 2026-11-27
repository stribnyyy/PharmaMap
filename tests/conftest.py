import re
import pytest

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db


TEST_PASSWORD_HASH = generate_password_hash(
    "test-password"
)


@pytest.fixture()
def app():

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-key",
        "AUTH_USERNAME": "test-user",
        "AUTH_PASSWORD_HASH": TEST_PASSWORD_HASH,
        "SESSION_COOKIE_SECURE": False
    })

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def anonymous_client(app):

    return app.test_client()


@pytest.fixture()
def client(anonymous_client):

    response = anonymous_client.get(
        "/auth/login"
    )

    assert response.status_code == 200

    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"',
        response.data
    )

    assert match is not None

    response = anonymous_client.post(
        "/auth/login",
        data={
            "username": "test-user",
            "password": "test-password",
            "csrf_token": match.group(1).decode()
        }
    )

    assert response.status_code == 303

    return anonymous_client