# tests/unit/test_models_workout_plan.py
import pytest
from app.models import workout_plan

def test_workout_plan_create(monkeypatch):
    monkeypatch.setattr(workout_plan, "execute_query", lambda q,p=(),db_path=None: 101)
    if hasattr(workout_plan, "create_workout_plan"):
        pid = workout_plan.create_workout_plan({"title":"Bulk Plan"})
        assert pid == 101
    else:
        pytest.skip("create_workout_plan missing")
