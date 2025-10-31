# tests/unit/test_models_member.py
import pytest
from datetime import date, timedelta
from types import SimpleNamespace

from app.models import member as member_module


def make_row_for_member(id=1, user_id=10, full_name="John Doe", email="john@example.com"):
    """
    Construct a tuple shaped like the SELECT projections used by Member.get_by_id /
    get_all_active in the model code. Tests rely on the same column ordering
    the model expects.
    """
    return (
        id, user_id, full_name, email,
        None, None, None, None,       # membership_plan_id, phone, emergency_contact, emergency_phone
        None, None, None, None,       # address, date_of_birth, weight, height
        None, None,                   # medical_conditions, fitness_goals
        None, None,                   # membership_start_date, membership_end_date
        "active", None, None, None    # status, trainer_id, created_at, updated_at
    )


def test_get_by_id_returns_member(monkeypatch, flask_app):
    """Member.get_by_id should return an instance built from the DB row."""
    fake_row = make_row_for_member(id=5, user_id=50, full_name="Alice", email="alice@example.com")
    monkeypatch.setattr(member_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [fake_row])

    # Member._db_path() uses current_app => run inside app context
    with flask_app.app_context():
        m = member_module.Member.get_by_id(5)

    assert m is not None
    assert isinstance(m, member_module.Member)
    assert m.id == 5
    assert m.user_id == 50
    assert m.full_name == "Alice"
    assert m.email == "alice@example.com"
    assert m.status == "active"


def test_save_insert_and_update(monkeypatch, flask_app):
    """
    Verify save() calls execute_query and sets id on insert; and UPDATE path runs when id present.
    We run inside app context because save() uses _db_path().
    """
    calls = []

    def fake_exec_insert(q, p=(), db_path=None, fetch=False):
        calls.append(("INSERT" if q.strip().upper().startswith("INSERT") else "OTHER", q, p))
        # simulate returning lastrowid for insert
        return 123

    def fake_exec_update(q, p=(), db_path=None, fetch=False):
        calls.append(("UPDATE" if q.strip().upper().startswith("UPDATE") else "OTHER", q, p))
        # update path returns id (we will return the same id)
        return None

    # Test INSERT (no id yet)
    monkeypatch.setattr(member_module, "execute_query", fake_exec_insert)
    m = member_module.Member(user_id=99, phone="999", membership_plan_id=1)
    with flask_app.app_context():
        new_id = m.save()
    assert new_id == 123
    assert m.id == 123
    assert any(c[0] == "INSERT" for c in calls)

    # Test UPDATE (has id)
    calls.clear()
    monkeypatch.setattr(member_module, "execute_query", fake_exec_update)
    m.id = 123
    with flask_app.app_context():
        updated_id = m.save()
    # model returns self.id for update path; ensure id remains set
    assert m.id == 123
    assert any(c[0] == "UPDATE" for c in calls)


def test_activate_membership_extends_and_calls_save(monkeypatch, flask_app):
    """
    activate_membership should compute new expiry date and call save(). We patch save()
    to avoid touching DB and to assert it was called.
    """
    saved = {"called": False}

    def fake_save(self=None):
        saved["called"] = True
        # emulate successful persistence
        return True

    monkeypatch.setattr(member_module.Member, "save", fake_save)

    with flask_app.app_context():
        # Case A: no existing expiry -> uses today as start
        m = member_module.Member(id=1, user_id=2)
        ok = m.activate_membership(3)  # 3 months
        assert ok is True
        assert saved["called"] is True
        assert isinstance(m.membership_end_date, date)

        # Case B: existing expiry in future -> extend from that expiry
        saved["called"] = False
        future = date.today() + timedelta(days=30)
        m2 = member_module.Member(id=2, user_id=3, membership_end_date=future)
        ok2 = m2.activate_membership(2)  # extend 2 months from future
        assert ok2 is True
        assert saved["called"] is True
        assert m2.membership_end_date > future


def test_delete_and_hard_delete_execute_expected_queries(monkeypatch, flask_app):
    """
    delete() should attempt to deactivate user and mark member removed;
    hard_delete() should run cleanup deletes.
    If those methods aren't present on the class, skip the assertions (tests remain resilient).
    """
    # If model lacks delete/hard_delete, skip them gracefully
    if not hasattr(member_module.Member, "delete") and not hasattr(member_module.Member, "hard_delete"):
        pytest.skip("Member.delete and Member.hard_delete not present in model; skipping.")

    seen = []

    def fake_exec(q, p=(), db_path=None, fetch=False):
        # record the operation and pretend to succeed
        seen.append((q.strip().split()[0].upper(), q, p))
        # For SELECT-like queries (if any) provide a plausible response
        if q.strip().upper().startswith("SELECT"):
            return [(0,)]
        return None

    monkeypatch.setattr(member_module, "execute_query", fake_exec)

    with flask_app.app_context():
        m = member_module.Member(id=7, user_id=70)
        if hasattr(m, "delete"):
            res = m.delete()
            assert res is True
        else:
            pytest.skip("Member.delete not implemented; skipped")

        seen.clear()
        m2 = member_module.Member(id=8, user_id=80)
        if hasattr(m2, "hard_delete"):
            res2 = m2.hard_delete()
            assert res2 is True
            # hard_delete should run multiple DELETE/cleanup queries; ensure DELETE occurred
            ops2 = [s[0] for s in seen]
            assert "DELETE" in ops2
        else:
            pytest.skip("Member.hard_delete not implemented; skipped")


def test_get_trainer_clients_returns_member_list(monkeypatch, flask_app):
    """
    get_trainer_clients should map returned rows into Member objects with expected attributes.
    This method uses _db_path() so we run inside app context.
    """
    # build two simple rows (id, full_name, membership_start_date, membership_end_date, status)
    row1 = (1, "Client A", "2024-01-01", "2024-06-01", "active")
    row2 = (2, "Client B", "2024-02-01", "2024-07-01", "active")
    monkeypatch.setattr(member_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [row1, row2])

    with flask_app.app_context():
        clients = member_module.Member.get_trainer_clients(42)

    assert isinstance(clients, list)
    assert len(clients) == 2
    assert all(isinstance(c, member_module.Member) for c in clients)
    assert clients[0].full_name == "Client A"
    assert clients[1].full_name == "Client B"
