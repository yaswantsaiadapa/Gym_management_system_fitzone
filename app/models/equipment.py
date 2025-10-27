from app.models.database import execute_query
from flask import current_app
from datetime import date

class Equipment:
    def __init__(self, id=None, name=None, category=None, brand=None, model=None,
                 purchase_date=None, warranty_end_date=None, status='working',
                 last_maintenance_date=None, next_maintenance_date=None,
                 maintenance_notes=None, location=None, created_at=None):
        self.id = id
        self.name = name
        self.category = category
        self.brand = brand
        self.model = model
        self.purchase_date = purchase_date
        self.warranty_end_date = warranty_end_date
        self.status = status
        self.last_maintenance_date = last_maintenance_date
        self.next_maintenance_date = next_maintenance_date
        self.maintenance_notes = maintenance_notes
        self.location = location
        self.created_at = created_at

    # ---------------------------
    # Fetch Queries
    # ---------------------------
    @classmethod
    def get_all(cls):
        """Get all equipment"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM equipment ORDER BY name'
        results = execute_query(query, (), db_path, fetch=True)
        return [cls(*row) for row in results]

    @classmethod
    def get_by_id(cls, equipment_id):
        """Get single equipment by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM equipment WHERE id = ?'
        result = execute_query(query, (equipment_id,), db_path, fetch=True)
        return cls(*result[0]) if result else None

    @classmethod
    def get_working(cls):
        """Get all equipment that is working"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM equipment WHERE status = "working" ORDER BY name'
        results = execute_query(query, (), db_path, fetch=True)
        return [cls(*row) for row in results]

    @classmethod
    def get_working_count(cls):
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT COUNT(*) FROM equipment WHERE status = "working"'
        result = execute_query(query, (), db_path, fetch=True)
        return result[0][0] if result else 0

    @classmethod
    def get_maintenance_count(cls):
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT COUNT(*) FROM equipment WHERE status = "maintenance"'
        result = execute_query(query, (), db_path, fetch=True)
        return result[0][0] if result else 0

    @classmethod
    def get_out_of_order_count(cls):
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT COUNT(*) FROM equipment WHERE status = "out_of_order"'
        result = execute_query(query, (), db_path, fetch=True)
        return result[0][0] if result else 0

    # ---------------------------
    # Save / Update / Delete
    # ---------------------------
    def save(self):
        """Insert or update equipment record"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

        if self.id:  # update
            query = '''
                UPDATE equipment 
                SET name=?, category=?, brand=?, model=?, purchase_date=?, 
                    warranty_end_date=?, status=?, last_maintenance_date=?, 
                    next_maintenance_date=?, maintenance_notes=?, location=? 
                WHERE id=?
            '''
            params = (self.name, self.category, self.brand, self.model,
                      self.purchase_date, self.warranty_end_date, self.status,
                      self.last_maintenance_date, self.next_maintenance_date,
                      self.maintenance_notes, self.location, self.id)
        else:  # insert
            query = '''
                INSERT INTO equipment 
                (name, category, brand, model, purchase_date, warranty_end_date, 
                 status, last_maintenance_date, next_maintenance_date, 
                 maintenance_notes, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = (self.name, self.category, self.brand, self.model,
                      self.purchase_date, self.warranty_end_date, self.status,
                      self.last_maintenance_date, self.next_maintenance_date,
                      self.maintenance_notes, self.location)
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id

    def delete(self):
        """Delete equipment"""
        if not self.id:
            return False
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'DELETE FROM equipment WHERE id=?'
        execute_query(query, (self.id,), db_path)
        return True

    # ---------------------------
    # Status Updates
    # ---------------------------
    def mark_for_maintenance(self, notes=None, next_date=None):
        """Mark equipment as maintenance"""
        self.status = 'maintenance'
        self.last_maintenance_date = date.today()
        self.maintenance_notes = notes
        self.next_maintenance_date = next_date
        return self.save()

    def mark_as_working(self):
        """Set equipment status back to working"""
        self.status = 'working'
        return self.save()

    def mark_out_of_order(self, notes=None):
        """Set equipment as out of order"""
        self.status = 'out_of_order'
        self.maintenance_notes = notes
        return self.save()

    # ---------------------------
    # Utility Checks
    # ---------------------------
    def is_working(self):
        return self.status == 'working'

    def is_under_maintenance(self):
        return self.status == 'maintenance'

    def is_out_of_order(self):
        return self.status == 'out_of_order'
