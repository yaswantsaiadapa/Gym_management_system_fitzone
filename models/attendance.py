# models/attendance.py
from .database import execute_query
from flask import current_app
from datetime import date, datetime, time as dtime

def _parse_date(d):
    """Return a date object for ISO-like strings or human-readable formats."""
    if not d or str(d).strip() == "":
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    s = str(d).strip()
    # Try ISO formats first
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        pass
    # Try multiple known formats
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def _parse_datetime(d):
    """Return a datetime object for ISO-like strings or datetime objects, else None."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d
    try:
        return datetime.fromisoformat(str(d))
    except Exception:
        try:
            return datetime.strptime(str(d), "%Y-%m-%d %H:%M:%S")
        except Exception:
            # try timestamp-only like "YYYY-MM-DDTHH:MM:SS" handled by fromisoformat above
            return None

def _parse_time_string(ts):
    """
    Parse a time like '6:00 AM' or '18:30' into a datetime.time.
    If parsing fails, return None.
    """
    if not ts:
        return None
    ts = str(ts).strip()
    for fmt in ("%I:%M %p", "%H:%M", "%I %p", "%I:%M%p"):
        try:
            return datetime.strptime(ts, fmt).time()
        except Exception:
            continue
    return None

def _slot_to_datetimes(slot_label, on_date=None):
    """
    Convert slot label like '6:00 AM - 8:00 AM' into two datetime ISO strings:
    (check_in_iso, check_out_iso). If parsing fails, return (None, None).
    - on_date: date object or None (defaults to today)
    """
    if not slot_label:
        return (None, None)
    if on_date is None:
        on_date = date.today()
    # split on common separators
    parts = None
    for sep in [" - ", "-", " to ", "–"]:
        if sep in slot_label:
            parts = [p.strip() for p in slot_label.split(sep, 1)]
            break
    if not parts:
        # can't detect two times; try to parse as single time
        t = _parse_time_string(slot_label)
        if t:
            dt = datetime.combine(on_date, t)
            return (dt.isoformat(), None)
        return (None, None)

    start_raw, end_raw = parts[0], parts[1]
    t1 = _parse_time_string(start_raw)
    t2 = _parse_time_string(end_raw)
    if not t1 and not t2:
        return (None, None)

    # if parse succeeded for one or both, combine with date
    dt1 = datetime.combine(on_date, t1) if t1 else None
    dt2 = datetime.combine(on_date, t2) if t2 else None
    return (dt1.isoformat() if dt1 else None, dt2.isoformat() if dt2 else None)

def _datetimes_to_slot(check_in_iso, check_out_iso):
    """
    Convert two ISO datetimes (strings or datetime) to a label like '6:00 AM - 8:00 AM'.
    If only one present, return single time like '6:00 AM'.
    """
    def fmt(dt):
        if dt is None:
            return None
        if isinstance(dt, str):
            dt = _parse_datetime(dt)
        if not dt:
            return None
        return dt.strftime("%-I:%M %p") if hasattr(dt, "strftime") else str(dt)

    a = fmt(check_in_iso)
    b = fmt(check_out_iso)
    if a and b:
        return f"{a} - {b}"
    return a or b or None

class Attendance:
    def __init__(self, id=None, member_id=None, trainer_id=None,
                 time_slot=None, check_in_time=None, check_out_time=None,
                 date=None, workout_type=None, notes=None,
                 status='present', created_at=None, updated_at=None):
        # Keep time_slot and check_in/check_out both available.
        self.id = id
        self.member_id = member_id
        self.trainer_id = trainer_id
        self.time_slot = time_slot  # descriptive slot label
        # store parsed datetimes internally
        self.check_in_time = _parse_datetime(check_in_time)
        self.check_out_time = _parse_datetime(check_out_time)
        self.date = _parse_date(date)
        self.workout_type = workout_type
        self.notes = notes
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

        # extras added by JOINs
        self.member_name = None
        self.trainer_name = None

    @classmethod
    def _db_path(cls):
        return current_app.config.get('DATABASE_PATH', 'gym_management.db')

    @classmethod
    def _from_attendance_row(cls, row, extras_order=None):
        """
        Build an Attendance from a DB row tuple.
        Defensive about column ordering/length.
        Handles joins with member_name, trainer_name, and time_slot.
        """
        if not row:
            return None

        # --- Base mapping (attendance table has 11 cols, no updated_at) ---
        base_len = min(len(row), 11)
        base = list(row[:base_len]) + [None] * (11 - base_len)

        id_ = base[0]
        member_id = base[1]
        trainer_id = base[2]
        col3, col4, col5 = base[3], base[4], base[5]

        time_slot_val = None
        check_in_val = None
        check_out_val = None
        date_val = base[6]
        workout_type = base[7]
        notes = base[8]
        status = base[9]
        created_at = base[10]

        # --- Heuristic: detect if col3 is a time slot string vs datetime ---
        if isinstance(col3, str) and any(x in col3.upper() for x in ("AM", "PM", "-")):
            time_slot_val = col3
            check_in_val, check_out_val = col4, col5
        else:
            check_in_val, check_out_val = col3, col4
            if isinstance(col5, str) and any(x in col5.upper() for x in ("AM", "PM", "-")):
                time_slot_val = col5

        # --- Derive time_slot if missing ---
        if not time_slot_val:
            time_slot_val = _datetimes_to_slot(check_in_val, check_out_val)

        att = cls(
            id=id_,
            member_id=member_id,
            trainer_id=trainer_id,
            time_slot=time_slot_val,
            check_in_time=_parse_datetime(check_in_val),
            check_out_time=_parse_datetime(check_out_val),
            date=_parse_date(date_val) if isinstance(date_val, str) else date_val,
            workout_type=workout_type,
            notes=notes,
            status=status,
            created_at=created_at,
        )

        # --- Handle joined extras (member_name, trainer_name, time_slot override) ---
        extras = list(row[11:])
        if extras_order:
            for i, name in enumerate(extras_order):
                if i < len(extras):
                    if name == "time_slot" and extras[i]:  # prefer SQL-provided label
                        att.time_slot = extras[i]
                    else:
                        setattr(att, name, extras[i])
        else:
            if len(extras) == 1:
                att.trainer_name = extras[0]
            elif len(extras) >= 2:
                att.member_name = extras[0]
                att.trainer_name = extras[1]

        return att

    # --- Data access methods ---
    @classmethod
    def get_by_id(cls, attendance_id):
        db_path = cls._db_path()
        rows = execute_query("SELECT * FROM attendance WHERE id = ?", (attendance_id,), db_path, fetch=True)
        return cls._from_attendance_row(rows[0]) if rows else None

    @classmethod
    def get_for_trainer_member_slot(cls, trainer_id, member_id, attendance_date, time_slot):
        """
        Locate a single attendance row matching trainer+member+date+time_slot.
        This query tests both a dedicated time_slot column OR textual match in check_in_time
        to remain tolerant to schema variations.
        """
        check_in, check_out = _slot_to_datetimes(time_slot, on_date=attendance_date)
        db_path = cls._db_path()
        date_param = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        query = """
    SELECT * FROM attendance
    WHERE trainer_id=? AND member_id=? AND date=? AND check_in_time = ?
    LIMIT 1
