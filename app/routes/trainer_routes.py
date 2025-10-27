from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session
from app.models.equipment import Equipment
from app.models.trainer import Trainer
from app.models.member import Member
from app.models.workout import Workout
from app.models.diet import Diet
from app.models.progress import Progress
from app.models.attendance import Attendance,_slot_to_datetimes
from app.models.announcement import Announcement

from app.utils.decorators import  login_required, trainer_required
from app.models.workout_plan import MemberWorkoutPlan, WorkoutPlanDetail
from datetime import date, datetime

def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()




trainer_routes_bp = Blueprint('trainer_routes', __name__,url_prefix='/trainer')
@trainer_routes_bp.route('/equipment')
def equipment_list():
    """View all equipment"""
    try:
        equipment = Equipment.get_all()
        return render_template('trainer/equipment_list.html', equipment=equipment)
    except Exception as e:
        flash(f"Error loading equipment list: {str(e)}", "danger")
        return render_template('admin/equipment_list.html', equipment=[])
@trainer_routes_bp.route('/equipment/maintenance/<int:equipment_id>', methods=['POST'])
def update_equipment_status(equipment_id):
    """Update maintenance status of equipment"""
    equipment = Equipment.get_by_id(equipment_id)
    if not equipment:
        flash('Equipment not found.', 'danger')
        return redirect(url_for('trainer_routes.equipment_list'))

    try:
        action = request.form.get('action')
        notes = request.form.get('maintenance_notes')
        next_date = request.form.get('next_maintenance_date')

        if action == 'maintenance':
            equipment.mark_for_maintenance(notes=notes, next_date=next_date)
            flash('Equipment marked for maintenance.', 'success')
        elif action == 'working':
            equipment.mark_as_working()
            flash('Equipment marked as working.', 'success')
        elif action == 'out_of_order':
            equipment.mark_out_of_order(notes=notes)
            flash('Equipment marked as out of order.', 'warning')
        else:
            flash('Invalid action.', 'danger')

    except Exception as e:
        flash(f"Error updating status: {str(e)}", 'danger')

    return redirect(url_for('trainer_routes.equipment_list'))

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
        # Log full stack trace to the Flask logger so you can see exactly what failed
        current_app.logger.exception("Error in trainer.dashboard")

        # Optional: show the exception message in the flash while debugging.
        # Remove or simplify this in production.
        flash(f'Error loading dashboard data: {str(e)}', 'danger')

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
                          client=member, 
                         attendance_records=attendance_records,
                         progress_records=progress_records,
                         current_workout_plan=current_workout_plan,
                         current_diet_plan=current_diet_plan)

@trainer_routes_bp.route('/diet-plans/<int:plan_id>/meals/add', methods=['POST'])
def add_meal(plan_id):
    meal_name = request.form.get("meal_name")
    meal_type = request.form.get("meal_type")
    ingredients = request.form.get("ingredients")
    calories = request.form.get("calories")
    
    Diet.add_meal(plan_id, meal_name, meal_type, ingredients, calories)
    flash("✅ Meal added successfully!", "success")
    return redirect(url_for("trainer_routes.edit_diet_plan", plan_id=plan_id))


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
    available_workouts = Workout.get_all_active()
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
    available_workouts = Workout.get_all_active()
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
    trainer_id = session.get('trainer_id')

    # Verify client belongs to this trainer
    member = Member.get_by_id(member_id)
    if not member or member.trainer_id != trainer_id:
        flash('Client not found or not assigned to you!')
        return redirect(url_for('trainer_routes.clients'))

    try:
        raw_date = request.form.get('date', '').strip()
        time_slot = request.form.get('time_slot', '').strip()
        requested_status = request.form.get('status', 'present').lower()

        # parse attendance_date
        attendance_date = date.today()
        if raw_date:
            try:
                attendance_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError:
                try:
                    attendance_date = datetime.strptime(raw_date, '%B %d, %Y').date()
                except ValueError:
                    pass

        # 1) Must find an existing scheduled attendance row for this trainer/member/date/slot
        existing = Attendance.get_for_trainer_member_slot(
            trainer_id=trainer_id,
            member_id=member_id,
            attendance_date=attendance_date,
            time_slot=time_slot
        )

        if not existing:
            flash('No scheduled session found for this member at that date/slot. Trainers can only mark scheduled sessions.', 'warning')
            return redirect(url_for('trainer_routes.client_details', member_id=member_id))

        # 2) Get slot datetimes
        start_iso, end_iso = _slot_to_datetimes(existing.time_slot, on_date=existing.date)
        now = datetime.now()
        start_dt = datetime.fromisoformat(start_iso) if start_iso else None
        end_dt = datetime.fromisoformat(end_iso) if end_iso else None

        # Check trainer is marking during scheduled slot
        if not (start_dt and end_dt and start_dt <= now <= end_dt):
            flash('You can only mark attendance during the scheduled time slot.', 'warning')
            return redirect(url_for('trainer_routes.client_details', member_id=member_id))

        # Only allow present/late during slot
        if requested_status not in ('present', 'late'):
            flash('During a slot you may mark the client as Present or Late only.', 'warning')
            return redirect(url_for('trainer_routes.client_details', member_id=member_id))

        # Update attendance
        if not existing.check_in_time:
            existing.check_in_time = now
        existing.status = requested_status
        existing.save()
        flash(f'Attendance updated to {requested_status} for {attendance_date.strftime("%B %d, %Y")}.')

    except Exception as e:
        current_app.logger.exception(f'Error marking attendance: {e}')
        flash('Error while marking attendance', 'danger')

    return redirect(url_for('trainer_routes.client_details', member_id=member_id))


