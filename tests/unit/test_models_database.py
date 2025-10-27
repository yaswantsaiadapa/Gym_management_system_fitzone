# tests/unit/test_models_database.py
import os
import sqlite3
import tempfile
from app.models import database
from app.models.database import get_db_connection, execute_query

def test_get_db_connection_creates_file(tmp_path):
    db_file = tmp_path / "test_db.sqlite"
    conn = get_db_connection(str(db_file))
    assert isinstance(conn, sqlite3.Connection)
    conn.execute("CREATE TABLE tmp (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO tmp (name) VALUES (?)", ("a",))
    conn.commit()
    cur = conn.cursor()
    cur.execute("SELECT name FROM tmp")
    row = cur.fetchone()
    assert row[0] == "a"
    conn.close()

def test_execute_query_insert_and_fetch(tmp_path):
    db_file = tmp_path / "test_db2.sqlite"
    # create table via direct sqlite then use execute_query to insert and fetch
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()

    execute_query("INSERT INTO users (name) VALUES (?)", ("tom",), str(db_file))
    rows = execute_query("SELECT id, name FROM users WHERE name = ?", ("tom",), str(db_file), fetch=True)
    assert isinstance(rows, list)
    assert rows and rows[0][1] == "tom"
