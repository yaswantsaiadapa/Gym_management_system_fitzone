import sys
import os
import types
import importlib.util
import re
from pathlib import Path
import pytest
from flask import Flask

# -------------------------------------------------------------------
# Ensure repository root is on sys.path so `import app...` works
# -------------------------------------------------------------------
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# -------------------------------------------------------------------
# Create minimal dummy modules to prevent ImportError during tests
# -------------------------------------------------------------------
dummy_names = ["flask_mail", "flask_bcrypt", "flask_wtf", "flask_login", "flask_migrate"]
for name in dummy_names:
    if name not in sys.modules:
        mod = types.ModuleType(name)

        if name == "flask_bcrypt":
            class Bcrypt:
                def __init__(self, *a, **k): pass
                def generate_password_hash(self, pw): return pw
                def check_password_hash(self, h, pw): return h == pw
            mod.Bcrypt = Bcrypt

        if name == "flask_mail":
            class Mail:
                def __init__(self, *a, **k): pass

            class Message:
                def __init__(self, subject="", recipients=None, body="", sender=None):
                    self.subject = subject
                    self.recipients = recipients or []
                    self.body = body
                    self.sender = sender

            mod.Mail = Mail
            mod.Message = Message

        sys.modules[name] = mod

# -------------------------------------------------------------------
# Ensure 'app' and 'app.models' packages exist for sensible imports
# -------------------------------------------------------------------
_app_dir = os.path.join(project_root, "app")
_models_dir = os.path.join(_app_dir, "models")
if "app" not in sys.modules:
    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = [_app_dir]
    sys.modules["app"] = app_pkg
if "app.models" not in sys.modules:
    models_pkg = types.ModuleType("app.models")
    models_pkg.__path__ = [_models_dir]
    sys.modules["app.models"] = models_pkg

# -------------------------------------------------------------------
# Try to import app factory if it exists
# -------------------------------------------------------------------
try:
    from app.app import create_app
    HAVE_FACTORY = True
except Exception:
    HAVE_FACTORY = False

# -------------------------------------------------------------------
# Flask app fixture (used by route and integration tests)
# -------------------------------------------------------------------
@pytest.fixture(scope="session")
def flask_app():
    """
    Create a minimal Flask app for testing.
    Registers dummy endpoint 'auth.login' to prevent url_for errors.
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

    # Add dummy login route if not already registered
    if "auth.login" not in app.view_functions:
        def _dummy_login():
            return "login page"
        app.add_url_rule(
            "/auth/login",
            endpoint="auth.login",
            view_func=_dummy_login,
            methods=["GET"]
        )

    yield app

@pytest.fixture()
def client(flask_app):
    """Flask test client fixture."""
    return flask_app.test_client()

# -------------------------------------------------------------------
# Custom dynamic module loader fixture
# -------------------------------------------------------------------
@pytest.fixture
def load_module_from_path():
    """
    Load a Python module from a file path without importing the entire package.
    For files under app/models, rewrite relative imports to absolute app.models.* imports.
    """
    def _loader(path, name=None):
        path = Path(path)
        src = path.read_text()

        # Rewrite relative imports for model files
        if 'app' in str(path.parts) and 'models' in str(path.parts):
            src = re.sub(r'from\s+\.(\w+)\s+import', r'from app.models.\1 import', src)
            rel_parts = path.parts[path.parts.index('app') + 1:]
            name = 'app.' + '.'.join(rel_parts).replace('/', '.').replace('\\', '.')

        if name is None:
            name = f"testmod_{path.stem}"

        spec = importlib.util.spec_from_file_location(name, str(path))
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = '.'.join(name.split('.')[:-1]) if '.' in name else ''
        code = compile(src, str(path), 'exec')
        exec(code, mod.__dict__)
        sys.modules[name] = mod
        return mod

    return _loader
