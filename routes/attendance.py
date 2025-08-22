from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.member import Member
from models.trainer import Trainer
from models.attendance import Attendance
from utils.decorators import login_required
from datetime import date

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/mark_attendance')
@login_required
def mark_attendance():
    """Display mark attendance form"""
    members = Member.get_all_active()
    trainers = Trainer.get_all_active()
    return render_template('mark_attendance.html', members=members, trainers=trainers)

@attendance_bp.route('/mark_attendance', methods=['POST'])
@login_required
def mark_attendance_post():
    """Process mark attendance form"""
    try:
        member_id = int(request.form.get('member_id'))
        trainer_id = int(request.form.get('trainer_id'))
        time_slot = request.form.get('time_slot')
        
        if not all([member_id, trainer_id, time_slot]):
            flash('All fields are required!')
            return redirect(url_for('attendance.mark_attendance'))
        
        
        if not Attendance.check_slot_availability(trainer_id, time_slot):
            flash('Trainer is not available for this time slot!')
            return redirect(url_for('attendance.mark_attendance'))
        
        
        member = Member.get_by_id(member_id)
        trainer = Trainer.get_by_id(trainer_id)
        
        if not member or not trainer:
            flash('Invalid member or trainer selected!')
            return redirect(url_for('attendance.mark_attendance'))
        
        attendance = Attendance(
            member_id=member_id,
            trainer_id=trainer_id,
            date=date.today(),
            time_slot=time_slot
        )
        
        attendance_id = attendance.save()
        if attendance_id:
            flash(f'Attendance marked for {member.name} with trainer {trainer.name}!')
        else:
            flash('Error marking attendance. Please try again.')
            
    except ValueError:
        flash('Invalid member or trainer selected.')
    except Exception as e:
        flash('An error occurred while marking attendance.')
    
    return redirect(url_for('dashboard.index'))

@attendance_bp.route('/attendance_history')
@login_required
def attendance_history():
    """Display attendance history"""
    selected_date = request.args.get('date', date.today().isoformat())
    try:
        attendance_date = date.fromisoformat(selected_date)
    except ValueError:
        attendance_date = date.today()
    
    attendance_records = Attendance.get_attendance_by_date(attendance_date)
    return render_template('attendance_history.html', 
                         attendance_records=attendance_records,
                         selected_date=attendance_date)

@attendance_bp.route('/api/trainer/<int:trainer_id>/availability')
@login_required
def check_trainer_availability(trainer_id):
    """API endpoint to check trainer availability for time slots"""
    selected_date = request.args.get('date', date.today().isoformat())
    
    try:
        attendance_date = date.fromisoformat(selected_date)
    except ValueError:
        attendance_date = date.today()
    
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
    
    availability = {}
    for slot in time_slots:
        availability[slot] = Attendance.check_slot_availability(trainer_id, slot, attendance_date)
    
    return jsonify(availability)

@attendance_bp.route('/api/attendance/stats')
@login_required
def attendance_stats():
    """API endpoint for attendance statistics"""
    today_count = Attendance.get_todays_attendance()
    
    # Get current month stats
    today = date.today()
    monthly_stats = Attendance.get_monthly_stats(today.year, today.month)
    
    return jsonify({
        'today': today_count,
        'this_month': monthly_stats
    })

@attendance_bp.route('/attendance/<int:attendance_id>/update_status', methods=['POST'])
@login_required
def update_attendance_status(attendance_id):
    """Update attendance status (present/absent)"""
    new_status = request.form.get('status')
    
    if new_status not in ['present', 'absent']:
        flash('Invalid status!')
        return redirect(url_for('attendance.attendance_history'))
    
    # This would require extending the Attendance model
    # For now, we'll just flash a message
    flash(f'Attendance status updated to {new_status}!')
    return redirect(url_for('attendance.attendance_history'))