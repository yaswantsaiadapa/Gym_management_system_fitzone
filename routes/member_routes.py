from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import date, datetime, timedelta
from models.user import User
from models.member import Member
from models.trainer import Trainer
from models.membership_plan import MembershipPlan
from models.payment import Payment
from models.workout import Workout
from models.diet import Diet
from models.progress import Progress
from models.attendance import Attendance, _slot_to_datetimes
from models.announcement import Announcement
from routes.admin import members
from utils.decorators import login_required, member_required
from models.workout_plan import MemberWorkoutPlan, WorkoutPlanDetail
from flask import current_app

member_routes_bp = Blueprint('member', __name__,url_prefix='/member')

@member_routes_bp.route('/announcements')
@login_required
def announcements():
    announcements = Announcement.get_for_role('member')
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

        # Attendance
        try:
            stats['recent_attendance'] = Attendance.get_member_attendance(member.id, limit=5)
        except Exception as ex:
            current_app.logger.warning("Attendance fetch failed: %s", ex)
        # Payments
        try:
            stats['pending_payments'] = Payment.get_member_payments(member.id)[:3]
        except Exception as ex:
            current_app.logger.warning("Payments fetch failed: %s", ex)

        # --- Alerts ---
        alert_message = None

        # ✅ NEW: Show alert if membership is not active (pending or suspended)
        if member.membership_status != "active":
            alert_message = "⚠️ Your membership is not active. Please complete payment or contact the admin."

        # Existing expiry warnings (still works for active members)
        elif membership_expires:
            if days_until_expiry < 0:
                alert_message = f"⚠️ Your membership expired on {membership_expires}. Please renew at the admin desk."
            elif days_until_expiry <= 7:
                alert_message = f"⏳ Your membership will expire in {days_until_expiry} days (on {membership_expires}). Please renew soon."

        # Pending payment notice (appended)
        if stats['pending_payments']:
            alert_message = (alert_message + " | " if alert_message else "") + \
                f"💰 You have {len(stats['pending_payments'])} pending payment(s). Please clear them at the admin desk."

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
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    member = Member.get_by_user_id(user_id)
    
    if not member:
        flash('Member profile not found')
        return redirect(url_for('member.dashboard'))
    
    return render_template('member/profile.html', user=user, member=member)

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
        
        # Update member information
        member.weight = float(request.form.get('weight')) if request.form.get('weight') else member.weight
        member.height = float(request.form.get('height')) if request.form.get('height') else member.height
        member.emergency_contact = request.form.get('emergency_contact')
        member.emergency_phone = request.form.get('emergency_phone')
        member.medical_conditions = request.form.get('medical_conditions')
        member.fitness_goals = request.form.get('fitness_goals')
        
        user.save()
        member.save()
        
        flash('Profile updated successfully!')
    except Exception as e:
        flash('Error updating profile')
    
    return redirect(url_for('member.profile'))

@member_routes_bp.route('/workouts')
@login_required
@member_required
def workouts():
    """Member workouts and workout plans"""
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


@member_routes_bp.route('/diet')
@login_required
@member_required
def diet():
    """Member diet plans"""
    user_id = session['user_id']
    member = Member.get_by_user_id(user_id)
    
    # Get member's diet plans
    diet_plans = Diet.get_member_diet_plans(member.id)
    
    return render_template('member/diet.html', diet_plans=diet_plans)

@member_routes_bp.route('/progress')
@login_required
@member_required
def progress():
    """Member progress tracking"""
    user_id = session['user_id']
    member = Member.get_by_user_id(user_id)
    
    # Get member's progress records
    progress_records = Progress.get_member_progress(member.id)
    
    return render_template('member/progress.html', 
                         progress_records=progress_records,
                         member=member)

@member_routes_bp.route('/attendance')
@login_required
@member_required
def attendance():
    Attendance.auto_mark_absent()
    """Member attendance history - SIMPLIFIED"""
    user_id = session['user_id']
    member = Member.get_by_user_id(user_id)

    # Get last 30 records
    attendance_records = Attendance.get_member_attendance(member.id, limit=30)

    # Simple auto-absent logic (optional - you can remove this if causing issues)
    now = datetime.now()
    for record in attendance_records:
        if record.status == "scheduled" and record.date and record.date < date.today():
            try:
                record.status = "absent"
                record.save()
            except Exception:
                pass  # Ignore errors in auto-absent

    # Re-fetch after updates
    attendance_records = Attendance.get_member_attendance(member.id, limit=30)

    # Stats
    total_sessions = len(attendance_records)
    present_sessions = sum(1 for a in attendance_records if a.status == 'present')
    absent_sessions = sum(1 for a in attendance_records if a.status == 'absent')
    late_sessions = sum(1 for a in attendance_records if a.status == 'late')

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
        attendance_percentage=attendance_percentage
    )