""" 
        rows = execute_query(query, (trainer_id, member_id, date_param, check_in), db_path, fetch=True)

        return cls._from_attendance_row(rows[0]) if rows else None

    @classmethod
    def get_todays_attendance(cls):
        db_path = cls._db_path()
        result = execute_query('SELECT COUNT(*) FROM attendance WHERE date = ?', (date.today().isoformat(),), db_path, fetch=True)
        return result[0][0] if result else 0

    @classmethod
    def get_attendance_by_date(cls, attendance_date):
        db_path = cls._db_path()
        date_param = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        query = '''
            SELECT a.*, um.full_name as member_name, ut.full_name as trainer_name
            FROM attendance a
            LEFT JOIN members m ON a.member_id = m.id
            LEFT JOIN users um ON m.user_id = um.id
            LEFT JOIN trainers t ON a.trainer_id = t.id
            LEFT JOIN users ut ON t.user_id = ut.id
            WHERE a.date = ?
            ORDER BY a.check_in_time
        '''
        results = execute_query(query, (date_param,), db_path, fetch=True)
        return [cls._from_attendance_row(r, extras_order=['member_name', 'trainer_name']) for r in results]

    @classmethod
    def get_trainer_daily_sessions(cls, trainer_id, attendance_date=None):
        if attendance_date is None:
            attendance_date = date.today()
        db_path = cls._db_path()
        date_param = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        query = '''
            SELECT a.*, um.full_name as member_name
            FROM attendance a
            LEFT JOIN members m ON a.member_id = m.id
            LEFT JOIN users um ON m.user_id = um.id
            WHERE a.trainer_id = ? AND a.date = ?
            ORDER BY a.check_in_time
        '''
        results = execute_query(query, (trainer_id, date_param), db_path, fetch=True)
        return [cls._from_attendance_row(r, extras_order=['member_name']) for r in results]

    @classmethod
    def get_member_attendance(cls, member_id, limit=10):
        db_path = cls._db_path()
        query = '''
            SELECT 
                a.id,
                a.member_id,
                a.trainer_id,
                -- Format time slot nicely
                CASE 
                    WHEN a.check_in_time IS NOT NULL AND a.check_out_time IS NOT NULL 
                    THEN strftime('%I:%M %p', a.check_in_time) || ' - ' || strftime('%I:%M %p', a.check_out_time)
                    WHEN a.check_in_time IS NOT NULL 
                    THEN strftime('%I:%M %p', a.check_in_time)
                    ELSE 'N/A'
                END AS time_slot,
                a.check_in_time,
                a.check_out_time,
                a.date,
                a.workout_type,
                a.notes,
                a.status,
                a.created_at,
                COALESCE(ut.full_name, 'N/A') AS trainer_name
            FROM attendance a
            LEFT JOIN trainers t ON a.trainer_id = t.id
            LEFT JOIN users ut ON t.user_id = ut.id
            WHERE a.member_id = ?
            ORDER BY a.date DESC, a.check_in_time DESC
            LIMIT ?
        '''
        results = execute_query(query, (member_id, limit), db_path, fetch=True)
        return [
            cls._from_attendance_row(r, extras_order=['trainer_name', 'time_slot'])
            for r in results
        ]




    @classmethod
    def get_trainer_schedule(cls, trainer_id, attendance_date=None):
        if attendance_date is None:
            attendance_date = date.today()
        db_path = cls._db_path()
        date_param = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        query = '''
            SELECT a.*, um.full_name as member_name
            FROM attendance a
            LEFT JOIN members m ON a.member_id = m.id
            LEFT JOIN users um ON m.user_id = um.id
            WHERE a.trainer_id = ? AND a.date = ?
            ORDER BY a.check_in_time
        '''
        results = execute_query(query, (trainer_id, date_param), db_path, fetch=True)
        return [cls._from_attendance_row(r, extras_order=['member_name']) for r in results]

    @classmethod
    def check_slot_availability(cls, trainer_id, time_slot, attendance_date=None):
        if attendance_date is None:
            attendance_date = date.today()
        db_path = cls._db_path()
        check_in, check_out = _slot_to_datetimes(time_slot, on_date=attendance_date)

        date_param = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        query = '''
    SELECT COUNT(*) FROM attendance
    WHERE trainer_id = ? AND check_in_time = ? AND date = ?
'''
        result = execute_query(query, (trainer_id, check_in, date_param), db_path, fetch=True)

        return (result[0][0] == 0) if result else True

    def save(self):
        db_path = self._db_path()

        # Normalize date into ISO string (or None)
        date_str = None
        if self.date is not None:
            date_str = self.date.isoformat() if isinstance(self.date, date) else str(self.date)

        # Ensure check_in/check_out values exist: prefer explicit datetimes; if absent, derive from time_slot
        check_in_iso = None
        check_out_iso = None

        if self.check_in_time:
            check_in_iso = self.check_in_time.isoformat()
        if self.check_out_time:
            check_out_iso = self.check_out_time.isoformat()

        # if missing but time_slot available, try to derive datetimes
        if (not check_in_iso or not check_out_iso) and self.time_slot:
            derived_in, derived_out = _slot_to_datetimes(self.time_slot, on_date=self.date or date.today())
            if not check_in_iso and derived_in:
                check_in_iso = derived_in
            if not check_out_iso and derived_out:
                check_out_iso = derived_out

        # If time_slot missing but check_in/check_out exist, derive a label
        time_slot_val = self.time_slot or _datetimes_to_slot(check_in_iso, check_out_iso)

        # Save to DB: try the modern INSERT/UPDATE with a time_slot column; if DB lacks that column, fall back.
        # In save()

        if self.id:
            # UPDATE
            try:
                query = '''UPDATE attendance 
                        SET member_id=?, trainer_id=?, time_slot=?, check_in_time=?, check_out_time=?, 
                            date=?, workout_type=?, notes=?, status=?
                        WHERE id=?'''
                params = (self.member_id, self.trainer_id, time_slot_val, check_in_iso, check_out_iso,
                        date_str, self.workout_type, self.notes, self.status, self.id)
                execute_query(query, params, db_path)
                return self.id
            except Exception as e:
                query = '''UPDATE attendance 
                        SET member_id=?, trainer_id=?, check_in_time=?, check_out_time=?, 
                            date=?, workout_type=?, notes=?, status=?
                        WHERE id=?'''
                params = (self.member_id, self.trainer_id, check_in_iso, check_out_iso,
                        date_str, self.workout_type, self.notes, self.status, self.id)
                execute_query(query, params, db_path)
                return self.id
        else:
            try:
                query = '''INSERT INTO attendance 
                        (member_id, trainer_id, time_slot, check_in_time, check_out_time, date, workout_type, notes, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
                params = (self.member_id, self.trainer_id, time_slot_val, check_in_iso, check_out_iso,
                        date_str, self.workout_type, self.notes, self.status)
                result = execute_query(query, params, db_path)
            except Exception as e:
                query = '''INSERT INTO attendance 
                        (member_id, trainer_id, check_in_time, check_out_time, date, workout_type, notes, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
                params = (self.member_id, self.trainer_id, check_in_iso, check_out_iso,
                        date_str, self.workout_type, self.notes, self.status)
                result = execute_query(query, params, db_path)


            # execute_query may return inserted id depending on implementation
            if result:
                try:
                    self.id = int(result)
                except Exception:
                    self.id = result
            return self.id

    def mark_absent(self):
        self.status = 'absent'
        return self.save()

    def mark_present(self):
        self.status = 'present'
        return self.save()

    @classmethod
    def get_monthly_stats(cls, year, month):
        db_path = cls._db_path()
        query = '''
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(DISTINCT member_id) as unique_members,
                COUNT(DISTINCT trainer_id) as active_trainers
            FROM attendance 
            WHERE strftime('%Y', date) = ? 
            AND strftime('%m', date) = ?
            AND status IN ('present', 'absent')  -- only count scheduled sessions
        '''
        result = execute_query(query, (str(year), f"{month:02d}"), db_path, fetch=True)
        if result:
            row = result[0]
            return {
                'total_sessions': row[0],
                'unique_members': row[1],
                'active_trainers': row[2]
            }
        return {'total_sessions': 0, 'unique_members': 0, 'active_trainers': 0}

    
    @classmethod
    def get_member_attendance_percentage(cls, member_id, up_to_date=None):
        """
        Calculate attendance percentage for a member.
        - Count only 'present' and 'absent' as scheduled sessions.
        - Exclude 'scheduled' from totals (not yet marked).
        """
        db_path = cls._db_path()
        if up_to_date is None:
            up_to_date = date.today()
        date_param = up_to_date.isoformat() if isinstance(up_to_date, date) else up_to_date

        query = '''
            SELECT status, COUNT(*)
            FROM attendance
            WHERE member_id = ? AND date <= ?
            GROUP BY status
        '''
        results = execute_query(query, (member_id, date_param), db_path, fetch=True)

        present = 0
        total = 0
        for status, count in results:
            if status in ('present', 'absent'):   # only count scheduled sessions
                total += count
                if status == 'present':
                    present += count

        return round((present / total) * 100, 2) if total > 0 else 0.0

