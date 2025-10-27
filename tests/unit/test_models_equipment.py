# tests/unit/test_models_equipment.py
import pytest
from app.models import equipment

def test_equipment_save_calls_db(monkeypatch, flask_app):
    calls = {}
    def fake_exec(query, params=(), db_path=None, fetch=False):
        calls['q'] = query
        return 10
    monkeypatch.setattr(equipment, "execute_query", fake_exec)

    eq = equipment.Equipment(name="Treadmill", category="cardio")
    with flask_app.app_context():
        new_id = eq.save()
    assert new_id == 10 or new_id is not None
    assert 'q' in calls
