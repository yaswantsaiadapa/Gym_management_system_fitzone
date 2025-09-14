# models/attendance.py - MINIMAL CHANGES VERSION
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
        NEW: Simplified to handle the consistent column order from updated schema
        """
        if not row:
            return None

        # Expected columns: id, member_id, trainer_id, check_in_time, check_out_time, date, time_slot, workout_type, notes, status, created_at
        att = cls(
            id=row[0],
            member_id=row[1],
            trainer_id=row[2],
            check_in_time=row[3],
            check_out_time=row[4],
            date=row[5],
            time_slot=row[6] if len(row) > 6 else None,
            workout_type=row[7] if len(row) > 7 else None,
            notes=row[8] if len(row) > 8 else None,
            status=row[9] if len(row) > 9 else 'scheduled',
            created_at=row[10] if len(row) > 10 else None,
        )

        # Handle joined extras (member_name, trainer_name, etc.)
        if len(row) > 11:
            if extras_order:
                for i, name in enumerate(extras_order):
                    if i < len(row) - 11:
                        setattr(att, name, row[11 + i])
            else:
                # Default handling for backwards compatibility
                if len(row) > 11:
                    att.member_name = row[11]
                if len(row) > 12:
                    att.trainer_name = row[12]

        # If time_slot is missing but we have check_in/check_out, derive it
        if not att.time_slot and (att.check_in_time or att.check_out_time):
            att.time_slot = _datetimes_to_slot(att.check_in_time, att.check_out_time)

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
        Updated to use time_slot column directly.
        """
        db_path = cls._db_path()
        date_param = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        
        query = """
            SELECT * FROM attendance
            WHERE trainer_id=? AND member_id=? AND date=? AND time_slot = ?
            LIMIT 1
        """ 
        rows = execute_query(query, (trainer_id, member_id, date_param, time_slot), db_path, fetch=True)
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
            ORDER BY a.time_slot, a.check_in_time
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
            ORDER BY a.time_slot, a.check_in_time
        '''
        results = execute_query(query, (trainer_id, date_param), db_path, fetch=True)
        return [cls._from_attendance_row(r, extras_order=['member_name']) for r in results]

    @classmethod
    def get_member_attendance(cls, member_id, limit=10):
        db_path = cls._db_path()
        query = '''
            SELECT a.*, ut.full_name as trainer_name
            FROM attendance a
            LEFT JOIN trainers t ON a.trainer_id = t.id
            LEFT JOIN users ut ON t.user_id = ut.id
            WHERE a.member_id = ?
            ORDER BY a.date DESC, a.time_slot DESC
            LIMIT ?
        '''
        results = execute_query(query, (member_id, limit), db_path, fetch=True)
        return [cls._from_attendance_row(r, extras_order=['trainer_name']) for r in results]

    @classmethod
    def get_trainer_schedule(cls, trainer_id, attendance_date=None):
        if attendance_date is None:
            attendance_date = date.today()
        db_path = cls._db_path()
        date_param = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        query = '''
            SELECT a.*, um.full_name as member_name, u.phone as member_phone
            FROM attendance a
            LEFT JOIN members m ON a.member_id = m.id
            LEFT JOIN users um ON m.user_id = um.id
            LEFT JOIN users u ON m.user_id = u.id
            WHERE a.trainer_id = ? AND a.date = ?
            ORDER BY a.time_slot, a.check_in_time
        '''
        results = execute_query(query, (trainer_id, date_param), db_path, fetch=True)
        return [cls._from_attendance_row(r, extras_order=['member_name', 'member_phone']) for r in results]

    @classmethod
    def check_slot_availability(cls, trainer_id, time_slot, attendance_date=None):
        if attendance_date is None:
            attendance_date = date.today()
        db_path = cls._db_path()
        date_param = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        
        query = '''
            SELECT COUNT(*) FROM attendance
            WHERE trainer_id = ? AND time_slot = ? AND date = ?
        '''
        result = execute_query(query, (trainer_id, time_slot, date_param), db_path, fetch=True)
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
        if not self.time_slot and (check_in_iso or check_out_iso):
            self.time_slot = _datetimes_to_slot(check_in_iso, check_out_iso)

        # Save to DB with time_slot column
        if self.id:
            # UPDATE
            query = '''UPDATE attendance 
                    SET member_id=?, trainer_id=?, check_in_time=?, check_out_time=?, 
                        date=?, time_slot=?, workout_type=?, notes=?, status=?
                    WHERE id=?'''
            params = (self.member_id, self.trainer_id, check_in_iso, check_out_iso,
                    date_str, self.time_slot, self.workout_type, self.notes, self.status, self.id)
            execute_query(query, params, db_path)
            return self.id
        else:
            # INSERT
            query = '''INSERT INTO attendance 
                    (member_id, trainer_id, check_in_time, check_out_time, date, time_slot, workout_type, notes, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (self.member_id, self.trainer_id, check_in_iso, check_out_iso,
                    date_str, self.time_slot, self.workout_type, self.notes, self.status)
            result = execute_query(query, params, db_path)
            if result:
                self.id = result
            return result

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
    
    @classmethod
    def auto_mark_absent(cls):
        """
        Mark all 'scheduled' sessions as 'absent' if their end time has passed.
        This keeps attendance data consistent even if trainers didn't mark manually.
        """
        db_path = cls._db_path()

        # Get all scheduled sessions
        rows = execute_query(
            "SELECT * FROM attendance WHERE status = 'scheduled'",
            (),
            db_path,
            fetch=True
        )
        now = datetime.now()
        updated = 0

        for r in rows:
            att = cls._from_attendance_row(r)
            if not att or not att.date:
                continue

            start_iso, end_iso = _slot_to_datetimes(att.time_slot, on_date=att.date)

            # Check if session has expired
            expired = False
            if att.date < date.today():
                expired = True
            elif end_iso:
                try:
                    expired = now > datetime.fromisoformat(end_iso)
                except Exception:
                    expired = False
            elif start_iso:
                # Fallback: if only start time present, consider expired if past start time + 1hr
                try:
                    start_dt = datetime.fromisoformat(start_iso)
                    expired = now > start_dt.replace(minute=start_dt.minute + 59)
                except Exception:
                    expired = False

            if expired:
                att.status = "absent"
                att.save()
                updated += 1

        return updated
    @classmethod
    def get_member_scheduled_on_date(cls, member_id, on_date):
        """
        Return all scheduled sessions for a given member on a specific date.
        Used by member_routes to prevent double-booking.
        """
        db_path = cls._db_path()
        date_param = on_date.isoformat() if isinstance(on_date, date) else on_date

        query = """
            SELECT * FROM attendance
            WHERE member_id = ? AND date = ? AND status = 'scheduled'
            ORDER BY time_slot
        """
        rows = execute_query(query, (member_id, date_param), db_path, fetch=True)
        return [cls._from_attendance_row(r) for r in rows] if rows else []
     

    def __repr__(self):
        return f"<Attendance id={self.id} member={self.member_name or self.member_id} trainer={self.trainer_name or self.trainer_id} date={self.date} slot={self.time_slot} status={self.status}>"

    def __str__(self):
        member = self.member_name or f"Member {self.member_id}"
        trainer = self.trainer_name or f"Trainer {self.trainer_}"
        d = self.date.isoformat() if isinstance(self.date, date) else str(self.date)
        return f"{d} | {self.time_slot or 'N/A'} | {member} with {trainer} | Status: {self.status}"

    __repr__ = __str__


        
