from flask import current_app
from app.models.database import execute_query
from app.models.workout import Workout


class MemberWorkoutPlan:
    def __init__(self, id=None, member_id=None, trainer_id=None,
                 name=None, description=None, start_date=None,
                 end_date=None, is_active=True, created_at=None):
        self.id = id
        self.member_id = member_id
        self.trainer_id = trainer_id
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        # store as bool in memory
        self.is_active = bool(is_active)
        self.created_at = created_at

    # ---------- Fetchers ----------

    @classmethod
    def get_member_plans(cls, member_id):
        """Fetch all active workout plans for a member."""
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = """
            SELECT id, member_id, trainer_id, name, description,
                   start_date, end_date, is_active, created_at
            FROM member_workout_plans
            WHERE member_id = ? AND is_active = 1
            ORDER BY start_date DESC, id DESC
        """
        rows = execute_query(query, (member_id,), db_path, fetch=True)
        plans = []
        for r in rows or []:
            plans.append(cls(
                id=r[0], member_id=r[1], trainer_id=r[2], name=r[3],
                description=r[4], start_date=r[5], end_date=r[6],
                is_active=bool(r[7]), created_at=r[8]
            ))
        return plans

    @classmethod
    def get_member_active_plan(cls, member_id):
        """Return the latest active plan for a member (or None)."""
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = """
            SELECT id, member_id, trainer_id, name, description,
                   start_date, end_date, is_active, created_at
            FROM member_workout_plans
            WHERE member_id = ? AND is_active = 1
            ORDER BY start_date DESC, id DESC
            LIMIT 1
        """
        rows = execute_query(query, (member_id,), db_path, fetch=True)
        if rows:
            r = rows[0]
            return cls(
                id=r[0], member_id=r[1], trainer_id=r[2], name=r[3],
                description=r[4], start_date=r[5], end_date=r[6],
                is_active=bool(r[7]), created_at=r[8]
            )
        return None

    @classmethod
    def get_by_id(cls, plan_id):
        """Fetch a plan by id (or None)."""
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = """
            SELECT id, member_id, trainer_id, name, description,
                   start_date, end_date, is_active, created_at
            FROM member_workout_plans
            WHERE id = ?
        """
        rows = execute_query(query, (plan_id,), db_path, fetch=True)
        if rows:
            r = rows[0]
            return cls(
                id=r[0], member_id=r[1], trainer_id=r[2], name=r[3],
                description=r[4], start_date=r[5], end_date=r[6],
                is_active=bool(r[7]), created_at=r[8]
            )
        return None

    @classmethod
    def get_trainer_active_plans_count(cls, trainer_id):
        """Count active plans owned by a trainer."""
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = "SELECT COUNT(*) FROM member_workout_plans WHERE trainer_id = ? AND is_active = 1"
        rows = execute_query(query, (trainer_id,), db_path, fetch=True)
        return rows[0][0] if rows else 0

    # ---------- Mutators ----------

    @classmethod
    def deactivate_member_plans(cls, member_id):
        """Deactivate all currently-active plans for a member."""
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = "UPDATE member_workout_plans SET is_active = 0 WHERE member_id = ? AND is_active = 1"
        execute_query(query, (member_id,), db_path)

    def save(self):
        """Insert or update a workout plan."""
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        if self.id:
            query = """
                UPDATE member_workout_plans
                SET member_id = ?, trainer_id = ?, name = ?, description = ?,
                    start_date = ?, end_date = ?, is_active = ?
                WHERE id = ?
            """
            params = (
                self.member_id, self.trainer_id, self.name, self.description,
                self.start_date, self.end_date, int(bool(self.is_active)), self.id
            )
        else:
            query = """
                INSERT INTO member_workout_plans
                (member_id, trainer_id, name, description, start_date, end_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                self.member_id, self.trainer_id, self.name, self.description,
                self.start_date, self.end_date, int(bool(self.is_active))
            )
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
    def delete(self):
        if not self.id:
            raise ValueError("Cannot delete a workout detail that hasn't been saved.")
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = "DELETE FROM workout_plan_details WHERE id = ?"
        execute_query(query, (self.id,), db_path)
    def deactivate(self):
        """Deactivate (soft delete) this workout plan."""
        if not self.id:
            raise ValueError("Plan must be saved before deactivating.")
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = "UPDATE member_workout_plans SET is_active = 0 WHERE id = ?"
        execute_query(query, (self.id,), db_path)
        self.is_active = False

    # ---------- Convenience ----------

    def get_plan_details(self):
        """Instance convenience to fetch details for this plan."""
        if not self.id:
            return []
        return WorkoutPlanDetail.get_plan_details(self.id)


class WorkoutPlanDetail:
    def __init__(self, id=None, plan_id=None, workout_id=None, day_of_week=None,
                 sets=None, reps=None, weight=None, rest_seconds=None, notes=None):
        self.id = id
        self.plan_id = plan_id
        self.workout_id = workout_id
        self.day_of_week = day_of_week
        self.sets = sets
        self.reps = reps
        self.weight = weight
        self.rest_seconds = rest_seconds
        self.notes = notes
        self.workout = None  # populated on fetch

    @classmethod
    def get_plan_details(cls, plan_id):
        """Fetch all workout details for a plan (joined with workout info)."""
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = """
            SELECT d.id, d.plan_id, d.workout_id, d.day_of_week,
                   d.sets, d.reps, d.weight, d.rest_seconds, d.notes,
                   w.name, w.description, w.category
            FROM workout_plan_details d
            JOIN workouts w ON d.workout_id = w.id
            WHERE d.plan_id = ?
            ORDER BY d.day_of_week, d.id
        """
        rows = execute_query(query, (plan_id,), db_path, fetch=True)
        details = []
        for r in rows or []:
            detail = cls(
                id=r[0], plan_id=r[1], workout_id=r[2], day_of_week=r[3],
                sets=r[4], reps=r[5], weight=r[6], rest_seconds=r[7], notes=r[8]
            )
            detail.workout = Workout(id=r[2], name=r[9], description=r[10], category=r[11])
            details.append(detail)
        return details

    @classmethod
    def get_trainer_plans(cls, trainer_id):
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = """
            SELECT id, member_id, trainer_id, name, description,
                start_date, end_date, is_active, created_at
            FROM member_workout_plans
            WHERE trainer_id = ? AND is_active = 1
            ORDER BY start_date DESC, id DESC
        """
        rows = execute_query(query, (trainer_id,), db_path, fetch=True)
        return [cls(
            id=r[0], member_id=r[1], trainer_id=r[2], name=r[3],
            description=r[4], start_date=r[5], end_date=r[6],
            is_active=bool(r[7]), created_at=r[8]
        ) for r in rows or []]

    @classmethod
    def get_all(cls):
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        query = """
            SELECT id, member_id, trainer_id, name, description,
                start_date, end_date, is_active, created_at
            FROM member_workout_plans
            ORDER BY start_date DESC, id DESC
        """
        rows = execute_query(query, (), db_path, fetch=True)
        return [cls(
            id=r[0], member_id=r[1], trainer_id=r[2], name=r[3],
            description=r[4], start_date=r[5], end_date=r[6],
            is_active=bool(r[7]), created_at=r[8]
        ) for r in rows or []]

    def save(self):
        """Insert or update a workout detail row."""
        db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")
        if self.id:
            query = """
                UPDATE workout_plan_details
                SET plan_id = ?, workout_id = ?, day_of_week = ?, sets = ?, reps = ?,
                    weight = ?, rest_seconds = ?, notes = ?
                WHERE id = ?
            """
            params = (
                self.plan_id, self.workout_id, self.day_of_week, self.sets, self.reps,
                self.weight, self.rest_seconds, self.notes, self.id
            )
        else:
            query = """
                INSERT INTO workout_plan_details
                (plan_id, workout_id, day_of_week, sets, reps, weight, rest_seconds, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                self.plan_id, self.workout_id, self.day_of_week, self.sets, self.reps,
                self.weight, self.rest_seconds, self.notes
            )
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
