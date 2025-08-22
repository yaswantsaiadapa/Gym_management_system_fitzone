from .database import execute_query
from flask import current_app
from datetime import date

class Attendance:
    def __init__(self, id=None, member_id=None, trainer_id=None, date=None, 
                 time_slot=None, status='present'):
        self.id = id
        self.member_id = member_id
        self.trainer_id = trainer_id
        self.date = date
        self.time_slot = time_slot
        self.status = status
    
    @classmethod
    def get_todays_attendance(cls):
        """Get today's attendance count"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT COUNT(*) FROM attendance WHERE date = ?'
        result = execute_query(query, (date.today(),), db_path, fetch=True)
        return result[0][0] if result else 0
    
    @classmethod
    def get_attendance_by_date(cls, attendance_date):
        """Get all attendance records for a specific date"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT a.*, m.name as member_name, t.name as trainer_name
            FROM attendance a
            JOIN members m ON a.member_id = m.id
            JOIN trainers t ON a.trainer_id = t.id
            WHERE a.date = ?
            ORDER BY a.time_slot
        '''
        results = execute_query(query, (attendance_date,), db_path, fetch=True)
        
        attendance_list = []
        for row in results:
            attendance = cls(
                id=row[0], member_id=row[1], trainer_id=row[2], 
                date=row[3], time_slot=row[4], status=row[5]
            )
            attendance.member_name = row[6]
            attendance.trainer_name = row[7]
            attendance_list.append(attendance)
        return attendance_list
    
    @classmethod
    def get_member_attendance(cls, member_id, limit=10):
        """Get recent attendance records for a member"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT a.*, t.name as trainer_name
            FROM attendance a
            JOIN trainers t ON a.trainer_id = t.id
            WHERE a.member_id = ?
            ORDER BY a.date DESC, a.time_slot DESC
            LIMIT ?
        '''
        results = execute_query(query, (member_id, limit), db_path, fetch=True)
        
        attendance_list = []
        for row in results:
            attendance = cls(
                id=row[0], member_id=row[1], trainer_id=row[2], 
                date=row[3], time_slot=row[4], status=row[5]
            )
            attendance.trainer_name = row[6]
            attendance_list.append(attendance)
        return attendance_list
    
    @classmethod
    def get_trainer_schedule(cls, trainer_id, attendance_date=None):
        """Get trainer's schedule for a specific date"""
        if attendance_date is None:
            attendance_date = date.today()
        
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT a.*, m.name as member_name
            FROM attendance a
            JOIN members m ON a.member_id = m.id
            WHERE a.trainer_id = ? AND a.date = ?
            ORDER BY a.time_slot
        '''
        results = execute_query(query, (trainer_id, attendance_date), db_path, fetch=True)
        
        schedule_list = []
        for row in results:
            attendance = cls(
                id=row[0], member_id=row[1], trainer_id=row[2], 
                date=row[3], time_slot=row[4], status=row[5]
            )
            attendance.member_name = row[6]
            schedule_list.append(attendance)
        return schedule_list
    
    @classmethod
    def check_slot_availability(cls, trainer_id, time_slot, attendance_date=None):
        """Check if a trainer is available for a specific time slot"""
        if attendance_date is None:
            attendance_date = date.today()
        
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT COUNT(*) FROM attendance 
            WHERE trainer_id = ? AND time_slot = ? AND date = ?
        '''
        result = execute_query(query, (trainer_id, time_slot, attendance_date), db_path, fetch=True)
        return result[0][0] == 0 if result else True
    
    def save(self):
        """Save attendance record to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if self.id:
            # Update existing attendance
            query = '''UPDATE attendance SET member_id = ?, trainer_id = ?, 
                      date = ?, time_slot = ?, status = ? WHERE id = ?'''
            params = (self.member_id, self.trainer_id, self.date, 
                     self.time_slot, self.status, self.id)
        else:
            # Create new attendance record
            query = '''INSERT INTO attendance (member_id, trainer_id, date, 
                      time_slot, status) VALUES (?, ?, ?, ?, ?)'''
            params = (self.member_id, self.trainer_id, self.date, 
                     self.time_slot, self.status)
        
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
    
    def mark_absent(self):
        """Mark attendance as absent"""
        self.status = 'absent'
        return self.save()
    
    def mark_present(self):
        """Mark attendance as present"""
        self.status = 'present'
        return self.save()
    
    @classmethod
    def get_monthly_stats(cls, year, month):
        """Get attendance statistics for a specific month"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(DISTINCT member_id) as unique_members,
                COUNT(DISTINCT trainer_id) as active_trainers
            FROM attendance 
            WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
        '''
        result = execute_query(query, (str(year), f"{month:02d}"), db_path, fetch=True)
        
        if result:
            row = result[0]
            return {
                'total_sessions': row[0],
                'unique_members': row[1],
                'active_trainers': row[2]
            }
        return {'total_sessions': 0, 'unique_members': 0, 'active_trainers': 0}