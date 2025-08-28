from .database import execute_query
from flask import current_app
from datetime import date, datetime

def _to_date(d):
    """Parse DB value to date (YYYY-MM-DD) or return as-is/None."""
    if d is None or isinstance(d, date):
        return d
    try:
        # Accept both 'YYYY-MM-DD' and full ISO with time
        return datetime.fromisoformat(str(d)).date()
    except Exception:
        try:
            return datetime.strptime(str(d), "%Y-%m-%d").date()
        except Exception:
            return d  # leave as-is if not parseable

def _to_str_date(d):
    """Serialize a date or string to 'YYYY-MM-DD' or None."""
    if d is None:
        return None
    if isinstance(d, date):
        return d.isoformat()
    # Assume already a string
    return str(d)

class Member:
    """
    Member model aligned to the current schema:
      id, user_id, membership_plan_id, phone, emergency_contact, emergency_phone,
      address, date_of_birth, weight, height, medical_conditions, fitness_goals,
      membership_start_date, membership_end_date, status, trainer_id, created_at, updated_at.

    # --- Backward-compatibility notes ---
    - Old code used: name, email, payment_status, membership_date, expiry_date.
      * name -> mapped to joined users.full_name (kept as self.full_name and alias property .name)
      * email -> mapped to joined users.email (kept as self.email)
      * payment_status -> kept on the Python object (not persisted; table has no column)
      * membership_date -> alias to membership_start_date
      * expiry_date -> alias to membership_end_date
    """

    def __init__(
        self,
        id=None,
        # New schema fields
        user_id=None,
        membership_plan_id=None,
        phone=None,
        emergency_contact=None,
        emergency_phone=None,
        address=None,
        date_of_birth=None,
        weight=None,
        height=None,
        medical_conditions=None,
        fitness_goals=None,
        membership_start_date=None,
        membership_end_date=None,
        status='active',
        trainer_id=None,
        created_at=None,
        updated_at=None,
        # Joined/derived fields (from users / plans / trainers)
        full_name=None,   # compatibility for old `name`
        email=None,
        plan_name=None,
        trainer_name=None,
        # Legacy/compat fields not stored in DB
        payment_status='pending',
        # Legacy aliases accepted on init (mapped to new fields if provided)
        name=None,                 # old alias for full_name
        membership_date=None,      # old alias for membership_start_date
        expiry_date=None           # old alias for membership_end_date
    ):
        self.id = id
        self.user_id = user_id
        self.membership_plan_id = membership_plan_id
        self.phone = phone
        self.emergency_contact = emergency_contact
        self.emergency_phone = emergency_phone
        self.address = address
        self.date_of_birth = _to_date(date_of_birth)
        self.weight = weight
        self.height = height
        self.medical_conditions = medical_conditions
        self.fitness_goals = fitness_goals
        # map legacy aliases if present
        self.membership_start_date = _to_date(membership_start_date or membership_date)
        self.membership_end_date = _to_date(membership_end_date or expiry_date)
        self.status = status
        self.trainer_id = trainer_id
        self.created_at = created_at
        self.updated_at = updated_at

        # Joined/derived (not persisted to members table)
        self.full_name = full_name or name  # compatibility: allow `name` arg to fill full_name
        self.email = email
        self.plan_name = plan_name
        self.trainer_name = trainer_name

        # Legacy compatibility field (not persisted)
        self.payment_status = payment_status

    # --- Compatibility alias properties ---
    @property
    def name(self):
        """Old code used .name; map to full_name (from users)."""
        return self.full_name

    @name.setter
    def name(self, v):
        self.full_name = v

    @property
    def membership_date(self):
        """Old code used membership_date; alias to membership_start_date."""
        return self.membership_start_date

    @membership_date.setter
    def membership_date(self, v):
        self.membership_start_date = _to_date(v)

    @property
    def expiry_date(self):
        """Old code used expiry_date; alias to membership_end_date."""
        return self.membership_end_date

    @expiry_date.setter
    def expiry_date(self, v):
        self.membership_end_date = _to_date(v)

    # -------------------- Fetchers --------------------

    @classmethod
    def _db_path(cls):
        return current_app.config.get('DATABASE_PATH', 'gym_management.db')

    @classmethod
    def get_all_active(cls):
        """
        Get all active members.
        Returns Member instances with:
          - members.* fields
          - joined users.full_name -> .full_name (.name alias works)
          - joined users.email     -> .email
        """
        db_path = cls._db_path()
        query = '''
            SELECT
                m.id, m.user_id, u.full_name, u.email,
                m.membership_plan_id, m.phone, m.emergency_contact, m.emergency_phone,
                m.address, m.date_of_birth, m.weight, m.height,
                m.medical_conditions, m.fitness_goals,
                m.membership_start_date, m.membership_end_date,
                m.status, m.trainer_id, m.created_at, m.updated_at
            FROM members m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.status = 'active'
            ORDER BY m.created_at DESC
        '''
        rows = execute_query(query, (), db_path, fetch=True)
        members = []
        for r in rows:
            members.append(cls(
                id=r[0], user_id=r[1], full_name=r[2], email=r[3],
                membership_plan_id=r[4], phone=r[5], emergency_contact=r[6], emergency_phone=r[7],
                address=r[8], date_of_birth=_to_date(r[9]), weight=r[10], height=r[11],
                medical_conditions=r[12], fitness_goals=r[13],
                membership_start_date=_to_date(r[14]), membership_end_date=_to_date(r[15]),
                status=r[16], trainer_id=r[17], created_at=r[18], updated_at=r[19]
            ))
        return members

    @classmethod
    def get_by_id(cls, member_id):
        """Get a single member by ID with joined user info (full_name, email)."""
        db_path = cls._db_path()
        query = '''
            SELECT
                m.id, m.user_id, u.full_name, u.email,
                m.membership_plan_id, m.phone, m.emergency_contact, m.emergency_phone,
                m.address, m.date_of_birth, m.weight, m.height,
                m.medical_conditions, m.fitness_goals,
                m.membership_start_date, m.membership_end_date,
                m.status, m.trainer_id, m.created_at, m.updated_at
            FROM members m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
            LIMIT 1
        '''
        rows = execute_query(query, (member_id,), db_path, fetch=True)
        if not rows:
            return None
        r = rows[0]
        return cls(
            id=r[0], user_id=r[1], full_name=r[2], email=r[3],
            membership_plan_id=r[4], phone=r[5], emergency_contact=r[6], emergency_phone=r[7],
            address=r[8], date_of_birth=_to_date(r[9]), weight=r[10], height=r[11],
            medical_conditions=r[12], fitness_goals=r[13],
            membership_start_date=_to_date(r[14]), membership_end_date=_to_date(r[15]),
            status=r[16], trainer_id=r[17], created_at=r[18], updated_at=r[19]
        )

    @classmethod
    def get_by_user_id(cls, user_id):
        """Fetch the member profile for a given users.id."""
        db_path = cls._db_path()
        query = '''
            SELECT
                m.id, m.user_id, u.full_name, u.email,
                m.membership_plan_id, m.phone, m.emergency_contact, m.emergency_phone,
                m.address, m.date_of_birth, m.weight, m.height,
                m.medical_conditions, m.fitness_goals,
                m.membership_start_date, m.membership_end_date,
                m.status, m.trainer_id, m.created_at, m.updated_at
            FROM members m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.user_id = ?
            LIMIT 1
        '''
        rows = execute_query(query, (user_id,), db_path, fetch=True)
        if not rows:
            return None
        r = rows[0]
        return cls(
            id=r[0], user_id=r[1], full_name=r[2], email=r[3],
            membership_plan_id=r[4], phone=r[5], emergency_contact=r[6], emergency_phone=r[7],
            address=r[8], date_of_birth=_to_date(r[9]), weight=r[10], height=r[11],
            medical_conditions=r[12], fitness_goals=r[13],
            membership_start_date=_to_date(r[14]), membership_end_date=_to_date(r[15]),
            status=r[16], trainer_id=r[17], created_at=r[18], updated_at=r[19]
        )

    @classmethod
    def get_count_active(cls):
        """Count active members (status = 'active')."""
        db_path = cls._db_path()
        query = "SELECT COUNT(*) FROM members WHERE status = 'active'"
        res = execute_query(query, (), db_path, fetch=True)
        return res[0][0] if res else 0

    @classmethod
    def get_all_with_details(cls):
        """
        Detailed list for admin screens:
          - includes plan name and trainer name (joined)
          - includes user full_name/email
        """
        db_path = cls._db_path()
        query = '''
            SELECT
                m.id, m.user_id, u.full_name, u.email,
                m.membership_plan_id, mp.name AS plan_name,
                m.phone, m.emergency_contact, m.emergency_phone,
                m.address, m.date_of_birth, m.weight, m.height,
                m.medical_conditions, m.fitness_goals,
                m.membership_start_date, m.membership_end_date,
                m.status, m.trainer_id, tu.full_name AS trainer_name,
                m.created_at, m.updated_at
            FROM members m
            LEFT JOIN users u ON m.user_id = u.id
            LEFT JOIN membership_plans mp ON m.membership_plan_id = mp.id
            LEFT JOIN trainers t ON m.trainer_id = t.id
            LEFT JOIN users tu ON t.user_id = tu.id
            ORDER BY m.created_at DESC
        '''
        rows = execute_query(query, (), db_path, fetch=True)
        out = []
        for r in rows:
            out.append(cls(
                id=r[0], user_id=r[1], full_name=r[2], email=r[3],
                membership_plan_id=r[4], plan_name=r[5],
                phone=r[6], emergency_contact=r[7], emergency_phone=r[8],
                address=r[9], date_of_birth=_to_date(r[10]), weight=r[11], height=r[12],
                medical_conditions=r[13], fitness_goals=r[14],
                membership_start_date=_to_date(r[15]), membership_end_date=_to_date(r[16]),
                status=r[17], trainer_id=r[18], trainer_name=r[19],
                created_at=r[20], updated_at=r[21]
            ))
        return out

    @classmethod
    def get_recent(cls, limit=5):
        """Most recently created members."""
        db_path = cls._db_path()
        query = '''
            SELECT
                m.id, m.user_id, u.full_name, u.email,
                m.membership_plan_id, m.phone,
                m.membership_start_date, m.membership_end_date,
                m.status, m.created_at
            FROM members m
            LEFT JOIN users u ON m.user_id = u.id
            ORDER BY m.created_at DESC
            LIMIT ?
        '''
        rows = execute_query(query, (limit,), db_path, fetch=True)
        out = []
        for r in rows:
            out.append(cls(
                id=r[0], user_id=r[1], full_name=r[2], email=r[3],
                membership_plan_id=r[4], phone=r[5],
                membership_start_date=_to_date(r[6]), membership_end_date=_to_date(r[7]),
                status=r[8], created_at=r[9]
            ))
        return out

    @classmethod
    def get_expiring_soon(cls, days=30):
        """
        Members whose membership_end_date is within the next `days`.
        Uses SQLite date('now', '+X days') to filter.
        """
        db_path = cls._db_path()
        # NOTE: SQLite accepts a modifier like '+30 days' as a single parameter.
        modifier = f'+{int(days)} days'
        query = '''
            SELECT
                m.id, m.user_id, u.full_name, u.email,
                m.membership_plan_id, m.phone,
                m.membership_start_date, m.membership_end_date,
                m.status
            FROM members m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.membership_end_date IS NOT NULL
              AND DATE(m.membership_end_date) >= DATE('now')
              AND DATE(m.membership_end_date) <= DATE('now', ?)
            ORDER BY m.membership_end_date ASC
        '''
        rows = execute_query(query, (modifier,), db_path, fetch=True)
        out = []
        for r in rows:
            out.append(cls(
                id=r[0], user_id=r[1], full_name=r[2], email=r[3],
                membership_plan_id=r[4], phone=r[5],
                membership_start_date=_to_date(r[6]), membership_end_date=_to_date(r[7]),
                status=r[8]
            ))
        return out

    @classmethod
    def get_statistics(cls):
        """
        Aggregated stats for reports:
          - total_members
          - total_active
          - new_this_month
          - expiring_next_7_days
        """
        db_path = cls._db_path()

        # total members
        total_members = execute_query("SELECT COUNT(*) FROM members", (), db_path, fetch=True)
        total_members = total_members[0][0] if total_members else 0

        # total active
        total_active = execute_query("SELECT COUNT(*) FROM members WHERE status = 'active'", (), db_path, fetch=True)
        total_active = total_active[0][0] if total_active else 0

        # new this month
        q_new = """
            SELECT COUNT(*) FROM members
            WHERE strftime('%Y-%m', membership_start_date) = strftime('%Y-%m', 'now')
        """
        new_this_month = execute_query(q_new, (), db_path, fetch=True)
        new_this_month = new_this_month[0][0] if new_this_month else 0

        # expiring in next 7 days
        q_exp_7 = """
            SELECT COUNT(*) FROM members
            WHERE membership_end_date IS NOT NULL
              AND DATE(membership_end_date) >= DATE('now')
              AND DATE(membership_end_date) <= DATE('now', '+7 days')
        """
        expiring_next_7_days = execute_query(q_exp_7, (), db_path, fetch=True)
        expiring_next_7_days = expiring_next_7_days[0][0] if expiring_next_7_days else 0

        return {
            'total_members': total_members,
            'total_active': total_active,
            'new_this_month': new_this_month,
            'expiring_next_7_days': expiring_next_7_days
        }

    # -------------------- Persistence --------------------

    def save(self):
        """
        Insert/Update a member row.
        - Writes only columns that exist in the members table (NO name/email/payment_status persistence).
        - Safe to call even if some optional fields are None.
        """
        db_path = self._db_path()

        dob = _to_str_date(self.date_of_birth)
        start = _to_str_date(self.membership_start_date)
        end = _to_str_date(self.membership_end_date)

        if self.id:
            # UPDATE existing
            query = '''
                UPDATE members
                SET user_id = ?, membership_plan_id = ?, phone = ?,
                    emergency_contact = ?, emergency_phone = ?, address = ?,
                    date_of_birth = ?, weight = ?, height = ?,
                    medical_conditions = ?, fitness_goals = ?,
                    membership_start_date = ?, membership_end_date = ?,
                    status = ?, trainer_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''
            params = (
                self.user_id, self.membership_plan_id, self.phone,
                self.emergency_contact, self.emergency_phone, self.address,
                dob, self.weight, self.height,
                self.medical_conditions, self.fitness_goals,
                start, end,
                self.status, self.trainer_id, self.id
            )
            execute_query(query, params, db_path)
            return self.id
        else:
            # INSERT new
            query = '''
                INSERT INTO members (
                    user_id, membership_plan_id, phone,
                    emergency_contact, emergency_phone, address,
                    date_of_birth, weight, height,
                    medical_conditions, fitness_goals,
                    membership_start_date, membership_end_date,
                    status, trainer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = (
                self.user_id, self.membership_plan_id, self.phone,
                self.emergency_contact, self.emergency_phone, self.address,
                dob, self.weight, self.height,
                self.medical_conditions, self.fitness_goals,
                start, end,
                self.status, self.trainer_id
            )
            new_id = execute_query(query, params, db_path)
            self.id = new_id
            return self.id

    # -------------------- Actions --------------------

    def renew_membership(self, new_expiry_date, payment_status='done'):
        """
        Renew membership end date.
        - Keeps compatibility with old signature:
            * new_expiry_date -> sets membership_end_date
            * payment_status stored on the object only (not persisted).
        """
        self.membership_end_date = _to_date(new_expiry_date)
        self.payment_status = payment_status  # compatibility (not stored in DB)
        return self.save()

    def get_attendance_history(self):
        """
        Member's attendance history with trainer details.
        Joins trainers -> users to fetch trainer's full name.
        """
        db_path = self._db_path()
        query = '''
            SELECT a.date, a.time_slot, COALESCE(ut.full_name, '') AS trainer_name, a.status
            FROM attendance a
            LEFT JOIN trainers t ON a.trainer_id = t.id
            LEFT JOIN users ut ON t.user_id = ut.id
            WHERE a.member_id = ?
            ORDER BY a.date DESC
        '''
        return execute_query(query, (self.id,), db_path, fetch=True)
    @classmethod
    def get_trainer_client_count(cls, trainer_id):
        """Count how many clients are assigned to a trainer"""
        import sqlite3
        conn = sqlite3.connect(cls._db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM members WHERE trainer_id = ?", (trainer_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    @classmethod
    def get_trainer_clients(cls, trainer_id):
        """Get basic list of clients assigned to a trainer"""
        import sqlite3
        conn = sqlite3.connect(cls._db_path())
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, membership_date, expiry_date, is_active
            FROM members
            WHERE trainer_id = ?
            ORDER BY full_name
        """, (trainer_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    @classmethod
    def get_trainer_clients_detailed(cls, trainer_id):
        """Get detailed client info for trainer’s dashboard/clients page"""
        import sqlite3
        conn = sqlite3.connect(cls._db_path())
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, email, phone, membership_date, expiry_date, height, is_active
            FROM members
            WHERE trainer_id = ?
            ORDER BY full_name
        """, (trainer_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

