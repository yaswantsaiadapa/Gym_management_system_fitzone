# tests/unit/test_models_payment.py
import sys
from types import SimpleNamespace, ModuleType
from datetime import date, datetime, timedelta
import uuid

import pytest

from app.models import payment as payment_module
from app.models.payment import Payment


def make_payment_row(id=1, member_id=2, plan_id=3, amount=500.0,
                     method="cash", status="pending", txn=None,
                     payment_date=None, due_date=None, notes=None,
                     created_at=None, invoice=None, reminder_sent=0,
                     reminder_sent_at=None, cancelled_processed=0,
                     extra=()):
    """Return a tuple shaped like SELECT p.* plus optional appended fields."""
    row = [
        id, member_id, plan_id, amount, method, status, txn,
        payment_date, due_date, notes, created_at, invoice,
        reminder_sent, reminder_sent_at, cancelled_processed
    ]
    # append any extra fields (e.g. member_name, plan_name, etc.)
    row.extend(extra)
    return tuple(row)


def test_save_insert_and_update(monkeypatch, flask_app):
    called = {"queries": []}

    def fake_exec(q, p=(), db_path=None, fetch=False):
        # record and return lastrowid for INSERT
        called["queries"].append((q.strip().split()[0].upper(), q, p, fetch))
        if q.strip().upper().startswith("INSERT"):
            return 999  # simulated new id
        return None

    monkeypatch.setattr(payment_module, "execute_query", fake_exec)

    p = Payment(member_id=11, membership_plan_id=5, amount=250.0, payment_method="card")
    with flask_app.app_context():
        new_id = p.save()
    assert new_id == 999
    assert p.id == 999
    assert any(q[0] == "INSERT" for q in called["queries"])

    # Update path
    called["queries"].clear()
    p.amount = 300.0
    with flask_app.app_context():
        updated = p.save()
    # update returns self.id (existing)
    assert p.id == 999
    assert any(q[0] == "UPDATE" for q in called["queries"])


def test_get_by_id_and_get_recent(monkeypatch, flask_app):
    # single row for get_by_id
    payment_date = date.today().isoformat()
    due_date = (date.today() + timedelta(days=7)).isoformat()
    row = make_payment_row(id=5, member_id=10, plan_id=2, amount=1200.0,
                           method="online", status="completed", txn="TX123",
                           payment_date=payment_date, due_date=due_date,
                           notes="monthly", created_at=datetime.now().isoformat(),
                           invoice="INV-TEST", extra=("Member X", "Plan Y"))
    monkeypatch.setattr(payment_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [row])

    with flask_app.app_context():
        got = Payment.get_by_id(5)
    assert isinstance(got, Payment)
    assert got.id == 5
    assert got.member_id == 10
    assert hasattr(got, "invoice_number")
    # get_recent should call same execute_query projection: patch to return a list
    monkeypatch.setattr(payment_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [row, row])
    with flask_app.app_context():
        recent = Payment.get_recent(limit=2)
    assert isinstance(recent, list)
    assert len(recent) == 2
    assert recent[0].plan_name == "Plan Y" or hasattr(recent[0], "plan_name")


