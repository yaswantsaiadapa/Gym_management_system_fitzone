from flask import Blueprint, render_template, session
from models.member import Member
from models.trainer import Trainer
from models.attendance import Attendance
from utils.decorators import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Display main dashboard with statistics"""
    try:
        # Get statistics
        total_members = Member.get_count_active()
        total_trainers = Trainer.get_count_active()
        today_attendance = Attendance.get_todays_attendance()
        
        return render_template('dashboard.html',
                             admin_name=session.get('admin_name'),
                             total_members=total_members,
                             total_trainers=total_trainers,
                             today_attendance=today_attendance)
    except Exception as e:
        # Log error in production
        print(f"Dashboard error: {e}")
        return render_template('dashboard.html',
                             admin_name=session.get('admin_name'),
                             total_members=0,
                             total_trainers=0,
                             today_attendance=0)