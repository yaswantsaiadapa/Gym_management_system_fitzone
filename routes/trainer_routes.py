from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.trainer import Trainer
from models.member import Member
from models.workout import Workout
from models.diet import Diet
from models.progress import Progress
from models.attendance import Attendance
from models.announcement import Announcement
from utils.decorators import login_required, trainer_required
from datetime import date, datetime
from models.workout_plan import MemberWorkoutPlan, WorkoutPlanDetail
from datetime import date, datetime

def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()




trainer_routes_bp = Blueprint('trainer_routes', __name__,url_prefix='/trainer')

@trainer_routes_bp.route('/dashboard')
@trainer_required
def dashboard():
    

    """Trainer dashboard"""
    try:
        trainer_id = session.get('trainer_id')
        trainer = Trainer.get_by_id(trainer_id)
        
        # Get trainer statistics
        total_clients = Member.get_trainer_client_count(trainer_id)
        today_sessions = Attendance.get_trainer_daily_sessions(trainer_id, date.today())
        active_workout_plans = MemberWorkoutPlan.get_trainer_active_plans_count(trainer_id)
        
        # Get today's schedule
        todays_schedule = Attendance.get_trainer_schedule(trainer_id, date.today())
        
        # Get recent client progress updates
        recent_progress = Progress.get_trainer_client_progress(trainer_id, limit=5)
        
        # Get assigned clients
        assigned_clients = Member.get_trainer_clients(trainer_id)
        
        # Get announcements for trainers
        announcements = Announcement.get_for_role('trainer')
        
        return render_template('trainer/dashboard.html',
                             trainer=trainer,
                             total_clients=total_clients,
                             today_sessions=today_sessions,
                             active_workout_plans=active_workout_plans,
                             todays_schedule=todays_schedule,
                             recent_progress=recent_progress,
                             assigned_clients=assigned_clients,
                             announcements=announcements)
    except Exception as e:
        flash('Error loading dashboard data.')
        return render_template('trainer/dashboard.html', trainer=None)
    

@trainer_routes_bp.route('/clients')
@trainer_required
def clients():
    """Trainer's clients page"""
    trainer_id = session.get('trainer_id')
    
    # Get assigned clients with details
    clients = Member.get_trainer_clients_detailed(trainer_id)
    
    return render_template('trainer/clients.html', clients=clients)

@trainer_routes_bp.route('/clients/<int:member_id>')
@trainer_required
def client_details(member_id):
    """View client details"""
    trainer_id = session.get('trainer_id')
    
    # Verify this client is assigned to this trainer
    member = Member.get_by_id(member_id)
    if not member or member.trainer_id != trainer_id:
        flash('Client not found or not assigned to you!')
        return redirect(url_for('trainer_routes.clients'))
    
    # Get client's comprehensive data
    attendance_records = Attendance.get_member_attendance(member_id, limit=10)
    progress_records = Progress.get_member_progress(member_id, limit=5)
    current_workout_plan = MemberWorkoutPlan.get_member_active_plan(member_id)
    current_diet_plan = Diet.get_member_active_plan(member_id)
    
    return render_template('trainer/client_details.html',
                         member=member,
                         attendance_records=attendance_records,
                         progress_records=progress_records,
                         current_workout_plan=current_workout_plan,
                         current_diet_plan=current_diet_plan)

