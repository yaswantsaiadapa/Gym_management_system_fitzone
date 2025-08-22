from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.trainer import Trainer
from utils.decorators import login_required

trainer_bp = Blueprint('trainer', __name__)

@trainer_bp.route('/hire_trainer')
@login_required
def hire_trainer():
    """Display hire trainer form"""
    return render_template('hire_trainer.html')

@trainer_bp.route('/hire_trainer', methods=['POST'])
@login_required
def hire_trainer_post():
    """Process hire trainer form"""
    try:
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        salary = float(request.form.get('salary'))
        working_hours = request.form.get('working_hours')
        
        # Validate required fields
        if not all([name, phone, email, salary, working_hours]):
            flash('All fields are required!')
            return redirect(url_for('trainer.hire_trainer'))
        
        trainer = Trainer(
            name=name,
            phone=phone,
            email=email,
            salary=salary,
            working_hours=working_hours
        )
        
        trainer_id = trainer.save()
        if trainer_id:
            flash(f'Trainer {name} hired successfully!')
        else:
            flash('Error hiring trainer. Please try again.')
            
    except ValueError:
        flash('Please enter a valid salary amount.')
    except Exception as e:
        flash('An error occurred while hiring the trainer.')
    
    return redirect(url_for('dashboard.index'))

@trainer_bp.route('/list_trainers')
@login_required
def list_trainers():
    """Display all active trainers"""
    trainers = Trainer.get_all_active()
    return render_template('list_trainers.html', trainers=trainers)

@trainer_bp.route('/trainer_details/<int:trainer_id>')
@login_required
def trainer_details(trainer_id):
    """Display detailed trainer information"""
    trainer = Trainer.get_by_id(trainer_id)
    if not trainer:
        flash('Trainer not found!')
        return redirect(url_for('trainer.list_trainers'))
    
    # Get trainer's today schedule
    todays_schedule = trainer.get_todays_schedule()
    
    return render_template('trainer_details.html', 
                         trainer=trainer, 
                         todays_schedule=todays_schedule)

@trainer_bp.route('/trainer/<int:trainer_id>/deactivate', methods=['POST'])
@login_required
def deactivate_trainer(trainer_id):
    """Deactivate a trainer"""
    trainer = Trainer.get_by_id(trainer_id)
    if not trainer:
        flash('Trainer not found!')
        return redirect(url_for('trainer.list_trainers'))
    
    trainer.deactivate()
    flash(f'Trainer {trainer.name} has been deactivated.')
    return redirect(url_for('trainer.list_trainers'))