import os

class Config:
    APP_NAME = "PharmaMap"
    VERSION = "0.1.0"

    SQLALCHEMY_DATABASE_URI = "sqlite:///pharmamap.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("PHARMAMAP_SECRET_KEY")

    AUTH_USERNAME = os.environ.get(
        "PHARMAMAP_USERNAME",
        "pharmacist"
    )

    AUTH_PASSWORD_HASH = os.environ.get(
        "PHARMAMAP_PASSWORD_HASH"
    )

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = (
        os.environ.get("PHARMAMAP_HTTPS") == "1"
    )