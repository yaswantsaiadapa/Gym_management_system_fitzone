# tests/unit/test_models_progress.py
from types import SimpleNamespace
from datetime import date, datetime, timedelta
import pytest

from app.models import progress as progress_module
from app.models.progress import Progress


def make_row_for_member_progress(
    id=1, member_id=2, recorded_date=None, weight=70.0,
    body_fat_percentage=18.5, muscle_mass=40.0, bmi=22.2,
    chest=90.0, waist=75.0, hips=95.0, bicep=30.0, thigh=50.0,
    notes="note", photo_path="/path.jpg", recorded_by=10, recorded_by_name="Trainer X"
):
    recorded_date_val = recorded_date or date.today().isoformat()
    # mp.* columns (15 entries in this helper: id..recorded_by)
    row = [
        id, member_id, recorded_date_val, weight, body_fat_percentage, muscle_mass,
        bmi, chest, waist, hips, bicep, thigh, notes, photo_path, recorded_by
    ]
    # append recorded_by_name for the LEFT JOIN
    row.append(recorded_by_name)
    return tuple(row)


def make_row_for_trainer_progress(
    id=1, member_id=2, recorded_date=None, weight=70.0, recorded_by=10, member_name="Member X"
):
    recorded_date_val = recorded_date or date.today().isoformat()
    row = [
        id, member_id, recorded_date_val, weight, None, None,
        None, None, None, None, None, None, None, None, recorded_by
    ]
    row.append(member_name)
    return tuple(row)


def test_get_by_id_returns_progress(monkeypatch, flask_app):
    fake_row = make_row_for_member_progress(
        id=5, member_id=42, recorded_date="2024-10-01", weight=82.5, recorded_by=99, recorded_by_name="Ravi"
    )
    monkeypatch.setattr(progress_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [fake_row])

    with flask_app.app_context():
        p = Progress.get_by_id(5)

    assert isinstance(p, Progress)
    assert p.id == 5
    assert p.member_id == 42
    assert isinstance(p.recorded_date, (date,))
    assert p.weight == 82.5
    assert p.recorded_by == 99
    assert p.recorded_by_name == "Ravi"


def test_get_member_progress_returns_list_and_limit_applies(monkeypatch, flask_app):
    r1 = make_row_for_member_progress(id=11, member_id=7, recorded_date="2024-09-01", weight=60.0, recorded_by_name="T1")
    r2 = make_row_for_member_progress(id=12, member_id=7, recorded_date="2024-08-01", weight=61.0, recorded_by_name="T2")
    monkeypatch.setattr(progress_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [r1, r2])

    with flask_app.app_context():
        all_rec = Progress.get_member_progress(7)
        limited = Progress.get_member_progress(7, limit=1)

    assert isinstance(all_rec, list)
    assert len(all_rec) == 2
    assert all_rec[0].member_id == 7
    assert all_rec[0].recorded_by_name == "T1"
    assert isinstance(limited, list)


def test_get_trainer_client_progress_returns_member_name(monkeypatch, flask_app):
    row = make_row_for_trainer_progress(id=21, member_id=33, recorded_date="2024-06-01", weight=75.0, member_name="Client A")
    monkeypatch.setattr(progress_module, "execute_query", lambda q, p=(), db_path=None, fetch=False: [row])

    with flask_app.app_context():
        recs = Progress.get_trainer_client_progress(trainer_id=9)

    assert isinstance(recs, list)
    assert len(recs) == 1
    assert recs[0].member_id == 33
    assert recs[0].member_name == "Client A"


def test_save_insert_sets_id_and_calls_db(monkeypatch, flask_app):
    calls = {"queries": []}

    def fake_exec(q, p=(), db_path=None, fetch=False):
        calls["queries"].append((q, p, fetch))
        if str(q).strip().upper().startswith("INSERT"):
            return 501
        return None

    monkeypatch.setattr(progress_module, "execute_query", fake_exec)

    p = Progress(member_id=77, recorded_date="2024-01-01", weight=88.0, recorded_by=5)
    with flask_app.app_context():
        new_id = p.save()

    assert new_id == 501
    assert p.id == 501
    assert any("INSERT" in q[0].upper() for q in calls["queries"])


def test_save_update_path_calls_update(monkeypatch, flask_app):
    calls = {"queries": []}

    def fake_exec(q, p=(), db_path=None, fetch=False):
        calls["queries"].append((q, p, fetch))
        return None

    monkeypatch.setattr(progress_module, "execute_query", fake_exec)

    p = Progress(id=888, member_id=77, recorded_date="2024-01-01", weight=70.0, recorded_by=5)
    with flask_app.app_context():
        res = p.save()

    assert res == 888
    assert any("UPDATE" in q[0].upper() for q in calls["queries"])


def test_delete_calls_db_with_correct_query(monkeypatch, flask_app):
    recorded = {"called": False, "query": None, "params": None}

    def fake_exec(q, p=(), db_path=None, fetch=False):
        recorded["called"] = True
        recorded["query"] = q
        recorded["params"] = p
        return None

    monkeypatch.setattr(progress_module, "execute_query", fake_exec)

    with flask_app.app_context():
        Progress.delete(1234)

    assert recorded["called"] is True
    # robust, compare upper-case forms
    assert "DELETE FROM MEMBER_PROGRESS" in recorded["query"].upper()
    assert recorded["params"] == (1234,)


def test_to_date_helper_handles_invalid_strings():
    assert Progress._to_date("2024-12-01") == date(2024, 12, 1)
    assert Progress._to_date("not-a-date") is None
    d = date.today()
    assert Progress._to_date(d) == d
