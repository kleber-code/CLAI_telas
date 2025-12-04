from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os

from .models import db, User, create_tables
from config import Config


login_manager = LoginManager()
login_manager.login_view = 'main.login'
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)
    bcrypt.init_app(app)

    @app.before_request
    def before_request():
        if db.is_closed():
            db.connect()

    @app.teardown_appcontext
    def teardown_db(exc):
        if not db.is_closed():
            db.close()

    @app.cli.command('init_db')
    def init_db_command():
        create_tables()
        print("Database tables created.")

        if os.environ.get('FLASK_DEBUG') == '1':
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

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.get(User.id == int(user_id))
        except User.DoesNotExist:
            return None

    from app import routes
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    app.register_blueprint(routes.bp)

    return app
