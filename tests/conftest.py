# tests/conftest.py
import sys
from pathlib import Path
import pytest
from flask import Flask

# ensure project root on sys.path (so imports like `from app.utils import ...` work)
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.app import create_app  # adjust if your factory is named differently
# If you don't have a factory, create a minimal Flask app in tests instead.

@pytest.fixture(scope="session")
def flask_app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        # Use sqlite memory if your app accepts SQLALCHEMY_DATABASE_URI
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    # If your app needs DB schema, create it here (depending on your DB setup)
    with app.app_context():
        # If using SQLAlchemy: create tables. Example:
        # from app.models.database import db
        # db.create_all()
        pass
    yield app

@pytest.fixture
def client(flask_app):
    return flask_app.test_client()

@pytest.fixture
def app_ctx(flask_app):
    with flask_app.app_context():
        yield
