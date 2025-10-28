import pytest
from flask import Flask, render_template_string
from unittest.mock import MagicMock, patch
from app.routes import admin


@pytest.fixture
def client(monkeypatch):
    """Create a Flask test client with admin blueprint registered and mocks"""
    app = Flask("test_routes_admin")
    app.secret_key = "test_key"
    app.config["TESTING"] = True

    # ✅ mock login and admin decorators globally
    import app.utils.decorators as decorators
    decorators.login_required = lambda f: f
    decorators.admin_required = lambda f: f

    # ✅ monkeypatch render_template to avoid TemplateNotFound
    monkeypatch.setattr(
        "flask.render_template",
        lambda template_name, **context: render_template_string(
            f"<h1>Rendered {template_name}</h1>"
        ),
    )

    # ✅ register the admin blueprint
    app.register_blueprint(admin.admin_bp)

    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def mock_models(monkeypatch):
    """Prevent real database calls"""
    models = [
        "Member", "Trainer", "Payment", "Equipment",
        "MembershipPlan", "Announcement", "Attendance"
    ]
    fake_methods = [
        "get_all", "get_by_id", "save", "update",
        "get_all_with_details", "get_all_active",
        "get_recent", "get_statistics", "get_pending_payments",
        "get_revenue_stats", "get_working_count", "get_maintenance_count",
        "get_todays_attendance", "get_count_active", "get_expiring_soon"
    ]
    for model_name in models:
        if hasattr(admin, model_name):
            model = getattr(admin, model_name)
            for fn in fake_methods:
                if hasattr(model, fn):
                    monkeypatch.setattr(model, fn, MagicMock(return_value=[]))

    monkeypatch.setattr(admin, "send_welcome_email", MagicMock(return_value=True))
    monkeypatch.setattr(admin, "send_membership_renewal_reminder", MagicMock(return_value=True))


def test_dashboard_route(client):
    res = client.get("/admin/dashboard")
    assert res.status_code == 200
    assert b"Rendered" in res.data


def test_equipment_route(client):
    res = client.get("/admin/equipment")
    assert res.status_code == 200


def test_members_route(client):
    res = client.get("/admin/members")
    assert res.status_code == 200


def test_add_equipment_post(client):
    data = {
        "name": "Treadmill",
        "category": "Cardio",
        "brand": "ProFit",
        "model": "TM-2000",
        "purchase_date": "2024-01-01",
        "warranty_end_date": "2025-01-01",
        "status": "working",
        "location": "Main Hall"
    }
    res = client.post("/admin/equipment/add", data=data, follow_redirects=True)
    assert res.status_code in (200, 302)


def test_payments_page(client):
    res = client.get("/admin/payments")
    assert res.status_code == 200


def test_renew_reminders_post(client):
    res = client.post("/admin/send-renewal-reminders", follow_redirects=True)
    assert res.status_code in (200, 302)


def test_membership_plans_page(client):
    res = client.get("/admin/membership-plans")
    assert res.status_code == 200