@trainer_routes_bp.route('/clients/<int:member_id>/workout-plan/create', methods=['GET', 'POST'])
@trainer_required
def create_workout_plan(member_id):
    """Create workout plan for client"""
    trainer_id = session.get('trainer_id')
    
    # Verify client assignment
    member = Member.get_by_id(member_id)
    if not member or member.trainer_id != trainer_id:
        flash('Client not found or not assigned to you!')
        return redirect(url_for('trainer_routes.clients'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            start_date_raw = request.form.get('start_date')
            end_date_raw = request.form.get('end_date')     
            
            if not all([name, start_date_raw]):
                flash('Please fill in all required fields!')
                return redirect(url_for('trainer_routes.create_workout_plan', member_id=member_id))

            start_date = _parse_date(start_date_raw)
            end_date = _parse_date(end_date_raw)

            if end_date and end_date < start_date:
                flash('End date cannot be before start date!')
                return redirect(url_for('trainer_routes.create_workout_plan', member_id=member_id))

            # Create workout plan
            workout_plan = MemberWorkoutPlan(
                member_id=member_id,
                trainer_id=trainer_id,
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date
            )
            
            plan_id = workout_plan.save()
            if plan_id:
                flash(f'Workout plan "{name}" created successfully!')
                return redirect(url_for('trainer_routes.edit_workout_plan', plan_id=plan_id))
            else:
                flash('Error creating workout plan!')
                
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
    
    # Get available workouts and equipment
    available_workouts = Workout.get_all()
    available_equipment = [eq for eq in Equipment.get_all() if eq.is_working()]
    
    return render_template(
        'trainer/create_workout_plan.html',
        member=member,
        available_workouts=available_workouts,
        available_equipment=available_equipment
    )


@trainer_routes_bp.route('/workout-plans/<int:plan_id>/edit')
@trainer_required
def edit_workout_plan(plan_id):
    """Edit workout plan"""
    trainer_id = session.get('trainer_id')
    
    # Get workout plan and verify ownership
    workout_plan = MemberWorkoutPlan.get_by_id(plan_id)
    if not workout_plan or workout_plan.trainer_id != trainer_id:
        flash('Workout plan not found!')
        return redirect(url_for('trainer_routes.clients'))
    
    # Get plan details, workouts, equipment, and member info
    plan_details = WorkoutPlanDetail.get_plan_details(plan_id)
    available_workouts = Workout.get_all()
    available_equipment = [eq for eq in Equipment.get_all() if eq.is_working()]
    member = Member.get_by_id(workout_plan.member_id)
    
    return render_template(
        'trainer/edit_workout_plan.html',
        workout_plan=workout_plan,
        plan_details=plan_details,
        available_workouts=available_workouts,
        available_equipment=available_equipment,
        member=member
    )

@trainer_routes_bp.route('/clients/<int:member_id>/diet-plan/create', methods=['GET', 'POST'])
@trainer_required
def create_diet_plan(member_id):
    """Create diet plan for client"""
    trainer_id = session.get('trainer_id')
    
    # Verify client assignment
    member = Member.get_by_id(member_id)
    if not member or member.trainer_id != trainer_id:
        flash('Client not found or not assigned to you!')
        return redirect(url_for('trainer_routes.clients'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            total_calories = request.form.get('total_calories')
            start_date_raw = request.form.get('start_date')
            end_date_raw = request.form.get('end_date')
            
            if not all([name, start_date_raw]):
                flash('Please fill in all required fields!')
                return redirect(url_for('trainer_routes.create_diet_plan', member_id=member_id))

            start_date = _parse_date(start_date_raw)
            end_date = _parse_date(end_date_raw)

            if end_date and end_date < start_date:
                flash('End date cannot be before start date!')
                return redirect(url_for('trainer_routes.create_diet_plan', member_id=member_id))

            diet_plan = Diet(
                member_id=member_id,
                trainer_id=trainer_id,
                name=name,
                description=description,
                total_calories=int(total_calories) if total_calories else None,
                start_date=start_date,
                end_date=end_date
            )
            
            plan_id = diet_plan.save()
            if plan_id:
                flash(f'Diet plan "{name}" created successfully!')
                return redirect(url_for('trainer_routes.edit_diet_plan', plan_id=plan_id))
            else:
                flash('Error creating diet plan!')
                
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
    
    return render_template('trainer/create_diet_plan.html', member=member)

@trainer_routes_bp.route('/diet-plans/<int:plan_id>/edit')
@trainer_required
def edit_diet_plan(plan_id):
    """Edit diet plan"""
    trainer_id = session.get('trainer_id')
    
    # Get diet plan and verify ownership
    diet_plan = Diet.get_by_id(plan_id)
    if not diet_plan or diet_plan.trainer_id != trainer_id:
        flash('Diet plan not found!')
        return redirect(url_for('trainer_routes.clients'))
    
    # Get plan meals
    meals = diet_plan.get_meals()
    member = Member.get_by_id(diet_plan.member_id)
    
    return render_template('trainer/edit_diet_plan.html',
                         diet_plan=diet_plan,
                         meals=meals,
                         member=member)

@trainer_routes_bp.route('/clients/<int:member_id>/progress/record', methods=['GET', 'POST'])
@trainer_required
def record_progress(member_id):
    """Record client progress"""
    trainer_id = session.get('trainer_id')
    
    # Verify client assignment
    member = Member.get_by_id(member_id)
    if not member or member.trainer_id != trainer_id:
        flash('Client not found or not assigned to you!')
        return redirect(url_for('trainer_routes.clients'))
    
    if request.method == 'POST':
        try:
            recorded_date = _parse_date(request.form.get('recorded_date')) or date.today()
            weight = request.form.get('weight')
            body_fat_percentage = request.form.get('body_fat_percentage')
            muscle_mass = request.form.get('muscle_mass')
            chest = request.form.get('chest')
            waist = request.form.get('waist')
            hips = request.form.get('hips')
            bicep = request.form.get('bicep')
            thigh = request.form.get('thigh')
            notes = request.form.get('notes')
            
            # Calculate BMI if weight and height are available
            bmi = None
            if weight and member.height:
                height_m = member.height / 100
                bmi = round(float(weight) / (height_m ** 2), 1)
            
            # Create progress record
            progress = Progress(
                member_id=member_id,
                recorded_date=recorded_date,
                weight=float(weight) if weight else None,
                body_fat_percentage=float(body_fat_percentage) if body_fat_percentage else None,
                muscle_mass=float(muscle_mass) if muscle_mass else None,
                bmi=bmi,
                chest=float(chest) if chest else None,
                waist=float(waist) if waist else None,
                hips=float(hips) if hips else None,
                bicep=float(bicep) if bicep else None,
                thigh=float(thigh) if thigh else None,
                notes=notes,
                recorded_by=trainer_id
            )
            
            progress_id = progress.save()
            if progress_id:
                flash('Progress recorded successfully!')
                return redirect(url_for('trainer_routes.client_details', member_id=member_id))
            else:
                flash('Error recording progress!')
                
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
    
    # Get recent progress for reference
    recent_progress = Progress.get_member_progress(member_id, limit=1)
    last_record = recent_progress[0] if recent_progress else None
    
    return render_template('trainer/record_progress.html',
                         member=member,
                         last_record=last_record)

@trainer_routes_bp.route('/clients/<int:member_id>/attendance/mark', methods=['POST'])
@trainer_required
def mark_attendance(member_id):
    """Trainer marks attendance for a client (upsert by trainer/member/date/slot)"""
    trainer_id = session.get('trainer_id')

    # Verify client belongs to this trainer
    member = Member.get_by_id(member_id)
    if not member or member.trainer_id != trainer_id:
        flash('Client not found or not assigned to you!')
        return redirect(url_for('trainer_routes.clients'))

    try:
        # Normalize inputs
        attendance_date = _parse_date(request.form.get('date')) or date.today()
        time_slot = request.form.get('time_slot') or "General"
        status = request.form.get('status', 'present').lower()  # present/absent

        # Try to find an existing scheduled session
        existing = Attendance.get_for_trainer_member_slot(
            trainer_id=trainer_id,
            member_id=member_id,
            attendance_date=attendance_date,
            time_slot=time_slot
        )

        if existing:
            existing.status = status
            existing.save()
            flash(f'Attendance updated to {status} for the session on {attendance_date}.')
        else:
            # Only check availability when creating a *new* row
            if not Attendance.check_slot_availability(trainer_id, time_slot, attendance_date):
                flash(f"Trainer already has a session at {time_slot} on {attendance_date}")
                return redirect(url_for('trainer_routes.client_details', member_id=member_id))

            new_att = Attendance(
                member_id=member_id,
                trainer_id=trainer_id,
                date=attendance_date,
                time_slot=time_slot,
                status=status
            )
            new_att.save()
            flash(f'Attendance marked as {status} for {attendance_date}.')

    except Exception as e:
        flash(f'Error while marking attendance: {str(e)}')

    return redirect(url_for('trainer_routes.client_details', member_id=member_id))



@trainer_routes_bp.route('/schedule')
@trainer_required
def schedule():
    """Trainer schedule view"""
    trainer_id = session.get('trainer_id')
    
    # Get selected date from query parameter or use today
    selected_date_str = request.args.get('date', date.today().isoformat())
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = date.today()
    
    # Get schedule for selected date
    schedule = Attendance.get_trainer_schedule(trainer_id, selected_date)
    
    return render_template('trainer/schedule.html',
                         schedule=schedule,
                         selected_date=selected_date)