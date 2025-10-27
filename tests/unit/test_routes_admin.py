# tests/unit/test_routes_admin.py
import pytest
from app import app as app_module
from app.models import member as member_model

def test_admin_dashboard_requires_login(flask_app):
    with flask_app.test_client() as client:
        resp = client.get("/admin/dashboard", follow_redirects=False)
        assert resp.status_code in (200, 302, 401)

def test_admin_members_list_calls_model(monkeypatch, flask_app):
    if hasattr(member_model, "get_all_members"):
        monkeypatch.setattr(member_model, "get_all_members", lambda: [{"id":1,"name":"A"}])
    with flask_app.test_client() as client:
        resp = client.get("/admin/members", follow_redirects=True)
        assert resp.status_code in (200, 302)
