from flask import current_app
from models.database import execute_query


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
        self.start_date = start_date
        self.end_date = end_date
        self.is_active = is_active
        self.created_at = created_at
        self.trainer_name = None

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
        """Get all diet plans for a member"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT dp.*, u.full_name as trainer_name 
                   FROM diet_plans dp
                   LEFT JOIN trainers t ON dp.trainer_id = t.id
                   LEFT JOIN users u ON t.user_id = u.id
                   WHERE dp.member_id = ? ORDER BY dp.created_at DESC'''
        results = execute_query(query, (member_id,), db_path, fetch=True)

        diet_plans = []
        for row in results:
            diet = cls(
                id=row[0], member_id=row[1], trainer_id=row[2], name=row[3],
                description=row[4], total_calories=row[5], start_date=row[6],
                end_date=row[7], is_active=bool(row[8]), created_at=row[9]
            )
            diet.trainer_name = row[10] if len(row) > 10 else None
            diet_plans.append(diet)
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
        """Save diet plan to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

        if self.id:
            # Update existing diet plan
            query = '''UPDATE diet_plans SET member_id = ?, trainer_id = ?,
                      name = ?, description = ?, total_calories = ?,
                      start_date = ?, end_date = ?, is_active = ? WHERE id = ?'''
            params = (self.member_id, self.trainer_id, self.name, self.description,
                     self.total_calories, self.start_date, self.end_date,
                     self.is_active, self.id)
        else:
            # Create new diet plan
            query = '''INSERT INTO diet_plans (member_id, trainer_id, name,
                      description, total_calories, start_date, end_date, is_active)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (self.member_id, self.trainer_id, self.name, self.description,
                     self.total_calories, self.start_date, self.end_date, self.is_active)

        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
