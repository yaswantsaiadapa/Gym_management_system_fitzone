from datetime import date
from flask import current_app

from models.database import execute_query


class Announcement:
    def __init__(self, id=None, title=None, content=None, announcement_type=None,
                 target_audience=None, is_public=False, is_active=True,
                 start_date=None, end_date=None, created_by=None):
        self.id = id
        self.title = title
        self.content = content
        self.announcement_type = announcement_type
        self.target_audience = target_audience
        self.is_public = is_public
        self.is_active = is_active
        self.start_date = start_date
        self.end_date = end_date
        self.created_by = created_by
    
    @classmethod
    def get_public_announcements(cls):
        """Get public announcements for home page"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        today = date.today()
        query = '''SELECT * FROM announcements 
          WHERE is_public = 1 AND is_active = 1 
          AND (start_date IS NULL OR start_date <= ?)
          AND (end_date IS NULL OR end_date >= ?)
          ORDER BY id DESC LIMIT 5''' 
        results = execute_query(query, (today, today), db_path, fetch=True)
        
        announcements = []
        for row in results:
            announcement = cls(
                id=row[0], title=row[1], content=row[2], announcement_type=row[3],
                target_audience=row[4], is_public=bool(row[5]), is_active=bool(row[6]),
                start_date=row[7], end_date=row[8], created_by=row[9]
            )
            announcements.append(announcement)
        return announcements
    
    @classmethod
    def get_for_role(cls, role):
        """Get announcements for specific role"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        today = date.today()
        query = '''SELECT * FROM announcements 
          WHERE is_active = 1 
          AND (target_audience = 'all' OR target_audience = ?)
          AND (start_date IS NULL OR start_date <= ?)
          AND (end_date IS NULL OR end_date >= ?)
          ORDER BY id DESC''' 
        results = execute_query(query, (role, today, today), db_path, fetch=True)
        
        announcements = []
        for row in results:
            announcement = cls(
                id=row[0], title=row[1], content=row[2], announcement_type=row[3],
                target_audience=row[4], is_public=bool(row[5]), is_active=bool(row[6]),
                start_date=row[7], end_date=row[8], created_by=row[9]
            )
            announcements.append(announcement)
        return announcements
    @classmethod
    def get_by_id(cls, announcement_id):
        """Fetch a single announcement by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM announcements WHERE id = ?'
        result = execute_query(query, (announcement_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0], title=row[1], content=row[2], announcement_type=row[3],
                target_audience=row[4], is_public=bool(row[5]), is_active=bool(row[6]),
                start_date=row[7], end_date=row[8], created_by=row[9]
            )
        return None

    @classmethod
    def get_by_creator(cls, creator_id):
        """Fetch all announcements created by a specific trainer/user"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM announcements WHERE created_by = ? ORDER BY id DESC'
        results = execute_query(query, (creator_id,), db_path, fetch=True)
        
        announcements = []
        for row in results:
            announcements.append(cls(
                id=row[0], title=row[1], content=row[2], announcement_type=row[3],
                target_audience=row[4], is_public=bool(row[5]), is_active=bool(row[6]),
                start_date=row[7], end_date=row[8], created_by=row[9]
            ))
        return announcements

    def save(self):
        """Save announcement to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if self.id:
            # Update existing announcement
            query = '''UPDATE announcements SET title = ?, content = ?,
                      announcement_type = ?, target_audience = ?, is_public = ?,
                      is_active = ?, start_date = ?, end_date = ?, created_by = ?
                      WHERE id = ?'''
            params = (self.title, self.content, self.announcement_type,
                     self.target_audience, self.is_public, self.is_active,
                     self.start_date, self.end_date, self.created_by, self.id)
        else:
            # Create new announcement
            query = '''INSERT INTO announcements (title, content, announcement_type,
                      target_audience, is_public, is_active, start_date, end_date,
                      created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (self.title, self.content, self.announcement_type,
                     self.target_audience, self.is_public, self.is_active,
                     self.start_date, self.end_date, self.created_by)
        
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
    def deactivate(self):
        """Soft delete / deactivate the announcement"""
        if not self.id:
            raise ValueError("Cannot deactivate an unsaved announcement.")
        
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'UPDATE announcements SET is_active = 0 WHERE id = ?'
        execute_query(query, (self.id,), db_path)
        self.is_active = False