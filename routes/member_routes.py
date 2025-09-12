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
from models.attendance import Attendance
from models.announcement import Announcement
from routes.admin import members
from utils.decorators import login_required, member_required
from models.workout_plan import MemberWorkoutPlan, WorkoutPlanDetail
from flask import current_app




member_routes_bp = Blueprint('member', __name__,url_prefix='/member')



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
        if membership_expires:
            if days_until_expiry < 0:
                alert_message = f"⚠️ Your membership expired on {membership_expires}. Please renew at the admin desk."
            elif days_until_expiry <= 7:
                alert_message = f"⏳ Your membership will expire in {days_until_expiry} days (on {membership_expires}). Please renew soon."

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
    """Member attendance history with auto-absent handling"""
    user_id = session['user_id']
    member = Member.get_by_user_id(user_id)

    # Get last 30 records
    attendance_records = Attendance.get_member_attendance(member.id, limit=30)

    now = datetime.now()

    # --- Auto-mark scheduled sessions as absent if time has passed ---
    # --- Auto-mark scheduled sessions as absent if time has passed ---
    for record in attendance_records:
        if record.status == "scheduled":
            try:
                check_in = record.check_in_time
                if isinstance(check_in, str):
                    check_in = Attendance._parse_datetime(check_in)
                if check_in and record.date:
                    session_datetime = datetime.combine(record.date, check_in.time())
                    if now > session_datetime:  # session already passed
                        record.status = "absent"
                        record.save()
            except Exception as e:
                current_app.logger.warning(
                    f"Auto-absent failed for record {getattr(record, 'id', 'N/A')}: {e}"
                )


    # --- Re-fetch after updates ---
    attendance_records = Attendance.get_member_attendance(member.id, limit=30)

    # Stats
    total_sessions = len(attendance_records)
    present_sessions = sum(1 for a in attendance_records if a.status == 'present')
    absent_sessions = sum(1 for a in attendance_records if a.status == 'absent')
    late_sessions = sum(1 for a in attendance_records if a.status == 'late')

    attendance_percentage = (present_sessions / (present_sessions + absent_sessions + late_sessions) * 100) \
                            if (present_sessions + absent_sessions + late_sessions) > 0 else 0

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
    """Process session scheduling"""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)
        assigned_trainer = Trainer.get_by_id(member.trainer_id)
        session_date = request.form.get('session_date')
        time_slot = request.form.get('time_slot')

        if not all([session_date, time_slot]):
            flash('All fields are required')
            return redirect(url_for('member.schedule_session'))

        session_date = datetime.strptime(session_date, '%Y-%m-%d').date()

        # ✅ Members can only schedule sessions from NEXT slot onwards
        today = date.today()
        now_time = datetime.now().time()

        if session_date == today:
            if " - " in time_slot:
                check_in, check_out = time_slot.split(" - ", 1)
                check_in_time = datetime.strptime(check_in.strip(), "%I:%M %p").time()  # ✅ Fix
                if now_time >= check_in_time:
                    flash("You can only schedule upcoming slots, not current or past ones.", "warning")
                    return redirect(url_for('member.schedule_session'))

        # Check if slot is available
        if not Attendance.check_slot_availability(assigned_trainer.id, time_slot, session_date):
            flash('This time slot is not available')
            return redirect(url_for('member.schedule_session'))

        # Split time_slot into check-in and check-out
        if " - " in time_slot:
            check_in, check_out = time_slot.split(" - ", 1)
        else:
            check_in, check_out = time_slot, None  # fallback

        # ✅ Always start with status="scheduled"
        attendance = Attendance(
            member_id=member.id,
            trainer_id=assigned_trainer.id,
            date=session_date,
            check_in_time=check_in.strip(),
            check_out_time=check_out.strip() if check_out else None,
            status="scheduled"
        )

        attendance_id = attendance.save()
        if attendance_id:
            flash('Session scheduled successfully!', 'success')
        else:
            flash('Error scheduling session', 'danger')
            
    except Exception as e:
        flash(f'Error scheduling session: {e}', 'danger')
    
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