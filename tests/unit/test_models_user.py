# tests/unit/test_models_user.py
import pytest
from types import SimpleNamespace
from app.models.user import User

# --- Utility fixtures for monkeypatching ---

@pytest.fixture
def mock_execute_query(monkeypatch):
    """Patch execute_query to avoid touching a real DB."""
    called = {}

    def fake_execute_query(query, params=None, db_path=None, fetch=False):
        called["query"] = query
        called["params"] = params
        called["fetch"] = fetch
        # Return synthetic data when needed
        if "FROM users WHERE username =" in query and fetch:
            # Simulate one matching row
            return [(1, "john", "john@example.com", "hashedpw", "member", "John Doe", "999", 1)]
        if "FROM users" in query and fetch:
            # General case for get_by_id/get_by_username_or_email
            return [(1, "john", "john@example.com", "hashedpw", "member", "John Doe", "999", 1)]
        # simulate insert returning id=42
        if query.strip().lower().startswith("insert"):
            return 42
        return None

    monkeypatch.setattr("app.models.user.execute_query", fake_execute_query)
    return called


@pytest.fixture
def mock_bcrypt(monkeypatch):
    """Patch Bcrypt methods used in the User model."""
    class DummyBcrypt:
        def generate_password_hash(self, pw):
            # Return fake bcrypt hash
            return f"$2b$fakehashfor-{pw}".encode("utf-8")

        def check_password_hash(self, stored, candidate):
            # Fake: return True if candidate in stored
            return candidate in stored

    monkeypatch.setattr("app.models.user.Bcrypt", lambda app=None: DummyBcrypt())
    return DummyBcrypt()


# --- Tests for helper methods ---

def test_is_already_hashed_variants():
    u = User()
    assert u._is_already_hashed("$2b$something") is True
    assert u._is_already_hashed("bcrypt:something") is True
    assert u._is_already_hashed("randomplain") is False
    assert u._is_already_hashed(None) is False


# --- Tests for fetching and authentication ---

def test_get_by_username(monkeypatch, mock_execute_query):
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        user = User.get_by_username("john")
        assert isinstance(user, User)
        assert user.username == "john"
        assert mock_execute_query["fetch"] is True


def test_get_by_id(monkeypatch, mock_execute_query):
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        user = User.get_by_id(1)
        assert user.id == 1
        assert user.full_name == "John Doe"


def test_get_by_username_or_email(monkeypatch, mock_execute_query):
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        user = User.get_by_username_or_email("john@example.com")
        assert user.email == "john@example.com"


def test_authenticate_success(monkeypatch, mock_bcrypt, mock_execute_query):
    """Simulate correct password match."""
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        # Patch execute_query to return fake row
        def fake_query(query, params, db_path, fetch):
            return [(1, "john", "john@example.com", "$2b$fakehashfor-pass123", "member", "John", "999", 1)]

        monkeypatch.setattr("app.models.user.execute_query", fake_query)
        user = User.authenticate("john", "pass123")
        assert isinstance(user, User)
        assert user.username == "john"


def test_authenticate_failure(monkeypatch, mock_bcrypt, mock_execute_query):
    """Simulate no match or invalid hash."""
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        # Return no rows
        monkeypatch.setattr("app.models.user.execute_query", lambda *a, **k: [])
        user = User.authenticate("ghost", "wrong")
        assert user is None


# --- Tests for save() behavior ---

def test_save_inserts_new_user(monkeypatch, mock_bcrypt, mock_execute_query):
    """Verify insert path hashes password and assigns new id."""
    from flask import Flask
    app = Flask(__name__)
    u = User(username="john", email="john@example.com", password_hash="plainpw",
             role="member", full_name="John Doe", phone="123")
    with app.app_context():
        new_id = u.save()
        assert new_id == 42
        assert u.id == 42
        assert u.password_hash.startswith("$2b$fakehashfor-")


def test_save_updates_existing_user(monkeypatch, mock_bcrypt, mock_execute_query):
    """Verify update path uses correct query and returns id unchanged."""
    from flask import Flask
    app = Flask(__name__)
    u = User(id=7, username="john", email="john@example.com",
             password_hash="$2b$fakehashfor-pw", role="member", full_name="John Doe")
    with app.app_context():
        result = u.save()
        assert result == 7
        assert "update" in mock_execute_query["query"].lower()




def test_update_password(monkeypatch, mock_bcrypt, mock_execute_query):
    """Ensure bcrypt hashing and DB update happen."""
    from flask import Flask
    app = Flask(__name__)
    u = User(id=99, username="sam", password_hash="$2b$old")
    with app.app_context():
        result = u.update_password("newpw123")
        assert result is True
        assert "$2b$fakehashfor-newpw123" in u.password_hash
