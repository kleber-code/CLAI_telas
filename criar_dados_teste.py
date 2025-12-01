import os
import random
import datetime
import unicodedata
from faker import Faker
from peewee import IntegrityError
from app import bcrypt

# Ajuste os imports conforme seu projeto
from app.models import db, User, Student, Observation, Attendance, Event, DailyLog

fake = Faker('pt_BR')

# --- Helper Functions ---

def sanitize_string(text):
    """Remove acentos e espaços para criar logins/emails."""
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    return only_ascii.lower().replace(' ', '.')

def generate_matricula():
    """Gera matrícula IFPB válida (Ano + 8 digitos)."""
    year = random.choice([2020, 2021, 2022, 2023, 2024, 2025])
    suffix = f"{random.randint(10000000, 99999999)}"
    return f"{year}{suffix}"

def generate_ifpb_email(name, is_student=True):
    """Gera emails institucionais."""
    clean_name = sanitize_string(name)
    parts = clean_name.split('.')
    if len(parts) > 1:
        email_user = f"{parts[0]}.{parts[-1]}"
    else:
        email_user = parts[0]
    
    if random.random() > 0.8:
        email_user += str(random.randint(1, 99))

    domain = "academico.ifpb.edu.br" if is_student else "academico.ifpb.edu.br"
    return f"{email_user}@{domain}"

# --- Data Generators ---

def create_users_and_pedagogues(num=3):
    print("1. Criando Usuários e Pedagogos...")
    pedagogues = []
    
    # Admin
    try:
        User.create(
            username='admin',
            email='admin@ifpb.edu.br', 
            password=bcrypt.generate_password_hash('admin').decode('utf-8'),
            name='Administrador Geral',
            role='admin',
            profile_picture='default_profile.png'
        )
    except IntegrityError: pass

    # Pedagogos
    for _ in range(num):
        name = fake.name()
        try:
            p = User.create(
                username=sanitize_string(name).split('.')[0] + str(random.randint(1,99)),
                email=generate_ifpb_email(name, is_student=False),
                password=bcrypt.generate_password_hash('senha').decode('utf-8'),
                name=name,
                role='pedagogue',
                profile_picture='default_profile.png'
            )
            pedagogues.append(p)
        except IntegrityError: continue
    
    # Se falhar na criação (já existem), busca no banco
    if not pedagogues:
        pedagogues = list(User.select().where(User.role == 'pedagogue'))
        
    print(f"   > {len(pedagogues)} pedagogos disponíveis.")
    return pedagogues

def create_students(pedagogues, num=20):
    print(f"2. Criando {num} Alunos...")
    students = []
    cursos = ['Técnico em Informática', 'Técnico em Meio Ambiente']
    
    for _ in range(num):
        name = fake.name()
        try:
            s = Student.create(
                name=name,
                matricula=generate_matricula(),
                dob=fake.date_of_birth(minimum_age=14, maximum_age=19),
                cid=random.choice(['F84.0', 'F90.0', None, None]),
                email=generate_ifpb_email(name, is_student=True),
                phone=f"(83) 9{random.randint(8000, 9999)}-{random.randint(1000, 9999)}",
                grade=f"{random.randint(1,3)}º Ano",
                course=random.choice(cursos),
                responsible_name=fake.name(),
                responsible_phone=f"(83) 9{random.randint(8000, 9999)}-{random.randint(1000, 9999)}",
                responsible_email=fake.email(),
                pedagogue=random.choice(pedagogues),
                student_picture='default_student.png'
            )
            students.append(s)
        except IntegrityError: continue
        
    print(f"   > {len(students)} alunos criados.")
    return students

def create_attendance(students):
    print("3. Gerando Frequência (Attendance) - Últimos 30 dias...")
    count = 0
    today = datetime.date.today()
    
    for student in students:
        # Gera frequência para os últimos 30 dias
        for i in range(30):
            date = today - datetime.timedelta(days=i)
            # Pula finais de semana (5=Sábado, 6=Domingo)
            if date.weekday() >= 5:
                continue
                
            # 85% de chance de presença
            status = 'present' if random.random() < 0.85 else random.choice(['absent', 'justified_absent'])
            
            try:
                Attendance.create(student=student, date=date, status=status)
                count += 1
            except IntegrityError: pass
            
    print(f"   > {count} registros de frequência criados.")

def create_daily_logs(students):
    print("4. Gerando Diários de Bordo (Daily Logs)...")
    count = 0
    activities = ['atendimento_individual', 'adaptacao_material', 'reuniao_familia', 'observacao_sala']
    shifts = ['Manhã', 'Tarde']
    
    for student in students:
        # Cria entre 1 e 5 logs por aluno
        for _ in range(random.randint(1, 5)):
            try:
                DailyLog.create(
                    student=student,
                    pedagogue=student.pedagogue,
                    date=fake.date_between(start_date='-2M', end_date='today'),
                    shift=random.choice(shifts),
                    activity_type=random.choice(activities),
                    difficulties=fake.sentence(nb_words=10),
                    actions_taken=fake.sentence(nb_words=12),
                    participants="Psicóloga Escolar" if random.random() > 0.8 else None
                )
                count += 1
            except IntegrityError: pass
    print(f"   > {count} diários de bordo criados.")

def create_events(pedagogues, students):
    print("5. Gerando Eventos (Calendário)...")
    count = 0
    titles = [
        "Reunião de Pais", "Conselho de Classe", "Atendimento Individual", 
        "Planejamento Pedagógico", "Entrega de Laudo"
    ]
    
    for _ in range(15): # 15 eventos no total
        start = fake.date_time_between(start_date='-1M', end_date='+1M')
        # Evento dura 1 hora
        end = start + datetime.timedelta(hours=1)
        
        # 50% de chance de ser vinculado a um aluno específico
        student = random.choice(students) if random.random() > 0.5 else None
        
        try:
            Event.create(
                title=random.choice(titles),
                description=fake.sentence(),
                start_time=start,
                end_time=end,
                student=student,
                pedagogue=random.choice(pedagogues)
            )
            count += 1
        except IntegrityError: pass
    print(f"   > {count} eventos criados.")

def generate_all():
    if not os.path.exists('clai.db'):
        print("ERRO: 'clai.db' não encontrado. Rode o app primeiro.")
        return

    db.connect()
    try:
        # Limpa dados antigos (opcional, cuidado em produção!)
        # Descomente se quiser limpar tudo antes de criar
        DailyLog.delete().execute()
        Event.delete().execute()
        Attendance.delete().execute()
        Observation.delete().execute()
        Student.delete().execute()
        User.delete().where(User.role != 'admin').execute()

        peds = create_users_and_pedagogues()
        studs = create_students(peds)
        
        if studs:
            create_attendance(studs)
            create_daily_logs(studs)
            create_events(peds, studs)
            
        print("\n=== CONCLUÍDO ===")
    finally:
        db.close()

if __name__ == "__main__":
    generate_all()