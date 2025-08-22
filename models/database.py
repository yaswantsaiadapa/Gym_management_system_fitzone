import sqlite3
from datetime import date

def get_db_connection(db_path='gym_management.db'):
    """Get database connection with row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path='gym_management.db'):
    """Initialize database with all required tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create admin table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT
        )
    ''')
    
    # Create members table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            weight REAL,
            height REAL,
            payment_status TEXT DEFAULT 'pending',
            membership_date DATE,
            expiry_date DATE,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Create trainers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            salary REAL,
            working_hours TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Create equipment table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'working',
            last_maintenance DATE
        )
    ''')
    
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            trainer_id INTEGER,
            date DATE,
            time_slot TEXT,
            status TEXT DEFAULT 'present',
            FOREIGN KEY (member_id) REFERENCES members (id),
            FOREIGN KEY (trainer_id) REFERENCES trainers (id)
        )
    ''')
    
    # Insert default admin if not exists
    cursor.execute('SELECT COUNT(*) FROM admin WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO admin (username, password, name, email) VALUES (?, ?, ?, ?)',
                       ('admin', 'admin123', 'Gym Administrator', 'admin@gym.com'))
    
    # Insert sample equipment if not exists
    cursor.execute('SELECT COUNT(*) FROM equipment')
    if cursor.fetchone()[0] == 0:
        equipment_list = [
            ('Treadmill 1', 'working'),
            ('Treadmill 2', 'working'),
            ('Bench Press', 'working'),
            ('Dumbbells Set', 'working'),
            ('Exercise Bike', 'maintenance')
        ]
        
        for equipment in equipment_list:
            cursor.execute('INSERT INTO equipment (name, status) VALUES (?, ?)', equipment)
    
    conn.commit()
    conn.close()

def execute_query(query, params=(), db_path='gym_management.db', fetch=False):
    """Execute a database query with optional parameters"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall()
            conn.close()
            return result
        else:
            conn.commit()
            conn.close()
            return cursor.lastrowid
    except Exception as e:
        conn.close()
        raise e