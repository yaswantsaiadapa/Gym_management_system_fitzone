from flask import current_app
from app.models.database import execute_query

from datetime import datetime, date


class Diet:
    def __init__(self, id=None, member_id=None, trainer_id=None, name=None,
                 description=None, total_calories=None, start_date=None,
                 end_date=None, is_active=True, created_at=None):
        self.id = id
        self.member_id = member_id
        self.trainer_id = trainer_id
        self.name = name
        self.description = description
        self.total_calories = total_calories
        # Normalize incoming date-like values to date objects (or None)
        self.start_date = self._to_date(start_date)
        self.end_date = self._to_date(end_date)
        self.is_active = bool(is_active)
        self.created_at = self._to_date(created_at)
        self.trainer_name = None

    @property
    def status(self):
        """Return 'active' or 'inactive' for templates."""
        return 'active' if self.is_active else 'inactive'

    @staticmethod
    def _to_date(value):
        """Convert value from DB or input to a date object or None."""
        if value is None:
            return None
        # If already a date (but not datetime), return as-is
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        # If it's a datetime, convert to date
        if isinstance(value, datetime):
            return value.date()
        # If string, try common formats and ISO
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            # final fallback: try fromisoformat
            try:
                return datetime.fromisoformat(value).date()
            except Exception:
                return None
        # otherwise not convertible
        return None

    @classmethod
    def get_by_id(cls, plan_id):
        """Get a single diet plan by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = "SELECT * FROM diet_plans WHERE id = ?"
        row = execute_query(query, (plan_id,), db_path, fetch=True)
        if row:
            row = row[0]
            return cls(
                id=row[0], member_id=row[1], trainer_id=row[2], name=row[3],
                description=row[4], total_calories=row[5], start_date=row[6],
                end_date=row[7], is_active=bool(row[8]), created_at=row[9]
            )
        return None

    @classmethod
    def get_member_diet_plans(cls, member_id):
        """
        Fetch all diet plans for a member along with their meals.
        Returns a list of Diet objects with a `meals` attribute.
        """
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

        # Fetch plans with trainer name
        plan_query = '''
            SELECT dp.id, dp.member_id, dp.trainer_id, dp.name, dp.description,
                dp.total_calories, dp.start_date, dp.end_date, dp.is_active,
                dp.created_at,
                u.full_name AS trainer_name
            FROM diet_plans dp
            LEFT JOIN trainers t ON dp.trainer_id = t.id
            LEFT JOIN users u ON t.user_id = u.id
            WHERE dp.member_id = ?
            ORDER BY dp.created_at DESC
        '''
        plans = execute_query(plan_query, (member_id,), db_path, fetch=True) or []

        diet_plans = []

        for row in plans:
            diet = cls(
                id=row[0],
                member_id=row[1],
                trainer_id=row[2],
                name=row[3],
                description=row[4],
                total_calories=row[5],
                start_date=row[6],
                end_date=row[7],
                is_active=bool(row[8]),
                created_at=row[9]
            )
            diet.trainer_name = row[10] if len(row) > 10 else None

            # Fetch meals for this plan in one query
            meal_query = '''
                SELECT id, meal_type, meal_name, ingredients, calories,
                    protein, carbs, fat, instructions
                FROM diet_plan_meals
                WHERE diet_plan_id = ?
                ORDER BY meal_type, id
            '''
            meals = execute_query(meal_query, (diet.id,), db_path, fetch=True) or []
            diet.meals = [
                {
                    "id": m[0],
                    "meal_type": m[1],
                    "meal_name": m[2],
                    "ingredients": m[3],
                    "calories": m[4],
                    "protein": m[5],
                    "carbs": m[6],
                    "fat": m[7],
                    "instructions": m[8]
                }
                for m in meals
            ]

            diet_plans.append(diet)

        current_app.logger.debug(
            "get_member_diet_plans: member_id=%s returned %d plans", member_id, len(diet_plans)
        )
        return diet_plans





    @classmethod
    def get_member_active_plan(cls, member_id):
        """Get the currently active diet plan for a member"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT * FROM diet_plans 
                   WHERE member_id = ? AND is_active = 1
                   ORDER BY created_at DESC LIMIT 1'''
        row = execute_query(query, (member_id,), db_path, fetch=True)
        if row:
            row = row[0]
            return cls(
                id=row[0], member_id=row[1], trainer_id=row[2], name=row[3],
                description=row[4], total_calories=row[5], start_date=row[6],
                end_date=row[7], is_active=bool(row[8]), created_at=row[9]
            )
        return None

    @classmethod
    def deactivate_member_plans(cls, member_id):
        """Deactivate all active diet plans for a member"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = "UPDATE diet_plans SET is_active = 0 WHERE member_id = ?"
        execute_query(query, (member_id,), db_path)

    @classmethod
    def add_meal(cls, diet_plan_id, meal_name, meal_type="breakfast",
                 ingredients=None, calories=None, protein=None,
                 carbs=None, fat=None, instructions=None):
        """Add a meal to a diet plan (meal_type must be: breakfast, lunch, dinner, snack)"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            INSERT INTO diet_plan_meals
            (diet_plan_id, meal_type, meal_name, ingredients, calories, protein, carbs, fat, instructions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        return execute_query(query, (
            diet_plan_id,
            meal_type,  # must be one of 'breakfast', 'lunch', 'dinner', 'snack'
            meal_name,
            ingredients,
            calories,
            protein,
            carbs,
            fat,
            instructions
        ), db_path)

    def get_meals(self):
        """Get meals linked to this diet plan"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT id, meal_type, meal_name, ingredients, calories,
                          protein, carbs, fat, instructions
                   FROM diet_plan_meals
                   WHERE diet_plan_id = ?'''
        results = execute_query(query, (self.id,), db_path, fetch=True)
        return [
            {
                "id": r[0],
                "meal_type": r[1],
                "meal_name": r[2],
                "ingredients": r[3],
                "calories": r[4],
                "protein": r[5],
                "carbs": r[6],
                "fat": r[7],
                "instructions": r[8]
            } for r in results
        ]

    def save(self):
        """Save diet plan to database (convert dates to ISO strings)."""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

        # convert date objects to ISO strings or leave None
        sd = self.start_date.isoformat() if isinstance(self.start_date, date) else self.start_date
        ed = self.end_date.isoformat() if isinstance(self.end_date, date) else self.end_date
        # created_at - if not present, use current timestamp (ISO)
        created = (self.created_at.isoformat() if isinstance(self.created_at, (date, datetime))
                   else (datetime.now().isoformat() if not self.created_at else self.created_at))

        if self.id:
            # Update existing diet plan
            query = '''UPDATE diet_plans SET member_id = ?, trainer_id = ?,
                      name = ?, description = ?, total_calories = ?,
                      start_date = ?, end_date = ?, is_active = ? WHERE id = ?'''
            params = (self.member_id, self.trainer_id, self.name, self.description,
                      self.total_calories, sd, ed, int(bool(self.is_active)), self.id)
            execute_query(query, params, db_path)
        else:
            # Create new diet plan
            query = '''INSERT INTO diet_plans (member_id, trainer_id, name,
                      description, total_calories, start_date, end_date, is_active, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (self.member_id, self.trainer_id, self.name, self.description,
                      self.total_calories, sd, ed, int(bool(self.is_active)), created)
            result = execute_query(query, params, db_path)
            # if execute_query returns lastrowid, set id
            if result:
                self.id = result
        return self.id
