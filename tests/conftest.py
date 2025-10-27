# tests/conftest.py
import sys
from pathlib import Path
import pytest
from flask import Flask

# Ensure repository root is on sys.path so `import app...` works
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import app factory if present. If your app factory is named differently, adjust this import.
try:
    from app.app import create_app  # recommended: you have app/app.py with create_app()
    HAVE_FACTORY = True
except Exception:
    HAVE_FACTORY = False

@pytest.fixture(scope="session")
def flask_app():
    """
    Minimal Flask app used by unit tests. It registers a simple endpoint named
    'auth.login' so `url_for('auth.login')` resolves inside decorators.
    """
    if HAVE_FACTORY:
        app = create_app()
        app.config.update({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
        })
    else:
        app = Flask("test_app")
        app.config.update({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
        })


    # use exact endpoint name used in your decorators: 'auth.login'
        # Register dummy endpoint *only if* it doesn’t already exist
    if "auth.login" not in app.view_functions:
        def _dummy_login():
            return "login page"
        app.add_url_rule(
            "/auth/login", endpoint="auth.login",
            view_func=_dummy_login, methods=["GET"]
        )

    yield app

@pytest.fixture()
def client(flask_app):
    """Flask test client fixture."""
    return flask_app.test_client()


