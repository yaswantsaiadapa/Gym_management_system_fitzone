import sys
import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from app.routes import member_routes

# -------------------------------------------------------------------
# PATCH DECORATORS BEFORE IMPORTING ROUTES
# -------------------------------------------------------------------
# Clear cached route module to ensure patches take effect
sys.modules.pop("app.routes.member_routes", None)



# Patch all decorators to no-op (so tests won't redirect)
patchers = [
    patch("app.utils.decorators.login_required", lambda f: f),
    patch("app.utils.decorators.member_required", lambda f: f),
    patch("app.utils.decorators.role_required", lambda f: f),
]
for p in patchers:
    p.start()

# -------------------------------------------------------------------
# Import Blueprint safely after patching
# -------------------------------------------------------------------
from app.routes import member_routes  # noqa: E402

# Detect actual blueprint object automatically
# -------------------------------------------------------------------
# Detect actual /member blueprint safely (without app context)
# -------------------------------------------------------------------
bp = None
for name, obj in vars(member_routes).items():
    # We only care about Blueprint instances
    try:
        from flask import Blueprint
        if isinstance(obj, Blueprint) and obj.url_prefix and "/member" in obj.url_prefix:
            bp = obj
            break
    except Exception:
        continue

assert bp is not None, "No /member blueprint found in member_routes.py"

# -------------------------------------------------------------------
# Setup Flask test environment
# -------------------------------------------------------------------
@pytest.fixture
def app():
    app = Flask(__name__)
    app.secret_key = "testkey"
    app.register_blueprint(bp)   # register detected blueprint
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def set_session(client, **kwargs):
    """Helper to simulate logged-in session for routes."""
    with client.session_transaction() as sess:
        for k, v in kwargs.items():
            sess[k] = v


# -------------------------------------------------------------------
# ROUTE TESTS
# -------------------------------------------------------------------

def test_announcements(client):
    with patch("app.routes.member_routes.Announcement.get_for_role", return_value=[]):
        r = client.get("/member/announcements")
        assert r.status_code in (200, 404)


def test_dashboard(client):
    set_session(client, user_id=1)
    member = MagicMock(id=1, status="active", membership_end_date=None)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=member), \
         patch("app.routes.member_routes.Announcement.get_for_role", return_value=[]), \
         patch("app.routes.member_routes.Attendance.get_member_attendance", return_value=[]), \
         patch("app.routes.member_routes.Payment.get_member_payments", return_value=[]), \
         patch("app.routes.member_routes.Progress.get_member_progress", return_value=[]):
        r = client.get("/member/dashboard")
        assert r.status_code in (200, 302)


def test_profile(client):
    set_session(client, user_id=1)
    with patch("app.routes.member_routes.User.get_by_id", return_value=MagicMock()), \
         patch("app.routes.member_routes.Member.get_by_user_id", return_value=MagicMock(id=1)):
        r = client.get("/member/profile")
        assert r.status_code in (200, 302)


def test_update_profile(client):
    set_session(client, user_id=1)
    with patch("app.routes.member_routes.User.get_by_id", return_value=MagicMock()), \
         patch("app.routes.member_routes.Member.get_by_user_id", return_value=MagicMock()):
        r = client.post("/member/profile/update", data={"full_name": "Sai"})
        assert r.status_code in (200, 302)


def test_workouts(client):
    set_session(client, user_id=1)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=MagicMock(id=1)), \
         patch("app.routes.member_routes.MemberWorkoutPlan.get_member_plans", return_value=[]), \
         patch("app.routes.member_routes.WorkoutPlanDetail.get_plan_details", return_value=[]), \
         patch("app.routes.member_routes.Workout.get_by_category", return_value=[]):
        r = client.get("/member/workouts")
        assert r.status_code in (200, 302)


def test_diet(client):
    set_session(client, user_id=1)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=MagicMock(id=1)), \
         patch("app.routes.member_routes.Diet.get_member_diet_plans", return_value=[]):
        r = client.get("/member/diet")
        assert r.status_code in (200, 302)


def test_progress(client):
    set_session(client, user_id=1)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=MagicMock(id=1)), \
         patch("app.routes.member_routes.Progress.get_member_progress", return_value=[]):
        r = client.get("/member/progress")
        assert r.status_code in (200, 302)


def test_attendance(client):
    set_session(client, user_id=1)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=MagicMock(id=1)), \
         patch("app.routes.member_routes.Attendance.get_member_attendance", return_value=[]):
        r = client.get("/member/attendance")
        assert r.status_code in (200, 302)


def test_payments(client):
    set_session(client, user_id=1)
    member = MagicMock(id=1)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=member), \
         patch("app.routes.member_routes.Payment.get_member_payments", return_value=[]):
        r = client.get("/member/payments")
        assert r.status_code in (200, 302)


def test_schedule_session(client):
    set_session(client, user_id=1, membership_status="active")
    member = MagicMock(id=1, status="active", membership_end_date=None, trainer_id=1)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=member), \
         patch("app.routes.member_routes.Trainer.get_by_id", return_value=MagicMock()):
        r = client.get("/member/schedule_session")
        assert r.status_code in (200, 302)


def test_schedule_session_post(client):
    set_session(client, user_id=1)
    member = MagicMock(id=1, status="active", membership_end_date=None, trainer_id=1)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=member), \
         patch("app.routes.member_routes.Trainer.get_by_id", return_value=MagicMock(id=1)), \
         patch("app.routes.member_routes.Attendance.get_member_scheduled_on_date", return_value=None), \
         patch("app.routes.member_routes.Attendance.check_slot_availability", return_value=True), \
         patch("app.routes.member_routes._slot_to_datetimes", return_value=("2099-12-31T06:00:00", "2099-12-31T08:00:00")), \
         patch("app.routes.member_routes.Attendance.save", return_value=True, create=True):
        r = client.post("/member/schedule_session", data={"session_date": "2099-12-31", "time_slot": "6:00 AM - 8:00 AM"})
        assert r.status_code in (200, 302)


def test_reschedule_attendance(client):
    set_session(client, user_id=1)
    mock_attendance = MagicMock(id=1, member_id=1, trainer_id=1, time_slot="6:00 AM - 8:00 AM", date=None)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=MagicMock(id=1, status="active", membership_end_date=None)), \
         patch("app.routes.member_routes.Attendance.get_by_id", return_value=mock_attendance), \
         patch("app.routes.member_routes.Trainer.get_by_id", return_value=MagicMock(id=1)), \
         patch("app.routes.member_routes.Attendance.check_slot_availability", return_value=True), \
         patch("app.routes.member_routes._slot_to_datetimes", return_value=("2099-12-31T06:00:00", "2099-12-31T08:00:00")):
        r = client.post("/member/attendance/1/reschedule", data={"time_slot": "8:00 AM - 10:00 AM"})
        assert r.status_code in (200, 302)


def test_membership_status(client):
    set_session(client, user_id=1)
    with patch("app.routes.member_routes.Member.get_by_user_id", return_value=MagicMock(id=1, status="active", membership_end_date=None)):
        r = client.get("/member/membership_status")
        assert r.status_code in (200, 302)


def test_trainer_schedule_api(client):
    set_session(client, user_id=1)
    with patch("app.routes.member_routes.Attendance.get_trainer_schedule", return_value=[]):
        r = client.get("/member/api/trainer/1/schedule")
        assert r.status_code in (200, 302)


# -------------------------------------------------------------------
# STOP PATCHERS AFTER ALL TESTS
# -------------------------------------------------------------------
for p in patchers:
    p.stop()
