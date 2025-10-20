# scripts/add_reset_columns.py
import sqlite3
import sys
from pathlib import Path

def ensure_columns(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("PRAGMA table_info(users);")
    cols = [row[1] for row in cur.fetchall()]  # column name is at index 1

    if 'reset_token' not in cols:
        print("Adding column: reset_token")
        cur.execute("ALTER TABLE users ADD COLUMN reset_token TEXT;")
    else:
        print("Column reset_token already exists")

    if 'reset_token_expires' not in cols:
        print("Adding column: reset_token_expires")
        cur.execute("ALTER TABLE users ADD COLUMN reset_token_expires TEXT;")
    else:
        print("Column reset_token_expires already exists")

    con.commit()
    con.close()
    print("Migration complete.")

if __name__ == "__main__":
    db_arg = sys.argv[1] if len(sys.argv) > 1 else "gym_management.db"
    db_path = Path(db_arg)
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path.resolve()}")
        sys.exit(1)
    ensure_columns(str(db_path))
