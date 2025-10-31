# tests/unit/test_routes_admin.py
import pytest
from datetime import date

# We patch dependencies of routes.admin
from app.routes import admin as admin_routes

# Helper to set a logged-in admin in the test client's session
def _login_as_admin(client):
    # Use session_transaction to set session values the decorators check
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
        # any other flags your decorator checks can be set here


@pytest.fixture(autouse=True)
def setup_admin_route_test(monkeypatch):
    """
    Global per-test setup for admin route tests:
      - Prevent TemplateNotFound by returning a simple string from render_template.
      - Make flash a no-op.
      - Provide small, stable fallbacks for items that may be missing in tests.
    """
    # Avoid missing templates by returning a simple string (flask will convert to response)
    monkeypatch.setattr(admin_routes, "render_template", lambda *a, **k: "<html>mocked-template</html>")

    # silence flash calls in tests (no-op)
    monkeypatch.setattr(admin_routes, "flash", lambda *a, **k: None)

    # Ensure url_for/redirect usage inside admin_routes won't blow up if used directly
    # (They probably won't be called if session has user_id, but this is safe fallback)
    try:
        from app.routes import admin as _admin  # noqa: F401
    except Exception:
        pass

    # Nothing to return; fixture is autouse and cleans up automatically


# ----------------------------
# BASIC ROUTE LOADING TESTS
# ----------------------------

def test_dashboard_renders(monkeypatch, flask_app):
    """Ensure /admin/dashboard renders without crashing."""
    monkeypatch.setattr(admin_routes.Payment, "process_pending_payments", staticmethod(lambda **k: None))
    monkeypatch.setattr(admin_routes.Member, "get_count_active", staticmethod(lambda: 10))
    monkeypatch.setattr(admin_routes.Trainer, "get_count_active", staticmethod(lambda: 5))
    monkeypatch.setattr(admin_routes.Attendance, "get_todays_attendance", staticmethod(lambda: 7))
    monkeypatch.setattr(admin_routes.Payment, "get_revenue_stats", staticmethod(lambda **k: {"total_revenue": 1000}))
    monkeypatch.setattr(admin_routes.Payment, "get_pending_payments", staticmethod(lambda: []))
    monkeypatch.setattr(admin_routes.Equipment, "get_working_count", staticmethod(lambda: 2))
    monkeypatch.setattr(admin_routes.Equipment, "get_maintenance_count", staticmethod(lambda: 1))
    monkeypatch.setattr(admin_routes.Member, "get_recent", staticmethod(lambda n: []))
    monkeypatch.setattr(admin_routes.Payment, "get_recent", staticmethod(lambda n: []))
    monkeypatch.setattr(admin_routes.Member, "get_expiring_soon", staticmethod(lambda n: []))
    monkeypatch.setattr(admin_routes.Announcement, "get_all", staticmethod(lambda: []))

    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.get("/admin/dashboard")
        assert resp.status_code in (200, 302)






# ----------------------------
# MEMBER MANAGEMENT
# ----------------------------

def test_add_member_form(monkeypatch, flask_app):
    monkeypatch.setattr(admin_routes.MembershipPlan, "get_all_active", staticmethod(lambda: []))
    monkeypatch.setattr(admin_routes.Trainer, "get_all_with_details", staticmethod(lambda: []))
    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.get("/admin/members/add")
        assert resp.status_code == 200


def test_add_member_post(monkeypatch, flask_app):
    """Simulate successful member creation via POST."""
    monkeypatch.setattr(admin_routes.User, "get_by_username_or_email", staticmethod(lambda u: None))
    # When saving, User.save is an instance method — patch as callable on class returning id
    monkeypatch.setattr(admin_routes.User, "save", staticmethod(lambda self=None: 1))
    monkeypatch.setattr(admin_routes.MembershipPlan, "get_by_id", staticmethod(lambda i: type("Plan", (), {"duration_months": 1, "price": 100})()))
    monkeypatch.setattr(admin_routes.Member, "save", staticmethod(lambda self=None: 10))
    monkeypatch.setattr(admin_routes.Payment, "save", staticmethod(lambda self=None: 1))
    monkeypatch.setattr(admin_routes, "send_welcome_email", lambda *a, **k: None)

    data = {
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "12345",
        "membership_plan_id": "1",
        "trainer_id": "",
    }

    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.post("/admin/members/add", data=data, follow_redirects=True)
        assert resp.status_code in (200, 302)


