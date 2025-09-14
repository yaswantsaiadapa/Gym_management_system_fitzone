import sqlite3
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash
import json

def get_db_connection(db_path='gym_management.db'):
    """Get database connection with row factory and FK enabled"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  
    return conn


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
            last_id = cursor.lastrowid
            conn.close()
            return last_id
    except Exception as e:
        conn.close()
        # Optional: log error in Flask if running inside app
        try:
            from flask import current_app
            current_app.logger.error(f"DB Error: {e} | Query: {query} | Params: {params}")
        except:
            print(f"DB Error: {e} | Query: {query} | Params: {params}")
        raise

def init_db(db_path='gym_management.db'):
    """Initialize database with all required tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Users table (for authentication - admin, member, trainer)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'member', 'trainer')),
            full_name TEXT NOT NULL,
            phone TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Membership Plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS membership_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            duration_months INTEGER NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            features TEXT, -- JSON string
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Enhanced Members table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        membership_plan_id INTEGER,
        phone TEXT NOT NULL,
        emergency_contact TEXT,
        emergency_phone TEXT,
        address TEXT,
        date_of_birth DATE,
        weight DECIMAL(5,2),
        height DECIMAL(5,2),
        medical_conditions TEXT,
        fitness_goals TEXT,
        membership_start_date DATE,
        membership_end_date DATE,
        status TEXT DEFAULT 'pending_payment' CHECK (status IN ('active', 'inactive', 'suspended', 'pending_payment')),
        trainer_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (membership_plan_id) REFERENCES membership_plans (id),
        FOREIGN KEY (trainer_id) REFERENCES trainers (id)
        )
    ''')

    
    # Enhanced Trainers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone TEXT NOT NULL,
            specialization TEXT,
            experience_years INTEGER,
            certification TEXT,
            salary DECIMAL(10,2),
            working_hours TEXT,
            bio TEXT,
            status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Payments table
    cursor.execute('''
        -- Payments table (updated)
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    membership_plan_id INTEGER NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method TEXT CHECK (payment_method IN ('cash','card','online','bank_transfer','upi')),
    payment_status TEXT DEFAULT 'pending' CHECK (payment_status IN ('pending', 'completed', 'failed', 'refunded')),
    transaction_id TEXT,
    payment_date DATE,
    due_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invoice_number TEXT,                 -- unique invoice/reference id (optional format)
    reminder_sent INTEGER DEFAULT 0,     -- 0/1 flag whether a reminder email was already sent
    reminder_sent_at TIMESTAMP,          -- when reminder was sent (nullable)
    cancelled_processed INTEGER DEFAULT 0, -- 0/1 flag whether cancellation action was taken
    FOREIGN KEY (member_id) REFERENCES members (id),
    FOREIGN KEY (membership_plan_id) REFERENCES membership_plans (id)
);

    ''')
    
    # Attendance table (enhanced with time_slot column)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            trainer_id INTEGER,
            check_in_time TIMESTAMP,
            check_out_time TIMESTAMP,
            date DATE NOT NULL,
            time_slot TEXT,
            workout_type TEXT,
            notes TEXT,
            status TEXT DEFAULT 'scheduled' CHECK (status IN ('present', 'absent', 'late','scheduled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members (id),
            FOREIGN KEY (trainer_id) REFERENCES trainers (id)
        )
    ''')
    
    # Workouts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT, -- strength, cardio, flexibility, etc.
            difficulty_level TEXT CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
            duration_minutes INTEGER,
            calories_burned INTEGER,
            instructions TEXT,
            equipment_needed TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_by INTEGER, -- trainer_id
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES trainers (id)
        )
    ''')
    
    # Member Workout Plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS member_workout_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            trainer_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            start_date DATE,
            end_date DATE,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members (id),
            FOREIGN KEY (trainer_id) REFERENCES trainers (id)
        )
    ''')
    
    # Workout Plan Details table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_plan_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            workout_id INTEGER NOT NULL,
            day_of_week INTEGER CHECK (day_of_week BETWEEN 1 AND 7), -- 1=Monday, 7=Sunday
            sets INTEGER,
            reps INTEGER,
            weight DECIMAL(5,2),
            rest_seconds INTEGER,
            notes TEXT,
            FOREIGN KEY (plan_id) REFERENCES member_workout_plans (id),
            FOREIGN KEY (workout_id) REFERENCES workouts (id)
        )
    ''')
    
    # Diet Plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diet_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            trainer_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            total_calories INTEGER,
            start_date DATE,
            end_date DATE,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members (id),
            FOREIGN KEY (trainer_id) REFERENCES trainers (id)
        )
    ''')
    
    # Diet Plan Meals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diet_plan_meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diet_plan_id INTEGER NOT NULL,
            meal_type TEXT CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
            meal_name TEXT NOT NULL,
            ingredients TEXT,
            calories INTEGER,
            protein DECIMAL(5,2),
            carbs DECIMAL(5,2),
            fat DECIMAL(5,2),
            instructions TEXT,
            FOREIGN KEY (diet_plan_id) REFERENCES diet_plans (id)
        )
    ''')
    
    # Progress Tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS member_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            recorded_date DATE NOT NULL,
            weight DECIMAL(5,2),
            body_fat_percentage DECIMAL(4,2),
            muscle_mass DECIMAL(5,2),
            bmi DECIMAL(4,2),
            chest DECIMAL(5,2),
            waist DECIMAL(5,2),
            hips DECIMAL(5,2),
            bicep DECIMAL(5,2),
            thigh DECIMAL(5,2),
            notes TEXT,
            photo_path TEXT,
            recorded_by INTEGER, -- trainer_id
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members (id),
            FOREIGN KEY (recorded_by) REFERENCES trainers (id)
        )
    ''')
    
    # Equipment table (enhanced)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            brand TEXT,
            model TEXT,
            purchase_date DATE,
            warranty_end_date DATE,
            status TEXT DEFAULT 'working' CHECK (status IN ('working', 'maintenance', 'out_of_order')),
            last_maintenance_date DATE,
            next_maintenance_date DATE,
            maintenance_notes TEXT,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Announcements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            announcement_type TEXT CHECK (announcement_type IN ('general', 'maintenance', 'event', 'offer')),
            target_audience TEXT CHECK (target_audience IN ('all', 'members', 'trainers')),
            is_public BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            start_date DATE,
            end_date DATE,
            created_by INTEGER, -- admin user_id
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Email Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT,
            email_type TEXT,
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
            sent_at TIMESTAMP,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if time_slot column exists and add it if it doesn't (for existing databases)
    cursor.execute("PRAGMA table_info(attendance)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'time_slot' not in columns:
        cursor.execute("ALTER TABLE attendance ADD COLUMN time_slot TEXT")
        print("Added time_slot column to existing attendance table")
    
    # Insert default data
    insert_default_data(cursor)
    
    conn.commit()
    conn.close()

def insert_default_data(cursor):
    """Insert default/seed data"""

    # Create default admin user
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    if cursor.fetchone()[0] == 0:
        admin_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, full_name, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@fitzonegym.com', admin_password, 'admin', 'Gym Administrator', '+919000000001'))

    # Create default membership plans
    cursor.execute('SELECT COUNT(*) FROM membership_plans')
    if cursor.fetchone()[0] == 0:
        plans = [
            ('Monthly Basic', 'Basic gym access', 1, 999.00, '["Gym Access", "Locker Room"]'),
            ('Quarterly Premium', 'Premium features with trainer support', 3, 2499.00, '["Gym Access", "Locker Room", "1 Personal Training Session/Month", "Diet Consultation"]'),
            ('Yearly VIP', 'Full access with premium benefits', 12, 8999.00, '["Unlimited Gym Access", "Locker Room", "4 Personal Training Sessions/Month", "Nutrition Plan", "Progress Tracking", "Priority Support"]'),
            ('Premium Plus', 'All-inclusive premium package', 6, 4999.00, '["Unlimited Access", "Personal Trainer", "Nutrition Plan", "Group Classes", "Massage Therapy"]')
        ]
        for plan in plans:
            cursor.execute('''
                INSERT INTO membership_plans (name, description, duration_months, price, features)
                VALUES (?, ?, ?, ?, ?)
            ''', plan)

    # Create sample trainers
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "trainer"')
    if cursor.fetchone()[0] == 0:
        trainer_users = [
            ('ravi_trainer', 'ravi@fitzonegym.com', 'trainer123', 'Ravi Kumar', '+919000000002'),
            ('sneha_trainer', 'sneha@fitzonegym.com', 'trainer123', 'Sneha Reddy', '+919000000003')
        ]

        for trainer in trainer_users:
            password_hash = generate_password_hash(trainer[2])
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, full_name, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (trainer[0], trainer[1], password_hash, 'trainer', trainer[3], trainer[4]))

        # Create trainer profiles
        cursor.execute('SELECT id, full_name FROM users WHERE role = "trainer"')
        trainer_users = cursor.fetchall()
        for user in trainer_users:
            cursor.execute('''
                INSERT INTO trainers (user_id, phone, specialization, experience_years, certification, salary, working_hours, bio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user[0],
                '+919000000002' if 'Ravi' in user[1] else '+919000000003',
                'Strength Training, Weight Loss' if 'Ravi' in user[1] else 'Yoga, Flexibility, Cardio',
                6 if 'Ravi' in user[1] else 4,
                'Certified Fitness Trainer' if 'Ravi' in user[1] else 'Certified Yoga Instructor',
                35000.00 if 'Ravi' in user[1] else 30000.00,
                '6:00 AM - 2:00 PM' if 'Ravi' in user[1] else '2:00 PM - 10:00 PM',
                'Passionate about helping members achieve strength goals.' if 'Ravi' in user[1] else 'Yoga expert with focus on flexibility and stress relief.'
            ))

    # Create sample members
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "member"')
    if cursor.fetchone()[0] == 0:
        member_users = [
            ('sai_member', 'sai@fitzonegym.com', 'member123', 'Sai Teja', '+919000000004'),
            ('priya_member', 'priya@fitzonegym.com', 'member123', 'Priya Chowdary', '+919000000005')
        ]

        for member in member_users:
            password_hash = generate_password_hash(member[2])
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, full_name, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (member[0], member[1], password_hash, 'member', member[3], member[4]))

        # Fetch available plans and trainers safely
        cursor.execute('SELECT id FROM membership_plans')
        plan_ids = [row[0] for row in cursor.fetchall()]
        cursor.execute('SELECT id FROM trainers')
        trainer_ids = [row[0] for row in cursor.fetchall()]

        if plan_ids and trainer_ids:
            cursor.execute('SELECT id, full_name FROM users WHERE role = "member"')
            member_users = cursor.fetchall()
            for i, user in enumerate(member_users):
                cursor.execute('''
                    INSERT INTO members (
                        user_id, membership_plan_id, phone, weight, height,
                        membership_start_date, membership_end_date, trainer_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user[0],
                    plan_ids[i % len(plan_ids)],
                    '+919000000004' if 'Sai' in user[1] else '+919000000005',
                    72.0 if 'Sai' in user[1] else 58.0,
                    178.0 if 'Sai' in user[1] else 162.0,
                    date.today(),
                    date.today().replace(year=date.today().year + 1),
                    trainer_ids[i % len(trainer_ids)]
                ))

    # Insert sample equipment
    cursor.execute('SELECT COUNT(*) FROM equipment')
    if cursor.fetchone()[0] == 0:
        equipment_list = [
            ('Treadmill Pro X1', 'Cardio', 'TechFit', 'TX-2024', 'working', 'Cardio Area'),
            ('Bench Press Station', 'Strength', 'PowerLift', 'BP-500', 'working', 'Free Weights'),
            ('Leg Press Machine', 'Strength', 'PowerLift', 'LP-800', 'working', 'Machine Area'),
            ('Rowing Machine', 'Cardio', 'CardioMax', 'RM-300', 'maintenance', 'Cardio Area'),
            ('Dumbbell Set (5-50 kg)', 'Strength', 'IronGrip', 'DB-SET-1', 'working', 'Free Weights')
        ]
        for equipment in equipment_list:
            cursor.execute('''
                INSERT INTO equipment (name, category, brand, model, status, location)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', equipment)

    # Insert sample workouts
    cursor.execute('SELECT COUNT(*) FROM workouts')
    if cursor.fetchone()[0] == 0:
        workouts = [
            ('Push-ups', 'Bodyweight exercise for chest and arms', 'strength', 'beginner', 15, 50, 'Lie face down, push body up and down using arms', 'None'),
            ('Treadmill Running', 'Cardiovascular exercise on treadmill', 'cardio', 'beginner', 30, 300, 'Start slow, increase speed gradually, maintain steady pace', 'Treadmill'),
            ('Bench Press', 'Chest strengthening exercise with barbell', 'strength', 'intermediate', 45, 200, 'Lie on bench, press barbell up and down', 'Barbell, Bench'),
            ('Squats', 'Lower body compound exercise', 'strength', 'beginner', 20, 100, 'Stand with feet apart, lower body as if sitting, return to standing', 'None or Weights'),
            ('Plank', 'Core strengthening exercise', 'strength', 'beginner', 10, 30, 'Hold body straight in push-up position', 'None')
        ]
        for workout in workouts:
            cursor.execute('''
                INSERT INTO workouts (name, description, category, difficulty_level, duration_minutes, calories_burned, instructions, equipment_needed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', workout)

    # Insert sample announcement
    cursor.execute('SELECT COUNT(*) FROM announcements')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id FROM users WHERE role = "admin" LIMIT 1')
        admin_id = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO announcements (title, content, announcement_type, target_audience, is_public, is_active, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Welcome to FitZone Gym!',
            'Welcome to our fitness center. We provide expert trainers, modern equipment, and personalized fitness plans to help you achieve your goals.',
            'general',
            'all',
            1,
            1,
            admin_id
        ))