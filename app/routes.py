from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify, send_from_directory
from flask_login import login_user, logout_user, current_user, login_required
from app import bcrypt
from app.models import User, Student, Observation, Event, Attendance, DailyReport, GeneralReport, Notification
import peewee
from app.forms import (
    LoginForm, StudentForm, UserForm, UpdateUserForm, ObservationForm,
    EventForm, ProfileForm, AttendanceForm, DailyReportForm, GeneralReportForm,
    ChangePasswordForm, AdminSetPasswordForm
)
from app.notification_utils import (
    get_unread_notifications, get_all_notifications,
    mark_notification_as_read, mark_all_notifications_as_read
)
from functools import wraps
import datetime
import os
from PIL import Image
from config import Config

bp = Blueprint('main', __name__)

@bp.route('/notifications')
@login_required
def list_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = Config.PAGINATION_PER_PAGE

    notifications_query = get_all_notifications(current_user.id)
    
    total_notifications = notifications_query.count()
    total_pages = (total_notifications + per_page - 1) // per_page
    
    notifications = notifications_query.paginate(page, per_page)

    paginator = {
        'page': page,
        'total_pages': total_pages,
        'route': 'main.list_notifications',
        'args': {}
    }
    
    return render_template(
        'notifications/list_notifications.html',
        title='Notificações',
        notifications=notifications,
        paginator=paginator
    )

@bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    if mark_notification_as_read(notification_id):
        flash('Notificação marcada como lida.', 'success')
    else:
        flash('Erro ao marcar notificação como lida.', 'danger')
    
    # Redirect to referer or default to notifications list
    return redirect(request.referrer or url_for('main.list_notifications'))

@bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    if mark_all_notifications_as_read(current_user.id):
        flash('Todas as notificações foram marcadas como lidas.', 'success')
    else:
        flash('Erro ao marcar todas as notificações como lidas.', 'danger')
    return redirect(request.referrer or url_for('main.list_notifications'))

@bp.route('/notifications/unread_count')
@login_required
def unread_notification_count():
    count = get_unread_notifications(current_user.id).count()
    return jsonify({'count': count})


# PWA routes
@bp.route('/service-worker.js')
def service_worker():
    return send_from_directory(os.path.join(bp.root_path, 'static'), 'service-worker.js')

@bp.route('/offline')
def offline():
    return render_template('offline.html')

@bp.app_template_filter('format_cpf')
def format_cpf_filter(cpf_raw):
    if not cpf_raw:
        return ""
    cpf = ''.join(filter(str.isdigit, cpf_raw))
    if len(cpf) == 11:
        return f"{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"
    return cpf # Return original if not 11 digits

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
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
    picture_path = os.path.join(bp.root_path, 'static', 'img', upload_folder, picture_fn)

    i = Image.open(picture_file)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@bp.route('/')
@bp.route('/home')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
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
        students = Student.select().limit(6)
        upcoming_events = Event.select().where(Event.start_time >= datetime.datetime.now())
        recent_observations = Observation.select().where(Observation.date >= today - datetime.timedelta(days=7))
    else:
        students = Student.select().where(Student.pedagogue == current_user).limit(6)
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
        students=students,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        try:
            if form.picture.data:
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
            student_picture_file = 'default_student.png'
            if form.picture.data:
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
                pedagogue=current_user,
                student_picture=student_picture_file
            )
            flash('Aluno adicionado com sucesso!', 'success')
            return redirect(url_for('main.list_students'))
        except Exception as e:
            flash(f'Erro ao adicionar aluno: {e}', 'danger')
    return render_template('students/add_student.html', title='Adicionar Aluno', form=form)

@bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    student = Student.get_or_none(Student.id == student_id)
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('main.list_students'))

    form = StudentForm(obj=student)
    if form.validate_on_submit():
        try:
            if form.picture.data:
                if student.student_picture != 'default_student.png':
                    old_picture_path = os.path.join(
                        bp.root_path, 'static', 'img', 'student_pics',
                        student.student_picture
                    )
                    if os.path.exists(old_picture_path):
                        os.remove(old_picture_path)
                
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
    
    return render_template('students/edit_student.html', title='Editar Aluno', form=form, student=student)

@bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@pedagogue_or_admin_required
def delete_student(student_id):
    student = Student.get_or_none(Student.id == student_id)
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
    student = Student.get_or_none(Student.id == student_id)
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
    student = Student.get_or_none(Student.id == student_id)
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
                justification=None
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
    student = Student.get_or_none(Student.id == student_id)
    if not student or (student.pedagogue != current_user and current_user.role != 'admin'):
        flash('Aluno não encontrado.', 'danger')
        return redirect(url_for('main.list_students'))

    observation = Observation.get_or_none(Observation.id == observation_id, Observation.student == student)
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

@bp.route('/attendance')
@login_required
def list_attendance():
    page = request.args.get('page', 1, type=int)
    per_page = Config.PAGINATION_PER_PAGE

    if current_user.role == 'admin':
        attendance_query = Attendance.select().order_by(Attendance.date.desc())
    else:
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
    if current_user.role != 'admin':
        form.student_id.choices = [
            (s.id, s.name) for s in Student.select().where(Student.pedagogue == current_user)
        ]
    
    if form.validate_on_submit():
        try:
            student = Student.get_by_id(form.student_id.data)
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
    
    if attendance.student.pedagogue != current_user and current_user.role != 'admin':
        flash('Você não tem permissão para editar este registro de frequência.', 'danger')
        return redirect(url_for('main.list_attendance'))

    form = AttendanceForm(obj=attendance)
    if current_user.role != 'admin':
        form.student_id.choices = [
            (s.id, s.name) for s in Student.select().where(Student.pedagogue == current_user)
        ]
    else:
        form.student_id.choices = [(s.id, s.name) for s in Student.select()]
    
    if form.validate_on_submit():
        try:
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
    if current_user.role == 'admin':
        students_query = Student.select()
    else:
        students_query = Student.select().where(Student.pedagogue == current_user)

    all_grades = sorted(list(set([s.grade for s in students_query if s.grade])))

    selected_grade = request.args.get('grade', '')
    selected_date_str = request.args.get('date', datetime.date.today().isoformat())
    
    if selected_grade:
        students_query = students_query.where(Student.grade == selected_grade)

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
        
        return redirect(url_for('main.mark_attendance', date=selected_date_str, grade=selected_grade))

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

    users_query = User.select().order_by(User.name)
    
    total_users = users_query.count()
    total_pages = (total_users + per_page - 1) // per_page

    users = users_query.paginate(page, per_page)

    paginator = {
        'page': page,
        'total_pages': total_pages,
        'route': 'main.list_users',
        'args': {}
    }
    
    role_map = {
        'admin': 'Administrador',
        'pedagogue': 'Pedagogo'
    }
    
    return render_template('users/list_users.html', title='Gerenciar Usuários', users=users, paginator=paginator, role_map=role_map)


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
                username=form.cpf.data,
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

    form = UpdateUserForm(original_cpf=user.username, original_email=user.email, obj=user)
    if form.validate_on_submit():
        try:
            user.name = form.name.data
            user.username = form.cpf.data
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