@trainer_routes_bp.route('/schedule')
@trainer_required
def schedule():
    Attendance.auto_mark_absent()
    """Trainer schedule view - MINIMAL FIX"""
    trainer_id = session.get('trainer_id')
    # Get selected date from query parameter or use today
    selected_date_str = request.args.get('date', date.today().isoformat())
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = date.today()
    
    # Get schedule for selected date using the fixed method
    schedule = Attendance.get_trainer_schedule(trainer_id, selected_date)
    
    return render_template('trainer/schedule.html',
                         schedule=schedule,
                         selected_date=selected_date)

@trainer_routes_bp.route('/workouts')
@trainer_required
def workouts():
    workouts = Workout.get_all_active()
    return render_template('admin/workouts.html', workouts=workouts)

@trainer_routes_bp.route('/workouts/add', methods=['GET', 'POST'])
@trainer_required
def add_workout():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            category = request.form.get('category')
            equipment_needed = request.form.get('equipment_needed')

            if not name:
                flash('Workout name is required!')
                return redirect(url_for('admin.add_workout'))

            workout = Workout(
                name=name,
                description=description,
                category=category,
                equipment_needed=equipment_needed
            )
            workout_id = workout.save()
            if workout_id:
                flash(f'Workout "{name}" added successfully!')
            else:
                flash('Error adding workout!')
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
        return redirect(url_for('admin.workouts'))

    return render_template('admin/add_workout.html')

@trainer_routes_bp.route('/workout-plans')
@trainer_required
def workout_plans():
    plans = MemberWorkoutPlan.get_all_with_details()
    members = Member.get_all_active()
    trainers = Trainer.get_all_active()
    return render_template('admin/workout_plans.html', plans=plans,
                           members=members, trainers=trainers)

@trainer_routes_bp.route('/workout-plans/add', methods=['GET', 'POST'])
@trainer_required
def add_workout_plan():
    if request.method == 'POST':
        try:
            member_id = request.form.get('member_id')
            trainer_id = request.form.get('trainer_id')
            name = request.form.get('name')
            description = request.form.get('description')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')

            if not all([member_id, trainer_id, name]):
                flash('Member, Trainer and Plan Name are required!')
                # FIX: Use trainer_routes, not admin
                return redirect(url_for('trainer_routes.add_workout_plan'))

            plan = MemberWorkoutPlan(
                member_id=member_id,
                trainer_id=trainer_id,
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date
            )
            plan_id = plan.save()
            if plan_id:
                flash(f'Workout Plan "{name}" created successfully!')
            else:
                flash('Error creating workout plan!')
        except Exception as e:
            flash(f'An error occurred: {str(e)}')

        # FIX: redirect to trainer_routes.workout_plans
        return redirect(url_for('trainer_routes.workout_plans'))

    members = Member.get_all_active()
    trainers = Trainer.get_all_active()
    # FIX: Render trainer template
    return render_template('trainer/create_workout_plan.html',
                           members=members, trainers=trainers)


@trainer_routes_bp.route('/workout-plans/<int:plan_id>/add-detail', methods=['GET', 'POST'])
@trainer_required
def add_workout_plan_detail(plan_id):
    if request.method == 'POST':
        try:
            workout_id = request.form.get('workout_id')
            day_of_week_raw = request.form.get('day_of_week')
            day_of_week = int(day_of_week_raw) if day_of_week_raw else None
            sets = request.form.get('sets')
            reps = request.form.get('reps')
            weight = request.form.get('weight')
            rest_seconds = request.form.get('rest_seconds')
            notes = request.form.get('notes')

            if not workout_id:
                flash('Workout is required!')
                # FIX: use trainer_routes, not admin
                return redirect(url_for('trainer_routes.add_workout_plan_detail', plan_id=plan_id))

            if day_of_week not in range(1, 8):
                    flash("Day of week must be between 1 and 7!", "danger")
                    return redirect(url_for("trainer_routes.add_workout_plan_detail", plan_id=plan_id))

            detail = WorkoutPlanDetail(
                plan_id=plan_id,
                workout_id=workout_id,
                day_of_week=day_of_week,
                sets=sets,
                reps=reps,
                weight=weight,
                rest_seconds=rest_seconds,
                notes=notes
            )
            detail_id = detail.save()
            if detail_id:
                flash('Workout detail added successfully!')
            else:
                flash('Error adding workout detail!')
        except Exception as e:
            flash(f'An error occurred: {str(e)}')

        # FIX: go back to edit_workout_plan (trainer version)
        return redirect(url_for('trainer_routes.edit_workout_plan', plan_id=plan_id))

    workouts = Workout.get_all_active()
    # FIX: Use a new template under trainer/
    return render_template('trainer/add_workout_plan_detail.html',
                           workouts=workouts, plan_id=plan_id)


@trainer_routes_bp.route('/announcements')
@login_required
def announcements():
    announcements = Announcement.get_for_role('trainer')
    return render_template('trainer/announcements.html', announcements=announcements)

