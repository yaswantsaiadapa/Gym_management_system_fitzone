from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, date

# Import enhanced models
from models.database import init_db
from models.user import User
from models.member import Member
from models.trainer import Trainer
from models.membership_plan import MembershipPlan
from models.payment import Payment
from models.workout import Workout
from models.diet import Diet
from models.progress import Progress
from models.announcement import Announcement

# Import route blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.member_routes import member_routes_bp
from routes.trainer_routes import trainer_routes_bp
from routes.payment import payment_bp
from routes.workout import workout_bp
from routes.diet import diet_bp
from routes.progress import progress_bp
from routes.reports import reports_bp

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', 'gym_management.db')
    
    # Mail configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'FitZone Gym <noreply@fitzonegym.com>')
    
    # Initialize database
    init_db(app.config['DATABASE_PATH'])
    
    # Initialize Mail
    mail = Mail(app)
    app.mail = mail
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(member_routes_bp, url_prefix='/member')
    app.register_blueprint(trainer_routes_bp, url_prefix='/trainer')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(workout_bp, url_prefix='/workout')
    # app.register_blueprint(diet_bp, url_prefix='/diet')
    # app.register_blueprint(progress_bp, url_prefix='/progress')
    # app.register_blueprint(reports_bp, url_prefix='/reports')
    
    # Context processors
    @app.context_processor
    def inject_global_vars():
        return {
            'session': session,
            'datetime': datetime,
            'date': date
        }
    
    # Home route
    @app.route('/')
    def home():
        """Display general gym information"""
        announcements = Announcement.get_public_announcements()
        membership_plans = MembershipPlan.get_all_active()
        return render_template('home.html', 
                             announcements=announcements,
                             membership_plans=membership_plans)
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('error.html', 
                             error_code=404, 
                             error_message="Page not found"), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Internal server error"), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)