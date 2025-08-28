from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def logout_required(f):
    """Decorator to require logout for routes (like login page)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            role = session.get('role', 'member')
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'member':
                return redirect(url_for('member_routes.dashboard'))
            elif role == 'trainer':
                return redirect(url_for('trainer_routes.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def member_required(f):
    """Decorator to require member role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login_form', role='member'))
        
        if session.get('role') != 'member':
            flash('Access denied. Member login required.', 'error')
            return redirect(url_for('auth.login_form', role='member'))
        
        # Check if member profile exists and is active
        if 'member_id' not in session:
            flash('Member profile not found. Please contact admin.', 'error')
            return redirect(url_for('auth.logout'))
        
        return f(*args, **kwargs)
    return decorated_function

def trainer_required(f):
    """Decorator to require trainer role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login_form', role='trainer'))
        
        if session.get('role') != 'trainer':
            flash('Access denied. Trainer login required.', 'error')
            return redirect(url_for('auth.login_form', role='trainer'))
        
        # Check if trainer profile exists and is active
        if 'trainer_id' not in session:
            flash('Trainer profile not found. Please contact admin.', 'error')
            return redirect(url_for('auth.logout'))
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash(f'Access denied. Required roles: {", ".join(allowed_roles)}', 'error')
                return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_membership_status(f):
    """Decorator to check if member's membership is active"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') == 'member':
            membership_status = session.get('membership_status', 'inactive')
            if membership_status not in ['active']:
                flash('Your membership is inactive. Please renew your membership.', 'warning')
                return redirect(url_for('member_routes.payments'))
        
        return f(*args, **kwargs)
    return decorated_function

def ajax_login_required(f):
    """Decorator for AJAX routes that require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return {'error': 'Authentication required', 'redirect': url_for('auth.login')}, 401
        return f(*args, **kwargs)
    return decorated_function