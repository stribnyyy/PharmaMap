import os

class Config:
    APP_NAME = "PharmaMap"
    VERSION = "0.1.0"

    SQLALCHEMY_DATABASE_URI = "sqlite:///pharmamap.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("PHARMAMAP_SECRET_KEY")