@bp.route('/general-reports')
@login_required
def list_general_reports():
    page = request.args.get('page', 1, type=int)
    per_page = Config.PAGINATION_PER_PAGE
    
    selected_student_id = request.args.get('student_id', type=int)
    selected_date_str = request.args.get('date', '')

    if current_user.role == 'admin':
        reports_query = GeneralReport.select().order_by(GeneralReport.date.desc())
        students = Student.select().order_by(Student.name)
    else:
        reports_query = GeneralReport.select().where(GeneralReport.pedagogue == current_user).order_by(GeneralReport.date.desc())
        students = Student.select().where(Student.pedagogue == current_user).order_by(Student.name)

    if selected_student_id:
        reports_query = reports_query.where(GeneralReport.student.id == selected_student_id)
    
    if selected_date_str:
        try:
            selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            reports_query = reports_query.where(GeneralReport.date == selected_date)
        except ValueError:
            flash('Formato de data inválido. Use AAAA-MM-DD.', 'warning')

    total_reports = reports_query.count()
    total_pages = (total_reports + per_page - 1) // per_page
    
    reports = reports_query.paginate(page, per_page)

    paginator_args = {}
    if selected_student_id:
        paginator_args['student_id'] = selected_student_id
    if selected_date_str:
        paginator_args['date'] = selected_date_str

    paginator = {
        'page': page,
        'total_pages': total_pages,
        'route': 'main.list_general_reports',
        'args': paginator_args
    }

    return render_template(
        'general_reports/list_general_reports.html',
        title='Relatórios Gerais',
        reports=reports,
        paginator=paginator,
        students=students,
        selected_student_id=selected_student_id,
        selected_date=selected_date_str
    )

