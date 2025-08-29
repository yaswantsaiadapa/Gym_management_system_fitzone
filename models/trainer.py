from .database import execute_query
from flask import current_app

class Trainer:
    def __init__(self, id=None, name=None, phone=None, email=None, 
                 salary=None, working_hours=None, status='active'):
        self.id = id
        self.name = name
        self.phone = phone
        self.email = email
        self.salary = salary
        self.working_hours = working_hours
        self.status = status
    
    @classmethod
    def get_all_active(cls):
        """Get all active trainers"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM trainers WHERE status = "active"'
        results = execute_query(query, (), db_path, fetch=True)
        
        trainers = []
        for row in results:
            trainer = cls(
                id=row[0], name=row[1], phone=row[2], email=row[3],
                salary=row[4], working_hours=row[5], status=row[6]
            )
            trainers.append(trainer)
        return trainers
    
    @classmethod
    def get_by_id(cls, trainer_id):
        """Get trainer by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM trainers WHERE id = ?'
        result = execute_query(query, (trainer_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0], name=row[1], phone=row[2], email=row[3],
                salary=row[4], working_hours=row[5], status=row[6]
            )
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
            id=row[0], name=row[1], phone=row[2], email=row[3],
            salary=row[4], working_hours=row[5], status=row[6]
        ) for row in results] if results else []

    @classmethod
    def get_all_with_details(cls):
        """Get all trainers with user details"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT t.id, u.username, u.email, t.phone, t.specialization, 
                t.experience_years, t.certification, t.salary, 
                t.working_hours, t.bio, t.status
            FROM trainers t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.id DESC
        '''
        results = execute_query(query, (), db_path, fetch=True)

        trainers = []
        for row in results:
            trainer = cls(
                id=row[0],
                name=row[1],       # comes from users table
                email=row[2],      # comes from users table
                phone=row[3],
                salary=row[7],
                working_hours=row[8],
                status=row[10]
            )
            trainers.append(trainer)
        return trainers



        
    def save(self):
        """Save trainer to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if self.id:
            # Update existing trainer
            query = '''UPDATE trainers SET name = ?, phone = ?, email = ?, 
                      salary = ?, working_hours = ?, status = ? 
                      WHERE id = ?'''
            params = (self.name, self.phone, self.email, self.salary, 
                     self.working_hours, self.status, self.id)
        else:
            # Create new trainer
            query = '''INSERT INTO trainers (name, phone, email, salary, 
                      working_hours, status) VALUES (?, ?, ?, ?, ?, ?)'''
            params = (self.name, self.phone, self.email, self.salary, 
                     self.working_hours, self.status)
        
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