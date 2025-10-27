# routes/member_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from datetime import date, datetime,timedelta
from app.models.user import User
from app.models.member import Member
from app.models.trainer import Trainer
from app.models.membership_plan import MembershipPlan
from app.models.payment import Payment
from app.models.workout import Workout
from app.models.diet import Diet
from app.models.progress import Progress
from app.models.attendance import Attendance, _slot_to_datetimes, _parse_datetime
from app.models.announcement import Announcement
from app.routes.admin import members
from app.utils.decorators import login_required, member_required
from app.models.workout_plan import MemberWorkoutPlan, WorkoutPlanDetail
import json

# NOTE: Keep blueprint without url_prefix so app.register_blueprint(..., url_prefix='/member') controls final path.
member_routes_bp = Blueprint('member', __name__)


@member_routes_bp.route('/announcements')
@login_required
def announcements():
    """Show announcements for members"""
    try:
        announcements = Announcement.get_for_role('member')
    except Exception as ex:
        current_app.logger.warning("Announcements fetch failed: %s", ex)
        announcements = []
    return render_template('member/announcements.html', announcements=announcements)


@member_routes_bp.route('/dashboard')
@login_required
@member_required
def dashboard():
    """Member dashboard with defensive error handling"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please login again.')
            return redirect(url_for('auth.login'))

        # --- Get Member record ---
        try:
            member = Member.get_by_user_id(user_id)
        except Exception as ex:
            current_app.logger.exception("Error fetching member: %s", ex)
            member = None

        if not member:
            flash('Member profile not found')
            return redirect(url_for('auth.login'))

        # --- Membership stats ---
        membership_expires = getattr(member, 'membership_end_date', None)
        days_until_expiry = (
            (membership_expires - date.today()).days
            if membership_expires else 0
        )

        stats = {
            'membership_status': getattr(member, 'status', 'inactive'),
            'membership_expires': membership_expires,
            'days_until_expiry': days_until_expiry,
            'recent_attendance': [],
            'pending_payments': []
        }

        # Attendance (recent)
        try:
            stats['recent_attendance'] = Attendance.get_member_attendance(member.id, limit=5)
        except Exception as ex:
            current_app.logger.warning("Attendance fetch failed: %s", ex)

        # Payments (pending)
                # Payments (filter only TRUE pending)
        try:
            all_payments = Payment.get_member_payments(member.id)
            stats['pending_payments'] = [
                p for p in all_payments 
                if getattr(p, 'payment_status', '').lower() == 'pending'
            ][:3]  # show only top 3 pending items if many
        except Exception as ex:
            current_app.logger.warning("Payments fetch failed: %s", ex)
            stats['pending_payments'] = []

        # --- Alerts ---
        alert_message = None

        # Show alert if membership is not active (pending or suspended)
        if getattr(member, 'status', 'inactive') != "active":
            alert_message = "⚠️ Your membership is not active. Please complete payment or contact the admin."

        # Expiry warnings for active members (or in general)
        elif membership_expires:
            if days_until_expiry < 0:
                alert_message = f"⚠️ Your membership expired on {membership_expires}. Please renew at the admin desk."
            elif days_until_expiry <= 7:
                alert_message = f"⏳ Your membership will expire in {days_until_expiry} days (on {membership_expires}). Please renew soon."

        # Pending payment notice (append)
        if stats['pending_payments']:
            # Show due date of first pending payment (if exists)
            next_due = getattr(stats['pending_payments'][0], 'due_date', None)
            next_due_str = f" Due by {next_due}." if next_due else ""
            alert_message = (alert_message + " | " if alert_message else "") + \
                f"💰 You have {len(stats['pending_payments'])} pending payment(s).{next_due_str}"

        # --- Announcements ---
        announcements = []
        try:
            announcements = Announcement.get_for_role('member')[:5]
        except Exception as ex:
            current_app.logger.warning("Announcements fetch failed: %s", ex)

        # --- Progress ---
        latest_progress = None
        try:
            progress_records = Progress.get_member_progress(member.id, limit=1)
            latest_progress = progress_records[0] if progress_records else None
        except Exception as ex:
            current_app.logger.warning("Progress fetch failed: %s", ex)

        # --- Render ---
        return render_template(
            'member/dashboard.html',
            member=member,
            stats=stats,
            announcements=announcements,
            latest_progress=latest_progress,
            alert_message=alert_message
        )

    except Exception as e:
        current_app.logger.exception("Critical error in dashboard: %s", e)
        flash('Unexpected error loading dashboard.')
        return redirect(url_for('auth.login'))


@member_routes_bp.route('/profile')
@login_required
@member_required
def profile():
    """Member profile management"""
    try:
        user_id = session['user_id']
        user = User.get_by_id(user_id)
        member = Member.get_by_user_id(user_id)

        if not member:
            flash('Member profile not found')
            return redirect(url_for('member.dashboard'))

        return render_template('member/profile.html', user=user, member=member)
    except Exception as e:
        current_app.logger.exception("Error loading profile: %s", e)
        flash('Error loading profile')
        return redirect(url_for('member.dashboard'))


@member_routes_bp.route('/profile/update', methods=['POST'])
@login_required
@member_required
def update_profile():
    """Update member profile"""
    try:
        user_id = session['user_id']
        user = User.get_by_id(user_id)
        member = Member.get_by_user_id(user_id)

        if not user or not member:
            flash('Profile not found')
            return redirect(url_for('member.profile'))

        # Update user information
        user.full_name = request.form.get('full_name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')

        # Update member information carefully (type-safe)
        try:
            weight_val = request.form.get('weight')
            if weight_val:
                member.weight = float(weight_val)
        except ValueError:
            flash('Invalid weight value', 'warning')

        try:
            height_val = request.form.get('height')
            if height_val:
                member.height = float(height_val)
        except ValueError:
            flash('Invalid height value', 'warning')

        member.emergency_contact = request.form.get('emergency_contact')
        member.emergency_phone = request.form.get('emergency_phone')
        member.medical_conditions = request.form.get('medical_conditions')
        member.fitness_goals = request.form.get('fitness_goals')

        user.save()
        member.save()

        flash('Profile updated successfully!')
    except Exception as e:
        current_app.logger.exception("Error updating profile: %s", e)
        flash('Error updating profile', 'danger')

    return redirect(url_for('member.profile'))


@member_routes_bp.route('/workouts')
@login_required
@member_required
def workouts():
    """Member workouts and workout plans"""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)

        # Get member's workout plans
        workout_plans = MemberWorkoutPlan.get_member_plans(member.id)

        # Optionally fetch details for each plan
        plans_with_details = []
        for plan in workout_plans:
            details = WorkoutPlanDetail.get_plan_details(plan.id)
            plans_with_details.append({
                "plan": plan,
                "details": details
            })

        # Get available workouts by category
        strength_workouts = Workout.get_by_category('strength')
        cardio_workouts = Workout.get_by_category('cardio')
        flexibility_workouts = Workout.get_by_category('flexibility')

        return render_template(
            'member/workouts.html',
            workout_plans=plans_with_details,
            strength_workouts=strength_workouts,
            cardio_workouts=cardio_workouts,
            flexibility_workouts=flexibility_workouts
        )
    except Exception as e:
        current_app.logger.exception("Error loading workouts: %s", e)
        flash('Error loading workouts')
        return redirect(url_for('member.dashboard'))


@member_routes_bp.route('/diet')
@login_required
@member_required
def diet():
    """Member diet plans"""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)
        diet_plans = Diet.get_member_diet_plans(member.id)
        return render_template('member/diet.html', diet_plans=diet_plans)
    except Exception as e:
        current_app.logger.exception("Error loading diet plans: %s", e)
        flash('Error loading diet plans')
        return redirect(url_for('member.dashboard'))


@member_routes_bp.route('/progress')
@login_required
@member_required
def progress():
    """Member progress tracking with charts"""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)
        progress_records = Progress.get_member_progress(member.id)

        # ---------------- Build Chart.js data ----------------
        chart_labels = []
        chart_weight = []
        chart_bmi = []
        chart_bodyfat = []

        for record in reversed(progress_records):  # chronological order
            dt = record.recorded_date  # already converted to date in model
            if dt:
                chart_labels.append(dt.strftime("%b %d"))
                chart_weight.append(record.weight or None)
                chart_bmi.append(record.bmi or None)
                chart_bodyfat.append(record.body_fat_percentage or None)

        return render_template(
            'member/progress.html',
            member=member,
            progress_records=progress_records,
            chart_labels=json.dumps(chart_labels),
            chart_weight=json.dumps(chart_weight),
            chart_bmi=json.dumps(chart_bmi),
            chart_bodyfat=json.dumps(chart_bodyfat)
        )

    except Exception as e:
        current_app.logger.exception("Error loading progress: %s", e)
        flash('Error loading progress')
        return redirect(url_for('member.dashboard'))



@member_routes_bp.route('/attendance')
@login_required
@member_required
def attendance():
    """Member attendance history with auto-absent handling"""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)

        # Try to call Attendance.auto_mark_absent() if provided by model; fallback to safe manual logic.
        try:
            if hasattr(Attendance, 'auto_mark_absent'):
                Attendance.auto_mark_absent()
            else:
                # Fallback: mark scheduled sessions for past dates as absent
                attendance_records_tmp = Attendance.get_member_attendance(member.id, limit=30)
                now = datetime.now()
                for record in attendance_records_tmp:
                    if getattr(record, 'status', None) == "scheduled" and getattr(record, 'date', None) and record.date < date.today():
                        try:
                            record.status = "absent"
                            record.save()
                        except Exception:
                            current_app.logger.debug("Failed to auto-mark absent for record %s", getattr(record, 'id', 'N/A'))
        except Exception as ex:
            current_app.logger.warning("Auto-absent operation failed: %s", ex)

        # Get last 30 records
        attendance_records = Attendance.get_member_attendance(member.id, limit=30)

        # More robust auto-absent: if scheduled and start time passed for same day
        now = datetime.now()
        for record in attendance_records:
            try:
                if getattr(record, 'status', None) == "scheduled":
                    check_in = getattr(record, 'check_in_time', None)
                    # if check_in stored as string, parse it
                    if isinstance(check_in, str):
                        check_in = _parse_datetime(check_in)
                    if check_in and record.date:
                        session_datetime = datetime.combine(record.date, check_in.time())
                        if now > session_datetime:
                            record.status = "absent"
                            record.save()
            except Exception as e:
                current_app.logger.warning("Auto-absent failed for %s: %s", getattr(record, 'id', 'N/A'), e)

        # Re-fetch after updates
        attendance_records = Attendance.get_member_attendance(member.id, limit=30)

        # Stats
        total_sessions = len(attendance_records)
        present_sessions = sum(1 for a in attendance_records if getattr(a, 'status', None) == 'present')
        absent_sessions = sum(1 for a in attendance_records if getattr(a, 'status', None) == 'absent')
        late_sessions = sum(1 for a in attendance_records if getattr(a, 'status', None) == 'late')

        # Only count completed sessions for percentage
        completed = present_sessions + absent_sessions + late_sessions
        attendance_percentage = (present_sessions / completed * 100) if completed > 0 else 0

        return render_template(
            'member/attendance.html',
            attendance_records=attendance_records,
            total_sessions=total_sessions,
            present_sessions=present_sessions,
            absent_sessions=absent_sessions,
            late_sessions=late_sessions,
            attendance_percentage=attendance_percentage,
            today=date.today()
        )

    except Exception as e:
        current_app.logger.exception("Error loading attendance: %s", e)
        flash('Error loading attendance')
        return redirect(url_for('member.dashboard'))


@member_routes_bp.route('/payments')
@login_required
@member_required
def payments():
    """Member payment history — robust and loop-safe."""
    try:
        user_id = session.get('user_id') or session.get('member_id')
        if not user_id:
            flash('Please log in to view payments.', 'danger')
            return redirect(url_for('auth.login'))

        member = Member.get_by_user_id(user_id)
        if not member:
            flash('Member profile not found.', 'danger')
            return redirect(url_for('auth.login'))

        # Try model first, fallback to direct query if model fails
        try:
            payment_records = Payment.get_member_payments(member.id) or []
        except Exception as ex:
            current_app.logger.exception("Payment model fetch failed, falling back to SQL: %s", ex)
            # fallback direct query
            from app.models.database import execute_query
            db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
            rows = execute_query(
                "SELECT id, member_id, amount, currency, method, transaction_id, status, note, created_at "
                "FROM payments WHERE member_id = ? ORDER BY created_at DESC",
                (member.id,), db_path, fetch=True
            )
            payment_records = []
            if rows:
                for r in rows:
                    if hasattr(r, 'keys'):
                        payment_records.append({k: r[k] for k in r.keys()})
                    elif isinstance(r, (list, tuple)):
                        payment_records.append({
                            'id': r[0] if len(r) > 0 else None,
                            'member_id': r[1] if len(r) > 1 else None,
                            'amount': r[2] if len(r) > 2 else None,
                            'currency': r[3] if len(r) > 3 else None,
                            'method': r[4] if len(r) > 4 else None,
                            'transaction_id': r[5] if len(r) > 5 else None,
                            'status': r[6] if len(r) > 6 else None,
                            'note': r[7] if len(r) > 7 else None,
                            'created_at': r[8] if len(r) > 8 else None
                        })
                    elif isinstance(r, dict):
                        payment_records.append(r)
                    else:
                        payment_records.append({'note': str(r)})

        # Normalize any object-like records to plain dict for template safety
        normalized = []
        for rec in payment_records:
            if rec is None:
                continue
            if isinstance(rec, dict):
                normalized.append(rec)
            elif hasattr(rec, '__dict__'):
                normalized.append(vars(rec))
            elif hasattr(rec, 'keys'):
                normalized.append({k: rec[k] for k in rec.keys()})
            else:
                normalized.append({'note': str(rec)})
        payment_records = normalized

        # Pass the member to the template (fixes UndefinedError)
        return render_template('member/payments.html', payment_records=payment_records, member=member)

    except Exception as e:
        # Log full traceback and render the payments page (empty) instead of redirecting.
        current_app.logger.exception("Unhandled error in /member/payments: %s", e)
        flash('Unable to load payments right now. Please contact support.', 'danger')
        # Render the page with safe defaults (prevents redirect loops)
        return render_template('member/payments.html', payment_records=[], member=None)


@member_routes_bp.route('/schedule_session')
@login_required
@member_required
def schedule_session():
    """Schedule training session (GET)"""
    try:
        membership_status = session.get('membership_status')
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)

        # 🔒 Prevent booking if membership is inactive/pending/expired
        if getattr(member, 'status', 'inactive') != "active" or (
                member.membership_end_date and member.membership_end_date < date.today()
        ):
            flash("Your membership is inactive or expired. Please contact admin to activate or renew.", "danger")
            return redirect(url_for("member.membership_status"))

        # Get available trainers
        assigned_trainer = Trainer.get_by_id(member.trainer_id)

        # Get available time slots
        time_slots = [
            "6:00 AM - 8:00 AM",
            "8:00 AM - 10:00 AM",
            "10:00 AM - 12:00 PM",
            "12:00 PM - 2:00 PM",
            "2:00 PM - 4:00 PM",
            "4:00 PM - 6:00 PM",
            "6:00 PM - 8:00 PM",
            "8:00 PM - 10:00 PM"
        ]

        return render_template(
            'member/schedule_session.html',
            today=date.today(),
            assigned_trainer=assigned_trainer,
            time_slots=time_slots,
            member=member,
            membership_status=membership_status
        )
    except Exception as e:
        current_app.logger.exception("Error loading schedule session page: %s", e)
        flash('Error loading scheduling page')
        return redirect(url_for('member.dashboard'))


@member_routes_bp.route('/schedule_session', methods=['POST'])
@login_required
@member_required
def schedule_session_post():
    """Process session scheduling with validation: one session per member per date (2 hrs).
       If member already has any scheduled session on that date, block creation and show a flash
       instructing them to reschedule via Attendance page.
    """
    try:
        user_id = session.get('user_id')
        member = Member.get_by_user_id(user_id)

        # Basic checks
        if not member:
            flash("Member profile not found.", "danger")
            return redirect(url_for('member.schedule_session'))

        if getattr(member, 'status', 'inactive') != "active" or (
                member.membership_end_date and member.membership_end_date < date.today()
        ):
            flash("Your membership is inactive or expired. Please contact admin to activate or renew.", "danger")
            return redirect(url_for("member.membership_status"))

        assigned_trainer = Trainer.get_by_id(member.trainer_id)
        if not assigned_trainer:
            flash("Assigned trainer not found. Contact admin.", "danger")
            return redirect(url_for('member.schedule_session'))

        session_date_raw = request.form.get('session_date')
        time_slot = request.form.get('time_slot')

        if not all([session_date_raw, time_slot]):
            flash('All fields are required', 'warning')
            return redirect(url_for('member.schedule_session'))

        # Parse session date
        try:
            session_date = datetime.strptime(session_date_raw, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format', 'warning')
            return redirect(url_for('member.schedule_session'))

        # 1) Can't book past dates
        if session_date < date.today():
            flash('Cannot schedule sessions for past dates', 'warning')
            return redirect(url_for('member.schedule_session'))

        # 2) Derive slot datetimes and require start > now
        start_iso, end_iso = _slot_to_datetimes(time_slot, on_date=session_date)
        if not start_iso:
            flash('Invalid time slot selected.', 'warning')
            return redirect(url_for('member.schedule_session'))

        try:
            start_dt = datetime.fromisoformat(start_iso)
        except Exception:
            flash('Failed to parse slot start time', 'warning')
            return redirect(url_for('member.schedule_session'))

        if start_dt <= datetime.now():
            flash('Cannot schedule a session that starts now or in the past. Please select a future slot.', 'warning')
            return redirect(url_for('member.schedule_session'))

        # --------------------
        # 3) Enforce: only one session per member per DATE (2 hrs)
        # --------------------
        existing_for_member = Attendance.get_member_scheduled_on_date(member.id, session_date)

        # Helper to normalize model returns (list/tuple/dict/sqlite3.Row/object) -> object-like with attributes
        from types import SimpleNamespace
        def _normalize_record(rec):
            if rec is None:
                return None
            # If list/tuple: take first element (most model helpers return list when they intend single)
            if isinstance(rec, (list, tuple)):
                if not rec:
                    return None
                rec = rec[0]
            # sqlite3.Row or dict-like
            if hasattr(rec, 'keys'):
                try:
                    return SimpleNamespace(**{k: rec[k] for k in rec.keys()})
                except Exception:
                    # fallback: try mapping to common names
                    data = {}
                    try:
                        data['id'] = rec['id']
                    except Exception:
                        pass
                    return SimpleNamespace(**data)
            # dict
            if isinstance(rec, dict):
                return SimpleNamespace(**rec)
            # object already with attributes
            if hasattr(rec, 'id') or hasattr(rec, 'time_slot'):
                return rec
            # tuple/list fallback: assume common ordering [id, member_id, trainer_id, date, time_slot, status, ...]
            if isinstance(rec, (list, tuple)):
                try:
                    return SimpleNamespace(
                        id=rec[0] if len(rec) > 0 else None,
                        member_id=rec[1] if len(rec) > 1 else None,
                        trainer_id=rec[2] if len(rec) > 2 else None,
                        date=rec[3] if len(rec) > 3 else None,
                        time_slot=rec[4] if len(rec) > 4 else None,
                        status=rec[5] if len(rec) > 5 else None
                    )
                except Exception:
                    return None
            return None

        existing_record = _normalize_record(existing_for_member)

        # If member already has any booking that day -> block creation and instruct reschedule via Attendance page
        if existing_record:
            # If booking is for the same slot, tell them they already booked it
            if getattr(existing_record, 'time_slot', None) == time_slot:
                flash('You already have this slot booked for that date.', 'info')
            else:
                flash('Only one booking per day is allowed. To change your slot, please reschedule from the Attendance page.', 'warning')
            return redirect(url_for('member.attendance'))

        # 4) New booking: check trainer's slot availability
        if not Attendance.check_slot_availability(assigned_trainer.id, time_slot, session_date):
            flash('This time slot is not available', 'warning')
            return redirect(url_for('member.schedule_session'))

        existing_for_member = Attendance.get_member_scheduled_on_date(member.id, session_date)
        # existing_for_member may be a list of Attendance objects (your model returns a list)
        existing_record = None
        if isinstance(existing_for_member, (list, tuple)):
            existing_record = existing_for_member[0] if existing_for_member else None
        else:
            existing_record = existing_for_member

        # if there's an existing record, check whether this request intends to reschedule
        wants_reschedule = request.form.get('reschedule', '').lower() in ('1', 'true', 'yes') or request.form.get('action') == 'reschedule'

        if existing_record:
            # If same slot already exists, simply inform user
            if getattr(existing_record, 'time_slot', None) == time_slot:
                flash('You already have this slot booked for that date.', 'info')
                return redirect(url_for('member.attendance'))

            # If user explicitly requested reschedule, attempt to reschedule
            if wants_reschedule:
                # check trainer availability excluding the existing attendance id
                if not Attendance.check_slot_availability(
                    assigned_trainer.id,
                    time_slot,
                    session_date,
                    exclude_attendance_id=getattr(existing_record, 'id', None)
                ):
                    flash('Trainer is not available for the new slot. Please choose a different slot.', 'warning')
                    return redirect(url_for('member.schedule_session'))

                # perform reschedule (update existing record)
                try:
                    existing_record.time_slot = time_slot
                    existing_record.status = 'scheduled'
                    existing_record.save()
                    flash('Your session has been rescheduled.', 'success')
                except Exception as ex:
                    current_app.logger.exception("Failed to reschedule attendance id=%s: %s", getattr(existing_record, 'id', None), ex)
                    flash('Failed to reschedule. Please try again or contact admin.', 'danger')
                return redirect(url_for('member.attendance'))

            # otherwise (no reschedule intent) block another booking the same day
            flash('Only one booking per day is allowed. To change your slot, please reschedule from the Attendance page.', 'warning')
            return redirect(url_for('member.attendance'))
        # 5) Create attendance record (store time_slot; Attendance.save will persist datetimes if needed)
        attendance = Attendance(
            member_id=member.id,
            trainer_id=assigned_trainer.id,
            date=session_date,
            time_slot=time_slot,
            status='scheduled'
        )
        attendance.save()
        flash('Session scheduled successfully!', 'success')

    except Exception as e:
        current_app.logger.exception(f'Error scheduling session: {e}')
        flash('Error scheduling session', 'danger')

    return redirect(url_for('member.attendance'))

@member_routes_bp.route('/attendance/<int:attendance_id>/reschedule', methods=['POST'])
@login_required
@member_required
def reschedule_attendance(attendance_id):
    """Reschedule a specific attendance booking (member-owned) with robust validation."""
    try:
        user_id = session.get('user_id')
        member = Member.get_by_user_id(user_id)
        
        # 1. Basic Member Check
        if not member:
            flash("Member profile not found.", "danger")
            return redirect(url_for('member.attendance'))

        # 2. ACTIVE MEMBERSHIP CHECK (Constraint from schedule_session_post)
        if getattr(member, 'status', 'inactive') != "active" or (
                member.membership_end_date and member.membership_end_date < date.today()
        ):
            flash("Your membership is inactive or expired. Please contact admin to activate or renew.", "danger")
            return redirect(url_for("member.membership_status")) 

        # Load the attendance record and ensure it belongs to this member
        attendance = Attendance.get_by_id(attendance_id)
        if not attendance or getattr(attendance, 'member_id', None) != member.id:
            flash("Booking not found or you don't have permission to modify it.", "danger")
            return redirect(url_for('member.attendance'))

        # Get the assigned trainer from the existing booking
        assigned_trainer = Trainer.get_by_id(attendance.trainer_id)

        # 3. ASSIGNED TRAINER CHECK (Constraint from schedule_session_post)
        if not assigned_trainer:
            flash("Assigned trainer not found for this session. Contact admin.", "danger")
            return redirect(url_for('member.attendance'))
        
        new_slot = request.form.get('time_slot')
        if not new_slot:
            flash('Please choose a new time slot.', 'warning')
            return redirect(url_for('member.attendance'))

        # 4. Check if the new slot is the same as the existing one (Good UX)
        if attendance.time_slot == new_slot:
            flash('You are already booked for this slot on that date.', 'info')
            return redirect(url_for('member.attendance'))

        # Derive datetimes for the new slot
        start_iso, end_iso = _slot_to_datetimes(new_slot, on_date=attendance.date)
        if not start_iso:
            flash('Invalid time slot selected.', 'warning')
            return redirect(url_for('member.attendance'))

        try:
            start_dt = datetime.fromisoformat(start_iso)
        except Exception:
            flash('Failed to parse slot start time', 'warning')
            return redirect(url_for('member.attendance'))

        # 5. FUTURE START TIME CHECK (Constraint from schedule_session_post)
        if start_dt <= datetime.now():
            flash('Cannot reschedule to a slot that starts now or in the past. Please select a future slot.', 'warning')
            return redirect(url_for('member.attendance'))

        # 6. Check trainer availability excluding this attendance id (Core rescheduling check)
        # We use the assigned_trainer ID retrieved earlier
        if not Attendance.check_slot_availability(assigned_trainer.id, new_slot, attendance.date, exclude_attendance_id=attendance.id):
            flash('Trainer is not available at the requested new slot.', 'warning')
            return redirect(url_for('member.attendance'))

        # Update and save
        attendance.time_slot = new_slot
        attendance.status = 'scheduled'
        attendance.save()
        flash('Booking rescheduled successfully!', 'success')
        return redirect(url_for('member.attendance'))

    except Exception as e:
        # current_app.logger.exception("Error rescheduling attendance id=%s: %s", attendance_id, e)
        flash('Error rescheduling booking. Please try again later.', 'danger')
        return redirect(url_for('member.attendance'))

@member_routes_bp.route('/membership_status')
@login_required
@member_required
def membership_status():
    """Show membership validity, expiry, and renewal notifications"""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)

        if not member:
            flash("Member profile not found")
            return redirect(url_for('member.dashboard'))

        today = date.today()
        expiry_date = member.membership_end_date
        days_left = (expiry_date - today).days if expiry_date else 0

        # Default notification
        notification = None

        if not expiry_date:
            notification = "Your membership has not been activated yet. Please contact the admin."
        elif days_left < 0:
            notification = f"Your membership expired on {expiry_date}. Please renew at the admin desk."
        elif days_left <= 7:
            notification = f"Your membership will expire in {days_left} days (on {expiry_date}). Please renew at the admin desk."

        # Also show an 'inactive' warning if status is not active
        if getattr(member, 'status', 'inactive') != 'active':
            notification = (notification + " | " if notification else "") + "⚠️ Your membership is not active. Please contact admin."

        return render_template(
            "member/membership_status.html",
            member=member,
            expiry_date=expiry_date,
            days_left=days_left,
            notification=notification
        )
    except Exception as e:
        current_app.logger.exception("Error loading membership status: %s", e)
        flash('Error loading membership status')
        return redirect(url_for('member.dashboard'))


@member_routes_bp.route('/api/trainer/<int:trainer_id>/schedule')
@login_required
@member_required
def trainer_schedule_api(trainer_id):
    """API endpoint for trainer schedule (JSON)"""
    session_date = request.args.get('date', date.today().isoformat())

    try:
        try:
            schedule_date = datetime.strptime(session_date, '%Y-%m-%d').date()
        except Exception:
            schedule_date = date.today()

        # Get trainer's schedule for the date
        schedule = Attendance.get_trainer_schedule(trainer_id, schedule_date)

        # Convert to JSON-serializable format
        schedule_data = []
        for booking in schedule:
            schedule_data.append({
                'time_slot': getattr(booking, 'time_slot', None),
                'member_name': getattr(booking, 'member_name', None),
                'status': getattr(booking, 'status', None)
            })

        return jsonify(schedule_data)
    except Exception as e:
        current_app.logger.exception("Error fetching trainer schedule: %s", e)
        return jsonify({'error': 'Failed to fetch schedule'}), 500
