from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def logout_required(f):
    """Decorator to require logout for routes (like login page)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' in session:
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


