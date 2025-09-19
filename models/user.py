from .database import execute_query
from flask import current_app
from flask_bcrypt import Bcrypt

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
    def _get_bcrypt(cls):
        """Return a Bcrypt instance bound to the current app (safe to call inside app context)."""
        # Create a new instance here; it is light-weight and uses current_app config
        return Bcrypt(current_app)

    @classmethod
    def authenticate(cls, username, password):
        """Authenticate user with username/email and password using bcrypt."""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT id, username, email, password_hash, role, full_name, phone, is_active
                   FROM users 
                   WHERE (username = ? OR email = ?) AND is_active = 1'''
        result = execute_query(query, (username, username), db_path, fetch=True)

        if result:
            row = result[0]
            stored_hash = row[3]
            bcrypt = cls._get_bcrypt()
            try:
                # bcrypt.check_password_hash accepts the stored hash and the candidate password
                if stored_hash and bcrypt.check_password_hash(stored_hash, password):
                    return cls(
                        id=row[0], username=row[1], email=row[2], password_hash=stored_hash,
                        role=row[4], full_name=row[5], phone=row[6], is_active=bool(row[7])
                    )
            except ValueError:
                # In case stored_hash has an unexpected format, treat as authentication failure
                pass

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

    def _is_already_hashed(self, value: str) -> bool:
        """Rudimentary detection of already-hashed passwords:
           checks common prefixes for known schemes including bcrypt ($2a$, $2b$, $2y$).
        """
        if not value:
            return False
        lowered = value.lower()
        known_prefixes = ('pbkdf2:', 'scrypt:', 'argon2:', 'bcrypt:')
        # bcrypt hashes ususally start with $2b$ or $2a$ or $2y$
        if lowered.startswith('$2a$') or lowered.startswith('$2b$') or lowered.startswith('$2y$'):
            return True
        for p in known_prefixes:
            if lowered.startswith(p):
                return True
        return False

    def save(self):
        """Save user to database (new/updated). Ensure new passwords are bcrypt-hashed."""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        bcrypt = self._get_bcrypt()

        # If password_hash field currently contains a plain password (not a hash),
        # generate a bcrypt hash and store that instead.
        if self.password_hash and not self._is_already_hashed(self.password_hash):
            # generate_password_hash returns bytes -> decode to utf-8 for DB storage
            hashed = bcrypt.generate_password_hash(self.password_hash)
            if isinstance(hashed, bytes):
                hashed = hashed.decode('utf-8')
            self.password_hash = hashed

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
            self.id = result
        return self.id

    def update_password(self, new_password):
        """Hash new_password with bcrypt and update DB."""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        bcrypt = self._get_bcrypt()
        hashed_pw = bcrypt.generate_password_hash(new_password)
        if isinstance(hashed_pw, bytes):
            hashed_pw = hashed_pw.decode('utf-8')
        query = "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        execute_query(query, (hashed_pw, self.id), db_path)
        self.password_hash = hashed_pw
        return True
