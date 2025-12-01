# run.py
from app import create_app, bcrypt
from app.models import create_tables, User
import os


app = create_app()


@app.cli.command('init_db')
def init_db_command():
    """Initializes the database tables and creates a default admin user."""
    create_tables()
    print("Database tables created.")

    # Create a default admin user if not exists
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


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)

