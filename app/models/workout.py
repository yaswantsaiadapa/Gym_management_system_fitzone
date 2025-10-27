from flask import current_app
from app.models.database import execute_query


class Workout:
    def __init__(self, id=None, name=None, description=None, category=None,
                 difficulty_level=None, duration_minutes=None, calories_burned=None,
                 instructions=None, equipment_needed=None, is_active=True, created_by=None):
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        self.difficulty_level = difficulty_level
        self.duration_minutes = duration_minutes
        self.calories_burned = calories_burned
        self.instructions = instructions
        self.equipment_needed = equipment_needed
        self.is_active = is_active
        self.created_by = created_by
    
    @classmethod
    def get_all_active(cls):
        """Get all active workouts"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM workouts WHERE is_active = 1'
        results = execute_query(query, (), db_path, fetch=True)
        
        workouts = []
        for row in results:
            workout = cls(
                id=row[0], name=row[1], description=row[2], category=row[3],
                difficulty_level=row[4], duration_minutes=row[5], 
                calories_burned=row[6], instructions=row[7], 
                equipment_needed=row[8], is_active=bool(row[9]), created_by=row[10]
            )
            workouts.append(workout)
        return workouts
    
    @classmethod
    def get_by_category(cls, category):
        """Get workouts by category"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM workouts WHERE category = ? AND is_active = 1'
        results = execute_query(query, (category,), db_path, fetch=True)
        
        workouts = []
        for row in results:
            workout = cls(
                id=row[0], name=row[1], description=row[2], category=row[3],
                difficulty_level=row[4], duration_minutes=row[5], 
                calories_burned=row[6], instructions=row[7], 
                equipment_needed=row[8], is_active=bool(row[9]), created_by=row[10]
            )
            workouts.append(workout)
        return workouts
    
    def save(self):
        """Save workout to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        active_flag = int(bool(self.is_active))  # ensure 0/1 for SQLite

        if self.id:
            # Update existing workout
            query = '''UPDATE workouts 
                    SET name = ?, description = ?, category = ?,
                        difficulty_level = ?, duration_minutes = ?, calories_burned = ?,
                        instructions = ?, equipment_needed = ?, is_active = ?, 
                        created_by = ? 
                    WHERE id = ?'''
            params = (
                self.name, self.description, self.category, self.difficulty_level,
                self.duration_minutes, self.calories_burned, self.instructions,
                self.equipment_needed, active_flag, self.created_by, self.id
            )
        else:
            # Create new workout
            query = '''INSERT INTO workouts 
                    (name, description, category, difficulty_level, duration_minutes,
                        calories_burned, instructions, equipment_needed, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (
                self.name, self.description, self.category, self.difficulty_level,
                self.duration_minutes, self.calories_burned, self.instructions,
                self.equipment_needed, active_flag, self.created_by
            )

        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id

    
    def deactivate(self):
        """Soft delete / deactivate the workout"""
        if not self.id:
            raise ValueError("Cannot deactivate a workout that hasn't been saved yet.")
        
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'UPDATE workouts SET is_active = 0 WHERE id = ?'
        execute_query(query, (self.id,), db_path)
        self.is_active = False