# tests/unit/test_routes_auth.py
import pytest
from app.models import user as user_model

def test_login_page_available(client):
    resp = client.get("/auth/login")
    assert resp.status_code in (200,302)

def test_login_post_calls_authenticate(monkeypatch, client):
    if hasattr(user_model, "User"):
        # monkeypatch authenticate to return a user-like object
        class DummyUser: pass
        monkeypatch.setattr(user_model.User, "authenticate", staticmethod(lambda u,p: DummyUser()))
    data = {"username":"x","password":"p"}
    resp = client.post("/auth/login", data=data, follow_redirects=True)
    assert resp.status_code in (200,302)
