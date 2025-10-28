import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from app import app as flask_app

# ✅ Automatically set up Flask app context and mock missing routes/templates
@pytest.fixture(autouse=True)
def app_context(monkeypatch):
    # Mock auth.login endpoint to prevent BuildError
    flask_app.add_url_rule('/login', endpoint='auth.login', view_func=lambda: 'mock login')

    # Mock render_template globally to prevent TemplateNotFound errors
    monkeypatch.setattr("app.routes.trainer_routes.render_template", lambda *a, **kw: "mock template")

    # Create a test client
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client


# ✅ Helper to simulate session data
def set_session(client, **kwargs):
    with client.session_transaction() as sess:
        for key, value in kwargs.items():
            sess[key] = value


# --------------------------- TESTS --------------------------- #

def test_equipment_list(client):
    with patch("app.routes.trainer_routes.Equipment.get_all", return_value=[]):
        r = client.get("/trainer/equipment")
        assert r.status_code in (200, 302)


def test_dashboard(client):
    set_session(client, trainer_id=1)
    with patch("app.routes.trainer_routes.Trainer.get_by_id", return_value=MagicMock()), \
         patch("app.routes.trainer_routes.Member.get_trainer_client_count", return_value=5), \
         patch("app.routes.trainer_routes.Attendance.get_trainer_daily_sessions", return_value=[]), \
         patch("app.routes.trainer_routes.MemberWorkoutPlan.get_trainer_active_plans_count", return_value=3), \
         patch("app.routes.trainer_routes.Attendance.get_trainer_schedule", return_value=[]), \
         patch("app.routes.trainer_routes.Progress.get_trainer_client_progress", return_value=[]), \
         patch("app.routes.trainer_routes.Member.get_trainer_clients", return_value=[]), \
         patch("app.routes.trainer_routes.Announcement.get_for_role", return_value=[]):
        r = client.get("/trainer/dashboard")
        assert r.status_code in (200, 302)


def test_clients(client):
    set_session(client, trainer_id=1)
    with patch("app.routes.trainer_routes.Member.get_trainer_clients_detailed", return_value=[]):
        r = client.get("/trainer/clients")
        assert r.status_code in (200, 302)


def test_client_details(client):
    set_session(client, trainer_id=1)
    m = MagicMock(id=1, trainer_id=1)
    with patch("app.routes.trainer_routes.Member.get_by_id", return_value=m), \
         patch("app.routes.trainer_routes.Attendance.get_member_attendance", return_value=[]), \
         patch("app.routes.trainer_routes.Progress.get_member_progress", return_value=[]), \
         patch("app.routes.trainer_routes.MemberWorkoutPlan.get_member_active_plan", return_value=None), \
         patch("app.routes.trainer_routes.Diet.get_member_active_plan", return_value=None):
        r = client.get("/trainer/clients/1")
        assert r.status_code in (200, 302)


def test_create_workout_plan(client):
    set_session(client, trainer_id=1)
    m = MagicMock(id=1, trainer_id=1)
    with patch("app.routes.trainer_routes.Member.get_by_id", return_value=m), \
         patch("app.routes.trainer_routes.Workout.get_all_active", return_value=[]), \
         patch("app.routes.trainer_routes.Equipment.get_all", return_value=[]), \
         patch("app.routes.trainer_routes.MemberWorkoutPlan.save", return_value=1):
        r = client.post("/trainer/clients/1/workout-plan/create", data={"name": "Plan A", "start_date": "2025-01-01"})
        assert r.status_code in (200, 302)


def test_edit_workout_plan(client):
    set_session(client, trainer_id=1)
    wp = MagicMock(trainer_id=1, member_id=1)
    with patch("app.routes.trainer_routes.MemberWorkoutPlan.get_by_id", return_value=wp), \
         patch("app.routes.trainer_routes.WorkoutPlanDetail.get_plan_details", return_value=[]), \
         patch("app.routes.trainer_routes.Workout.get_all_active", return_value=[]), \
         patch("app.routes.trainer_routes.Equipment.get_all", return_value=[]), \
         patch("app.routes.trainer_routes.Member.get_by_id", return_value=MagicMock()):
        r = client.get("/trainer/workout-plans/1/edit")
        assert r.status_code in (200, 302)


