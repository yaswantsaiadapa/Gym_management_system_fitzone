# payment.py (UPDATED)
from datetime import date, datetime
from flask import current_app
from models.database import execute_query
import uuid

class Payment:
    ALLOWED_STATUSES = ['pending', 'completed', 'failed', 'refunded']

    def __init__(self, id=None, member_id=None, membership_plan_id=None, amount=None,
                 payment_method=None, payment_status='pending', transaction_id=None,
                 payment_date=None, due_date=None, notes=None, created_at=None,
                 invoice_number=None, reminder_sent=0, reminder_sent_at=None, cancelled_processed=0):
        self.id = id
        self.member_id = member_id
        self.membership_plan_id = membership_plan_id
        self.amount = amount
        self.payment_method = payment_method
        self.payment_status = payment_status
        self.transaction_id = transaction_id
        # Use ISO date strings or date objects; DB stores as TEXT/DATE
        self.payment_date = payment_date
        self.due_date = due_date
        self.notes = notes
        self.created_at = created_at

        # New fields (appended to DB)
        self.invoice_number = invoice_number
        self.reminder_sent = int(reminder_sent) if reminder_sent is not None else 0
        self.reminder_sent_at = reminder_sent_at
        self.cancelled_processed = int(cancelled_processed) if cancelled_processed is not None else 0

    # ----------------- Basic fetchers (updated to include new columns where possible) -----------------
    @classmethod
    def get_member_payments(cls, member_id):
        """Get all payments for a member and add computed fields like is_overdue & days_left."""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT p.*, mp.name as plan_name 
                FROM payments p
                JOIN membership_plans mp ON p.membership_plan_id = mp.id
                WHERE p.member_id = ? 
                ORDER BY p.created_at DESC'''
        results = execute_query(query, (member_id,), db_path, fetch=True) or []

        payments = []
        today = date.today()

        for row in results:
            payment = cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10],
                invoice_number=row[11] if len(row) > 11 else None,
                reminder_sent=row[12] if len(row) > 12 else 0,
                reminder_sent_at=row[13] if len(row) > 13 else None,
                cancelled_processed=row[14] if len(row) > 14 else 0
            )
            payment.plan_name = row[-1]  # plan_name is last from SELECT

            # --- Compute helper fields for template usage ---
            due_date_obj = None
            try:
                if payment.due_date:
                    due_date_obj = datetime.fromisoformat(str(payment.due_date)).date()
            except Exception:
                try:
                    due_date_obj = datetime.strptime(str(payment.due_date), "%Y-%m-%d").date()
                except Exception:
                    pass

            payment.due_date_obj = due_date_obj
            payment.days_left = (due_date_obj - today).days if due_date_obj else None
            payment.is_overdue = (payment.payment_status == "pending" and due_date_obj and due_date_obj < today)

            payments.append(payment)

        return payments


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
            payment = cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10],
                invoice_number=row[11] if len(row) > 11 else None,
                reminder_sent=row[12] if len(row) > 12 else 0,
                reminder_sent_at=row[13] if len(row) > 13 else None,
                cancelled_processed=row[14] if len(row) > 14 else 0
            )
            # The SELECT projection appended extra fields: member_name, plan_name, member_user_id
            # Their positions depend on DB column count. Here we read them safely if present:
            extra_idx = 11
            payment.member_name = row[extra_idx] if len(row) > extra_idx else None
            payment.plan_name = row[extra_idx + 1] if len(row) > extra_idx + 1 else None
            payment.member_user_id = row[extra_idx + 2] if len(row) > extra_idx + 2 else None
            payments.append(payment)
        return payments

    @classmethod
    def get_revenue_stats(cls, year=None, month=None):
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        if year and month:
            query = '''SELECT SUM(amount), COUNT(*) 
                       FROM payments 
                       WHERE payment_status = 'completed' 
                       AND strftime('%Y', payment_date) = ? 
                       AND strftime('%m', payment_date) = ?'''
            params = (str(year), f"{month:02d}")
        elif year:
            query = '''SELECT SUM(amount), COUNT(*) 
                       FROM payments 
                       WHERE payment_status = 'completed' 
                       AND strftime('%Y', payment_date) = ?'''
            params = (str(year),)
        else:
            query = '''SELECT SUM(amount), COUNT(*) 
                       FROM payments 
                       WHERE payment_status = 'completed' '''
            params = ()

        result = execute_query(query, params, db_path, fetch=True)
        if result and result[0][0]:
            return {'total_revenue': result[0][0], 'total_payments': result[0][1]}
        return {'total_revenue': 0, 'total_payments': 0}

    @classmethod
    def get_by_id(cls, payment_id):
        """Fetch a payment by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT * FROM payments WHERE id = ?'''
        result = execute_query(query, (payment_id,), db_path, fetch=True)

        if result:
            row = result[0]
            return cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10],
                invoice_number=row[11] if len(row) > 11 else None,
                reminder_sent=row[12] if len(row) > 12 else 0,
                reminder_sent_at=row[13] if len(row) > 13 else None,
                cancelled_processed=row[14] if len(row) > 14 else 0
            )
        return None

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
            payment = cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10],
                invoice_number=row[11] if len(row) > 11 else None,
                reminder_sent=row[12] if len(row) > 12 else 0,
                reminder_sent_at=row[13] if len(row) > 13 else None,
                cancelled_processed=row[14] if len(row) > 14 else 0
            )
            # member_name and plan_name likely sit after the appended columns
            idx = 11
            payment.member_name = row[idx] if len(row) > idx else None
            payment.plan_name = row[idx + 1] if len(row) > idx + 1 else None
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
            payment = cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10],
                invoice_number=row[11] if len(row) > 11 else None,
                reminder_sent=row[12] if len(row) > 12 else 0,
                reminder_sent_at=row[13] if len(row) > 13 else None,
                cancelled_processed=row[14] if len(row) > 14 else 0
            )
            payment.member_name = row[11] if len(row) > 11 else None
            payment.plan_name = row[12] if len(row) > 12 else None
            payments.append(payment)
        return payments

    # ----------------- Save / Persist -----------------
    def save(self):
        """Save payment to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

        # Ensure invoice_number exists for new payments
        if not self.invoice_number:
            self.invoice_number = f"INV-{uuid.uuid4().hex[:12]}"

        if self.id:
            # Update existing payment
            query = '''UPDATE payments 
                       SET member_id=?, membership_plan_id=?, amount=?, payment_method=?, 
                           payment_status=?, transaction_id=?, payment_date=?, due_date=?, notes=?,
                           invoice_number=?, reminder_sent=?, reminder_sent_at=?, cancelled_processed=?
                       WHERE id=?'''
            params = (self.member_id, self.membership_plan_id, self.amount,
                     self.payment_method, self.payment_status, self.transaction_id,
                     self.payment_date, self.due_date, self.notes,
                     self.invoice_number, int(self.reminder_sent), self.reminder_sent_at, int(self.cancelled_processed),
                     self.id)
        else:
            # Create new payment (include new columns at the end)
            query = '''INSERT INTO payments (
                        member_id, membership_plan_id, amount, payment_method, payment_status, 
                        transaction_id, payment_date, due_date, notes, invoice_number, reminder_sent, reminder_sent_at, cancelled_processed
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (self.member_id, self.membership_plan_id, self.amount,
                     self.payment_method, self.payment_status, self.transaction_id,
                     self.payment_date, self.due_date, self.notes,
                     self.invoice_number, int(self.reminder_sent), self.reminder_sent_at, int(self.cancelled_processed))

        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id

    # ----------------- Workflow helpers -----------------
    @classmethod
    def mark_completed(cls, payment_id, transaction_id=None):
        """Mark payment completed and activate the member (without changing membership_start_date)."""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        payment = cls.get_by_id(payment_id)
        if not payment:
            return False

        # Update payment record
        payment.payment_status = 'completed'
        payment.payment_date = date.today().isoformat()
        if transaction_id:
            payment.transaction_id = transaction_id
        payment.save()

        # Activate member and their user account
        try:
            # Set member.status to active (membership_status column expected on members)
            execute_query("UPDATE members SET membership_status = ? WHERE id = ?", ('active', payment.member_id), db_path)
            # Find user_id for this member
            rows = execute_query("SELECT user_id FROM members WHERE id = ?", (payment.member_id,), db_path, fetch=True)
            if rows:
                user_id = rows[0][0]
                execute_query("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,), db_path)
        except Exception as e:
            try:
                current_app.logger.exception(f"Failed to activate member after payment {payment_id}: {e}")
            except:
                print(f"Failed to activate member after payment {payment_id}: {e}")

        # Send confirmation email if possible
        try:
            from utils.email_utils import send_membership_payment_success
            # send_membership_payment_success(email, full_name, invoice, amount, date) -- if implemented in your project
            rows = execute_query("SELECT m.user_id, u.email, u.full_name FROM members m JOIN users u ON m.user_id = u.id WHERE m.id = ?", (payment.member_id,), db_path, fetch=True)
            if rows:
                _, email, full_name = rows[0]
                try:
                    send_membership_payment_success(email, full_name, payment.invoice_number, payment.amount, payment.payment_date)
                except Exception as e:
                    current_app.logger.warning(f"Payment success email failed for payment {payment_id}: {e}")
        except Exception:
            # email helper might not exist — that's fine, we logged already
            pass

        return True

    @classmethod
    def process_pending_payments(cls, reminder_before_days=5):
        """
        Send reminders and cancel expired pending payments.
        - reminder_before_days : number of days before due_date to send reminder (5 -> reminder at due_date - 5)
        This method is intended to be run daily (cron/Flask CLI or invoked from admin dashboard).
        """
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        today = date.today()

        # Get all pending payments with due_date
        query = '''SELECT p.*, m.user_id as member_user_id, u.email as member_email, u.full_name as member_name
                   FROM payments p
                   JOIN members m ON p.member_id = m.id
                   JOIN users u ON m.user_id = u.id
                   WHERE p.payment_status = 'pending' AND p.due_date IS NOT NULL'''
        rows = execute_query(query, (), db_path, fetch=True) or []

        reminders_sent = []
        cancellations_done = []

        for row in rows:
            # parse fields
            payment = cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10],
                invoice_number=row[11] if len(row) > 11 else None,
                reminder_sent=row[12] if len(row) > 12 else 0,
                reminder_sent_at=row[13] if len(row) > 13 else None,
                cancelled_processed=row[14] if len(row) > 14 else 0
            )
            member_user_id = row[-3]  # from projection: member_user_id
            member_email = row[-2]
            member_name = row[-1]

            # normalize due_date to date object if present
            try:
                due_date_obj = datetime.fromisoformat(payment.due_date).date() if isinstance(payment.due_date, str) else (payment.due_date if isinstance(payment.due_date, date) else None)
            except Exception:
                # fallback for other formats
                try:
                    due_date_obj = datetime.strptime(payment.due_date, "%Y-%m-%d").date() if payment.due_date else None
                except Exception:
                    due_date_obj = None

            if not due_date_obj:
                continue

            days_left = (due_date_obj - today).days

            # 1) Send reminder when days_left == reminder_before_days and reminder not already sent
            if days_left == reminder_before_days and payment.reminder_sent == 0:
                # Try to call an email helper, otherwise log
                try:
                    from utils.email_utils import send_membership_payment_reminder
                    # expected signature (email, full_name, due_date_str, days_left, invoice)
                    try:
                        send_membership_payment_reminder(member_email, member_name, due_date_obj.isoformat(), days_left, payment.invoice_number)
                    except TypeError:
                        # fallback signature variations
                        send_membership_payment_reminder(member_email, member_name, due_date_obj.isoformat(), days_left)
                except Exception as e:
                    try:
                        current_app.logger.info(f"Reminder would be sent to {member_email} for payment {payment.id} (no helper available or failed): {e}")
                    except:
                        print(f"Reminder would be sent to {member_email} for payment {payment.id} (no helper available or failed): {e}")

                # Mark reminder sent
                try:
                    execute_query("UPDATE payments SET reminder_sent = 1, reminder_sent_at = ? WHERE id = ?", (datetime.now().isoformat(), payment.id), db_path)
                    reminders_sent.append(payment.id)
                except Exception as e:
                    try:
                        current_app.logger.exception(f"Failed to mark reminder_sent for payment {payment.id}: {e}")
                    except:
                        print(f"Failed to mark reminder_sent for payment {payment.id}: {e}")

            # 2) Cancel expired pending payments (due_date < today) and not yet processed
            if due_date_obj < today and (payment.cancelled_processed == 0):
                try:
                    # Cancel membership and disable user
                    execute_query("UPDATE members SET membership_status = ? WHERE id = ?", ('cancelled', payment.member_id), db_path)
                    # get user_id
                    user_rows = execute_query("SELECT user_id FROM members WHERE id = ?", (payment.member_id,), db_path, fetch=True)
                    if user_rows:
                        user_id = user_rows[0][0]
                        execute_query("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,), db_path)

                    # mark payment as cancelled_processed (don't change payment_status here; keep it 'pending' or let admin mark failed)
                    execute_query("UPDATE payments SET cancelled_processed = 1 WHERE id = ?", (payment.id,), db_path)

                    # attempt to send cancellation email
                    try:
                        from utils.email_utils import send_membership_cancelled_notification
                        try:
                            send_membership_cancelled_notification(member_email, member_name, payment.invoice_number, due_date_obj.isoformat())
                        except TypeError:
                            send_membership_cancelled_notification(member_email, member_name, due_date_obj.isoformat())
                    except Exception as e:
                        try:
                            current_app.logger.info(f"Cancellation notification for {member_email} (helper missing or failed): {e}")
                        except:
                            print(f"Cancellation notification for {member_email} (helper missing or failed): {e}")

                    cancellations_done.append(payment.id)
                except Exception as e:
                    try:
                        current_app.logger.exception(f"Failed to cancel membership for payment {payment.id}: {e}")
                    except:
                        print(f"Failed to cancel membership for payment {payment.id}: {e}")

        # return lists for callers to inspect/log
        return {'reminders_sent': reminders_sent, 'cancellations_done': cancellations_done}
