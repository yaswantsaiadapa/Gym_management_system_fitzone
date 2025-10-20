from .database import execute_query
from flask import current_app

def delete(self):
    """
    Soft-delete trainer:
    - Deactivate underlying user account (users.is_active = 0)
    - Mark trainer.status = 'removed' (or 'inactive')
    """
    from models.database import execute_query
    db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

    try:
        execute_query(
            "UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (self.user_id,),
            db_path
        )

        execute_query(
            "UPDATE trainers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            ("removed", self.id),
            db_path
        )

        # Optional set removed_at if column exists
        try:
            execute_query(
                "UPDATE trainers SET removed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (self.id,),
                db_path
            )
        except Exception:
            pass

        return True
    except Exception:
        current_app.logger.exception("Failed to soft-delete trainer %s", getattr(self, 'id', None))
        return False


def hard_delete(self):
    """
    Permanently delete trainer and related records.
    WARNING: destructive. Back up DB before use.
    """
    from models.database import execute_query
    db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

    try:
        # Delete trainer-related tables (update names according to your schema)
        for q in [
            ("DELETE FROM workouts WHERE trainer_id = ?", (self.id,)),
            ("DELETE FROM trainer_schedules WHERE trainer_id = ?", (self.id,)),
            ("DELETE FROM trainer_assignments WHERE trainer_id = ?", (self.id,)),
        ]:
            try:
                execute_query(q[0], q[1], db_path)
            except Exception:
                current_app.logger.exception("Failed to execute cleanup query for trainer %s: %s", self.id, q[0])

        # Delete trainer row and user row
        execute_query("DELETE FROM trainers WHERE id = ?", (self.id,), db_path)
        execute_query("DELETE FROM users WHERE id = ?", (self.user_id,), db_path)

        return True
    except Exception:
        current_app.logger.exception("Failed to hard-delete trainer %s", getattr(self, 'id', None))
        return False
