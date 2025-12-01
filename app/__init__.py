# app/__init__.py
from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os # Added for FLASK_DEBUG check

from .models import db, User, create_tables
from config import Config


login_manager = LoginManager()
login_manager.login_view = 'main.login'  # The name of the login view function
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Peewee specific setup
    @app.before_request
    def before_request():
        db.connect()

    @app.after_request
    def after_request(response):
        db.close()
        return response

    @app.cli.command('init_db')
    def init_db_command():
        """Initializes the database tables and optionally creates a default admin user."""
        create_tables()
        print("Database tables created.")

        # --- WARNING: Default Admin User Creation for Development ONLY ---
        # This block creates a default admin user if one doesn't exist.
        # This SHOULD BE REMOVED or significantly secured (e.g., strong random password,
        # one-time setup) for production deployments.
        if os.environ.get('FLASK_DEBUG') == '1': # Only create in debug/development mode
            # Ensure app context is available for User model access
            with app.app_context():
                if not User.select().where(User.email == 'admin@clai.com').exists():
                    hashed_password = bcrypt.generate_password_hash('admin').decode('utf-8')
                    User.create(
                        username='admin',
                        email='admin@clai.com',
                        password=hashed_password,
                        role='admin',
                        name='Admin CLAI'
                    )
                    print("Default admin user created: admin@clai.com with password 'admin'")
                else:
                    print("Admin user already exists.")
        # --- END WARNING ---

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.get(User.id == int(user_id))
        except User.DoesNotExist:
            return None

    # Register blueprints here
    from app import routes
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    app.register_blueprint(routes.bp)  # Assuming routes are in a blueprint named 'bp' in routes.py

    return app
