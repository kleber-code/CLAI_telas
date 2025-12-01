# app/models.py
from peewee import Model, CharField, DateField, ForeignKeyField, TextField, DateTimeField, SqliteDatabase
from flask_login import UserMixin
import datetime


# Configure your database here. For development, SQLite is simple.
db = SqliteDatabase('clai.db')

class BaseModel(Model):
    class Meta:
        database = db

class User(UserMixin, BaseModel):
    username = CharField(unique=True)
    email = CharField(unique=True)
    password = CharField()
    name = CharField()
    profile_picture = CharField(default='default_profile.png')
    role = CharField(default='pedagogue')  # 'admin', 'pedagogue'

    def get_id(self):
        return str(self.id)

    class Meta:
        # Define table name explicitly
        table_name = 'users'

class Student(BaseModel):
    name = CharField()
    matricula = CharField(unique=True)
    dob = DateField()  # Date of Birth
    # WARNING: This field may contain sensitive medical information (International Classification of Diseases - CID).
    # Consider encryption at rest, stricter access controls, or re-evaluating its necessity.
    cid = CharField(null=True)  # International Classification of Diseases
    email = CharField(null=True)
    phone = CharField(null=True)
    grade = CharField(null=True)  # Turma
    course = CharField(null=True)
    responsible_name = CharField(null=True)
    responsible_phone = CharField(null=True)
    responsible_email = CharField(null=True)
    pedagogue = ForeignKeyField(User, backref='students', null=True)  # Assign a primary pedagogue
    student_picture = CharField(default='default_student.png')
    specific_needs_description = TextField(null=True)  # New field for RF05

    class Meta:
        table_name = 'students'

class Observation(BaseModel):
    student = ForeignKeyField(Student, backref='observations')
    pedagogue = ForeignKeyField(User, backref='made_observations')
    date = DateField(default=datetime.date.today)
    observation_text = TextField()
    justification = TextField(null=True)  # For updates, not for initial creation

    class Meta:
        table_name = 'observations'

class Attendance(BaseModel):
    student = ForeignKeyField(Student, backref='attendance_records')
    date = DateField(default=datetime.date.today)
    status = CharField(default='present')  # 'present', 'absent', 'justified_absent'

    class Meta:
        table_name = 'attendance'

class Event(BaseModel):
    title = CharField()
    description = TextField(null=True)
    start_time = DateTimeField()
    end_time = DateTimeField()
    student = ForeignKeyField(Student, backref='events', null=True)
    pedagogue = ForeignKeyField(User, backref='events', null=True)

    class Meta:
        table_name = 'events'

class DailyLog(BaseModel):
    student = ForeignKeyField(Student, backref='daily_logs')
    pedagogue = ForeignKeyField(User, backref='daily_logs')
    date = DateField(default=datetime.date.today)
    shift = CharField()  # Manhã, Tarde, Integral, Noite
    activity_type = CharField()
    difficulties = TextField(null=True)
    actions_taken = TextField(null=True)
    participants = TextField(null=True)

    class Meta:
        table_name = 'daily_logs'

# Function to create tables
def create_tables():
    with db:
        db.create_tables([User, Student, Observation, Attendance, Event, DailyLog])

# It's a good practice to connect and close the database explicitly
# or use a request handler in Flask.
