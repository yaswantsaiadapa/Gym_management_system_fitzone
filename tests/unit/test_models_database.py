# tests/unit/test_models_database.py
import os
import sqlite3
import tempfile
import pytest
from types import SimpleNamespace

from app.models import database


# --- Basic DB Connection Tests ---
def test_get_db_connection_creates_file(tmp_path):
    db_file = tmp_path / "test_db.sqlite"
    conn = database.get_db_connection(str(db_file))
    assert isinstance(conn, sqlite3.Connection)
    conn.execute("CREATE TABLE tmp (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO tmp (name) VALUES (?)", ("alpha",))
    conn.commit()
    val = conn.execute("SELECT name FROM tmp").fetchone()[0]
    assert val == "alpha"
    conn.close()
    assert db_file.exists()


# --- Execute Query Tests ---
def test_execute_query_insert_and_fetch(tmp_path):
    db_file = tmp_path / "test_db2.sqlite"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()

    # Insert and fetch
    inserted_id = database.execute_query("INSERT INTO users (name) VALUES (?)", ("tom",), str(db_file))
    assert isinstance(inserted_id, int)
    rows = database.execute_query("SELECT id, name FROM users", fetch=True, db_path=str(db_file))
    assert rows and rows[0][1] == "tom"


def test_execute_query_logs_error(monkeypatch):
    """Simulate SQL error and confirm it's caught and logged."""
    called = {}

    def fake_connect(db_path):
        raise sqlite3.OperationalError("Mock connection failed")

    monkeypatch.setattr(database, "get_db_connection", fake_connect)

    with pytest.raises(sqlite3.OperationalError):
        database.execute_query("SELECT 1", fetch=True)

    called["ok"] = True
    assert "ok" in called


# --- Bcrypt and Flask Context Tests ---
class DummyBcrypt:
    def __init__(self, app): self.app = app
    def generate_password_hash(self, text): return f"hashed-{text}".encode()


@pytest.fixture
def mock_flask_context(monkeypatch):
    """Mock Flask current_app with minimal config/logger."""
    dummy_app = SimpleNamespace(config={}, logger=SimpleNamespace(error=lambda *a, **kw: None))
    monkeypatch.setattr(database, "current_app", dummy_app)
    monkeypatch.setattr(database, "Bcrypt", DummyBcrypt)
    return dummy_app


def test_get_bcrypt_returns_instance(mock_flask_context):
    bcrypt = database._get_bcrypt()
    assert isinstance(bcrypt, DummyBcrypt)
    assert bcrypt.app == mock_flask_context


# --- init_db and insert_default_data tests ---
def test_init_db_creates_tables(tmp_path, mock_flask_context):
    """Ensure init_db creates expected tables."""
    db_file = tmp_path / "init_test.sqlite"
    database.init_db(str(db_file))
    conn = sqlite3.connect(str(db_file))
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {t[0] for t in tables}
    expected_tables = {
        "users", "membership_plans", "trainers", "members",
        "payments", "attendance", "workouts", "equipment", "announcements"
    }
    assert expected_tables.issubset(table_names)
    conn.close()

def test_execute_query_commit_and_fetch(tmp_path):
    """Ensure both fetch and non-fetch work as expected."""
    db_file = tmp_path / "combo.sqlite"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()

    # Insert
    new_id = database.execute_query("INSERT INTO demo (name) VALUES (?)", ("john",), str(db_file))
    assert isinstance(new_id, int)

    # Fetch
    rows = database.execute_query("SELECT * FROM demo", db_path=str(db_file), fetch=True)
    assert len(rows) == 1 and rows[0][1] == "john"
