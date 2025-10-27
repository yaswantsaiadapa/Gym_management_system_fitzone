from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_mail import Mail
# removed werkzeug.security import; using flask_bcrypt instead
from flask_bcrypt import Bcrypt
import os
from datetime import datetime, date
import json
# Import enhanced models
from app.models.database import init_db
from app.models.user import User
from app.models.member import Member
from app.models.trainer import Trainer
from app.models.membership_plan import MembershipPlan
from app.models.payment import Payment
from app.models.workout import Workout
from app.models.diet import Diet
from app.models.progress import Progress
from app.models.announcement import Announcement
from app.models.equipment import Equipment  # ✅ added equipment model

# Import route blueprints (ONLY 4 main ones)
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.member_routes import member_routes_bp
from app.routes.trainer_routes import trainer_routes_bp

from datetime import timedelta


def create_app():
    app = Flask(__name__)
    app.jinja_env.globals['timedelta'] = timedelta

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY',
        'your-secret-key-change-in-production'
    )
    app.config['DATABASE_PATH'] = os.environ.get(
        'DATABASE_PATH',
        'gym_management.db'
    )
    
    # Mail configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'fitzonegym1111@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'piwwnfohnhvzvmif')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        'FitZone Gym <noreply@fitzonegym.com>'
    )
    
    # Initialize Mail
    mail = Mail(app)
    app.mail = mail

    # Initialize Bcrypt and attach to app for convenience
    bcrypt = Bcrypt(app)
    app.bcrypt = bcrypt
    
    # Initialize database inside app context (required because seeding uses current_app / bcrypt)
    with app.app_context():
        init_db(app.config['DATABASE_PATH'])

    app.config.setdefault('SESSION_COOKIE_SECURE', False)   # must be False for http://127.0.0.1
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)

    import logging
    # ensure debug logging is enabled
    app.logger.setLevel(logging.DEBUG)

    @app.after_request
    def log_session_and_cookies(response):
        try:
            # log session contents (shallow)
            app.logger.debug("=== SESSION DEBUG === keys=%s", list(session.keys()))
            for k in list(session.keys()):
                app.logger.debug(" session['%s'] = %r", k, session.get(k))
            # log Set-Cookie headers if present
            cookies = response.headers.getlist('Set-Cookie')
            if cookies:
                for c in cookies:
                    app.logger.debug(" Set-Cookie -> %s", c)
            else:
                app.logger.debug(" No Set-Cookie headers on response")
        except Exception as e:
            app.logger.debug("Error logging session: %s", e)
        return response
    
    # Register ONLY 4 blueprints
    app.register_blueprint(auth_bp,url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(member_routes_bp, url_prefix='/member')
    app.register_blueprint(trainer_routes_bp, url_prefix='/trainer')
    
    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%b %d, %Y %I:%M %p'):
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value  # return as-is if it can’t parse
        return value.strftime(format)
    # Context processors (global vars for templates)
    @app.context_processor
    def inject_global_vars():
        return {
            'session': session,
            'datetime': datetime,
            'date': date
        }
    



    @app.route('/')
    def home():
        announcements = Announcement.get_public_announcements()
        membership_plans = MembershipPlan.get_all_active()

        # Decode features JSON (if stored as string)
        for plan in membership_plans:
            if isinstance(plan.features, str):
                try:
                    plan.features = json.loads(plan.features)
                except Exception:
                    plan.features = []

        return render_template(
            'home.html',
            announcements=announcements,
            membership_plans=membership_plans
        )

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template(
            'error.html',
            error_code=404,
            error_message="Page not found"
        ), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template(
            'error.html',
            error_code=500,
            error_message="Internal server error"
        ), 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
