from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, SelectField,
    TextAreaField, SelectMultipleField, DateField, DateTimeLocalField
)
# AQUI ESTAVA O ERRO: Adicione 'Optional' na lista abaixo vvv
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp, Optional
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from app.models import User, Student
from config import Config

# --- LOGIN FORM ---
class LoginForm(FlaskForm):
    # Alterado para "login_id" para ser agnóstico (pode ser email ou matrícula)
    # Removemos a validação de Email aqui, pois se for matrícula, falharia.
    login_id = StringField('Email ou Matrícula', validators=[
        DataRequired(message='Por favor, insira seu email ou matrícula.')
    ], render_kw={"placeholder": "Ex: joao.silva@ifpb.edu.br ou 2023..."})
    
    password = PasswordField('Senha', validators=[
        DataRequired(message='A senha é obrigatória.')
    ], render_kw={"placeholder": "Sua senha"})
    
    remember = BooleanField('Lembrar de mim')

    submit = SubmitField('Entrar')


# --- STUDENT FORM ---
class StudentForm(FlaskForm):
    name = StringField('Nome do Aluno(a)', validators=[
        DataRequired(message='Nome é obrigatório'), 
        Length(min=2, max=100, message='Nome deve ter entre 2 e 100 caracteres')
    ], render_kw={"placeholder": "Nome completo"})
    
    # Atualizei o regex para aceitar matrículas futuras (até 2030) para não quebrar o sistema ano que vem
    matricula = StringField('Matrícula', validators=[
        DataRequired(), 
        Regexp(r'^(2019|20[2-3][0-9])\d{8}$', message='Matrícula inválida. Deve ter 12 dígitos.')
    ], render_kw={"placeholder": "Ex: 202312345678"})
    
    dob = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()], render_kw={"placeholder": "DD/MM/AAAA"})
    
    cid = StringField('CID', validators=[Length(max=50)], render_kw={"placeholder": "Classificação Internacional de Doenças"})
    
    email = StringField('E-mail Acadêmico', validators=[
        Email(message='Email inválido'), 
        Length(max=120)
    ], render_kw={"placeholder": "aluno@academico.ifpb.edu.br"})
    
    phone = StringField('Telefone', validators=[Length(max=20)], render_kw={"placeholder": "(83) 9xxxx-xxxx"})
    grade = StringField('Turma', validators=[Length(max=20)], render_kw={"placeholder": "Ex: 3º Ano A"})
    course = StringField('Curso', validators=[Length(max=50)], render_kw={"placeholder": "Ex: Informática"})
    
    responsible_name = StringField('Nome do Responsável', validators=[Length(max=100)])
    responsible_phone = StringField('Contato do Responsável', validators=[Length(max=20)])
    responsible_email = StringField('E-mail do Responsável', validators=[Optional(), Email()])
    
    picture = FileField('Foto do Aluno', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    submit = SubmitField('Salvar Aluno')


# --- USER FORMS ---
class UserForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=2, max=100)])
    
    # Corrigido o erro de sintaxe grave aqui
    email = StringField('Email', validators=[
        DataRequired(),
        Regexp(r'^[a-zA-Z0-9\._-]+@academico\.ifpb\.edu\.br$', message='Apenas emails @academico.ifpb.edu.br são permitidos.')
    ], render_kw={"placeholder": "usuario@academico.ifpb.edu.br"})
    
    username = StringField('Matrícula/Usuário', validators=[DataRequired(), Length(min=2, max=20)])
    
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirme a Senha', validators=[DataRequired(), EqualTo('password', message='Senhas devem ser iguais')])
    
    role = SelectField('Função', choices=[('pedagogue', 'Pedagoga'), ('admin', 'Administrador')], validators=[DataRequired()])
    submit = SubmitField('Salvar Usuário')

    # Validação customizada para garantir unicidade
    def validate_email(self, email):
        user = User.select().where(User.email == email.data).first()
        if user:
            raise ValidationError('Este email já está cadastrado.')

    def validate_username(self, username):
        user = User.select().where(User.username == username.data).first()
        if user:
            raise ValidationError('Esta matrícula/usuário já está cadastrada.')


class UpdateUserForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=2, max=100)])
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[
        DataRequired(), 
        Regexp(r'^[a-zA-Z0-9\._-]+@academico\.ifpb\.edu\.br$', message='Email acadêmico inválido')
    ])
    role = SelectField('Função', choices=[('pedagogue', 'Pedagoga'), ('admin', 'Administrador')], validators=[DataRequired()])
    submit = SubmitField('Atualizar Usuário')
    
    # Na edição, precisamos validar unicidade APENAS se o valor mudou
    def validate_email(self, email):
        # Assumindo que você passa o 'original_user' ou usa current_user no contexto, 
        # mas como é admin editando outro user, a validação padrão do Flask-WTF pode ser chata.
        # Simplificação: verificar se existe ALGUÉM com esse email que NÃO SEJA o usuário atual sendo editado.
        pass # Implementar lógica no route ou aqui se tiver acesso ao ID do user sendo editado.


class ProfileForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Imagens apenas!')])
    submit = SubmitField('Atualizar Perfil')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.select().where(User.email == email.data).first()
            if user:
                raise ValidationError('Este email já está em uso.')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Senha Atual', validators=[DataRequired()])
    new_password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirme a Nova Senha', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Alterar Senha')


class AdminSetPasswordForm(FlaskForm):
    new_password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirme a Nova Senha', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Definir Senha')


# --- OPERATIONAL FORMS ---

class ObservationForm(FlaskForm):
    observation_text = TextAreaField('Observação', validators=[DataRequired(), Length(min=10)])
    justification = TextAreaField('Justificativa (para edições)', validators=[Length(max=500)])
    submit = SubmitField('Salvar Observação')


class ReportForm(FlaskForm):
    student_id = SelectField('Aluno', coerce=int, validators=[DataRequired()])
    start_date = DateField('Data de Início', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('Data de Fim', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Gerar Relatório')

    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        # Otimização: Query apenas id e nome, não o objeto todo, se possível
        self.student_id.choices = [(s.id, s.name) for s in Student.select(Student.id, Student.name)]
        if not self.student_id.choices:
             self.student_id.choices = [(0, 'Nenhum aluno cadastrado')]
             self.student_id.render_kw = {'disabled': 'disabled'}


class EventForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField('Descrição', validators=[Length(max=500)])
    start_time = DateTimeLocalField('Início', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('Fim', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    student_id = SelectField('Aluno (opcional)', coerce=int, choices=[(0, 'Nenhum')], default=0)
    submit = SubmitField('Salvar Evento')

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.student_id.choices = [(0, 'Nenhum')] + [(s.id, s.name) for s in Student.select(Student.id, Student.name)]


class DailyLogForm(FlaskForm):
    student_id = SelectField('Aluno', coerce=int, validators=[DataRequired()])
    date = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    shift = SelectMultipleField('Turno', choices=[('Manhã', 'Manhã'), ('Tarde', 'Tarde'), ('Integral', 'Integral'), ('Noite', 'Noite')], validators=[DataRequired()])
    activity_type = SelectField('Tipo de Atendimento', choices=[], validators=[DataRequired()])
    difficulties = TextAreaField('Dificuldades', render_kw={"rows": 3}, validators=[Length(max=1000)])
    actions_taken = TextAreaField('Medidas', render_kw={"rows": 3}, validators=[Length(max=1000)])
    participants = TextAreaField('Participantes', render_kw={"rows": 3}, validators=[Length(max=500)])
    submit = SubmitField('Salvar Diário')

    def __init__(self, *args, **kwargs):
        super(DailyLogForm, self).__init__(*args, **kwargs)
        self.student_id.choices = [(s.id, s.name) for s in Student.select(Student.id, Student.name)]
        self.activity_type.choices = Config.DAILY_LOG_ACTIVITY_CHOICES


class AttendanceForm(FlaskForm):
    student_id = SelectField('Aluno', coerce=int, validators=[DataRequired()])
    date = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    status = SelectField('Status', choices=[('present', 'Presente'), ('absent', 'Ausente'), ('justified_absent', 'Justificado')], validators=[DataRequired()])
    submit = SubmitField('Salvar Frequência')

    def __init__(self, *args, **kwargs):
        super(AttendanceForm, self).__init__(*args, **kwargs)
        self.student_id.choices = [(s.id, s.name) for s in Student.select(Student.id, Student.name)]