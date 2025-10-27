# models/membership_plan.py
from datetime import datetime
import json
from flask import current_app
from app.models.database import execute_query

class MembershipPlan:
    """
    MembershipPlan model with validation and safe features handling.

    Fields:
      - id, name, description, duration_months (int), price (float),
        features (list), is_active (bool), created_at (datetime), updated_at (datetime)
    """

    def __init__(self, id=None, name=None, description=None, duration_months=None,
                 price=None, features=None, is_active=True, created_at=None, updated_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.duration_months = int(duration_months) if duration_months is not None else None
        # ensure numeric price if provided
        try:
            self.price = float(price) if price is not None else None
        except Exception:
            self.price = price

        # Normalize features: accept JSON string, list, or None -> keep as list
        if isinstance(features, str):
            try:
                parsed = json.loads(features)
                self.features = parsed if isinstance(parsed, list) else []
            except Exception:
                # If it's a comma-separated string, try splitting
                try:
                    self.features = [f.strip() for f in features.split(',') if f.strip()]
                except Exception:
                    self.features = []
        elif isinstance(features, list):
            self.features = features
        else:
            # None or other type -> empty list
            self.features = features or []

        # normalize boolean-ish
        self.is_active = bool(int(is_active)) if isinstance(is_active, (str, int)) else bool(is_active)

        # parse created_at/updated_at if strings
        self.created_at = (
            datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
        )
        self.updated_at = (
            datetime.fromisoformat(updated_at) if isinstance(updated_at, str) else updated_at
        )

    # ----------------- Helpers & Validation -----------------
    @classmethod
    def _db_path(cls):
        return current_app.config.get('DATABASE_PATH', 'gym_management.db')

    def validate(self):
        """Validate fields before saving. Raises ValueError on invalid data."""
        if not self.name or not str(self.name).strip():
            raise ValueError("Plan name is required.")
        if self.duration_months is None:
            raise ValueError("duration_months is required and must be an integer >= 1.")
        try:
            dm = int(self.duration_months)
        except Exception:
            raise ValueError("duration_months must be an integer.")
        if dm < 1:
            raise ValueError("duration_months must be at least 1.")
        if self.price is None:
            raise ValueError("price is required and must be >= 0.")
        try:
            p = float(self.price)
        except Exception:
            raise ValueError("price must be a number.")
        if p < 0:
            raise ValueError("price must be >= 0.")
        # Ensure features is a list; convert if necessary (non-fatal)
        if not isinstance(self.features, list):
            try:
                self.features = json.loads(self.features)
                if not isinstance(self.features, list):
                    self.features = []
            except Exception:
                self.features = []

    def to_dict(self):
        """Return a plain dict useful for templates / JSON."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'duration_months': self.duration_months,
            'price': self.price,
            'features': list(self.features),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }

    # ----------------- Query methods (unchanged semantics) -----------------
    @classmethod
    def get_all_active(cls):
        """Get all active membership plans"""
        db_path = cls._db_path()
        query = 'SELECT * FROM membership_plans WHERE is_active = 1'
        results = execute_query(query, (), db_path, fetch=True) or []

        plans = []
        for row in results:
            plan = cls(
                id=row[0], name=row[1], description=row[2], duration_months=row[3],
                price=row[4], features=row[5], is_active=bool(row[6]), created_at=row[7], updated_at=row[8]
            )
            plans.append(plan)
        return plans

    @classmethod
    def get_by_id(cls, plan_id):
        """Get membership plan by ID"""
        db_path = cls._db_path()
        query = 'SELECT * FROM membership_plans WHERE id = ?'
        result = execute_query(query, (plan_id,), db_path, fetch=True)

        if result:
            row = result[0]
            return cls(
                id=row[0], name=row[1], description=row[2], duration_months=row[3],
                price=row[4], features=row[5], is_active=bool(row[6]), created_at=row[7], updated_at=row[8]
            )
        return None

    @classmethod
    def get_all(cls):
        """Get all membership plans (active + inactive)"""
        db_path = cls._db_path()
        query = 'SELECT * FROM membership_plans ORDER BY id DESC'
        results = execute_query(query, (), db_path, fetch=True) or []

        plans = []
        for row in results:
            plan = cls(
                id=row[0], name=row[1], description=row[2], duration_months=row[3],
                price=row[4], features=row[5], is_active=bool(row[6]), created_at=row[7], updated_at=row[8]
            )
            plans.append(plan)
        return plans

    # ----------------- Persistence (save) -----------------
    def save(self):
        """Save membership plan to database (create or update). Raises ValueError on invalid data."""
        db_path = self._db_path()

        # Validate inputs
        self.validate()

        # Ensure features is serialized as JSON string when saved
        features_json = json.dumps(self.features or [])

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
                int(self.duration_months),
                float(self.price),
                features_json,
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
                int(self.duration_months),
                float(self.price),
                features_json,
                int(self.is_active)
            )

        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
