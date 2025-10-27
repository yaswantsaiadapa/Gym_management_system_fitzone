# tests/unit/test_routes_trainer_routes.py
import pytest
from app.models import trainer as trainer_model

def test_trainer_dashboard(client):
    resp = client.get("/trainer/dashboard")
    assert resp.status_code in (200,302)

def test_trainer_view_calls_model(monkeypatch, client):
    if hasattr(trainer_model, "get_trainer_by_id"):
        monkeypatch.setattr(trainer_model, "get_trainer_by_id", lambda x: {"id":x,"name":"T"})
    resp = client.get("/trainer/profile/1", follow_redirects=True)
    assert resp.status_code in (200,302)
