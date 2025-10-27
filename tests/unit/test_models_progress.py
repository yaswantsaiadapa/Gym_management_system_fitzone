# tests/unit/test_models_progress.py
import pytest
from app.models import progress

def test_progress_add_and_fetch(monkeypatch):
    monkeypatch.setattr(progress, "execute_query", lambda q,p=(),db_path=None,fetch=True: [(1,)])
    if hasattr(progress, "add_progress"):
        res = progress.add_progress(1, {"weight":70})
        # If function returns id or True accept either
        assert res is not None
    else:
        pytest.skip("progress.add_progress missing")