@bp.route('/general-reports/new', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def add_general_report():
    form = GeneralReportForm()
    if form.validate_on_submit():
        try:
            student = Student.get_by_id(form.student_id.data)
            if student.pedagogue != current_user and current_user.role != 'admin':
                flash('Você não tem permissão para criar um relatório para este aluno.', 'danger')
                return redirect(url_for('main.list_general_reports'))

            GeneralReport.create(
                student=student,
                pedagogue=current_user,
                date=form.date.data,
                location=form.location.data,
                initial_conditions=form.initial_conditions.data,
                difficulties_found=form.difficulties_found.data,
                observed_abilities=form.observed_abilities.data,
                activities_performed=form.activities_performed.data,
                evolutions_observed=form.evolutions_observed.data,
                adapted_assessments=form.adapted_assessments.data,
                professional_impediments=form.professional_impediments.data,
                solutions=form.solutions.data,
                additional_information=form.additional_information.data
            )
            flash('Relatório geral adicionado com sucesso!', 'success')
            return redirect(url_for('main.list_general_reports'))
        except Exception as e:
            flash(f'Erro ao adicionar relatório geral: {e}', 'danger')
    return render_template('general_reports/add_general_report.html', title='Novo Relatório Geral', form=form)


@bp.route('/general-reports/<int:report_id>')
@login_required
def view_general_report(report_id):
    report = GeneralReport.get_or_none(GeneralReport.id == report_id)
    if not report or (report.pedagogue != current_user and current_user.role != 'admin'):
        flash('Relatório geral não encontrado ou você não tem permissão para visualizá-lo.', 'danger')
        return redirect(url_for('main.list_general_reports'))

    return render_template(
        'general_reports/view_general_report.html',
        title='Detalhes do Relatório Geral',
        report=report
    )


@bp.route('/general-reports/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def edit_general_report(report_id):
    report = GeneralReport.get_or_none(GeneralReport.id == report_id)
    if not report:
        flash('Relatório geral não encontrado.', 'danger')
        return redirect(url_for('main.list_general_reports'))

    if report.pedagogue != current_user and current_user.role != 'admin':
        flash('Você não tem permissão para editar este relatório.', 'danger')
        return redirect(url_for('main.list_general_reports'))

    form = GeneralReportForm(obj=report)
    if form.validate_on_submit():
        try:
            report.student = Student.get_by_id(form.student_id.data)
            report.date = form.date.data
            report.location = form.location.data
            report.initial_conditions = form.initial_conditions.data
            report.difficulties_found = form.difficulties_found.data
            report.observed_abilities = form.observed_abilities.data
            report.activities_performed = form.activities_performed.data
            report.evolutions_observed = form.evolutions_observed.data
            report.adapted_assessments = form.adapted_assessments.data
            report.professional_impediments = form.professional_impediments.data
            report.solutions = form.solutions.data
            report.additional_information = form.additional_information.data
            report.save()
            flash('Relatório geral atualizado com sucesso!', 'success')
            return redirect(url_for('main.list_general_reports'))
        except Exception as e:
            flash(f'Erro ao atualizar relatório geral: {e}', 'danger')

    elif request.method == 'GET':
        form.student_id.data = report.student.id

    return render_template('general_reports/edit_general_report.html', title='Editar Relatório Geral', form=form, report=report)


@bp.route('/general-reports/<int:report_id>/delete', methods=['POST'])
@login_required
@pedagogue_or_admin_required
def delete_general_report(report_id):
    report = GeneralReport.get_or_none(GeneralReport.id == report_id)
    if not report:
        flash('Relatório geral não encontrado.', 'danger')
        return redirect(url_for('main.list_general_reports'))

    if report.pedagogue != current_user and current_user.role != 'admin':
        flash('Você não tem permissão para excluir este relatório.', 'danger')
        return redirect(url_for('main.list_general_reports'))

    try:
        report.delete_instance()
        flash('Relatório geral excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir relatório: {e}', 'danger')
    
    return redirect(url_for('main.list_general_reports'))


@bp.route('/daily-reports')
@login_required
def list_daily_reports():
    page = request.args.get('page', 1, type=int)
    per_page = Config.PAGINATION_PER_PAGE
    
    selected_student_id = request.args.get('student_id', type=int)
    selected_date_str = request.args.get('date', '')

    if current_user.role == 'admin':
        reports_query = DailyReport.select().order_by(DailyReport.date.desc())
        students = Student.select().order_by(Student.name)
    else:
        reports_query = DailyReport.select().where(DailyReport.pedagogue == current_user).order_by(DailyReport.date.desc())
        students = Student.select().where(Student.pedagogue == current_user).order_by(Student.name)

    if selected_student_id:
        reports_query = reports_query.where(DailyReport.student == selected_student_id)
    
    if selected_date_str:
        try:
            selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            reports_query = reports_query.where(DailyReport.date == selected_date)
        except ValueError:
            flash('Formato de data inválido. Use AAAA-MM-DD.', 'warning')

    total_reports = reports_query.count()
    total_pages = (total_reports + per_page - 1) // per_page
    
    reports = reports_query.paginate(page, per_page)

    paginator_args = {}
    if selected_student_id:
        paginator_args['student_id'] = selected_student_id
    if selected_date_str:
        paginator_args['date'] = selected_date_str

    paginator = {
        'page': page,
        'total_pages': total_pages,
        'route': 'main.list_daily_reports',
        'args': paginator_args
    }
    
    activity_choices_map = {choice[0]: choice[1] for choice in Config.DAILY_LOG_ACTIVITY_CHOICES}

    return render_template(
        'daily_reports/list_daily_reports.html',
        title='Relatórios Diários',
        reports=reports,
        paginator=paginator,
        students=students,
        selected_student_id=selected_student_id,
        selected_date=selected_date_str,
        activity_choices_map=activity_choices_map
    )

@bp.route('/daily-reports/new', methods=['GET', 'POST'])
@login_required
@pedagogue_or_admin_required
def add_daily_report():
    form = DailyReportForm()
    if form.validate_on_submit():
        try:
            student = Student.get_by_id(form.student_id.data)
            if student.pedagogue != current_user and current_user.role != 'admin':
                flash('Você não tem permissão para criar um diário para este aluno.', 'danger')
                return redirect(url_for('main.list_daily_reports'))

            DailyReport.create(
                student=student,
                pedagogue=current_user,
                date=form.date.data,
                professional_role=form.professional_role.data,
                shift=', '.join(form.shift.data),
                activity_type=form.activity_type.data,
                difficulties=form.difficulties.data,
                actions_taken=form.actions_taken.data,
                participants=form.participants.data,
                observations=form.observations.data
            )
            flash('Relatório diário adicionado com sucesso!', 'success')
            return redirect(url_for('main.list_daily_reports'))
        except Exception as e:
            flash(f'Erro ao adicionar relatório diário: {e}', 'danger')
    return render_template('daily_reports/add_daily_report.html', title='Novo Relatório Diário', form=form)

@bp.route('/daily-reports/<int:report_id>')
@login_required
def view_daily_report(report_id):
    report = DailyReport.get_or_none(DailyReport.id == report_id)
    if not report or (report.pedagogue != current_user and current_user.role != 'admin'):
        flash('Relatório diário não encontrado ou você não tem permissão para visualizá-lo.', 'danger')
        return redirect(url_for('main.list_daily_reports'))
    
    activity_choices_map = {choice[0]: choice[1] for choice in Config.DAILY_LOG_ACTIVITY_CHOICES}

    return render_template(
        'daily_reports/view_daily_report.html',
        title='Detalhes do Relatório Diário',
        report=report,
        activity_choices_map=activity_choices_map
    )


@bp.route('/daily-reports/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_daily_report(report_id):
    report = DailyReport.get_or_none(DailyReport.id == report_id)
    if not report:
        flash('Relatório diário não encontrado.', 'danger')
        return redirect(url_for('main.list_daily_reports'))

    if report.pedagogue != current_user and current_user.role != 'admin':
        flash('Você não tem permissão para editar este relatório.', 'danger')
        return redirect(url_for('main.list_daily_reports'))

    form = DailyReportForm(obj=report)
    if form.validate_on_submit():
        try:
            report.student = Student.get_by_id(form.student_id.data)
            report.date = form.date.data
            report.professional_role = form.professional_role.data
            report.shift = ', '.join(form.shift.data)
            report.activity_type = form.activity_type.data
            report.difficulties = form.difficulties.data
            report.actions_taken = form.actions_taken.data
            report.participants = form.participants.data
            report.observations = form.observations.data
            report.save()
            flash('Relatório diário atualizado com sucesso!', 'success')
            return redirect(url_for('main.list_daily_reports'))
        except Exception as e:
            flash(f'Erro ao atualizar relatório: {e}', 'danger')
    
    elif request.method == 'GET':
        form.shift.data = report.shift.split(', ') if report.shift else []
        form.activity_type.data = report.activity_type
        form.student_id.data = report.student.id

    return render_template('daily_reports/edit_daily_report.html', title='Editar Relatório Diário', form=form, report=report)


@bp.route('/daily-reports/<int:report_id>/delete', methods=['POST'])
@login_required
def delete_daily_report(report_id):
    report = DailyReport.get_or_none(DailyReport.id == report_id)
    if not report:
        flash('Relatório diário não encontrado.', 'danger')
        return redirect(url_for('main.list_daily_reports'))

    if report.pedagogue != current_user and current_user.role != 'admin':
        flash('Você não tem permissão para excluir este relatório.', 'danger')
        return redirect(url_for('main.list_daily_reports'))

    try:
        report.delete_instance()
        flash('Relatório diário excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir relatório: {e}', 'danger')
    
    return redirect(url_for('main.list_daily_reports'))


@bp.route('/calendar')
@login_required
def calendar():
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
            'allDay': False
        })
    return jsonify(events_data)

@bp.route('/calendar/new', methods=['GET', 'POST'])
@login_required
def add_event():
    form = EventForm()
    if request.method == 'GET' and 'start_time' in request.args:
        start_time_str = request.args.get('start_time')
        try:
            if 'T' in start_time_str:
                form.start_time.data = datetime.datetime.fromisoformat(start_time_str)
            else:
                form.start_time.data = datetime.datetime.fromisoformat(start_time_str + 'T00:00:00')
            
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
                pedagogue=current_user
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
    if request.is_json:
        data = request.get_json()
        try:
            event.start_time = datetime.datetime.fromisoformat(
                data['start_time'].replace('Z', '+00:00')
            )
            event.end_time = datetime.datetime.fromisoformat(
                data['end_time'].replace('Z', '+00:00')
            )
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
