from .database import execute_query
from flask import current_app
from datetime import date

class Equipment:
    def __init__(self, id=None, name=None, status='working', last_maintenance=None):
        self.id = id
        self.name = name
        self.status = status
        self.last_maintenance = last_maintenance
    
    @classmethod
    def get_all(cls):
        """Get all equipment"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM equipment'
        results = execute_query(query, (), db_path, fetch=True)
        
        equipment_list = []
        for row in results:
            equipment = cls(
                id=row[0], name=row[1], status=row[2], 
                last_maintenance=row[3] if len(row) > 3 else None
            )
            equipment_list.append(equipment)
        return equipment_list
    
    @classmethod
    def get_by_id(cls, equipment_id):
        """Get equipment by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM equipment WHERE id = ?'
        result = execute_query(query, (equipment_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0], name=row[1], status=row[2], 
                last_maintenance=row[3] if len(row) > 3 else None
            )
        return None
    
    @classmethod
    def get_working_count(cls):
        """Get count of working equipment"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT COUNT(*) FROM equipment WHERE status = "working"'
        result = execute_query(query, (), db_path, fetch=True)
        return result[0][0] if result else 0
    
    @classmethod
    def get_maintenance_count(cls):
        """Get count of equipment under maintenance"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT COUNT(*) FROM equipment WHERE status = "maintenance"'
        result = execute_query(query, (), db_path, fetch=True)
        return result[0][0] if result else 0
    
    def save(self):
        """Save equipment to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if self.id:
            # Update existing equipment
            query = '''UPDATE equipment SET name = ?, status = ?, 
                      last_maintenance = ? WHERE id = ?'''
            params = (self.name, self.status, self.last_maintenance, self.id)
        else:
            # Create new equipment
            query = '''INSERT INTO equipment (name, status, last_maintenance) 
                      VALUES (?, ?, ?)'''
            params = (self.name, self.status, self.last_maintenance)
        
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
    
    def mark_for_maintenance(self):
        """Mark equipment for maintenance"""
        self.status = 'maintenance'
        self.last_maintenance = date.today()
        return self.save()
    
    def mark_as_working(self):
        """Mark equipment as working"""
        self.status = 'working'
        return self.save()
    
    def is_working(self):
        """Check if equipment is working"""
        return self.status == 'working'
    
    def is_under_maintenance(self):
        """Check if equipment is under maintenance"""
        return self.status == 'maintenance'