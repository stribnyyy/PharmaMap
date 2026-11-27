from flask import current_app

from flask_login import UserMixin

from werkzeug.security import check_password_hash

from app.extensions import login_manager


class User(UserMixin):

    def __init__(self, username):

        self.id = username
        self.username = username


@login_manager.user_loader
def load_user(user_id):

    username = current_app.config["AUTH_USERNAME"]
    password_hash = current_app.config["AUTH_PASSWORD_HASH"]

    if password_hash and user_id == username:
        return User(username)

    return None


def authenticate(username, password):

    expected_username = current_app.config[
        "AUTH_USERNAME"
    ]

    password_hash = current_app.config[
        "AUTH_PASSWORD_HASH"
    ]

    if not password_hash:
        return None

    if username != expected_username:
        return None

    if not check_password_hash(
        password_hash,
        password
    ):
        return None

    return User(expected_username)