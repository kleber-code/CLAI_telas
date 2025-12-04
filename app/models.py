from peewee import Model, CharField, DateField, ForeignKeyField, TextField, DateTimeField, SqliteDatabase, BooleanField
from flask_login import UserMixin
import datetime


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
        table_name = 'users'

class Student(BaseModel):
    name = CharField()
    matricula = CharField(unique=True)
    dob = DateField()  # Date of Birth
    cid = CharField(null=True)  # International Classification of Diseases
    email = CharField(null=True)
    phone = CharField(null=True)
    grade = CharField(null=True)  # Turma
    course = CharField(null=True)
    responsible_name = CharField(null=True)
    responsible_phone = CharField(null=True)
    responsible_email = CharField(null=True)
    responsible_cpf = CharField(null=True) # Responsible CPF field added
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

class DailyReport(BaseModel):
    student = ForeignKeyField(Student, backref='daily_reports')
    pedagogue = ForeignKeyField(User, backref='daily_reports')
    date = DateField(default=datetime.date.today)
    shift = CharField()
    activity_type = CharField()
    difficulties = TextField(null=True)
    actions_taken = TextField(null=True)
    participants = TextField(null=True)
    observations = TextField(null=True)
    professional_role = CharField(null=True)

    class Meta:
        table_name = 'daily_reports'

class GeneralReport(BaseModel):
    student = ForeignKeyField(Student, backref='general_reports')
    pedagogue = ForeignKeyField(User, backref='general_reports')
    date = DateField(default=datetime.date.today)
    location = CharField(null=True)
    initial_conditions = TextField(null=True)
    difficulties_found = TextField(null=True)
    observed_abilities = TextField(null=True)
    activities_performed = TextField(null=True)
    evolutions_observed = TextField(null=True)
    adapted_assessments = BooleanField(null=True)
    professional_impediments = TextField(null=True)
    solutions = TextField(null=True)
    additional_information = TextField(null=True)

    class Meta:
        table_name = 'general_reports'

class Notification(BaseModel):
    recipient = ForeignKeyField(User, backref='notifications')
    message = TextField()
    link = CharField(null=True) # Optional URL for the notification
    is_read = BooleanField(default=False)
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'notifications'


def create_tables():
    with db:
        db.create_tables([User, Student, Observation, Attendance, Event, DailyReport, GeneralReport, Notification])

