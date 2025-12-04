from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, SelectField,
    TextAreaField, SelectMultipleField, DateField, DateTimeLocalField
)
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp, Optional
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from app.models import User, Student
from config import Config

def validate_cpf_number(cpf_raw):
    """
    Valida um número de CPF.
    Remove caracteres não numéricos e verifica os dígitos verificadores.
    """
    cpf = ''.join(filter(str.isdigit, cpf_raw))

    if not cpf or len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    # Valida o primeiro dígito verificador
    sum_digits = 0
    for i in range(9):
        sum_digits += int(cpf[i]) * (10 - i)
    first_verifier_digit = 11 - (sum_digits % 11)
    if first_verifier_digit > 9:
        first_verifier_digit = 0
    if first_verifier_digit != int(cpf[9]):
        return False

    # Valida o segundo dígito verificador
    sum_digits = 0
    for i in range(10):
        sum_digits += int(cpf[i]) * (11 - i)
    second_verifier_digit = 11 - (sum_digits % 11)
    if second_verifier_digit > 9:
        second_verifier_digit = 0
    if second_verifier_digit != int(cpf[10]):
        return False

    return True

class LoginForm(FlaskForm):
    login_id = StringField('Email ou CPF', validators=[
        DataRequired(message='Por favor, insira seu email ou CPF.')
    ], render_kw={"placeholder": "Ex: joao.silva@ifpb.edu.br ou 123.456.789-00"})
    
    password = PasswordField('Senha', validators=[
        DataRequired(message='A senha é obrigatória.')
    ], render_kw={"placeholder": "Sua senha"})
    
    remember = BooleanField('Lembrar de mim')
    submit = SubmitField('Entrar')


class StudentForm(FlaskForm):
    name = StringField('Nome do Aluno(a)', validators=[
        DataRequired(message='Nome é obrigatório'), 
        Length(min=2, max=100)
    ], render_kw={"placeholder": "Insira o nome completo do aluno"})
    
    matricula = StringField('Matrícula', validators=[
        DataRequired(), 
        Regexp(r'^(2019|20[2-3][0-9])\d{8}$', message='Matrícula inválida. Deve ter 12 dígitos e iniciar com o ano.')
    ], render_kw={"placeholder": "Ex: 202412345678"})
    
    dob = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()], render_kw={"placeholder": "Use o seletor ou digite AAAA-MM-DD"})
    
    cid = StringField('CID', validators=[Optional(), Length(max=50)], render_kw={"placeholder": "Ex: F84.0 (Opcional)"})
    
    email = StringField('E-mail Acadêmico', validators=[
        Optional(),
        Email(message='Email inválido'), 
        Length(max=120)
    ], render_kw={"placeholder": "aluno@academico.ifpb.edu.br (Opcional)"})
    
    phone = StringField('Telefone', validators=[Optional(), Length(max=20)], render_kw={"placeholder": "(83) 9xxxx-xxxx (Opcional)"})
    grade = StringField('Turma', validators=[Optional(), Length(max=20)], render_kw={"placeholder": "Ex: 3º Ano B (Opcional)"})
    course = StringField('Curso', validators=[Optional(), Length(max=50)], render_kw={"placeholder": "Ex: Técnico em Informática (Opcional)"})
    
    responsible_name = StringField('Nome do Responsável', validators=[Optional(), Length(max=100)], render_kw={"placeholder": "Nome do pai, mãe ou responsável"})
    responsible_phone = StringField('Contato do Responsável', validators=[Optional(), Length(max=20)], render_kw={"placeholder": "(83) 9xxxx-xxxx"})
    responsible_email = StringField('E-mail do Responsável', validators=[Optional(), Email()], render_kw={"placeholder": "email.responsavel@exemplo.com"})
    responsible_cpf = StringField('CPF do Responsável', validators=[
        Optional(), 
        Length(min=11, max=14, message='CPF deve ter entre 11 e 14 caracteres (incluindo pontos e traço).')
    ], render_kw={"placeholder": "Ex: 123.456.789-00"})
    
    picture = FileField('Foto do Aluno', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    submit = SubmitField('Salvar Aluno')

    def validate_responsible_cpf(self, field):
        if field.data and not validate_cpf_number(field.data):
            raise ValidationError('CPF do Responsável inválido.')


class UserForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=2, max=100)], render_kw={"placeholder": "Nome completo do usuário"})
    
    email = StringField('Email', validators=[
        DataRequired(),
        Regexp(r'^[a-zA-Z0-9\._-]+@academico\.ifpb\.edu\.br$', message='Apenas emails @academico.ifpb.edu.br são permitidos.')
    ], render_kw={"placeholder": "usuario@academico.ifpb.edu.br"})
    
    cpf = StringField('CPF', validators=[
        DataRequired(), 
        Length(min=11, max=14, message='CPF deve ter entre 11 e 14 caracteres (incluindo pontos e traço).')
    ], render_kw={"placeholder": "Ex: 123.456.789-00"})
    
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)], render_kw={"placeholder": "Mínimo de 6 caracteres"})
    confirm_password = PasswordField('Confirme a Senha', validators=[DataRequired(), EqualTo('password', message='Senhas devem ser iguais')], render_kw={"placeholder": "Repita a senha"})
    
    role = SelectField('Função', choices=[('pedagogue', 'Pedagogo(a)'), ('admin', 'Administrador(a)')], validators=[DataRequired()])
    submit = SubmitField('Salvar Usuário')

    def validate_email(self, email):
        user = User.select().where(User.email == email.data).first()
        if user:
            raise ValidationError('Este email já está cadastrado.')

    def validate_cpf(self, field):
        if not validate_cpf_number(field.data):
            raise ValidationError('CPF inválido.')
        user = User.select().where(User.username == field.data).first() # Still checking 'username' column in DB
        if user:
            raise ValidationError('Este CPF já está cadastrado.')


class UpdateUserForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=2, max=100)], render_kw={"placeholder": "Nome completo do usuário"})
    cpf = StringField('CPF', validators=[
        DataRequired(), 
        Length(min=11, max=14, message='CPF deve ter entre 11 e 14 caracteres (incluindo pontos e traço).')
    ], render_kw={"placeholder": "Ex: 123.456.789-00"})
    email = StringField('Email', validators=[
        DataRequired(), 
        Regexp(r'^[a-zA-Z0-9\._-]+@academico\.ifpb\.edu\.br$', message='Email acadêmico inválido')
    ], render_kw={"placeholder": "usuario@academico.ifpb.edu.br"})
    role = SelectField('Função', choices=[('pedagogue', 'Pedagogo(a)'), ('admin', 'Administrador(a)')], validators=[DataRequired()])
    submit = SubmitField('Atualizar Usuário')
    
    def __init__(self, original_cpf, original_email, *args, **kwargs):
        super(UpdateUserForm, self).__init__(*args, **kwargs)
        self.original_cpf = original_cpf
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.select().where(User.email == email.data).first()
            if user:
                raise ValidationError('Este email já está em uso por outro usuário.')

    def validate_cpf(self, field):
        if not validate_cpf_number(field.data):
            raise ValidationError('CPF inválido.')
        if field.data != self.original_cpf:
            user = User.select().where(User.username == field.data).first() # Still checking 'username' column in DB
            if user:
                raise ValidationError('Este CPF já está em uso por outro usuário.')


class ProfileForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=2, max=100)], render_kw={"placeholder": "Seu nome completo"})
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={"placeholder": "Seu endereço de email"})
    picture = FileField('Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Imagens apenas!')])
    submit = SubmitField('Atualizar Perfil')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.select().where(User.email == email.data).first()
            if user:
                raise ValidationError('Este email já está em uso.')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Senha Atual', validators=[DataRequired()], render_kw={"placeholder": "Sua senha atual"})
    new_password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)], render_kw={"placeholder": "Mínimo de 6 caracteres"})
    confirm_new_password = PasswordField('Confirme a Nova Senha', validators=[DataRequired(), EqualTo('new_password')], render_kw={"placeholder": "Repita a nova senha"})
    submit = SubmitField('Alterar Senha')


class AdminSetPasswordForm(FlaskForm):
    new_password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)], render_kw={"placeholder": "Mínimo de 6 caracteres"})
    confirm_new_password = PasswordField('Confirme a Nova Senha', validators=[DataRequired(), EqualTo('new_password')], render_kw={"placeholder": "Repita a nova senha"})
    submit = SubmitField('Definir Senha')



class ObservationForm(FlaskForm):
    observation_text = TextAreaField('Observação', validators=[DataRequired(), Length(min=10)], render_kw={"placeholder": "Descreva a observação com detalhes..."})
    justification = TextAreaField('Justificativa (para edições)', validators=[Optional(), Length(max=500)], render_kw={"placeholder": "Se estiver editando, justifique a alteração..."})
    submit = SubmitField('Salvar Observação')