def test_members_list(monkeypatch, flask_app):
    monkeypatch.setattr(admin_routes.Member, "get_all_with_details", staticmethod(lambda: []))
    monkeypatch.setattr(admin_routes.MembershipPlan, "get_all_active", staticmethod(lambda: []))
    monkeypatch.setattr(admin_routes.Trainer, "get_all_active", staticmethod(lambda: []))

    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.get("/admin/members")
        assert resp.status_code in (200, 302)


# ----------------------------
# TRAINER MANAGEMENT
# ----------------------------

def test_add_trainer_post(monkeypatch, flask_app):
    monkeypatch.setattr(admin_routes.User, "get_by_username", staticmethod(lambda u: None))
    monkeypatch.setattr(admin_routes.User, "save", staticmethod(lambda self=None: 1))
    monkeypatch.setattr(admin_routes.Trainer, "save", staticmethod(lambda self=None: 2))
    monkeypatch.setattr(admin_routes, "send_welcome_email", lambda *a, **k: None)

    data = {
        "full_name": "Jane Trainer",
        "email": "jane@example.com",
        "phone": "12345",
        "specialization": "Yoga"
    }
    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.post("/admin/trainers/add", data=data, follow_redirects=True)
        assert resp.status_code in (200, 302)


def test_trainers_list(monkeypatch, flask_app):
    monkeypatch.setattr(admin_routes.Trainer, "get_all_with_details", staticmethod(lambda: []))
    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.get("/admin/trainers")
        assert resp.status_code in (200, 302)


# ----------------------------
# ANNOUNCEMENTS
# ----------------------------

def test_add_announcement(monkeypatch, flask_app):
    monkeypatch.setattr(admin_routes.Announcement, "save", staticmethod(lambda self=None: 1))
    # session is set on the client; do not monkeypatch the module-level session object.
    data = {
        "title": "Test Announcement",
        "content": "Body",
        "announcement_type": "info",
        "target_audience": "all",
        "is_public": "on",
        "start_date": date.today().strftime("%Y-%m-%d"),
    }
    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.post("/admin/announcements/add", data=data, follow_redirects=True)
        assert resp.status_code in (200, 302)


def test_announcement_list(monkeypatch, flask_app):
    monkeypatch.setattr(admin_routes.Announcement, "get_all", staticmethod(lambda: []))
    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.get("/admin/announcements")
        assert resp.status_code in (200, 302)


# ----------------------------
# REPORTS & RENEWALS
# ----------------------------

def test_reports_view(monkeypatch, flask_app):
    monkeypatch.setattr(admin_routes.Member, "get_statistics", staticmethod(lambda: {"active": 5}))
    monkeypatch.setattr(admin_routes.Payment, "get_revenue_stats", staticmethod(lambda **k: {"total_revenue": 500}))
    monkeypatch.setattr(admin_routes.Attendance, "get_monthly_stats", staticmethod(lambda y, m: {"total_sessions": 20, "present": 15, "attendance_rate": 75}))
    monkeypatch.setattr(admin_routes, "execute_query", staticmethod(lambda *a, **k: []))
    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.get("/admin/reports")
        assert resp.status_code in (200, 302)


def test_send_renewal_reminders(monkeypatch, flask_app):
    member = type("M", (), {
        "email": "m@x.com",
        "full_name": "M",
        "membership_end_date": date.today(),
    })()
    monkeypatch.setattr(admin_routes.Member, "get_expiring_soon", staticmethod(lambda d: [member]))
    monkeypatch.setattr(admin_routes, "send_membership_renewal_reminder", lambda *a, **k: None)

    with flask_app.test_client() as client:
        _login_as_admin(client)
        resp = client.post("/admin/send-renewal-reminders", follow_redirects=True)
        assert resp.status_code in (200, 302)