def test_create_diet_plan(client):
    set_session(client, trainer_id=1)
    m = MagicMock(id=1, trainer_id=1)
    with patch("app.routes.trainer_routes.Member.get_by_id", return_value=m), \
         patch("app.routes.trainer_routes.Diet.save", return_value=1):
        r = client.post("/trainer/clients/1/diet-plan/create", data={"name": "Plan A", "start_date": "2025-01-01"})
        assert r.status_code in (200, 302)


def test_edit_diet_plan(client):
    set_session(client, trainer_id=1)
    dp = MagicMock(trainer_id=1, member_id=1)
    with patch("app.routes.trainer_routes.Diet.get_by_id", return_value=dp), \
         patch("app.routes.trainer_routes.Member.get_by_id", return_value=MagicMock()), \
         patch("app.routes.trainer_routes.Diet.get_meals", return_value=[]):
        r = client.get("/trainer/diet-plans/1/edit")
        assert r.status_code in (200, 302)


def test_record_progress(client):
    set_session(client, trainer_id=1)
    m = MagicMock(id=1, trainer_id=1, height=180)
    with patch("app.routes.trainer_routes.Member.get_by_id", return_value=m), \
         patch("app.routes.trainer_routes.Progress.save", return_value=1), \
         patch("app.routes.trainer_routes.Progress.get_member_progress", return_value=[]):
        r = client.post("/trainer/clients/1/progress/record", data={"weight": "70"})
        assert r.status_code in (200, 302)


def test_schedule(client):
    set_session(client, trainer_id=1)
    with patch("app.routes.trainer_routes.Attendance.get_trainer_schedule", return_value=[]), \
         patch("app.routes.trainer_routes.Attendance.auto_mark_absent", return_value=None):
        r = client.get("/trainer/schedule")
        assert r.status_code in (200, 302)


def test_workouts(client):
    with patch("app.routes.trainer_routes.Workout.get_all_active", return_value=[]):
        r = client.get("/trainer/workouts")
        assert r.status_code in (200, 302)


def test_add_workout(client):
    set_session(client, trainer_id=1)
    with patch("app.routes.trainer_routes.Workout.save", return_value=1):
        r = client.post("/trainer/workouts/add", data={"name": "Push Ups"})
        assert r.status_code in (200, 302)


def test_workout_plans(client):
    # ✅ Updated to correct missing method name
    with patch("app.routes.trainer_routes.MemberWorkoutPlan.get_all", return_value=[]), \
         patch("app.routes.trainer_routes.Member.get_all_active", return_value=[]), \
         patch("app.routes.trainer_routes.Trainer.get_all_active", return_value=[]):
        r = client.get("/trainer/workout-plans")
        assert r.status_code in (200, 302)


def test_add_workout_plan(client):
    with patch("app.routes.trainer_routes.MemberWorkoutPlan.save", return_value=1), \
         patch("app.routes.trainer_routes.Member.get_all_active", return_value=[]), \
         patch("app.routes.trainer_routes.Trainer.get_all_active", return_value=[]):
        r = client.post("/trainer/workout-plans/add", data={"member_id": 1, "trainer_id": 1, "name": "Plan A"})
        assert r.status_code in (200, 302)


def test_add_workout_plan_detail(client):
    with patch("app.routes.trainer_routes.WorkoutPlanDetail.save", return_value=1), \
         patch("app.routes.trainer_routes.Workout.get_all_active", return_value=[]):
        r = client.post("/trainer/workout-plans/1/add-detail", data={"workout_id": 1, "day_of_week": "2"})
        assert r.status_code in (200, 302)


def test_announcements(client):
    with patch("app.routes.trainer_routes.Announcement.get_for_role", return_value=[]):
        r = client.get("/trainer/announcements")
        assert r.status_code in (200, 302)
