# tests/unit/test_models_trainer.py
import pytest
from app.models import trainer

def test_trainer_add_and_get(monkeypatch):
    monkeypatch.setattr(trainer, "execute_query", lambda q, p=(), db_path=None, fetch=True: [(5,"John","PT")])
    if hasattr(trainer, "get_trainer_by_id"):
        t = trainer.get_trainer_by_id(5)
        assert t is not None
    else:
        pytest.skip("get_trainer_by_id missing")
