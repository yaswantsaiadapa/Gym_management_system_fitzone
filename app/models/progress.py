from flask import current_app
from app.models.database import execute_query


from datetime import datetime, date

class Progress:
    def __init__(self, id=None, member_id=None, recorded_date=None, weight=None,
                 body_fat_percentage=None, muscle_mass=None, bmi=None,
                 chest=None, waist=None, hips=None, bicep=None, thigh=None,
                 notes=None, photo_path=None, recorded_by=None):
        self.id = id
        self.member_id = member_id
        self.recorded_date = self._to_date(recorded_date)
        self.weight = weight
        self.body_fat_percentage = body_fat_percentage
        self.muscle_mass = muscle_mass
        self.bmi = bmi
        self.chest = chest
        self.waist = waist
        self.hips = hips
        self.bicep = bicep
        self.thigh = thigh
        self.notes = notes
        self.photo_path = photo_path
        self.recorded_by = recorded_by
        self.recorded_by_name = None
        self.member_name = None

    @staticmethod
    def _to_date(value):
        """Convert string from DB to date object if needed"""
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
        return value

    @classmethod
    def get_by_id(cls, progress_id):
        """Get a single progress record by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT mp.*, u.full_name as recorded_by_name 
                   FROM member_progress mp
                   LEFT JOIN trainers t ON mp.recorded_by = t.id
                   LEFT JOIN users u ON t.user_id = u.id
                   WHERE mp.id = ?'''
        row = execute_query(query, (progress_id,), db_path, fetch=True)
        if row:
            row = row[0]
            progress = cls(
                id=row[0], member_id=row[1], recorded_date=row[2], weight=row[3],
                body_fat_percentage=row[4], muscle_mass=row[5], bmi=row[6],
                chest=row[7], waist=row[8], hips=row[9], bicep=row[10],
                thigh=row[11], notes=row[12], photo_path=row[13], recorded_by=row[14]
            )
            progress.recorded_by_name = row[15] if len(row) > 15 else None
            return progress
        return None

    @classmethod
    def get_member_progress(cls, member_id, limit=None):
        """Get progress records for a member"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT mp.*, u.full_name as recorded_by_name 
                   FROM member_progress mp
                   LEFT JOIN trainers t ON mp.recorded_by = t.id
                   LEFT JOIN users u ON t.user_id = u.id
                   WHERE mp.member_id = ? ORDER BY mp.recorded_date DESC'''
        if limit:
            query += f' LIMIT {limit}'

        results = execute_query(query, (member_id,), db_path, fetch=True)
        
        progress_records = []
        for row in results:
            progress = cls(
                id=row[0], member_id=row[1], recorded_date=row[2], weight=row[3],
                body_fat_percentage=row[4], muscle_mass=row[5], bmi=row[6],
                chest=row[7], waist=row[8], hips=row[9], bicep=row[10],
                thigh=row[11], notes=row[12], photo_path=row[13], recorded_by=row[14]
            )
            progress.recorded_by_name = row[15] if len(row) > 15 else None
            progress_records.append(progress)
        return progress_records

    @classmethod
    def get_trainer_client_progress(cls, trainer_id, limit=None):
        """Get recent progress records for all clients of a trainer"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT mp.*, u.full_name as member_name
            FROM member_progress mp
            JOIN members m ON mp.member_id = m.id
            JOIN users u ON m.user_id = u.id
            WHERE m.trainer_id = ?
            ORDER BY mp.recorded_date DESC
        '''
        if limit:
            query += f' LIMIT {limit}'
        
        results = execute_query(query, (trainer_id,), db_path, fetch=True)
        
        progress_records = []
        for row in results:
            progress = cls(
                id=row[0], member_id=row[1], recorded_date=row[2], weight=row[3],
                body_fat_percentage=row[4], muscle_mass=row[5], bmi=row[6],
                chest=row[7], waist=row[8], hips=row[9], bicep=row[10],
                thigh=row[11], notes=row[12], photo_path=row[13], recorded_by=row[14]
            )
            progress.member_name = row[-1] if len(row) > 15 else None
            progress_records.append(progress)
        return progress_records

    def save(self):
        """Save progress record to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if self.id:
            # Update existing progress record
            query = '''UPDATE member_progress SET member_id = ?, recorded_date = ?,
                      weight = ?, body_fat_percentage = ?, muscle_mass = ?, bmi = ?,
                      chest = ?, waist = ?, hips = ?, bicep = ?, thigh = ?,
                      notes = ?, photo_path = ?, recorded_by = ? WHERE id = ?'''
            params = (self.member_id, self.recorded_date, self.weight,
                     self.body_fat_percentage, self.muscle_mass, self.bmi,
                     self.chest, self.waist, self.hips, self.bicep, self.thigh,
                     self.notes, self.photo_path, self.recorded_by, self.id)
        else:
            # Create new progress record
            query = '''INSERT INTO member_progress (member_id, recorded_date, weight,
                      body_fat_percentage, muscle_mass, bmi, chest, waist, hips,
                      bicep, thigh, notes, photo_path, recorded_by)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (self.member_id, self.recorded_date, self.weight,
                     self.body_fat_percentage, self.muscle_mass, self.bmi,
                     self.chest, self.waist, self.hips, self.bicep, self.thigh,
                     self.notes, self.photo_path, self.recorded_by)
        
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id

    @classmethod
    def delete(cls, progress_id):
        """Delete a progress record (hard delete)"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = "DELETE FROM member_progress WHERE id = ?"
        execute_query(query, (progress_id,), db_path)
