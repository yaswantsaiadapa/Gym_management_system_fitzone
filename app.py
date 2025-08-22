
from flask import Flask, render_template, session
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.member import member_bp
from routes.trainer import trainer_bp
from routes.attendance import attendance_bp
from routes.equipment import equipment_bp
from models.database import init_db
import os

def create_app():
    app = Flask(__name__)
    
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', 'gym_management.db')
    
    
    init_db(app.config['DATABASE_PATH'])
    
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(trainer_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(equipment_bp)
    
    
    @app.context_processor
    def inject_global_vars():
        return {
            'session': session
        }
    
    
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