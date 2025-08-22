from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.admin import Admin
from utils.decorators import logout_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
@logout_required
def login():
    """Display login page"""
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
@logout_required
def login_post():
    """Process login form"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Please enter both username and password!')
        return redirect(url_for('auth.login'))
    
    admin = Admin.authenticate(username, password)
    
    if admin:
        session['admin_id'] = admin.id
        session['admin_name'] = admin.name
        flash(f'Welcome back, {admin.name}!')
        return redirect(url_for('dashboard.index'))
    else:
        flash('Invalid credentials! Please try again.')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    """Logout user and clear session"""
    admin_name = session.get('admin_name', 'User')
    session.clear()
    flash(f'Goodbye, {admin_name}! You have been logged out successfully.')
    return redirect(url_for('auth.login'))