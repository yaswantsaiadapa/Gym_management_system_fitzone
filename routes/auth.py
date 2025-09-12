from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from models.user import User
from models.member import Member
from models.trainer import Trainer
from utils.decorators import logout_required
from utils.email_utils import send_password_change_notification
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/')
def index():
    """Auth index -> redirect to auth.login"""
    return redirect(url_for('auth.login'))


@auth_bp.route('/login')
@logout_required
def login():
    """Display login selection page"""
    return render_template('auth/login_select.html')


@auth_bp.route('/login/<role>')
@logout_required
def login_form(role):
    """Display role-specific login form"""
    if role not in ['admin', 'member', 'trainer']:
        flash('Invalid login type!')
        return redirect(url_for('auth.login'))

    return render_template('auth/login_form.html', role=role)


@auth_bp.route('/login/<role>', methods=['POST'])
@logout_required
def login_post(role):
    """Process role-specific login"""
    if role not in ['admin', 'member', 'trainer']:
        flash('Invalid login type!', 'danger')
        return redirect(url_for('auth.login'))

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('⚠️ Please enter both username and password!', 'warning')
        return redirect(url_for('auth.login_form', role=role))

    # Authenticate user
    user = User.authenticate(username, password)

    if user and user.role == role:
        # Set session data
        session['user_id'] = user.id
        session['username'] = user.username
        session['full_name'] = user.full_name
        session['role'] = user.role
        session['email'] = user.email

        # Get additional profile data based on role
        if role == 'member':
            member = Member.get_by_user_id(user.id)
            if member:
                session['member_id'] = member.id
                session['membership_status'] = member.status
            flash(f'✅ Welcome back, {user.full_name}! Redirecting to Member Dashboard.', 'success')
            return redirect(url_for('member.dashboard'))

        elif role == 'trainer':
            trainer = Trainer.get_by_user_id(user.id)
            if trainer:
                session['trainer_id'] = trainer.id
                session['trainer_status'] = trainer.status
            flash(f'✅ Welcome back, {user.full_name}! Redirecting to Trainer Dashboard.', 'success')
            return redirect(url_for('trainer_routes.dashboard'))

        elif role == 'admin':
            flash(f'✅ Welcome back, {user.full_name}! Redirecting to Admin Dashboard.', 'success')
            return redirect(url_for('admin.dashboard'))

    # If authentication fails
    flash('❌ Invalid credentials! Please check your username and password.', 'danger')
    return redirect(url_for('auth.login_form', role=role))



@auth_bp.route('/logout')
def logout():
    """Logout user and clear session"""
    user_name = session.get('full_name', 'User')
    role = session.get('role', '')
    session.clear()
    flash(f'Goodbye, {user_name}! You have been logged out successfully.')
    # Redirect to the application home (app-level route)
    return redirect(url_for('home'))


@auth_bp.route('/change_password')
def change_password_form():
    """Display change password form"""
    if 'user_id' not in session:
        flash('Please login to change your password.')
        return redirect(url_for('auth.login'))

    return render_template('auth/change_password.html')


@auth_bp.route('/change_password', methods=['POST'])
def change_password_post():
    """Process change password form"""
    if 'user_id' not in session:
        flash('Please login to change your password.')
        return redirect(url_for('auth.login'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not all([current_password, new_password, confirm_password]):
        flash('All fields are required!')
        return redirect(url_for('auth.change_password_form'))

    if new_password != confirm_password:
        flash('New passwords do not match!')
        return redirect(url_for('auth.change_password_form'))

    if len(new_password) < 6:
        flash('New password must be at least 6 characters long!')
        return redirect(url_for('auth.change_password_form'))

    # Get current user
    user = User.get_by_id(session['user_id'])
    if not user:
        flash('User not found!')
        return redirect(url_for('auth.logout'))

    # Verify current password
    if not check_password_hash(user.password_hash, current_password):
        flash('Current password is incorrect!')
        return redirect(url_for('auth.change_password_form'))

    # Update password
    try:
        user.update_password(new_password)

        # Send email notification
        try:
            send_password_change_notification(user.email, user.full_name)
        except Exception as e:
            current_app.logger.exception(f"Failed to send password change email: {e}")

        flash('Password changed successfully! You have been logged out for security.')
        return redirect(url_for('auth.logout'))

    except Exception:
        current_app.logger.exception("Error changing password for user id %s", session.get('user_id'))
        flash('An error occurred while changing password. Please try again.')
        return redirect(url_for('auth.change_password_form'))


@auth_bp.route('/forgot_password')
@logout_required
def forgot_password_form():
    """Display forgot password form"""
    return render_template('auth/forgot_password.html')


@auth_bp.route('/forgot_password', methods=['POST'])
@logout_required
def forgot_password_post():
    """Process forgot password form"""
    email = request.form.get('email')

    if not email:
        flash('Please enter your email address!')
        return redirect(url_for('auth.forgot_password_form'))

    # Check if user exists
    from models.database import execute_query
    db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
    query = 'SELECT * FROM users WHERE email = ? AND is_active = 1'
    result = execute_query(query, (email,), db_path, fetch=True)

    # Always show a generic message to avoid leaking account existence
    flash('If an account with this email exists, you will receive password reset instructions.')

    # In production: generate reset token and send email here

    return redirect(url_for('auth.login'))

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
@logout_required
def reset_password(token):
    """Reset password using a secure token"""
    from models.database import execute_query
    db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')

    # Verify token (example assumes you store token in users table)
    query = "SELECT id FROM users WHERE reset_token = ? AND is_active = 1"
    result = execute_query(query, (token,), db_path, fetch=True)

    if not result:
        flash("Invalid or expired password reset link!", "danger")
        return redirect(url_for('auth.forgot_password_form'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('auth.reset_password', token=token))

        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return redirect(url_for('auth.reset_password', token=token))

        hashed = generate_password_hash(new_password)
        execute_query(
            "UPDATE users SET password_hash = ?, reset_token = NULL WHERE id = ?",
            (hashed, result[0]['id']),
            db_path
        )

        flash("Password reset successful! Please login.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)