class Trainer:
    def __init__(self, id=None, user_id=None, phone=None, specialization=None,
             experience_years=None, certification=None, salary=None,
             working_hours=None, bio=None, status='active',
             created_at=None, updated_at=None):
        self.id = id
        self.user_id = user_id
        self.phone = phone
        self.specialization = specialization
        self.experience_years = experience_years
        self.certification = certification
        self.salary = salary
        self.working_hours = working_hours
        self.bio = bio
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def get_all_active(cls):
        """Get all active trainers"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM trainers WHERE status = "active"'
        results = execute_query(query, (), db_path, fetch=True)
        
        trainers = []
        for row in results:
            trainer = cls(
                id=row[0],
                user_id=row[1],
                phone=row[2],
                specialization=row[3],
                experience_years=row[4],
                certification=row[5],
                salary=row[6],
                working_hours=row[7],
                bio=row[8],
                status=row[9],
                created_at=row[10],
                updated_at=row[11]
            )
            trainers.append(trainer)
        return trainers

    
    @classmethod
    def get_by_id(cls, trainer_id):
        """Get trainer by ID (with full_name from users table)"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = """
            SELECT t.id, t.user_id, t.phone, t.specialization, t.experience_years,
                t.certification, t.salary, t.working_hours, t.bio, t.status,
                t.created_at, t.updated_at, u.full_name
            FROM trainers t
            LEFT JOIN users u ON t.user_id = u.id
            WHERE t.id = ?
        """
        result = execute_query(query, (trainer_id,), db_path, fetch=True)

        if result:
            row = result[0]
            trainer = cls(
                id=row[0],
                user_id=row[1],
                phone=row[2],
                specialization=row[3],
                experience_years=row[4],
                certification=row[5],
                salary=row[6],
                working_hours=row[7],
                bio=row[8],
                status=row[9],
                created_at=row[10],
                updated_at=row[11]
            )
            trainer.full_name = row[12]  # ✅ add full_name from users
            return trainer
        return None


    
    @classmethod
    def get_count_active(cls):
        """Get count of active trainers"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT COUNT(*) FROM trainers WHERE status = "active"'
        result = execute_query(query, (), db_path, fetch=True)
        return result[0][0] if result else 0
    
    @classmethod
    def get_available_for_slot(cls, time_slot, check_date=None):
        """Return trainers who are free in a given time slot and date"""
        from datetime import date
        if check_date is None:
            check_date = date.today()

        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

        # Trainers who already have a session at that slot/date
        query = '''
            SELECT trainer_id 
            FROM attendance 
            WHERE date = ? AND time_slot = ?
        '''
        busy = execute_query(query, (check_date, time_slot), db_path, fetch=True)
        busy_ids = [row[0] for row in busy] if busy else []

        # Now fetch active trainers excluding busy ones
        if busy_ids:
            placeholders = ','.join('?' * len(busy_ids))
            query = f'SELECT * FROM trainers WHERE status = "active" AND id NOT IN ({placeholders})'
            results = execute_query(query, busy_ids, db_path, fetch=True)
        else:
            query = 'SELECT * FROM trainers WHERE status = "active"'
            results = execute_query(query, db_path=db_path, fetch=True)

        return [cls(
            id=row[0],
            user_id=row[1],
            phone=row[2],
            specialization=row[3],
            experience_years=row[4],
            certification=row[5],
            salary=row[6],
            working_hours=row[7],
            bio=row[8],
            status=row[9],
            created_at=row[10],
            updated_at=row[11]
        ) for row in results] if results else []

    @classmethod
    def get_by_user_id(cls, user_id):
        """Get trainer by linked user_id"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM trainers WHERE user_id = ?'
        result = execute_query(query, (user_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0],
                user_id=row[1],
                phone=row[2],
                specialization=row[3],
                experience_years=row[4],
                certification=row[5],
                salary=row[6],
                working_hours=row[7],
                bio=row[8],
                status=row[9],
                created_at=row[10],
                updated_at=row[11]
            )
        return None

    @classmethod
    def get_all_with_details(cls):
        """Get all trainers with user details"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT t.id, t.user_id, u.username, u.email, u.full_name, 
                t.phone, t.specialization, t.experience_years, 
                t.certification, t.salary, t.working_hours, 
                t.bio, t.status, t.created_at, t.updated_at
            FROM trainers t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.id DESC
        '''
        results = execute_query(query, (), db_path, fetch=True)

        trainers = []
        for row in results:
            trainer = cls(
                id=row[0],
                user_id=row[1],
                phone=row[5],
                specialization=row[6],
                experience_years=row[7],
                certification=row[8],
                salary=row[9],
                working_hours=row[10],
                bio=row[11],
                status=row[12],
                created_at=row[13],
                updated_at=row[14]
            )
            # attach user details as extra attributes
            trainer.username = row[2]
            trainer.email = row[3]
            trainer.full_name = row[4]

            trainers.append(trainer)
        return trainers


        
    def save(self):
        """Save trainer to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

        if self.id:
            # Update existing trainer
            query = '''
                UPDATE trainers 
                SET user_id = ?, phone = ?, specialization = ?, 
                    experience_years = ?, certification = ?, salary = ?, 
                    working_hours = ?, bio = ?, status = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''
            params = (self.user_id, self.phone, self.specialization, 
                    self.experience_years, self.certification, self.salary,
                    self.working_hours, self.bio, self.status, self.id)
        else:
            # Create new trainer
            query = '''
                INSERT INTO trainers 
                (user_id, phone, specialization, experience_years, certification, 
                salary, working_hours, bio, status, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            '''
            params = (self.user_id, self.phone, self.specialization, 
                    self.experience_years, self.certification, self.salary,
                    self.working_hours, self.bio, self.status)

        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id

    def deactivate(self):
        """Deactivate trainer"""
        self.status = 'inactive'
        return self.save()
    
    def get_todays_schedule(self):
        """Get trainer's schedule for today"""
        from datetime import date
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT a.time_slot, m.name as member_name, a.status
            FROM attendance a
            JOIN members m ON a.member_id = m.id
            WHERE a.trainer_id = ? AND a.date = ?
            ORDER BY a.time_slot
        '''
        return execute_query(query, (self.id, date.today()), db_path, fetch=True)