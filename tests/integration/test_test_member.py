
import os
from pathlib import Path
import sqlite3
import tempfile

def test_member_create_and_query(tmp_path, load_module_from_path):
    db_mod = load_module_from_path(os.path.join(os.getcwd(), "app", "models", "database.py"), "db_module")
    member_mod = load_module_from_path(os.path.join(os.getcwd(), "app", "models", "member.py"), "member_module")
    # set up db schema minimally for member operations (assume members table)
    db_file = tmp_path / "test_db.sqlite"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT, password TEXT, role TEXT, is_active INTEGER DEFAULT 1)")
    cur.execute("CREATE TABLE members (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT)")
    conn.commit()
    conn.close()
    # Use execute_query to insert user and member
    uid = db_mod.execute_query("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                               params=("u1","e@x.com","pw","member"), db_path=str(db_file), fetch=False)
    mid = db_mod.execute_query("INSERT INTO members (user_id, name) VALUES (?, ?)",
                               params=(uid, "John Doe"), db_path=str(db_file), fetch=False)
    # Query back
    rows = db_mod.execute_query("SELECT m.id, u.username FROM members m JOIN users u ON m.user_id=u.id WHERE m.id=?",
                                params=(mid,), db_path=str(db_file), fetch=True)
    assert rows and rows[0]["username"] == "u1"