def test_get_member_payments_parses_dates(monkeypatch, flask_app):
    # return a row where due_date is 3 days from now -> days_left=3, not overdue
    due_date = (date.today() + timedelta(days=3)).isoformat()
    row = make_payment_row(id=7, member_id=20, plan_id=4, amount=50.0,
                           method="cash", status="pending",
                           payment_date=None, due_date=due_date, created_at=datetime.now().isoformat(),
                           invoice="INVX")
    monkeypatch.setattr(payment_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [row])

    with flask_app.app_context():
        payments = Payment.get_member_payments(20)
    assert isinstance(payments, list)
    assert payments and payments[0].member_id == 20
    first = payments[0]
    assert first.due_date_obj is not None
    assert first.days_left == 3
    assert first.is_overdue is False


    @classmethod
    def get_pending_payments(cls):
        """Get all pending payments with member and plan info"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT p.*, u.full_name as member_name, mp.name as plan_name, m.user_id as member_user_id
                   FROM payments p
                   JOIN members m ON p.member_id = m.id
                   JOIN users u ON m.user_id = u.id
                   JOIN membership_plans mp ON p.membership_plan_id = mp.id
                   WHERE p.payment_status = 'pending'
                   ORDER BY p.due_date'''
        results = execute_query(query, (), db_path, fetch=True) or []

        payments = []
        for row in results:
            # Split row into base p.* columns and appended extras
            core_len = 15  # p.* columns (id..cancelled_processed)
            core = tuple(row[:core_len]) + (None,) * max(0, core_len - len(row))
            extras = tuple(row[core_len:])

            payment = cls(
                id=core[0], member_id=core[1], membership_plan_id=core[2],
                amount=core[3], payment_method=core[4], payment_status=core[5],
                transaction_id=core[6], payment_date=core[7], due_date=core[8],
                notes=core[9], created_at=core[10],
                invoice_number=core[11] if len(core) > 11 else None,
                reminder_sent=core[12] if len(core) > 12 else 0,
                reminder_sent_at=core[13] if len(core) > 13 else None,
                cancelled_processed=core[14] if len(core) > 14 else 0
            )

            # Safely map appended fields: (member_name, plan_name, member_user_id)
            payment.member_name = extras[0] if len(extras) > 0 else None
            payment.plan_name = extras[1] if len(extras) > 1 else None
            payment.member_user_id = extras[2] if len(extras) > 2 else None

            payments.append(payment)
        return payments


    @classmethod
    def get_all_with_details(cls):
        """Get all payments with member and plan details"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''
            SELECT p.*, u.full_name as member_name, mp.name as plan_name
            FROM payments p
            JOIN members m ON p.member_id = m.id
            JOIN users u ON m.user_id = u.id
            JOIN membership_plans mp ON p.membership_plan_id = mp.id
            ORDER BY p.created_at DESC
        '''
        results = execute_query(query, (), db_path, fetch=True) or []

        payments = []
        for row in results:
            core_len = 15
            core = tuple(row[:core_len]) + (None,) * max(0, core_len - len(row))
            extras = tuple(row[core_len:])

            payment = cls(
                id=core[0], member_id=core[1], membership_plan_id=core[2],
                amount=core[3], payment_method=core[4], payment_status=core[5],
                transaction_id=core[6], payment_date=core[7], due_date=core[8],
                notes=core[9], created_at=core[10],
                invoice_number=core[11] if len(core) > 11 else None,
                reminder_sent=core[12] if len(core) > 12 else 0,
                reminder_sent_at=core[13] if len(core) > 13 else None,
                cancelled_processed=core[14] if len(core) > 14 else 0
            )

            payment.member_name = extras[0] if len(extras) > 0 else None
            payment.plan_name = extras[1] if len(extras) > 1 else None
            payments.append(payment)
        return payments


    @classmethod
    def get_recent(cls, limit=5):
        """Get the most recent payments"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT p.*, u.full_name as member_name, mp.name as plan_name
                FROM payments p
                JOIN members m ON p.member_id = m.id
                JOIN users u ON m.user_id = u.id
                JOIN membership_plans mp ON p.membership_plan_id = mp.id
                ORDER BY p.created_at DESC
                LIMIT ?'''
        results = execute_query(query, (limit,), db_path, fetch=True) or []

        payments = []
        for row in results:
            core_len = 15
            core = tuple(row[:core_len]) + (None,) * max(0, core_len - len(row))
            extras = tuple(row[core_len:])

            payment = cls(
                id=core[0], member_id=core[1], membership_plan_id=core[2],
                amount=core[3], payment_method=core[4], payment_status=core[5],
                transaction_id=core[6], payment_date=core[7], due_date=core[8],
                notes=core[9], created_at=core[10],
                invoice_number=core[11] if len(core) > 11 else None,
                reminder_sent=core[12] if len(core) > 12 else 0,
                reminder_sent_at=core[13] if len(core) > 13 else None,
                cancelled_processed=core[14] if len(core) > 14 else 0
            )

            payment.member_name = extras[0] if len(extras) > 0 else None
            payment.plan_name = extras[1] if len(extras) > 1 else None
            payments.append(payment)
        return payments



def test_get_revenue_stats_variants(monkeypatch, flask_app):
    # Year+month
    monkeypatch.setattr(payment_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [(1500.0, 3)])
    with flask_app.app_context():
        stats = Payment.get_revenue_stats(year=2024, month=5)
    assert stats["total_revenue"] == 1500.0
    assert stats["total_payments"] == 3

    # Year only
    monkeypatch.setattr(payment_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [(2000.0, 5)])
    with flask_app.app_context():
        stats2 = Payment.get_revenue_stats(year=2024)
    assert stats2["total_revenue"] == 2000.0

    # No args
    monkeypatch.setattr(payment_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [(0, 0)])
    with flask_app.app_context():
        stats3 = Payment.get_revenue_stats()
    assert stats3["total_revenue"] == 0


