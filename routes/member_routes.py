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
from utils.decorators import login_required, member_required
from models.workout_plan import MemberWorkoutPlan, WorkoutPlanDetail




member_routes_bp = Blueprint('member', __name__)

@member_routes_bp.route('/dashboard')
@login_required
@member_required
def dashboard():
    """Member dashboard"""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)
        
        if not member:
            flash('Member profile not found')
            return redirect(url_for('auth.login'))
        
        # Get member statistics
        stats = {
            'membership_status': member.status,
            'membership_expires': member.membership_end_date,
            'days_until_expiry': (member.membership_end_date - date.today()).days if member.membership_end_date else 0,
            'recent_attendance': Attendance.get_member_attendance(member.id, limit=5),
            'pending_payments': Payment.get_member_payments(member.id)[:3]
        }

        # 🔔 Alert message for expiry & pending payments
        alert_message = None
        if member.membership_end_date:
            days_left = (member.membership_end_date - date.today()).days
            if days_left < 0:
                alert_message = f"⚠️ Your membership expired on {member.membership_end_date}. Please renew at the admin desk."
            elif days_left <= 7:
                alert_message = f"⏳ Your membership will expire in {days_left} days (on {member.membership_end_date}). Please renew soon."
        
        if stats['pending_payments']:
            alert_message = (alert_message + " | " if alert_message else "") + \
                            f"💰 You have {len(stats['pending_payments'])} pending payment(s). Please clear them at the admin desk."

        # Get announcements for members
        announcements = Announcement.get_for_role('member')[:5]
        
        # Get latest progress record
        progress_records = Progress.get_member_progress(member.id, limit=1)
        latest_progress = progress_records[0] if progress_records else None
        
        return render_template('member/dashboard.html',
                             member=member,
                             stats=stats,
                             announcements=announcements,
                             latest_progress=latest_progress,
                             alert_message=alert_message)   # 🔔 send alert
    except Exception as e:
        flash('Error loading dashboard')
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
    """Member attendance history"""
    user_id = session['user_id']
    member = Member.get_by_user_id(user_id)
    
    # Get attendance records
    attendance_records = Attendance.get_member_attendance(member.id, limit=30)
    
    # Calculate attendance statistics
    total_sessions = len(attendance_records)
    present_sessions = len([a for a in attendance_records if a.status == 'present'])
    attendance_percentage = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    return render_template('member/attendance.html',
                         attendance_records=attendance_records,
                         total_sessions=total_sessions,
                         present_sessions=present_sessions,
                         attendance_percentage=attendance_percentage)

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
    trainers = Trainer.get_all_active()
    
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
    
    return render_template('member/schedule_session.html',
                         trainers=trainers,
                         time_slots=time_slots)

@member_routes_bp.route('/schedule_session', methods=['POST'])
@login_required
@member_required
def schedule_session_post():
    """Process session scheduling"""
    try:
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)
        
        trainer_id = request.form.get('trainer_id')
        session_date = request.form.get('session_date')
        time_slot = request.form.get('time_slot')
        
        if not all([trainer_id, session_date, time_slot]):
            flash('All fields are required')
            return redirect(url_for('member.schedule_session'))
        
        session_date = datetime.strptime(session_date, '%Y-%m-%d').date()
        
        # Check if slot is available
        if not Attendance.check_slot_availability(trainer_id, time_slot, session_date):
            flash('This time slot is not available')
            return redirect(url_for('member.schedule_session'))
        
        # Create attendance record
        attendance = Attendance(
            member_id=member.id,
            trainer_id=int(trainer_id),
            date=session_date,
            time_slot=time_slot
        )
        
        attendance_id = attendance.save()
        if attendance_id:
            flash('Session scheduled successfully!')
        else:
            flash('Error scheduling session')
            
    except Exception as e:
        flash('Error scheduling session')
    
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