class DailyReportForm(FlaskForm):
    student_id = SelectField('Aluno', coerce=int, validators=[DataRequired()])
    date = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()], render_kw={"placeholder": "Selecione a data"})
    professional_role = SelectField('Papel do Profissional', choices=[('Psicopedagoga', 'Psicopedagoga'), ('Audiodescritor', 'Audiodescritor'), ('Cuidador(a)', 'Cuidador(a)'), ('Coordenador(a)', 'Coordenador(a)')], validators=[DataRequired()])
    shift = SelectMultipleField('Turno', choices=[('Manhã', 'Manhã'), ('Tarde', 'Tarde'), ('Integral', 'Integral'), ('Noite', 'Noite')], validators=[DataRequired()])
    activity_type = SelectField('Tipo de Atendimento', choices=[], validators=[DataRequired()])
    difficulties = TextAreaField('Dificuldades encontradas no dia', render_kw={"rows": 4, "placeholder": "Descreva as dificuldades observadas..."}, validators=[Optional(), Length(max=1000)])
    actions_taken = TextAreaField('Medidas tomadas', render_kw={"rows": 4, "placeholder": "Quais ações foram realizadas para auxiliar?"}, validators=[Optional(), Length(max=1000)])
    participants = TextAreaField('Participações', render_kw={"rows": 4, "placeholder": "Houve a participação de outros profissionais? Quais?"}, validators=[Optional(), Length(max=1000)])
    observations = TextAreaField('Observações', render_kw={"rows": 4, "placeholder": "Outras observações relevantes..."})
    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(DailyReportForm, self).__init__(*args, **kwargs)
        self.student_id.choices = [(s.id, s.name) for s in Student.select(Student.id, Student.name).order_by(Student.name)]
        self.activity_type.choices = Config.DAILY_LOG_ACTIVITY_CHOICES


class GeneralReportForm(FlaskForm):
    student_id = SelectField('Aluno', coerce=int, validators=[DataRequired()])
    date = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()], render_kw={"placeholder": "Selecione a data"})
    location = StringField('Local', validators=[Optional(), Length(max=100)], render_kw={"placeholder": "Ex: Sala de aula, pátio, sala de recursos"})
    initial_conditions = TextAreaField('Condições observadas do aluno no início da intervenção', render_kw={"rows": 4, "placeholder": "Como o aluno se apresentava no início?"}, validators=[Optional(), Length(max=2000)])
    difficulties_found = TextAreaField('Dificuldades encontradas', render_kw={"rows": 4, "placeholder": "Quais as principais dificuldades observadas?"}, validators=[Optional(), Length(max=2000)])
    observed_abilities = TextAreaField('Habilidades observadas', render_kw={"rows": 4, "placeholder": "Quais habilidades e potencialidades se destacaram?"}, validators=[Optional(), Length(max=2000)])
    activities_performed = TextAreaField('Atividades realizadas', render_kw={"rows": 4, "placeholder": "Liste as atividades desenvolvidas com o aluno."}, validators=[Optional(), Length(max=2000)])
    evolutions_observed = TextAreaField('Evoluções observadas após o acompanhamento', render_kw={"rows": 4, "placeholder": "Quais progressos foram notados?"}, validators=[Optional(), Length(max=2000)])
    adapted_assessments = BooleanField('Os professores fazem avaliações adaptadas, ler com o estudante?')
    professional_impediments = TextAreaField('Dificuldades encontradas pelo profissional', render_kw={"rows": 4, "placeholder": "Houve alguma dificuldade para o profissional realizar o trabalho?"}, validators=[Optional(), Length(max=2000)])
    solutions = TextAreaField('Medidas tomadas para reduzir dificuldades', render_kw={"rows": 4, "placeholder": "Quais encaminhamentos ou soluções foram propostos?"}, validators=[Optional(), Length(max=2000)])
    additional_information = TextAreaField('Informações adicionais referente ao semestre em curso', render_kw={"rows": 4, "placeholder": "Alguma outra informação relevante?"}, validators=[Optional(), Length(max=2000)])
    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(GeneralReportForm, self).__init__(*args, **kwargs)
        self.student_id.choices = [(s.id, s.name) for s in Student.select(Student.id, Student.name).order_by(Student.name)]


class EventForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(min=5, max=100)], render_kw={"placeholder": "Ex: Reunião Pedagógica com a família"})
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)], render_kw={"placeholder": "Detalhes sobre o evento (opcional)"})
    start_time = DateTimeLocalField('Início', format='%Y-%m-%dT%H:%M', validators=[DataRequired()], render_kw={"placeholder": "YYYY-MM-DDTHH:MM"})
    end_time = DateTimeLocalField('Fim', format='%Y-%m-%dT%H:%M', validators=[DataRequired()], render_kw={"placeholder": "YYYY-MM-DDTHH:MM"})
    student_id = SelectField('Aluno (opcional)', coerce=int, choices=[(0, 'Nenhum')], default=0)
    submit = SubmitField('Salvar Evento')

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.student_id.choices = [(0, 'Nenhum')] + [(s.id, s.name) for s in Student.select(Student.id, Student.name).order_by(Student.name)]


class AttendanceForm(FlaskForm):
    student_id = SelectField('Aluno', coerce=int, validators=[DataRequired()])
    date = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()], render_kw={"placeholder": "Selecione a data"})
    status = SelectField('Status', choices=[('present', 'Presente'), ('absent', 'Ausente'), ('justified_absent', 'Justificado')], validators=[DataRequired()])
    submit = SubmitField('Salvar Frequência')

    def __init__(self, *args, **kwargs):
        super(AttendanceForm, self).__init__(*args, **kwargs)
        self.student_id.choices = [(s.id, s.name) for s in Student.select(Student.id, Student.name).order_by(Student.name)]
