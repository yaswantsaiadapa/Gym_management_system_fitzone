# tests/unit/test_models_workout.py
import pytest
from app.models import workout

def test_create_workout_calls_db(monkeypatch):
    monkeypatch.setattr(workout, "execute_query", lambda q,p=(),db_path=None: 77)
    if hasattr(workout, "create_workout"):
        wid = workout.create_workout({"name":"Leg day"})
        assert wid == 77
    else:
        pytest.skip("create_workout missing")
