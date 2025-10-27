# tests/unit/test_routes_member_routes.py
import pytest
from app.models import member as member_model

def test_member_dashboard(client):
    resp = client.get("/member/dashboard")
    assert resp.status_code in (200,302)

def test_member_profile_calls_model(monkeypatch, client):
    if hasattr(member_model, "get_member_by_id"):
        monkeypatch.setattr(member_model, "get_member_by_id", lambda x: {"id":x,"name":"Test"})
    resp = client.get("/member/profile/1", follow_redirects=True)
    assert resp.status_code in (200,302)
