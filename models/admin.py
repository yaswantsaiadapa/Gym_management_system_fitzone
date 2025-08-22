from .database import execute_query, get_db_connection
from flask import current_app

class Admin:
    def __init__(self, id=None, username=None, password=None, name=None, email=None):
        self.id = id
        self.username = username
        self.password = password
        self.name = name
        self.email = email
    
    @classmethod
    def authenticate(cls, username, password):
        """Authenticate admin user"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM admin WHERE username = ? AND password = ?'
        result = execute_query(query, (username, password), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0],
                username=row[1],
                password=row[2],
                name=row[3],
                email=row[4] if len(row) > 4 else None
            )
        return None
    
    @classmethod
    def get_by_id(cls, admin_id):
        """Get admin by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM admin WHERE id = ?'
        result = execute_query(query, (admin_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0],
                username=row[1],
                password=row[2],
                name=row[3],
                email=row[4] if len(row) > 4 else None
            )
        return None
    
    def save(self):
        """Save admin to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        if self.id:
            # Update existing admin
            query = '''UPDATE admin SET username = ?, password = ?, name = ?, email = ? 
                      WHERE id = ?'''
            params = (self.username, self.password, self.name, self.email, self.id)
        else:
            # Create new admin
            query = '''INSERT INTO admin (username, password, name, email) 
                      VALUES (?, ?, ?, ?)'''
            params = (self.username, self.password, self.name, self.email)
            self.id = execute_query(query, params, db_path)
        
        if self.id:
            execute_query(query, params, db_path)
        
        return self.id