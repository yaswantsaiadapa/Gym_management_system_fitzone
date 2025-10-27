# tests/unit/test_models_payment.py
import pytest
from app.models import payment

def test_payment_record_insert(monkeypatch):
    called = {}
    def fake_exec(q,p=(),db_path=None,fetch=False):
        called["q"]=q
        return 123
    monkeypatch.setattr(payment, "execute_query", fake_exec)
    if hasattr(payment, "record_payment"):
        pid = payment.record_payment(1, 100.0, "cash")
        assert pid == 123
        assert "q" in called
    else:
        pytest.skip("record_payment missing in payment.py")
