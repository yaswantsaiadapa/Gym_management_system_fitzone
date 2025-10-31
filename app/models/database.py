import sqlite3
from datetime import date, datetime, timedelta
from flask import current_app
from flask_bcrypt import Bcrypt
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

def _get_bcrypt():
    """Return a Bcrypt instance bound to the current app (call inside app context)."""
    return Bcrypt(current_app)

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
            -- reset_token TEXT,
            -- reset_token_expires TEXT
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
    # Create Bcrypt instance (must be called inside app context)
    bcrypt = _get_bcrypt()

    # Create default admin user
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    if cursor.fetchone()[0] == 0:
        admin_password = bcrypt.generate_password_hash('admin123')
        if isinstance(admin_password, bytes):
            admin_password = admin_password.decode('utf-8')
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

    # Create sample trainers (you provided 2 trainer users)
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "trainer"')
    if cursor.fetchone()[0] == 0:
        trainer_users = [
            ('Anusha_t', 'venkataraghupathisaimannava@gmail.com', 'trainer123', 'Anusha Reddy', '+919000000011'),
            ('Arjun_t', 'mannava23bcs96@iiitkottayam.ac.in', 'trainer123', 'Arjun Patel', '+919000000012')
        ]
        for trainer in trainer_users:
            password_hash = bcrypt.generate_password_hash(trainer[2])
            if isinstance(password_hash, bytes):
                password_hash = password_hash.decode('utf-8')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, full_name, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (trainer[0], trainer[1], password_hash, 'trainer', trainer[3], trainer[4]))

        # Create trainer profiles using the phone saved in users (keeps things consistent)
        cursor.execute('SELECT id, full_name FROM users WHERE role = "trainer"')
        trainer_users = cursor.fetchall()
        for user in trainer_users:
            user_id = user[0]
            full_name = user[1]
            # read phone from users table so it's always in sync
            phone_row = cursor.execute('SELECT phone FROM users WHERE id = ?', (user_id,)).fetchone()
            phone = phone_row[0] if phone_row else None

            if 'Anusha' in full_name:
                specialization = 'Yoga, Flexibility, Cardio'
                exp = 6
                cert = 'Certified Yoga Instructor'
                salary = 35000.00
                hours = '6:00 AM - 2:00 PM'
                bio = 'Yoga specialist helping members with mobility and stress relief.'
            elif 'Arjun' in full_name:
                specialization = 'CrossFit, Functional Training'
                exp = 5
                cert = 'CrossFit Level 1'
                salary = 32000.00
                hours = '9:00 AM - 5:00 PM'
                bio = 'CrossFit coach focusing on high-intensity functional workouts.'
            else:
                specialization = 'General Fitness'
                exp = 4
                cert = 'Certified Fitness Trainer'
                salary = 30000.00
                hours = '9:00 AM - 5:00 PM'
                bio = 'Passionate trainer.'

            cursor.execute('''
                INSERT INTO trainers (user_id, phone, specialization, experience_years, certification, salary, working_hours, bio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, phone, specialization, exp, cert, salary, hours, bio))

    # Create sample members (you provided 4 members)
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "member"')
    if cursor.fetchone()[0] == 0:
        member_users = [
            ('sai', 'yaswantsaiadapa@gmail.com', 'member123', 'Raghu Sai', '+919000000020'),
            ('Raju', 'yaswantsai2006@gmail.com', 'member123', 'Ram Raju', '+919000000021'),
            ('Sunil', 'm.v.raghupathisai@gmail.com', 'member123', 'Sunil Kumar', '+919000000010'),
            ('ashok', 'adapa23bcs30@iiitkottayam.ac.in', 'member123', 'Ashok Kumar', '+919000000022')
        ]

        for member in member_users:
            password_hash = bcrypt.generate_password_hash(member[2])
            if isinstance(password_hash, bytes):
                password_hash = password_hash.decode('utf-8')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, full_name, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (member[0], member[1], password_hash, 'member', member[3], member[4]))

        # Fetch available plans and trainers safely
        cursor.execute('SELECT id FROM membership_plans')
        plan_ids = [row[0] for row in cursor.fetchall()]
        cursor.execute('SELECT id FROM trainers ORDER BY id')  # deterministic ordering
        trainer_ids = [row[0] for row in cursor.fetchall()]

        if plan_ids and trainer_ids:
            cursor.execute('SELECT id, full_name FROM users WHERE role = "member" ORDER BY id')
            member_users = cursor.fetchall()
            for i, user in enumerate(member_users):
                # Assign first 3 members to trainer_ids[0], last member to trainer_ids[1]
                assigned_trainer = trainer_ids[0] if i < 3 else (trainer_ids[1] if len(trainer_ids) > 1 else trainer_ids[0])

                # sensible per-member defaults based on name
                full_name = user[1]
                if 'Raghu' in full_name or 'Sai' in full_name:
                    phone = '+919000000020'
                    weight = 78.0
                    height = 175.0
                elif 'Ram' in full_name or 'Raju' in full_name:
                    phone = '+919000000021'
                    weight = 75.0
                    height = 172.0
                elif 'Sunil' in full_name:
                    phone = '+919000000010'
                    weight = 85.0
                    height = 180.0
                else:
                    phone = '+919000000022'
                    weight = 70.0
                    height = 168.0

                today = date.today()
                cursor.execute('''
                    INSERT INTO members (
                        user_id, membership_plan_id, phone, weight, height,
                        membership_start_date, membership_end_date, trainer_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user[0],
                    plan_ids[i % len(plan_ids)],
                    phone,
                    weight,
                    height,
                    today,  # placeholder, will be adjusted by payments seeding
                    today.replace(year=today.year + 1),
                    assigned_trainer
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
        admin_row = cursor.fetchone()
        admin_id = admin_row[0] if admin_row else None
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

    # Payments — insert sample payments AND activate corresponding members
    cursor.execute('SELECT COUNT(*) FROM payments')
    if cursor.fetchone()[0] == 0:
        # Fetch members with their plan_id and user_id so we can activate user rows as well
        cursor.execute('SELECT id, membership_plan_id, user_id FROM members')
        members = cursor.fetchall()

        # helper to add months to a date (handles month rollover)
        import calendar
        def _add_months(sourcedate, months):
            month = sourcedate.month - 1 + int(months)
            year = sourcedate.year + month // 12
            month = month % 12 + 1
            day = min(sourcedate.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        for i, m in enumerate(members, start=1):
            member_id = m[0]
            membership_plan_id = m[1]
            user_id = m[2]

            # Fetch plan price and duration safely
            cur_plan = cursor.execute('SELECT price, duration_months FROM membership_plans WHERE id = ?', (membership_plan_id,)).fetchone()
            plan_price = cur_plan[0] if cur_plan and cur_plan[0] is not None else 0.0
            try:
                duration_months = int(cur_plan[1]) if cur_plan and cur_plan[1] is not None else 1
            except Exception:
                duration_months = 1

            invoice_number = f"INV{str(i).zfill(4)}"
            transaction_id = f"TXN{str(i).zfill(6)}"

            cursor.execute('''
                INSERT INTO payments (
                    member_id, membership_plan_id, amount, payment_method, payment_status,
                    transaction_id, payment_date, due_date, notes, invoice_number,
                    reminder_sent, reminder_sent_at, cancelled_processed
                ) VALUES (?, ?, ?, ?, ?, ?, DATE('now'), DATE('now','+30 day'), ?, ?, 0, NULL, 0)
            ''', (
                member_id,
                membership_plan_id,
                plan_price,
                'cash',
                'completed',
                transaction_id,
                'Membership fee payment',
                invoice_number
            ))

            start_dt = date.today()
            end_dt = _add_months(start_dt, duration_months)

            cursor.execute("""
                UPDATE members
                SET membership_start_date = ?, membership_end_date = ?, status = ?
                WHERE id = ?
            """, (start_dt.isoformat(), end_dt.isoformat(), 'active', member_id))

            if user_id:
                cursor.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))

    # --- Add sample diet plans & meals for each member ---
    cursor.execute('SELECT COUNT(*) FROM diet_plans')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id, trainer_id FROM members')
        member_rows = cursor.fetchall()

        for idx, m in enumerate(member_rows, start=1):
            member_id = m[0]
            assigned_trainer_id = m[1]  # use each member's trainer assignment
            name = 'Weight Loss Plan' if idx == 1 else ('Maintenance Plan' if idx == 2 else ('Muscle Gain Plan' if idx == 3 else 'Balanced Plan'))
            total_cal = 1800 if idx == 1 else (2200 if idx == 2 else (3000 if idx == 3 else 2400))
            start_date = date.today()
            end_date = start_date + timedelta(days=90)

            cursor.execute('''
                INSERT INTO diet_plans (member_id, trainer_id, name, description, total_calories, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (member_id, assigned_trainer_id, name, f"{name} created by trainer", total_cal, start_date.isoformat(), end_date.isoformat()))

            diet_plan_id = cursor.lastrowid

            # Add typical meals for Indian context
            if idx == 1:  # weight loss
                meals = [
                    ('breakfast', 'Poha with vegetables', 'Poha, peas, carrots, peanuts', 350, 10.0, 55.0, 8.0, 'Cook poha with minimal oil and vegetables'),
                    ('lunch', 'Grilled chicken + salad', 'Chicken breast, salad greens, tomato, cucumber', 500, 40.0, 20.0, 15.0, 'Grill chicken with spices, serve with salad'),
                    ('dinner', 'Mixed vegetable sabzi + chapati', 'Mixed veg, 1 chapati', 450, 12.0, 60.0, 10.0, 'Lightly sauté vegetables and serve with chapati'),
                    ('snack', 'Buttermilk and fruit', 'Curd, water, seasonal fruit', 200, 6.0, 30.0, 5.0, 'Buttermilk without added sugar')
                ]
            elif idx == 2:  # maintenance
                meals = [
                    ('breakfast', 'Upma with nuts', 'Semolina, peanuts, vegetables', 400, 9.0, 60.0, 10.0, 'Cook upma with vegetables and a few nuts'),
                    ('lunch', 'Paneer bhurji + brown rice', 'Paneer, spices, brown rice', 650, 30.0, 70.0, 20.0, 'Light cooking with minimal oil'),
                    ('dinner', 'Dal tadka + roti', 'Toor dal, spices, 2 rotis', 500, 20.0, 65.0, 10.0, 'Cook dal with tempering'),
                    ('snack', 'Roasted chana', 'Chana', 150, 8.0, 20.0, 3.0, 'Roast lightly')
                ]
            elif idx == 3:  # muscle gain
                meals = [
                    ('breakfast', 'Egg omelette + oats', 'Eggs, oats', 600, 35.0, 70.0, 18.0, 'Cook omelette and serve with oats'),
                    ('lunch', 'Chicken biryani (protein rich portion)', 'Chicken, rice, spices', 900, 50.0, 90.0, 30.0, 'Prefer lean portions'),
                    ('dinner', 'Fish curry + rice', 'Fish, rice, coconut milk', 700, 45.0, 80.0, 25.0, 'Cook fish with light oil'),
                    ('snack', 'Peanut butter sandwich', 'Peanut butter, whole wheat bread', 300, 12.0, 32.0, 15.0, 'Use natural peanut butter')
                ]
            else:  # 4th member balanced
                meals = [
                    ('breakfast', 'Vegetable idli', 'Idli, vegetables, chutney', 350, 10.0, 60.0, 7.0, 'Steam idlis and serve with chutney'),
                    ('lunch', 'Grilled fish + salad', 'Fish, salad', 650, 45.0, 40.0, 20.0, 'Grill fish with spices'),
                    ('dinner', 'Mixed dal + roti', 'Dal, 2 rotis', 500, 22.0, 65.0, 10.0, 'Cook dal with tempering'),
                    ('snack', 'Fruit bowl', 'Seasonal fruits', 200, 3.0, 50.0, 1.0, 'Fresh fruit bowl')
                ]

            for meal in meals:
                cursor.execute('''
                    INSERT INTO diet_plan_meals (diet_plan_id, meal_type, meal_name, ingredients, calories, protein, carbs, fat, instructions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (diet_plan_id, meal[0], meal[1], meal[2], meal[3], meal[4], meal[5], meal[6], meal[7]))

    # --- Add member workout plans and plan details ---
    cursor.execute('SELECT COUNT(*) FROM member_workout_plans')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id FROM members')
        member_rows = [r[0] for r in cursor.fetchall()]
        cursor.execute('SELECT id, name FROM workouts')
        workout_rows = cursor.fetchall()

        for i, member_id in enumerate(member_rows):
            # use the trainer actually assigned to this member
            trainer_row = cursor.execute('SELECT trainer_id FROM members WHERE id = ?', (member_id,)).fetchone()
            trainer_id = trainer_row[0] if trainer_row else None

            plan_name = 'Beginner Strength Plan' if i == 0 else ('Cardio & Mobility' if i == 1 else ('Hypertrophy Plan' if i == 2 else 'Balanced Plan'))
            start_date = date.today()
            end_date = start_date + timedelta(days=60)

            cursor.execute('''
                INSERT INTO member_workout_plans (member_id, trainer_id, name, description, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (member_id, trainer_id, plan_name, f"{plan_name} for member {member_id}", start_date.isoformat(), end_date.isoformat()))

            plan_id = cursor.lastrowid

            # Assign 3 workouts for each plan (use existing workout ids)
            chosen_workouts = [workout_rows[0][0], workout_rows[2][0], workout_rows[3][0]] if len(workout_rows) >= 4 else [w[0] for w in workout_rows]
            days = [1, 3, 5]
            for wk, day in zip(chosen_workouts, days):
                cursor.execute('''
                    INSERT INTO workout_plan_details (plan_id, workout_id, day_of_week, sets, reps, weight, rest_seconds, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (plan_id, wk, day, 3, 10, 20.0, 60, 'Keep form strict'))

    # --- Add sample attendance and progress entries ---
    cursor.execute('SELECT COUNT(*) FROM attendance')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id, trainer_id FROM members')
        members_with_trainer = cursor.fetchall()
        today = date.today()
        for i, (mem_id, mem_trainer_id) in enumerate(members_with_trainer):
            check_in = datetime.now().isoformat()
            check_out = (datetime.now() + timedelta(hours=1)).isoformat()
            time_slot = 'Morning' if i == 0 else ('Evening' if i == 1 else ('Afternoon' if i == 2 else 'Evening'))
            cursor.execute('''
                INSERT INTO attendance (member_id, trainer_id, check_in_time, check_out_time, date, time_slot, workout_type, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (mem_id, mem_trainer_id, check_in, check_out, today.isoformat(), time_slot, 'strength', 'Good session', 'present'))

    cursor.execute('SELECT COUNT(*) FROM member_progress')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id, trainer_id FROM members')
        members_with_trainer = cursor.fetchall()
        rec_date = date.today() - timedelta(days=7)
        for i, (mem_id, mem_trainer_id) in enumerate(members_with_trainer):
            # simple sample metrics
            if i == 0:
                weight = 78.0
                body_fat = 18.5
                height_m = 1.75
            elif i == 1:
                weight = 75.0
                body_fat = 20.0
                height_m = 1.72
            elif i == 2:
                weight = 85.0
                body_fat = 20.0
                height_m = 1.80
            else:
                weight = 70.0
                body_fat = 22.0
                height_m = 1.68

            bmi = round((weight / (height_m ** 2)), 2)
            cursor.execute('''
                INSERT INTO member_progress (member_id, recorded_date, weight, body_fat_percentage, muscle_mass, bmi, chest, waist, hips, bicep, thigh, notes, recorded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (mem_id, rec_date.isoformat(), weight, body_fat, 30.0, bmi, 95.0, 82.0, 96.0, 32.0, 55.0, 'Initial recording', mem_trainer_id))

    # All done seeding
    return
