from datetime import datetime
import json
from flask import current_app
from models.database import execute_query

class MembershipPlan:
    def __init__(self, id=None, name=None, description=None, duration_months=None,
                 price=None, features=None, is_active=True,created_at=None,updated_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.duration_months = duration_months
        self.price = price
        if isinstance(features, str):
            try:
                self.features = json.loads(features)
            except:
                self.features = []
        else:
            self.features = features or []
        self.is_active = is_active
        self.created_at = (
            datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
        )
        self.updated_at = (
            datetime.fromisoformat(updated_at) if isinstance(updated_at, str) else updated_at
        )
    @classmethod
    def get_all_active(cls):
        """Get all active membership plans"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM membership_plans WHERE is_active = 1'
        results = execute_query(query, (), db_path, fetch=True) or []
        
        plans = []
        for row in results:
            plan = cls(
                id=row[0], name=row[1], description=row[2], duration_months=row[3],
                price=row[4], features=row[5], is_active=bool(row[6]),created_at=row[7],updated_at=row[8]  
            )
            plans.append(plan)
        return plans
    
    @classmethod
    def get_by_id(cls, plan_id):
        """Get membership plan by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM membership_plans WHERE id = ?'
        result = execute_query(query, (plan_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0], name=row[1], description=row[2], duration_months=row[3],
                price=row[4], features=row[5], is_active=bool(row[6]),updated_at=row[8] ,created_at=row[7]
            )
        return None
    
    @classmethod
    def get_all(cls):
        """Get all membership plans (active + inactive)"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = 'SELECT * FROM membership_plans ORDER BY id DESC'
        results = execute_query(query, (), db_path, fetch=True) or []
        
        plans = []
        for row in results:
            plan = cls(
                id=row[0], name=row[1], description=row[2], duration_months=row[3],
                price=row[4], features=row[5], is_active=bool(row[6]),created_at=row[7],updated_at=row[8]  
            )
            plans.append(plan)
        return plans
    def save(self):
        """Save membership plan to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if self.id:
            # Update existing plan
            query = '''UPDATE membership_plans 
                    SET name = ?, description = ?, 
                        duration_months = ?, price = ?, features = ?, is_active = ?, 
                        updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?'''
            params = (
                self.name, 
                self.description, 
                self.duration_months, 
                self.price, 
                self.features, 
                int(self.is_active), 
                self.id
            )
        else:
            # Create new plan
            query = '''INSERT INTO membership_plans 
                    (name, description, duration_months, price, features, is_active) 
                    VALUES (?, ?, ?, ?, ?, ?)'''
            params = (
                self.name, 
                self.description, 
                self.duration_months, 
                self.price, 
                self.features, 
                int(self.is_active)
            )
        
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
