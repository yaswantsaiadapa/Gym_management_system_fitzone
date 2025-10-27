# tests/unit/test_models_member.py
import pytest
from app.models import member

def test_member_fetch_by_id(monkeypatch):
    # patch execute_query to return a fake row
    monkeypatch.setattr(member, "execute_query", lambda q, p=(), db_path=None, fetch=False: [(1,"John","john@example.com")])
    # call the model helper if exists
    if hasattr(member, "get_member_by_id"):
        m = member.get_member_by_id(1)
        assert m is not None
    else:
        pytest.skip("get_member_by_id not found in member.py")
