
import os
from pathlib import Path
import tempfile

def test_execute_and_fetch(tmp_path, load_module_from_path):
    # load database module
    db_mod = load_module_from_path(os.path.join(os.getcwd(), "app", "models", "database.py"), "db_module")
    # create a temp sqlite file
    db_file = tmp_path / "test_db.sqlite"
    # create a table and insert data via execute_query
    create = "CREATE TABLE users_test (id INTEGER PRIMARY KEY, name TEXT)"
    db_mod.execute_query(create, params=(), db_path=str(db_file), fetch=False)
    insert_sql = "INSERT INTO users_test (name) VALUES (?)"
    lid = db_mod.execute_query(insert_sql, params=("Alice",), db_path=str(db_file), fetch=False)
    assert isinstance(lid, int)
    rows = db_mod.execute_query("SELECT name FROM users_test WHERE id=?", params=(lid,), db_path=str(db_file), fetch=True)
    assert len(rows) == 1
    assert rows[0][0] == "Alice"
