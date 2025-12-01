from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import bcrypt  # Import bcrypt from app package
from app.models import User, Student, Observation, Event, DailyLog, Attendance
import peewee
from app.forms import (
    LoginForm, StudentForm, UserForm, UpdateUserForm, ObservationForm,
    ReportForm, EventForm, DailyLogForm, ProfileForm, AttendanceForm
)
from functools import wraps
import datetime
import os
from PIL import Image
from config import Config # Import Config to access activity choices


bp = Blueprint('main', __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))  # Redirect to dashboard or login
        return f(*args, **kwargs)
    return decorated_function


def pedagogue_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (current_user.role != 'pedagogue' and current_user.role != 'admin'):
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def save_picture(picture_file, upload_folder, output_size=(125, 125)):
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(picture_file.filename)
    picture_fn = random_hex + f_ext
    # Define absolute path to save the picture
    picture_path = os.path.join(bp.root_path, 'static', 'img', upload_folder, picture_fn)

    i = Image.open(picture_file)
    i.thumbnail(output_size)  # Resize image
    i.save(picture_path)  # Save image

    return picture_fn


@bp.route('/')
@bp.route('/home')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


# No routes.py -> def login():
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # LÓGICA CORRIGIDA:
        # Tenta achar um usuário onde o email OU o username (matricula) seja igual ao input
        identifier = form.login_id.data
        user = User.get_or_none((User.email == identifier) | (User.username == identifier))
        
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Login falhou. Verifique suas credenciais.', 'danger')
            
    return render_template('login.html', title='Login', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@bp.route('/dashboard')
@login_required
def dashboard():
    today = datetime.date.today()
    if current_user.role == 'admin':
        students = Student.select()
        upcoming_events = Event.select().where(Event.start_time >= datetime.datetime.now())
        recent_observations = Observation.select().where(Observation.date >= today - datetime.timedelta(days=7))
    else:
        students = Student.select().where(Student.pedagogue == current_user)
        upcoming_events = Event.select().where(
            (Event.pedagogue == current_user) and 
            (Event.start_time >= datetime.datetime.now())
        )
        recent_observations = Observation.select().where(
            (Observation.pedagogue == current_user) and 
            (Observation.date >= today - datetime.timedelta(days=7))
        )
    
    student_count = students.count()
    upcoming_events_count = upcoming_events.count()
    recent_observations_count = recent_observations.count()

    # Data for chart: students per course
    students_per_course = (
        Student.select(Student.course, peewee.fn.COUNT(Student.id).alias('count'))
        .group_by(Student.course)
        .order_by(Student.course)
    )
    chart_labels = [s.course for s in students_per_course]
    chart_data = [s.count for s in students_per_course]
    
    return render_template(
        'dashboard.html', 
        title='Dashboard', 
        student_count=student_count,
        upcoming_events_count=upcoming_events_count,
        recent_observations_count=recent_observations_count,
        students=students,  # Pass students for the list view as well
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        try:
            # Handle picture upload
            if form.picture.data:
                # Delete old picture if not default
                if current_user.profile_picture != 'default_profile.png':
                    old_picture_path = os.path.join(
                        bp.root_path, 'static', 'img', 'profile_pics',
                        current_user.profile_picture
                    )
                    if os.path.exists(old_picture_path):
                        os.remove(old_picture_path)
                
                picture_file = save_picture(form.picture.data, 'profile_pics')
                current_user.profile_picture = picture_file

            current_user.name = form.name.data
            current_user.email = form.email.data
            current_user.save()
            flash('Seu perfil foi atualizado com sucesso!', 'success')
            return redirect(url_for('main.profile'))
        except Exception as e:
            flash(f'Erro ao atualizar perfil: {e}', 'danger')
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
        # Construct image_file path for template
        image_file = url_for('static', filename='img/profile_pics/' + current_user.profile_picture)
        return render_template(
            'users/profile.html', title='Meu Perfil', form=form, image_file=image_file
        )


@bp.route('/profile/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if bcrypt.check_password_hash(current_user.password, form.old_password.data):
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            current_user.password = hashed_password
            current_user.save()
            flash('Sua senha foi alterada com sucesso!', 'success')
            return redirect(url_for('main.profile'))
        else:
            flash('Senha atual incorreta.', 'danger')
    return render_template('users/change_password.html', title='Alterar Senha', form=form)
    
@bp.route('/students')
@login_required
def list_students():
    page = request.args.get('page', 1, type=int)
    per_page = Config.PAGINATION_PER_PAGE
    search_query = request.args.get('search', '')

    if current_user.role == 'admin':
        students_query = Student.select()
    else:
        students_query = Student.select().where(Student.pedagogue == current_user)
    
    if search_query:
        students_query = students_query.where(
            (Student.name.contains(search_query)) |
            (Student.matricula.contains(search_query))
        )
    
    total_students = students_query.count()
    total_pages = (total_students + per_page - 1) // per_page
    
    students = students_query.order_by(Student.name).paginate(page, per_page)

    paginator_args = {}
    if search_query:
        paginator_args['search'] = search_query

    paginator = {
        'page': page,
        'total_pages': total_pages,
        'route': 'main.list_students',
        'args': paginator_args
    }
    
    return render_template(
        'students/list_students.html', 
        title='Lista de Alunos', 
        students=students, 
        paginator=paginator
    )

@bp.route('/students/new', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def add_student():
    form = StudentForm()
    if form.validate_on_submit():
        try:
            student_picture_file = 'default_student.png'  # Default if no picture uploaded
            if form.picture.data:
                # Larger size for student pic
                student_picture_file = save_picture(form.picture.data, 'student_pics', output_size=(200, 200))

            Student.create(
                name=form.name.data,
                matricula=form.matricula.data,
                dob=form.dob.data,
                cid=form.cid.data,
                email=form.email.data,
                phone=form.phone.data,
                grade=form.grade.data,
                course=form.course.data,
                responsible_name=form.responsible_name.data,
                responsible_phone=form.responsible_phone.data,
                responsible_email=form.responsible_email.data,
                pedagogue=current_user,  # Assign the current logged-in pedagogue
                student_picture=student_picture_file  # Save the picture filename
            )
            flash('Aluno adicionado com sucesso!', 'success')
            return redirect(url_for('main.list_students'))
        except Exception as e:
            flash(f'Erro ao adicionar aluno: {e}', 'danger')
    return render_template('students/add_student.html', title='Adicionar Aluno', form=form)

@bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    student = Student.get_or_none(
        Student.id == student_id
    )  # Fetch student regardless of pedagogue
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('main.list_students'))

    form = StudentForm(obj=student)  # Populate form with existing student data
    if form.validate_on_submit():
        try:
            # Handle picture upload
            if form.picture.data:
                # Delete old picture if not default
                if student.student_picture != 'default_student.png':
                    old_picture_path = os.path.join(
                        bp.root_path, 'static', 'img', 'student_pics',
                        student.student_picture
                    )
                    if os.path.exists(old_picture_path):
                        os.remove(old_picture_path)
                
                # Larger size for student pic
                student_picture_file = save_picture(
                    form.picture.data, 'student_pics', output_size=(200, 200)
                )
                student.student_picture = student_picture_file

            student.name = form.name.data
            student.matricula = form.matricula.data
            student.dob = form.dob.data
            student.cid = form.cid.data
            student.email = form.email.data
            student.phone = form.phone.data
            student.grade = form.grade.data
            student.course = form.course.data
            student.responsible_name = form.responsible_name.data
            student.responsible_phone = form.responsible_phone.data
            student.responsible_email = form.responsible_email.data
            student.save()
            flash('Aluno atualizado com sucesso!', 'success')
            return redirect(url_for('main.list_students'))
        except Exception as e:
            flash(f'Erro ao atualizar aluno: {e}', 'danger')
    elif request.method == 'GET':
        # Populate form with current picture data (though FileField doesn't show current file)
        pass  # The obj=student handles initial population
    
    return render_template('students/edit_student.html', title='Editar Aluno', form=form, student=student)

@bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@pedagogue_or_admin_required  # Only pedagogues or admins can delete
def delete_student(student_id):
    student = Student.get_or_none(
        Student.id == student_id
    )  # Fetch student regardless of pedagogue
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado ou você não tem permissão para excluí-lo.', 'danger')
    else:
        try:
            student.delete_instance()
            flash('Aluno excluído com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao excluir aluno: {e}', 'danger')
    return redirect(url_for('main.list_students'))

@bp.route('/students/<int:student_id>')
@login_required
def student_detail(student_id):
    student = Student.get_or_none(
        Student.id == student_id
    )  # Fetch student regardless of pedagogue
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado ou você não tem permissão para visualizá-lo.', 'danger')
        return redirect(url_for('main.list_students'))
    observations = Observation.select().where(
        Observation.student == student
    ).order_by(Observation.date.desc())
    attendance_records = Attendance.select().where(
        Attendance.student == student
    ).order_by(Attendance.date.desc())
    return render_template(
        'students/student_detail.html',
        title=student.name,
        student=student,
        observations=observations,
        attendance_records=attendance_records
    )

@bp.route('/students/<int:student_id>/observations/new', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def add_observation(student_id):
    student = Student.get_or_none(
        Student.id == student_id
    )  # Fetch student regardless of pedagogue
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado ou você não tem permissão para adicionar observações a ele.', 'danger')
        return redirect(url_for('main.list_students'))

    form = ObservationForm()
    if form.validate_on_submit():
        try:
            Observation.create(
                student=student,
                pedagogue=current_user,
                observation_text=form.observation_text.data,
                justification=None  # No justification needed for initial creation
            )
            flash('Observação adicionada com sucesso!', 'success')
            return redirect(url_for('main.student_detail', student_id=student.id))
        except Exception as e:
            flash(f'Erro ao adicionar observação: {e}', 'danger')
    return render_template(
        'students/add_observation.html', title='Adicionar Observação', form=form, student=student
    )

@bp.route('/students/<int:student_id>/observations/<int:observation_id>/edit', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def edit_observation(student_id, observation_id):
    student = Student.get_or_none(
        Student.id == student_id
    )  # Fetch student regardless of pedagogue
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('main.list_students'))

    observation = Observation.get_or_none(
        Observation.id == observation_id,
        Observation.student == student
    )  # Fetch observation related to student
    if not observation or (observation.pedagogue != current_user and current_user.role != 'admin'):
        flash('Observação não encontrada ou você não tem permissão para editá-la.', 'danger')
        return redirect(url_for('main.student_detail', student_id=student.id))

    form = ObservationForm(obj=observation)
    if form.validate_on_submit():
        if not form.justification.data:
            flash('Uma justificativa é necessária para editar uma observação.', 'danger')
            return render_template(
                'students/edit_observation.html',
                title='Editar Observação',
                form=form,
                student=student,
                observation=observation
            )
        try:
            observation.observation_text = form.observation_text.data
            observation.justification = form.justification.data
            observation.save()
            flash('Observação atualizada com sucesso!', 'success')
            return redirect(url_for('main.student_detail', student_id=student.id))
        except Exception as e:
            flash(f'Erro ao atualizar observação: {e}', 'danger')
    return render_template(
        'students/edit_observation.html',
        title='Editar Observação',
        form=form,
        student=student,
        observation=observation
    )


# ATTENDANCE ROUTES
@bp.route('/attendance')
@login_required
def list_attendance():
    page = request.args.get('page', 1, type=int)
    per_page = Config.PAGINATION_PER_PAGE

    if current_user.role == 'admin':
        attendance_query = Attendance.select().order_by(Attendance.date.desc())
    else:
        # Filter by students assigned to the current pedagogue
        pedagogue_students = Student.select().where(Student.pedagogue == current_user)
        attendance_query = Attendance.select().where(
            Attendance.student.in_(pedagogue_students)
        ).order_by(Attendance.date.desc())
    
    total_attendance_records = attendance_query.count()
    total_pages = (total_attendance_records + per_page - 1) // per_page

    attendance_records = attendance_query.paginate(page, per_page)

    paginator = {
        'page': page,
        'total_pages': total_pages,
        'route': 'main.list_attendance',
        'args': {}
    }
    
    return render_template(
        'attendance/list_attendance.html',
        title='Registros de Frequência',
        attendance_records=attendance_records,
        paginator=paginator
    )

@bp.route('/attendance/new', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def add_attendance():
    form = AttendanceForm()
    # Limit student choices to those assigned to the current pedagogue or all for admin
    if current_user.role != 'admin':
        form.student_id.choices = [
            (s.id, s.name) for s in Student.select().where(Student.pedagogue == current_user)
        ]
    
    if form.validate_on_submit():
        try:
            student = Student.get_by_id(form.student_id.data)
            # Security check: ensure the pedagogue is assigned to the student or is an admin
            if student.pedagogue != current_user and current_user.role != 'admin':
                flash('Você não tem permissão para registrar frequência para este aluno.', 'danger')
                return redirect(url_for('main.list_attendance'))

            Attendance.create(
                student=student,
                date=form.date.data,
                status=form.status.data
            )
            flash('Registro de frequência adicionado com sucesso!', 'success')
            return redirect(url_for('main.list_attendance'))
        except Exception as e:
            flash(f'Erro ao adicionar registro de frequência: {e}', 'danger')
    return render_template('attendance/add_attendance.html', title='Adicionar Frequência', form=form)

@bp.route('/attendance/<int:attendance_id>/edit', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def edit_attendance(attendance_id):
    attendance = Attendance.get_or_none(Attendance.id == attendance_id)
    if not attendance:
        flash('Registro de frequência não encontrado.', 'danger')
        return redirect(url_for('main.list_attendance'))
    
    # Security check: ensure the current user is an admin or the pedagogue assigned to the student
    if attendance.student.pedagogue != current_user and current_user.role != 'admin':
        flash('Você não tem permissão para editar este registro de frequência.', 'danger')
        return redirect(url_for('main.list_attendance'))

    form = AttendanceForm(obj=attendance)
    # Limit student choices to those assigned to the current pedagogue or all for admin
    if current_user.role != 'admin':
        form.student_id.choices = [
            (s.id, s.name) for s in Student.select().where(Student.pedagogue == current_user)
        ]
    else:
        form.student_id.choices = [(s.id, s.name) for s in Student.select()]
    
    if form.validate_on_submit():
        try:
            # Re-check student permission in case it was changed in the form by an admin
            student = Student.get_by_id(form.student_id.data)
            if student.pedagogue != current_user and current_user.role != 'admin':
                flash(
                    'Você não tem permissão para registrar frequência para este aluno.',
                    'danger'
                )
                return render_template('attendance/edit_attendance.html', title='Editar Frequência', form=form, attendance=attendance)

            attendance.student = student
            attendance.date = form.date.data
            attendance.status = form.status.data
            attendance.save()
            flash('Registro de frequência atualizado com sucesso!', 'success')
            return redirect(url_for('main.list_attendance'))
        except Exception as e:
            flash(f'Erro ao atualizar registro de frequência: {e}', 'danger')
    
    # Pre-populate student_id for GET request if not already set by obj=attendance
    if request.method == 'GET' and not form.student_id.data:
        form.student_id.data = attendance.student.id

    return render_template('attendance/edit_attendance.html', title='Editar Frequência', form=form, attendance=attendance)

@bp.route('/attendance/<int:attendance_id>/delete', methods=['POST'])
@login_required
@pedagogue_or_admin_required
def delete_attendance(attendance_id):
    attendance = Attendance.get_or_none(Attendance.id == attendance_id)
    if not attendance:
        flash('Registro de frequência não encontrado.', 'danger')
        return redirect(url_for('main.list_attendance'))
    
    # Security check: ensure the current user is an admin or the pedagogue assigned to the student
    if attendance.student.pedagogue != current_user and current_user.role != 'admin':
        flash('Você não tem permissão para excluir este registro de frequência.', 'danger')
        return redirect(url_for('main.list_attendance'))
    
    try:
        attendance.delete_instance()
        flash('Registro de frequência excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir registro de frequência: {e}', 'danger')
    
    return redirect(url_for('main.list_attendance'))


@bp.route('/attendance/mark', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def mark_attendance():
    # Base query for students based on user role
    if current_user.role == 'admin':
        students_query = Student.select()
    else:
        students_query = Student.select().where(Student.pedagogue == current_user)

    # Get distinct grades for the filter dropdown
    # The list comprehension is used to handle None values and create a sorted list
    all_grades = sorted(list(set([s.grade for s in students_query if s.grade])))

    # Get filters from request arguments
    selected_grade = request.args.get('grade', '')
    selected_date_str = request.args.get('date', datetime.date.today().isoformat())
    
    # Apply grade filter if a grade is selected
    if selected_grade:
        students_query = students_query.where(Student.grade == selected_grade)

    # Finalize the student list
    students = students_query.order_by(Student.name)
    
    try:
        selected_date = datetime.date.fromisoformat(selected_date_str)
    except ValueError:
        flash('Data inválida fornecida.', 'danger')
        selected_date = datetime.date.today()
        selected_date_str = selected_date.isoformat()

    if request.method == 'POST':
        successful_updates = 0
        failed_updates = 0
        # NOTE: We are iterating over the 'students' query which is already filtered
        for student in students:
            student_status = request.form.get(f'status_{student.id}')
            if student_status:
                try:
                    attendance_record, created = Attendance.get_or_create(
                        student=student,
                        date=selected_date,
                        defaults={'status': student_status}
                    )
                    if not created:
                        attendance_record.status = student_status
                        attendance_record.save()
                    successful_updates += 1
                except Exception as e:
                    print(f"Error updating attendance for {student.name}: {e}")
                    failed_updates += 1
        
        if successful_updates > 0:
            flash(f'Frequência para {successful_updates} alunos atualizada com sucesso!', 'success')
        if failed_updates > 0:
            flash(f'Falha ao atualizar frequência para {failed_updates} alunos.', 'danger')
        
        # Preserve filters on redirect
        return redirect(url_for('main.mark_attendance', date=selected_date_str, grade=selected_grade))

    # For GET request, fetch existing attendance to pre-fill the form
    existing_attendance = {
        att.student.id: att.status 
        for att in Attendance.select().where(Attendance.date == selected_date, Attendance.student.in_(students))
    }

    return render_template(
        'attendance/mark_attendance.html',
        title=f'Marcar Frequência - {selected_date.strftime("%d/%m/%Y")}',
        students=students,
        selected_date=selected_date,
        selected_date_str=selected_date_str,
        existing_attendance=existing_attendance,
        all_grades=all_grades,
        selected_grade=selected_grade
    )


@bp.route('/admin/users')
@login_required
@admin_required
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = Config.PAGINATION_PER_PAGE

    users_query = User.select().order_by(User.name) # Assuming sorting by name
    
    total_users = users_query.count()
    total_pages = (total_users + per_page - 1) // per_page

    users = users_query.paginate(page, per_page)

    paginator = {
        'page': page,
        'total_pages': total_pages,
        'route': 'main.list_users',
        'args': {}
    }
    return render_template('users/list_users.html', title='Gerenciar Usuários', users=users, paginator=paginator)


@bp.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            User.create(
                name=form.name.data,
                username=form.username.data,
                email=form.email.data,
                password=hashed_password,
                role=form.role.data
            )
            flash('Usuário adicionado com sucesso!', 'success')
            return redirect(url_for('main.list_users'))
        except Exception as e:
            flash(f'Erro ao adicionar usuário: {e}', 'danger')
    return render_template('users/add_user.html', title='Adicionar Usuário', form=form)


@bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('main.list_users'))

    form = UpdateUserForm(obj=user)
    if form.validate_on_submit():
        try:
            user.name = form.name.data
            user.username = form.username.data
            user.email = form.email.data
            user.role = form.role.data
            user.save()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('main.list_users'))
        except Exception as e:
            flash(f'Erro ao atualizar usuário: {e}', 'danger')
    return render_template('users/edit_user.html', title='Editar Usuário', form=form, user=user)


@bp.route('/admin/users/<int:user_id>/set_password', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_set_password(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('main.list_users'))

    form = AdminSetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
        user.password = hashed_password
        user.save()
        flash(f'Senha para {user.username} foi alterada com sucesso!', 'success')
        return redirect(url_for('main.edit_user', user_id=user.id))
    return render_template('users/admin_set_password.html', title=f'Definir Senha para {user.username}', form=form, target_user=user)


@bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        flash('Usuário não encontrado.', 'danger')
    else:
        try:
            user.delete_instance()
            flash('Usuário excluído com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao excluir usuário: {e}', 'danger')
    return redirect(url_for('main.list_users'))

@bp.route('/reports/generate', methods=['GET', 'POST'])
@login_required
def generate_report():
    form = ReportForm()
    if form.validate_on_submit():
        student_id = form.student_id.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        
        # Pass data to the report view template
        return redirect(
            url_for(
                'main.view_report',
                student_id=student_id,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
        )
    return render_template('reports/report_form.html', title='Gerar Relatório', form=form)

@bp.route('/reports/view')
@login_required
def view_report():
    student_id = request.args.get('student_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not all([student_id, start_date_str, end_date_str]):
        flash('Parâmetros de relatório inválidos.', 'danger')
        return redirect(url_for('main.generate_report'))
    
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()

    student = Student.get_or_none(
        Student.id == student_id
    )  # Fetch student regardless of pedagogue
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado ou você não tem permissão para gerar relatórios para este aluno.', 'danger')
        return redirect(url_for('main.generate_report'))
    
    observations = Observation.select().where(
        (Observation.student == student) &
        (Observation.date >= start_date) &
        (Observation.date <= end_date)
    ).order_by(Observation.date.desc())

    # Calculate Summary Statistics
    total_observations = observations.count()
    report_duration_days = (end_date - start_date).days + 1  # Include start and end day

    # Calculate observations per week/month
    # Group observations by date to check unique days with observations
    unique_observation_dates = set([obs.date for obs in observations])
    days_with_observations = len(unique_observation_dates)
    
    avg_obs_per_day = total_observations / report_duration_days if report_duration_days > 0 else 0
    
    return render_template(
        'reports/report_view.html',
        title=f'Relatório de {student.name}',
        student=student,
        observations=observations,
        start_date=start_date,
        end_date=end_date,
        total_observations=total_observations,
        report_duration_days=report_duration_days,
        days_with_observations=days_with_observations,
        avg_obs_per_day=f"{avg_obs_per_day:.2f}"
    )

@bp.route('/reports/view_printable')
@login_required
def view_report_printable():
    student_id = request.args.get('student_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not all([student_id, start_date_str, end_date_str]):
        flash('Parâmetros de relatório inválidos para visualização.', 'danger')
        return redirect(url_for('main.generate_report'))
    
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()

    student = Student.get_or_none(
        Student.id == student_id
    )  # Fetch student regardless of pedagogue
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado ou você não tem permissão para gerar relatórios para este aluno.', 'danger')
        return redirect(url_for('main.generate_report'))
    
    observations = Observation.select().where(
        (Observation.student == student) &
        (Observation.date >= start_date) &
        (Observation.date <= end_date)
    ).order_by(Observation.date.desc())

    # Render the report content to HTML
    return render_template(
        'reports/report_pdf.html', # Keep using this template, but it will be rendered as HTML
        title=f'Relatório de {student.name}',
        student=student,
        observations=observations,
        start_date=start_date,
        end_date=end_date,
        now=datetime.datetime.now()
    )


@bp.route('/calendar')
@login_required
def calendar():
    # events are fetched via calendar_api, no need to pass them here
    return render_template('calendar/calendar.html', title='Calendário')


@bp.route('/calendar_api')
@login_required
def calendar_api():
    events_query = Event.select()
    if current_user.role != 'admin':
        events_query = events_query.where(Event.pedagogue == current_user)
    
    events_data = []
    for event in events_query:
        events_data.append({
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'description': event.description,
            'allDay': False  # Assuming events have specific times
        })
    return jsonify(events_data)

@bp.route('/calendar/new', methods=['GET', 'POST'])
@login_required
def add_event():
    form = EventForm()
    # Pre-fill start_time if provided in URL (from FullCalendar dateClick)
    if request.method == 'GET' and 'start_time' in request.args:
        start_time_str = request.args.get('start_time')
        try:
            # Handle both date-only and datetime formats from FullCalendar
            if 'T' in start_time_str:
                form.start_time.data = datetime.datetime.fromisoformat(start_time_str)
            else:
                form.start_time.data = datetime.datetime.fromisoformat(start_time_str + 'T00:00:00')
            
            # If start_time is set, also set end_time to start_time + 1 hour as a sensible default
            if form.start_time.data:
                form.end_time.data = form.start_time.data + datetime.timedelta(hours=1)

        except ValueError:
            flash('Formato de date/hora inválido.', 'danger')


    if form.validate_on_submit():
        try:
            student = None
            if form.student_id.data != 0:
                student = Student.get_or_none(Student.id == form.student_id.data)
                if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
                    flash(
                        'Aluno selecionado inválido ou você não tem permissão para'
                        ' relacionar o evento a este aluno.',
                        'danger'
                    )
                    return render_template('calendar/add_event.html', title='Adicionar Evento', form=form)

            Event.create(
                title=form.title.data,
                description=form.description.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                student=student,
                pedagogue=current_user  # Assign the current user as the creator/owner of the event
            )
            flash('Evento adicionado com sucesso!', 'success')
            return redirect(url_for('main.calendar'))
        except Exception as e:
            flash(f'Erro ao adicionar evento: {e}', 'danger')
    return render_template('calendar/add_event.html', title='Adicionar Evento', form=form)

@bp.route('/calendar/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.get_or_none(Event.id == event_id)
    if not event or (event.pedagogue != current_user and current_user.role != 'admin'):
        flash('Evento não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('main.calendar'))

    form = EventForm(obj=event)
    # If it's an AJAX POST request (from eventDrop/eventResize), handle it differently
    if request.is_json:
        data = request.get_json()
        try:
            event.start_time = datetime.datetime.fromisoformat(
                data['start_time'].replace('Z', '+00:00')
            )  # Handle 'Z' for UTC
            event.end_time = datetime.datetime.fromisoformat(
                data['end_time'].replace('Z', '+00:00')
            )  # Handle 'Z' for UTC
            event.save()
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    if form.validate_on_submit():
        try:
            student = None
            if form.student_id.data != 0:
                student = Student.get_or_none(Student.id == form.student_id.data)
                if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
                    flash(
                        'Aluno selecionado inválido ou você não tem permissão para'
                        ' relacionar o evento a este aluno.',
                        'danger'
                    )
                    return render_template('calendar/edit_event.html', title='Editar Evento', form=form, event=event)
            
            event.title = form.title.data
            event.description = form.description.data
            event.start_time = form.start_time.data
            event.end_time = form.end_time.data
            event.student = student
            event.save()
            flash('Evento atualizado com sucesso!', 'success')
            return redirect(url_for('main.calendar'))
        except Exception as e:
            flash(f'Erro ao atualizar evento: {e}', 'danger')
    return render_template('calendar/edit_event.html', title='Editar Evento', form=form, event=event)

@bp.route('/calendar/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.get_or_none(Event.id == event_id)
    if not event or (event.pedagogue != current_user and current_user.role != 'admin'):
        flash('Evento não encontrado ou você não tem permissão para excluí-lo.', 'danger')
    else:
        try:
            event.delete_instance()
            flash('Evento excluído com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao excluir evento: {e}', 'danger')
    return redirect(url_for('main.calendar'))

@bp.route('/daily-logs')
@login_required
def list_daily_logs():
    page = request.args.get('page', 1, type=int)
    per_page = Config.PAGINATION_PER_PAGE

    # Admin sees all, pedagogues see theirs
    if current_user.role == 'admin':
        logs_query = DailyLog.select().order_by(DailyLog.date.desc())
    else:
        logs_query = DailyLog.select().where(DailyLog.pedagogue == current_user).order_by(DailyLog.date.desc())

    logs = logs_query.paginate(page, per_page)

    # Calculate total pages for pagination display
    total_logs = logs_query.count()
    total_pages = (total_logs + per_page - 1) // per_page

    # Create paginator object for the universal pagination macro
    paginator = {
        'page': page,
        'total_pages': total_pages,
        'route': 'main.list_daily_logs',
        'args': {} # No additional args for now, but keeping it for future use (e.g., search)
    }

    # Create a mapping from activity_type value to label
    activity_choices_map = {choice[0]: choice[1] for choice in Config.DAILY_LOG_ACTIVITY_CHOICES}

    return render_template(
        'daily_logs/list_logs.html',
        title='Diários de Bordo',
        logs=logs,
        paginator=paginator, # Pass the paginator object
        activity_choices_map=activity_choices_map
    )


@bp.route('/daily-logs/new', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def add_daily_log():
    form = DailyLogForm()
    if form.validate_on_submit():
        try:
            student = Student.get_by_id(form.student_id.data)
            # Security check: ensure the pedagogue is assigned to the student or is an admin
            if student.pedagogue != current_user and current_user.role != 'admin':
                flash('Você não tem permissão para criar um diário para este aluno.', 'danger')
                return redirect(url_for('main.list_daily_logs'))

            DailyLog.create(
                student=student,
                pedagogue=current_user,
                date=form.date.data,
                shift=', '.join(form.shift.data),  # Save multiple shifts as a string
                activity_type=form.activity_type.data,
                difficulties=form.difficulties.data,
                actions_taken=form.actions_taken.data,
                participants=form.participants.data
            )
            flash('Diário de bordo adicionado com sucesso!', 'success')
            return redirect(url_for('main.list_daily_logs'))
        except Exception as e:
            flash(f'Erro ao adicionar diário: {e}', 'danger')
    return render_template('daily_logs/add_log.html', title='Adicionar Diário de Bordo', form=form)


@bp.route('/daily-logs/<int:log_id>')
@login_required
def daily_log_detail(log_id):
    log = DailyLog.get_or_none(log_id)
    if not log or (log.pedagogue != current_user and current_user.role != 'admin'):
        flash('Registro de diário não encontrado ou você não tem permissão para visualizá-lo.', 'danger')
        return redirect(url_for('main.list_daily_logs'))
    # Create a mapping from activity_type value to label
    activity_choices_map = {choice[0]: choice[1] for choice in Config.DAILY_LOG_ACTIVITY_CHOICES}

    return render_template(
        'daily_logs/daily_log_detail.html',
        title='Detalhes do Diário de Bordo',
        log=log,
        activity_choices_map=activity_choices_map
    )