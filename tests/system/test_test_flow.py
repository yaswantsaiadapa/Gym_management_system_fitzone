
import os
from pathlib import Path

def test_seed_db_and_read(tmp_path, load_module_from_path):
    db_mod = load_module_from_path(os.path.join(os.getcwd(), "app", "models", "database.py"), "db_module")
    # If there's a seed function create_db or init_db, try to call it safely
    # We'll create a temp DB and ensure init_db can be called (best-effort)
    db_file = tmp_path / "system_db.sqlite"
    try:
        init_mod = load_module_from_path(os.path.join(os.getcwd(), "app", "models", "database.py"), "db_init_mod")
        # Some projects provide init_db function; call it if present
        if hasattr(init_mod, "init_db"):
            init_mod.init_db(str(db_file))
            # check the file exists
            assert os.path.exists(str(db_file))
        else:
            # fallback: create a simple table
            db_mod.execute_query("CREATE TABLE sys_test (id INTEGER PRIMARY KEY, v TEXT)", params=(), db_path=str(db_file), fetch=False)
            nid = db_mod.execute_query("INSERT INTO sys_test (v) VALUES (?)", params=("x",), db_path=str(db_file), fetch=False)
            rows = db_mod.execute_query("SELECT v FROM sys_test WHERE id=?", params=(nid,), db_path=str(db_file), fetch=True)
            assert rows and rows[0][0] == "x"
    except Exception as e:
        # If anything unexpected happens, fail the test with the exception for debugging
        raise
