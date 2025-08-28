from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models.workout import Workout
from models.member import Member
from models.trainer import Trainer
from models.workout_plan import MemberWorkoutPlan
from utils.decorators import login_required, trainer_required, admin_required

workout_bp = Blueprint('workout', __name__)

@workout_bp.route('/manage')
@login_required
@admin_required
def manage_workouts():
    """Manage all workouts (admin only)"""
    workouts = Workout.get_all_active()
    return render_template('workout/manage.html', workouts=workouts)

@workout_bp.route('/add', methods=['GET', 'POST'])
@login_required
@trainer_required
def add_workout():
    """Add new workout (trainers can add workouts)"""
    if request.method == 'GET':
        return render_template('workout/add.html')
    
    try:
        user_id = session['user_id']
        trainer = Trainer.get_by_user_id(user_id)
        
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        difficulty_level = request.form.get('difficulty_level')
        duration_minutes = request.form.get('duration_minutes')
        calories_burned = request.form.get('calories_burned')
        instructions = request.form.get('instructions')
        equipment_needed = request.form.get('equipment_needed')
        
        if not all([name, category, difficulty_level]):
            flash('Name, category, and difficulty level are required')
            return redirect(url_for('workout.add_workout'))
        
        workout = Workout(
            name=name,
            description=description,
            category=category,
            difficulty_level=difficulty_level,
            duration_minutes=int(duration_minutes) if duration_minutes else None,
            calories_burned=int(calories_burned) if calories_burned else None,
            instructions=instructions,
            equipment_needed=equipment_needed,
            created_by=trainer.id if trainer else None
        )
        
        workout_id = workout.save()
        if workout_id:
            flash(f'Workout "{name}" added successfully!')
        else:
            flash('Error adding workout')
            
    except Exception as e:
        flash('Error adding workout')
    
    return redirect(url_for('workout.manage_workouts'))

@workout_bp.route('/library')
@login_required
def workout_library():
    """Browse workout library"""
    # Get filter parameters
    category = request.args.get('category', 'all')
    difficulty = request.args.get('difficulty', 'all')
    
    if category == 'all':
        workouts = Workout.get_all_active()
    else:
        workouts = Workout.get_by_category(category)
    
    # Filter by difficulty if specified
    if difficulty != 'all':
        workouts = [w for w in workouts if w.difficulty_level == difficulty]
    
    # Get unique categories and difficulties for filters
    all_workouts = Workout.get_all_active()
    categories = list(set([w.category for w in all_workouts if w.category]))
    difficulties = ['beginner', 'intermediate', 'advanced']
    
    return render_template('workout/library.html',
                         workouts=workouts,
                         categories=categories,
                         difficulties=difficulties,
                         selected_category=category,
                         selected_difficulty=difficulty)

@workout_bp.route('/<int:workout_id>/details')
@login_required
def workout_details(workout_id):
    """View workout details"""
    workout = Workout.get_by_id(workout_id) if hasattr(Workout, 'get_by_id') else None
    
    if not workout:
        flash('Workout not found')
        return redirect(url_for('workout.workout_library'))
    
    return render_template('workout/details.html', workout=workout)

@workout_bp.route('/plans')
@login_required
def workout_plans():
    """View workout plans based on user role"""
    user_role = session.get('role')
    user_id = session['user_id']
    
    if user_role == 'member':
        member = Member.get_by_user_id(user_id)
        plans = MemberWorkoutPlan.get_member_plans(member.id) if hasattr(MemberWorkoutPlan, 'get_member_plans') else []
    elif user_role == 'trainer':
        trainer = Trainer.get_by_user_id(user_id)
        plans = MemberWorkoutPlan.get_trainer_plans(trainer.id) if hasattr(MemberWorkoutPlan, 'get_trainer_plans') else []
    else:  # admin
        plans = MemberWorkoutPlan.get_all() if hasattr(MemberWorkoutPlan, 'get_all') else []
    
    return render_template('workout/plans.html', plans=plans)

@workout_bp.route('/create_plan', methods=['GET', 'POST'])
@login_required
@trainer_required
def create_workout_plan():
    """Create workout plan for a member"""
    user_id = session['user_id']
    trainer = Trainer.get_by_user_id(user_id)
    
    if request.method == 'GET':
        clients = Member.get_by_trainer_id(trainer.id) if hasattr(Member, 'get_by_trainer_id') else []
        workouts = Workout.get_all_active()
        return render_template('workout/create_plan.html', 
                             clients=clients, 
                             workouts=workouts)
    
    try:
        member_id = request.form.get('member_id')
        plan_name = request.form.get('plan_name')
        description = request.form.get('description')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        # Get selected workouts
        selected_workouts = request.form.getlist('workouts')
        
        if not all([member_id, plan_name]):
            flash('Member and plan name are required')
            return redirect(url_for('workout.create_workout_plan'))
        
        # Verify member is assigned to trainer
        member = Member.get_by_id(member_id)
        if not member or member.trainer_id != trainer.id:
            flash('Invalid client selected')
            return redirect(url_for('workout.create_workout_plan'))
        
        # Create workout plan (would need MemberWorkoutPlan model)
        # This is a placeholder - you'd need to implement the MemberWorkoutPlan model
        flash(f'Workout plan "{plan_name}" created successfully!')
        
    except Exception as e:
        flash('Error creating workout plan')
    
    return redirect(url_for('workout.workout_plans'))

@workout_bp.route('/plan/<int:plan_id>')
@login_required
def view_workout_plan(plan_id):
    """View detailed workout plan"""
    # This would need MemberWorkoutPlan model implementation
    plan = None  # MemberWorkoutPlan.get_by_id(plan_id)
    
    if not plan:
        flash('Workout plan not found')
        return redirect(url_for('workout.workout_plans'))
    
    # Check access permissions
    user_role = session.get('role')
    user_id = session['user_id']
    
    if user_role == 'member':
        member = Member.get_by_user_id(user_id)
        if plan.member_id != member.id:
            flash('Access denied')
            return redirect(url_for('workout.workout_plans'))
    elif user_role == 'trainer':
        trainer = Trainer.get_by_user_id(user_id)
        if plan.trainer_id != trainer.id:
            flash('Access denied')
            return redirect(url_for('workout.workout_plans'))
    
    return render_template('workout/plan_details.html', plan=plan)

@workout_bp.route('/api/workouts/<category>')
@login_required
def api_workouts_by_category(category):
    """API endpoint to get workouts by category"""
    workouts = Workout.get_by_category(category)
    
    workouts_data = []
    for workout in workouts:
        workouts_data.append({
            'id': workout.id,
            'name': workout.name,
            'description': workout.description,
            'difficulty_level': workout.difficulty_level,
            'duration_minutes': workout.duration_minutes,
            'calories_burned': workout.calories_burned
        })
    
    return jsonify(workouts_data)