@member_routes_bp.route('/payments')
@login_required
@member_required
def payments():
    """Member payment history"""
    user_id = session['user_id']
    member = Member.get_by_user_id(user_id)
    
    # Get payment records
    payment_records = Payment.get_member_payments(member.id)
    
    return render_template('member/payments.html', payment_records=payment_records)

@member_routes_bp.route('/schedule_session')
@login_required
@member_required
def schedule_session():
    """Schedule training session"""
    user_id = session['user_id']
    member = Member.get_by_user_id(user_id)

    # 🔒 Prevent booking if membership is inactive/pending/expired
    if member.membership_status != "active" or (
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
        time_slots=time_slots
    )


@member_routes_bp.route('/schedule_session', methods=['POST'])
@login_required
@member_required
def schedule_session_post():
    """Process session scheduling with validation: one session per member per date; future slot start only; reschedule allowed."""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)

        # 🔒 Prevent scheduling if membership is inactive/pending/expired
        if member.membership_status != "active" or (
            member.membership_end_date and member.membership_end_date < date.today()
        ):
            flash("Your membership is inactive or expired. Please contact admin to activate or renew.", "danger")
            return redirect(url_for("member.membership_status"))

        assigned_trainer = Trainer.get_by_id(member.trainer_id)

        session_date_raw = request.form.get('session_date')
        time_slot = request.form.get('time_slot')

        if not all([session_date_raw, time_slot]):
            flash('All fields are required', 'warning')
            return redirect(url_for('member.schedule_session'))

        session_date = datetime.strptime(session_date_raw, '%Y-%m-%d').date()

        # 1) Can't book past dates
        if session_date < date.today():
            flash('Cannot schedule sessions for past dates', 'warning')
            return redirect(url_for('member.schedule_session'))

        # 2) Derive slot datetimes and require start > now
        start_iso, end_iso = _slot_to_datetimes(time_slot, on_date=session_date)
        if not start_iso:
            flash('Invalid time slot selected.', 'warning')
            return redirect(url_for('member.schedule_session'))

        start_dt = datetime.fromisoformat(start_iso)
        if start_dt <= datetime.now():
            flash('Cannot schedule a session that starts now or in the past. Please select a future slot.', 'warning')
            return redirect(url_for('member.schedule_session'))

        # 3) Check member already has a scheduled session for this date
        existing_for_member = Attendance.get_member_scheduled_on_date(member.id, session_date)
        if existing_for_member:
            if existing_for_member.time_slot == time_slot:
                flash('You already have this slot booked for that date.', 'info')
                return redirect(url_for('member.attendance'))

            if not Attendance.check_slot_availability(
                assigned_trainer.id,
                time_slot,
                session_date,
                exclude_attendance_id=existing_for_member.id
            ):
                flash('Trainer is not available for the new slot. Please choose a different slot.', 'warning')
                return redirect(url_for('member.schedule_session'))

            existing_for_member.time_slot = time_slot
            existing_for_member.status = 'scheduled'
            existing_for_member.save()
            flash('Your session has been rescheduled.', 'success')
            return redirect(url_for('member.attendance'))

        # 4) New booking: check trainer's slot availability
        if not Attendance.check_slot_availability(assigned_trainer.id, time_slot, session_date):
            flash('This time slot is not available', 'warning')
            return redirect(url_for('member.schedule_session'))

        # 5) Create attendance record
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


@member_routes_bp.route('/membership_status')
@login_required
@member_required
def membership_status():
    """Show membership validity, expiry, and renewal notifications"""
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

    return render_template(
        "member/membership_status.html",
        member=member,
        expiry_date=expiry_date,
        days_left=days_left,
        notification=notification
    )


@member_routes_bp.route('/api/trainer/<int:trainer_id>/schedule')
@login_required
@member_required
def trainer_schedule_api(trainer_id):
    """API endpoint for trainer schedule"""
    session_date = request.args.get('date', date.today().isoformat())
    
    try:
        schedule_date = datetime.strptime(session_date, '%Y-%m-%d').date()
    except ValueError:
        schedule_date = date.today()
    
    # Get trainer's schedule for the date
    schedule = Attendance.get_trainer_schedule(trainer_id, schedule_date)
    
    # Convert to JSON-serializable format
    schedule_data = []
    for booking in schedule:
        schedule_data.append({
            'time_slot': booking.time_slot,
            'member_name': booking.member_name,
            'status': booking.status
        })

    
    return jsonify(schedule_data)