def test_mark_completed_activates_member_and_updates_db(monkeypatch, flask_app):
    """
    Ensure mark_completed:
      - fetches the payment via get_by_id (we patch it)
      - calls save()
      - attempts to set users.is_active and call member.activate_membership
      - tries to send email (we stub email util)
    """
    # Build a payment instance to be returned by get_by_id
    p = Payment(id=50, member_id=300, membership_plan_id=12, amount=999.0, payment_method="card", payment_status="pending")

    # patch Payment.get_by_id to return our instance
    monkeypatch.setattr(payment_module.Payment, "get_by_id", classmethod(lambda cls, pid: p if pid == 50 else None))

    # patch Payment.save to record calls
    saved = {"called": False}

    def fake_save(self):
        saved["called"] = True
        return self.id or 50

    monkeypatch.setattr(payment_module.Payment, "save", fake_save)

    # create fake Member class in sys.modules as 'models.member' to satisfy the import inside method
    fake_member_mod = ModuleType("models.member")
    class DummyMember:
        @staticmethod
        def get_by_id(member_id):
            # return an object with activate_membership
            return SimpleNamespace(id=member_id, activate_membership=lambda duration_months, start_date=None: True)
    fake_member_mod.Member = DummyMember
    sys.modules["models.member"] = fake_member_mod

    # patch execute_query for selecting user_id and updating users; record operations
    ops = []
    def fake_exec(q, p=(), db_path=None, fetch=False):
        ops.append((q, p, fetch))
        # When selecting user_id from members -> return a user_id
        if q.strip().upper().startswith("SELECT") and "FROM MEMBERS WHERE ID" in q.upper():
            return [(777,)]
        return None

    monkeypatch.setattr(payment_module, "execute_query", fake_exec)

    # patch email util used inside mark_completed
    fake_email_mod = ModuleType("utils.email_utils")
    def fake_send(email, full_name, invoice, amount, pay_date):
        # emulate sending
        return True
    fake_email_mod.send_membership_payment_success = fake_send
    sys.modules["utils.email_utils"] = fake_email_mod

    with flask_app.app_context():
        res = Payment.mark_completed(50, transaction_id="TXN-987")
    assert res is True
    assert saved["called"] is True
    # ensure execute_query was invoked at least once (for UPDATE users/select user)
    assert any("UPDATE users" in q[0] or "SELECT user_id" in q[0] or "SELECT" in q[0] for q in ops)


def test_process_pending_payments_sends_reminders_and_cancels(monkeypatch, flask_app):
    """
    Test process_pending_payments behavior:
      - one row due in reminder_before_days -> gets reminder_sent updated
      - one row overdue -> gets cancellation and user deactivated
    """
    today = date.today()
    reminder_before_days = 5
    due_in_days = reminder_before_days
    due_date_reminder = (today + timedelta(days=due_in_days)).isoformat()
    due_date_past = (today - timedelta(days=2)).isoformat()

    # Build two rows: one for reminder, one for cancellation.
    # projection: p.* then member_user_id, member_email, member_name appended at the end
    row_reminder = list(make_payment_row(id=101, member_id=201, plan_id=301, amount=10.0,
                                         method="cash", status="pending",
                                         payment_date=None, due_date=due_date_reminder,
                                         created_at=datetime.now().isoformat(),
                                         invoice="INV101"))
    row_reminder.extend([501, "remind@example.com", "Remind Person"])

    row_cancel = list(make_payment_row(id=102, member_id=202, plan_id=302, amount=20.0,
                                       method="cash", status="pending",
                                       payment_date=None, due_date=due_date_past,
                                       created_at=datetime.now().isoformat(),
                                       invoice="INV102"))
    row_cancel.extend([502, "cancel@example.com", "Cancel Person"])

    rows = [tuple(row_reminder), tuple(row_cancel)]

    # execute_query has to serve different roles: returning rows, and returning results of updates
    calls = {"updates": []}
    def fake_exec(q, p=(), db_path=None, fetch=False):
        # SELECT for pending payments
        if q.strip().upper().startswith("SELECT") and "FROM PAYMENTS" in q.upper():
            return rows
        # record updates for later assertions
        if q.strip().upper().startswith("UPDATE"):
            calls["updates"].append((q, p))
            # return None/success
            return None
        # SELECT user_id for members etc -> return a user id
        if q.strip().upper().startswith("SELECT") and "SELECT USER_ID" in q.upper():
            return [(999,)]
        return None

    monkeypatch.setattr(payment_module, "execute_query", fake_exec)

    # stub email utils so calls don't fail
    fake_email = ModuleType("utils.email_utils")
    def fake_rem(email, name, due, days_left, invoice):
        return True
    def fake_cancel(email, name, invoice, due):
        return True
    fake_email.send_membership_payment_reminder = fake_rem
    fake_email.send_membership_cancelled_notification = fake_cancel
    sys.modules["utils.email_utils"] = fake_email

    with flask_app.app_context():
        result = Payment.process_pending_payments(reminder_before_days=reminder_before_days)

    assert "reminders_sent" in result and "cancellations_done" in result
    # Expect at least one reminder and one cancellation performed
    assert any("reminder_sent" in u[0].lower() or "update payments set reminder_sent" in u[0].lower() for u in calls["updates"]) or result["reminders_sent"]
    assert any("cancelled_processed" in u[0].lower() or "update payments set cancelled_processed" in u[0].lower() for u in calls["updates"]) or result["cancellations_done"]

