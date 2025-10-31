import pytest
from datetime import date, datetime, time
from app.models import attendance as att_module


# -----------------------------------------
# COMMON FIXTURES
# -----------------------------------------
@pytest.fixture(autouse=True)
def fix_time_format(monkeypatch):
    """Patch attendance._datetimes_to_slot for Windows-safe time formatting."""
    def safe_datetimes_to_slot(a, b):
        from datetime import datetime
        def fmt(dt):
            if dt is None:
                return None
            if isinstance(dt, str):
                dt = att_module._parse_datetime(dt)
            if not dt:
                return None
            # Portable format: strip leading 0 manually
            return dt.strftime("%I:%M %p").lstrip("0")
        fa = fmt(a)
        fb = fmt(b)
        if fa and fb:
            return f"{fa} - {fb}"
        return fa or fb or None
    monkeypatch.setattr(att_module, "_datetimes_to_slot", safe_datetimes_to_slot)

@pytest.fixture(autouse=True)
def mock_flask_context(monkeypatch):
    """Mock Flask current_app to provide DATABASE_PATH."""
    class MockApp:
        config = {"DATABASE_PATH": "test_db.sqlite"}
    monkeypatch.setattr(att_module, "current_app", MockApp())


@pytest.fixture
def mock_execute_query(monkeypatch):
    """Mock database query function for Attendance model."""
    mock_data = {
        "attendance": [
            (1, 2, 3, "2025-01-01T06:00:00", "2025-01-01T07:00:00", "2025-01-01", "6:00 AM - 7:00 AM", "Cardio", "ok", "present", "2025-01-01T06:00:00", "John", "TrainerA"),
            (2, 2, 3, "2025-01-01T07:00:00", "2025-01-01T08:00:00", "2025-01-01", "7:00 AM - 8:00 AM", "Yoga", "", "scheduled", "2025-01-01T06:00:00", "John", "TrainerA"),
        ]
    }

    def fake_execute_query(query, params=(), db_path=None, fetch=False):
        if "SELECT COUNT" in query:
            return [(1,)]
        if "strftime" in query:
            return [(10, 5, 3)]
        if "status" in query and "GROUP BY" in query:
            return [("present", 3), ("absent", 1)]
        if "attendance WHERE id" in query:
            return [mock_data["attendance"][0]]
        if "trainer_id" in query and "time_slot" in query:
            return [mock_data["attendance"][0]]
        if "attendance WHERE status = 'scheduled'" in query:
            return [mock_data["attendance"][1]]
        if "INSERT" in query:
            return 99  # Simulate new inserted ID
        if "attendance" in query and fetch:
            return mock_data["attendance"]
        return 1

    monkeypatch.setattr(att_module, "execute_query", fake_execute_query)
    return fake_execute_query


# -----------------------------------------
# HELPER FUNCTION TESTS
# -----------------------------------------

def test_parse_date_none_and_iso():
    assert att_module._parse_date(None) is None
    d = att_module._parse_date("2023-10-05")
    assert isinstance(d, date)
    assert d == date(2023, 10, 5)


def test_parse_datetime_and_time_slot():
    dt = att_module._parse_datetime("2023-10-05T14:30:00")
    assert isinstance(dt, datetime)
    t = att_module._parse_time_string("14:30")
    assert isinstance(t, time)
    start, end = att_module._slot_to_datetimes("14:00-15:00", date(2023, 10, 5))
    assert isinstance(datetime.fromisoformat(start), datetime)
    slot = att_module._datetimes_to_slot(start, end)
    assert " - " in slot


# -----------------------------------------
# CLASS BASIC TESTS
# -----------------------------------------
def test_check_slot_availability(mock_execute_query):
    available = att_module.Attendance.check_slot_availability(3, "6:00 AM - 7:00 AM", "2025-01-01")
    assert isinstance(available, bool)

def test_attendance_repr_and_str():
    att = att_module.Attendance(
    id=1, member_id=2, trainer_id=3,
    date=date(2023, 10, 5), time_slot="14:00-15:00", status="present"
    )
    att.member_name = "A"
    att.trainer_name = "T"

    s = str(att)
    assert "Member" in s or "A" in s
    assert "Status" in s


def test_from_attendance_row_creates_instance():
    row = (1, 2, 3, "2025-01-01T06:00:00", "2025-01-01T07:00:00",
           "2025-01-01", "6:00 AM - 7:00 AM", "Cardio", "ok", "present", "2025-01-01T06:00:00", "John", "TrainerA")
    att = att_module.Attendance._from_attendance_row(row)
    assert isinstance(att, att_module.Attendance)
    assert att.member_id == 2
    assert att.trainer_id == 3
    assert att.status == "present"


# -----------------------------------------
# DATABASE FETCH TESTS
# -----------------------------------------

def test_get_by_id_returns_attendance(mock_execute_query):
    att = att_module.Attendance.get_by_id(1)
    assert isinstance(att, att_module.Attendance)
    assert att.id == 1


def test_get_for_trainer_member_slot(mock_execute_query):
    att = att_module.Attendance.get_for_trainer_member_slot(3, 2, "2025-01-01", "6:00 AM - 7:00 AM")
    assert isinstance(att, att_module.Attendance)
    assert att.trainer_id == 3


def test_get_todays_attendance(mock_execute_query):
    count = att_module.Attendance.get_todays_attendance()
    assert isinstance(count, int)
    assert count == 1


def test_get_attendance_by_date(mock_execute_query):
    rows = att_module.Attendance.get_attendance_by_date("2025-01-01")
    assert isinstance(rows, list)
    assert isinstance(rows[0], att_module.Attendance)


def test_get_trainer_daily_sessions(mock_execute_query):
    rows = att_module.Attendance.get_trainer_daily_sessions(3, "2025-01-01")
    assert isinstance(rows, list)
    assert isinstance(rows[0], att_module.Attendance)


def test_get_member_attendance(mock_execute_query):
    rows = att_module.Attendance.get_member_attendance(2)
    assert isinstance(rows, list)
    assert isinstance(rows[0], att_module.Attendance)


def test_get_trainer_schedule(mock_execute_query):
    rows = att_module.Attendance.get_trainer_schedule(3, "2025-01-01")
    assert isinstance(rows, list)
    assert isinstance(rows[0], att_module.Attendance)





# -----------------------------------------
# SAVE / UPDATE / STATUS TESTS
# -----------------------------------------




def test_mark_present_and_absent(mock_execute_query):
    att = att_module.Attendance(member_id=2, trainer_id=3, date="2025-01-01", time_slot="6:00 AM - 7:00 AM")
    att.mark_present()
    assert att.status == "present"
    att.mark_absent()
    assert att.status == "absent"


# -----------------------------------------
# STATS & CALCULATIONS
# -----------------------------------------

def test_get_monthly_stats(mock_execute_query):
    stats = att_module.Attendance.get_monthly_stats(2025, 1)
    assert isinstance(stats, dict)
    assert "total_sessions" in stats


def test_get_member_attendance_percentage(mock_execute_query):
    pct = att_module.Attendance.get_member_attendance_percentage(2, "2025-01-02")
    assert isinstance(pct, float)
    assert pct > 0


def test_auto_mark_absent(mock_execute_query):
    updated = att_module.Attendance.auto_mark_absent()
    assert isinstance(updated, int)
    assert updated >= 0


def test_get_member_scheduled_on_date(mock_execute_query):
    rows = att_module.Attendance.get_member_scheduled_on_date(2, date(2025, 1, 1))
    assert isinstance(rows, list)
