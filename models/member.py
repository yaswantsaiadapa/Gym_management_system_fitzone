from .database import execute_query
from flask import current_app
from datetime import date, datetime

class Member:
    def __init__(self, id=None, name=None, phone=None, email=None, weight=None, 
                 height=None, payment_status='pending', membership_date=None, 
                 expiry_date=None, status='active'):
        self.id = id
        self.name = name
        self.phone = phone
        self.email = email
        self.weight = weight
        self.height = height
        self.payment_status = payment_status
        self.membership_date = membership_date
        self.expiry_date = expiry_date
        self.status = status
    
    @classmethod
    def get_all_active(cls):
        """Get all active members"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM members WHERE status = "active"'
        results = execute_query(query, (), db_path, fetch=True)
        
        members = []
        for row in results:
            member = cls(
                id=row[0], name=row[1], phone=row[2], email=row[3],
                weight=row[4], height=row[5], payment_status=row[6],
                membership_date=row[7], expiry_date=row[8], status=row[9]
            )
            members.append(member)
        return members
    
    @classmethod
    def get_by_id(cls, member_id):
        """Get member by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM members WHERE id = ?'
        result = execute_query(query, (member_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0], name=row[1], phone=row[2], email=row[3],
                weight=row[4], height=row[5], payment_status=row[6],
                membership_date=row[7], expiry_date=row[8], status=row[9]
            )
        return None
    
    @classmethod
    def get_count_active(cls):
        """Get count of active members"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT COUNT(*) FROM members WHERE status = "active"'
        result = execute_query(query, (), db_path, fetch=True)
        return result[0][0] if result else 0
    
    def save(self):
        """Save member to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if self.id:
            # Update existing member
            query = '''UPDATE members SET name = ?, phone = ?, email = ?, 
                      weight = ?, height = ?, payment_status = ?, 
                      membership_date = ?, expiry_date = ?, status = ? 
                      WHERE id = ?'''
            params = (self.name, self.phone, self.email, self.weight, 
                     self.height, self.payment_status, self.membership_date, 
                     self.expiry_date, self.status, self.id)
        else:
            # Create new member
            query = '''INSERT INTO members (name, phone, email, weight, height, 
                      payment_status, membership_date, expiry_date, status)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (self.name, self.phone, self.email, self.weight, 
                     self.height, self.payment_status, self.membership_date, 
                     self.expiry_date, self.status)
        
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
    
    def renew_membership(self, new_expiry_date, payment_status='done'):
        """Renew member's membership"""
        self.expiry_date = new_expiry_date
        self.payment_status = payment_status
        return self.save()
    
    def get_attendance_history(self):
        """Get member's attendance history with trainer details"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT a.date, a.time_slot, t.name as trainer_name, a.status
            FROM attendance a
            JOIN trainers t ON a.trainer_id = t.id
            WHERE a.member_id = ?
            ORDER BY a.date DESC
        '''
        return execute_query(query, (self.id,), db_path, fetch=True)