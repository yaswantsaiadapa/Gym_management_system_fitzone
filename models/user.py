from .database import execute_query
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

class User:
    def __init__(self, id=None, username=None, email=None, password_hash=None, 
                 role=None, full_name=None, phone=None, is_active=True):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.full_name = full_name
        self.phone = phone
        self.is_active = is_active
    
    @classmethod
    def authenticate(cls, username, password):
        """Authenticate user with username/email and password"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT id, username, email, password_hash, role, full_name, phone, is_active
               FROM users 
               WHERE (username = ? OR email = ?) AND is_active = 1'''
        result = execute_query(query, (username, username), db_path, fetch=True)
        
        if result and check_password_hash(result[0][3], password):
            row = result[0]
            return cls(
                id=row[0], username=row[1], email=row[2], password_hash=row[3],
                role=row[4], full_name=row[5], phone=row[6], is_active=bool(row[7])
            )
        return None
    
    @classmethod
    def get_by_id(cls, user_id):
        """Get user by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT id, username, email, password_hash, role, full_name, phone, is_active
               FROM users WHERE id = ?'''
        result = execute_query(query, (user_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0], username=row[1], email=row[2], password_hash=row[3],
                role=row[4], full_name=row[5], phone=row[6], is_active=bool(row[7])
            )
        return None
    @classmethod
    def get_by_username_or_email(cls, identifier):
        """Fetch user by username or email"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT id, username, email, password_hash, role, full_name, phone, is_active
               FROM users WHERE username = ? OR email = ?'''
        result = execute_query(query, (identifier, identifier), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0], username=row[1], email=row[2], password_hash=row[3],
                role=row[4], full_name=row[5], phone=row[6], is_active=bool(row[7])
            )
        return None
    
    def save(self):
        """Save user to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        # Ensure password is hashed before saving
        if self.password_hash and not self.password_hash.startswith('pbkdf2:'):
            self.password_hash = generate_password_hash(self.password_hash)

        if self.id:
            query = '''UPDATE users SET username = ?, email = ?, password_hash = ?, 
                      role = ?, full_name = ?, phone = ?, is_active = ?, 
                      updated_at = CURRENT_TIMESTAMP WHERE id = ?'''
            params = (self.username, self.email, self.password_hash, self.role,
                     self.full_name, self.phone, int(self.is_active), self.id)
        else:
            query = '''INSERT INTO users (username, email, password_hash, role, 
                      full_name, phone, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)'''
            params = (self.username, self.email, self.password_hash, self.role,
                     self.full_name, self.phone, int(self.is_active))
        
        result = execute_query(query, params, db_path)
        if not self.id:
            # Make sure database.py returns lastrowid
            self.id = result
        return self.id
    
    def update_password(self, new_password):
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        hashed_pw = generate_password_hash(new_password)
        query = "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        execute_query(query, (hashed_pw, self.id), db_path)
        self.password_hash = hashed_pw
        return True