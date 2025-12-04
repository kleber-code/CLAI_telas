import os
import random
import datetime
import unicodedata
from faker import Faker
from peewee import IntegrityError
from app import bcrypt

from config import Config
from app.models import db, User, Student, Observation, Attendance, Event, DailyReport, GeneralReport

fake = Faker('pt_BR')



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

def generate_cpf():
    """Gera um número de CPF válido."""
    while True:
        # Gerar 9 dígitos aleatórios
        nine_digits = [random.randint(0, 9) for _ in range(9)]

        # Calcular o primeiro dígito verificador
        sum_digits = 0
        for i in range(9):
            sum_digits += nine_digits[i] * (10 - i)
        first_verifier_digit = 11 - (sum_digits % 11)
        if first_verifier_digit > 9:
            first_verifier_digit = 0

        # Adicionar o primeiro dígito verificador
        ten_digits = nine_digits + [first_verifier_digit]

        # Calcular o segundo dígito verificador
        sum_digits = 0
        for i in range(10):
            sum_digits += ten_digits[i] * (11 - i)
        second_verifier_digit = 11 - (sum_digits % 11)
        if second_verifier_digit > 9:
            second_verifier_digit = 0
        
        cpf_list = ten_digits + [second_verifier_digit]
        cpf = "".join(map(str, cpf_list))

        # Basic check to avoid known invalid CPFs like '11111111111'
        if not all(c == cpf[0] for c in cpf):
            return cpf

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


def create_users_and_pedagogues(num=3):
    print("1. Criando Usuários e Pedagogos...")
    pedagogues = []
    
    try:
        with db.atomic():
            User.create(
                username='admin',
                email='admin@ifpb.edu.br', 
                password=bcrypt.generate_password_hash('admin').decode('utf-8'),
                name='Administrador Geral',
                role='admin',
                profile_picture='default_profile.png'
            )
    except IntegrityError:
        print("   - Usuário 'admin' já existe.")

    for _ in range(num):
        name = fake.name_female()
        try:
            with db.atomic():
                p = User.create(
                    username=generate_cpf(),
                    email=generate_ifpb_email(name, is_student=False),
                    password=bcrypt.generate_password_hash('senha').decode('utf-8'),
                    name=name,
                    role='pedagogue',
                    profile_picture='default_profile.png'
                )
                pedagogues.append(p)
        except IntegrityError: 
            continue
    
    if not pedagogues:
        pedagogues = list(User.select().where(User.role == 'pedagogue'))
        
    print(f"   > {len(pedagogues)} pedagogos disponíveis.")
    return pedagogues

def create_students(pedagogues, num=50):
    print(f"2. Criando {num} Alunos...")
    students = []
    cursos = ['Técnico em Informática', 'Técnico em Meio Ambiente']
    cids = ['F84.0', 'F90.0', 'G40.0', 'F81.0', 'F80.1', 'F91.3', 'F41.1', 'T90.5']
    needs = [
        "Necessita de mediação para interação com os colegas.",
        "Requer auxílio para organização de materiais e cadernos.",
        "Utiliza software leitor de tela para acessar conteúdos digitais.",
        "Precisa de tempo adicional para completar avaliações.",
        "Apresenta alta sensibilidade a ruídos em sala de aula.",
        "Tem dificuldade de concentração em atividades longas.",
        "Beneficia-se de instruções visuais e passo a passo.",
        "Requer material com fontes ampliadas e maior contraste."
    ]

    for _ in range(num):
        is_male = random.choice([True, False])
        name = fake.name_male() if is_male else fake.name_female()
        
        grade_num = random.randint(1, 3)
        grade = f"{grade_num}º Ano"
        
        current_year = datetime.date.today().year
        birth_year = current_year - (14 + grade_num) # Idade base de 14 para o 1º ano
        dob = fake.date_of_birth(minimum_age=(14+grade_num-1), maximum_age=(14+grade_num))

        student_last_name = name.split(' ')[-1]
        responsible_is_male = random.choice([True, False])
        responsible_name = (fake.name_male() if responsible_is_male else fake.name_female()).split(' ')
        responsible_name[-1] = student_last_name # Garante o mesmo sobrenome
        responsible_name = " ".join(responsible_name)

        try:
            with db.atomic():
                s = Student.create(
                    name=name,
                    matricula=generate_matricula(),
                    dob=dob,
                    cid=random.choice(cids + [None]*5), # Aumenta a chance de ser nulo
                    email=generate_ifpb_email(name, is_student=True),
                    phone=f"(83) 9{random.randint(8000, 9999)}-{random.randint(1000, 9999)}",
                    grade=grade,
                    course=random.choice(cursos),
                    responsible_name=responsible_name,
                    responsible_phone=f"(83) 9{random.randint(8000, 9999)}-{random.randint(1000, 9999)}",
                    responsible_email=fake.email(),
                    pedagogue=random.choice(pedagogues),
                    student_picture='default_student.png',
                    specific_needs_description=random.choice(needs) if random.random() > 0.6 else None
                )
                students.append(s)
        except IntegrityError: 
            continue
        
    print(f"   > {len(students)} alunos criados.")
    return students

def create_attendance(students):
    print("3. Gerando Frequência (Attendance) - Últimos 60 dias...")
    count = 0
    today = datetime.date.today()
    
    for student in students:
        for i in range(60): # Aumentado para 60 dias
            date = today - datetime.timedelta(days=i)
            if date.weekday() >= 5: # Pula Sábado e Domingo
                continue
                
            status = 'present' if random.random() < 0.90 else random.choice(['absent', 'justified_absent'])
            
            try:
                with db.atomic():
                    Attendance.create(student=student, date=date, status=status)
                    count += 1
            except IntegrityError: 
                pass
            
    print(f"   > {count} registros de frequência criados.")

def create_daily_reports(students):
    print("4. Gerando Relatórios Diários (Daily Reports)...")
    count = 0
    activities = [choice[0] for choice in Config.DAILY_LOG_ACTIVITY_CHOICES]
    shifts = ['Manhã', 'Tarde']
    roles = ['Pedagogo(a)', 'Intérprete de LIBRAS', 'Cuidador(a)', 'Psicólogo(a) Escolar']
    
    difficulties_texts = [
        "Dificuldade em manter o foco durante a explicação do conteúdo.",
        "Demonstrou ansiedade ao ser questionado sobre a atividade.",
        "Isolou-se do restante da turma no intervalo.",
        "Recusou-se a participar da atividade em grupo proposta pelo professor.",
        "Apresentou dificuldade na leitura e interpretação do enunciado da questão."
    ]
    actions_texts = [
        "Realizada escuta ativa e acolhimento das angústias do aluno.",
        "Sugerido ao professor o uso de exemplos práticos para facilitar a compreensão.",
        "Mediamos a interação com um colega para iniciar um diálogo.",
        "Oferecido suporte individual para a realização da tarefa.",
        "Explicado o conteúdo de forma individualizada, com outros termos."
    ]

    for student in students:
        for _ in range(random.randint(1, 8)):
            try:
                with db.atomic():
                    DailyReport.create(
                        student=student,
                        pedagogue=student.pedagogue,
                        date=fake.date_between(start_date='-3M', end_date='today'),
                        shift=random.choice(shifts),
                        activity_type=random.choice(activities),
                        difficulties=random.choice(difficulties_texts),
                        actions_taken=random.choice(actions_texts),
                        participants="Psicóloga Escolar" if random.random() > 0.8 else None,
                        observations=fake.sentence(nb_words=15),
                        professional_role=random.choice(roles)
                    )
                    count += 1
            except IntegrityError: 
                pass
    print(f"   > {count} relatórios diários criados.")

def create_general_reports(students, pedagogues):
    print("5. Gerando Relatórios Gerais (General Reports)...")
    count = 0
    locations = ['Sala de aula regular', 'Sala de Recursos Multifuncionais (SRM)', 'Pátio', 'Biblioteca', 'Laboratório de Informática']
    
    initial_conditions_texts = [
        "O aluno chegou à escola calmo e comunicativo, interagindo com colegas e professores.",
        "A estudante apresentou-se mais retraída e sonolenta no início da manhã.",
        "Demonstrou entusiasmo para o início das aulas, especialmente para a disciplina de Artes.",
        "Chegou um pouco atrasado, mas logo se integrou às atividades propostas."
    ]
    difficulties_found_texts = [
        "Observou-se dificuldade de concentração em tarefas que exigem leitura extensa.",
        "A aluna demonstrou insegurança para expressar suas opiniões no grupo.",
        "Ainda apresenta resistência para aceitar auxílio dos profissionais de apoio.",
        "Dificuldade na organização do tempo para finalizar as atividades dentro do prazo."
    ]
    observed_abilities_texts = [
        "Grande habilidade com cálculos matemáticos e raciocínio lógico.",
        "Demonstra criatividade e originalidade na produção de textos e desenhos.",
        "Facilidade para ajudar colegas com dificuldades, demonstrando empatia.",
        "Excelente memória para fatos e datas históricas."
    ]
    evolutions_observed_texts = [
        "Houve uma melhora significativa na interação com os colegas durante trabalhos em grupo.",
        "A aluna está mais confiante para tirar dúvidas com o professor em sala.",
        "Com o uso de recursos de acessibilidade, sua autonomia aumentou.",
        "Observa-se um progresso na organização de seus materiais escolares."
    ]

    for student in random.sample(students, k=min(len(students), 15)): 
        for _ in range(random.randint(1, 3)):
            try:
                with db.atomic():
                    GeneralReport.create(
                        student=student,
                        pedagogue=random.choice(pedagogues),
                        date=fake.date_between(start_date='-6M', end_date='today'),
                        location=random.choice(locations),
                        initial_conditions=random.choice(initial_conditions_texts),
                        difficulties_found=random.choice(difficulties_found_texts),
                        observed_abilities=random.choice(observed_abilities_texts),
                        activities_performed=fake.paragraph(nb_sentences=3),
                        evolutions_observed=random.choice(evolutions_observed_texts),
                        adapted_assessments=random.choice([True, False]),
                        professional_impediments=fake.sentence() if random.random() > 0.8 else None,
                        solutions=fake.paragraph(nb_sentences=2),
                        additional_information=fake.sentence() if random.random() > 0.6 else None
                    )
                    count += 1
            except IntegrityError: 
                pass
    print(f"   > {count} relatórios gerais criados.")

def create_events(pedagogues, students):
    print("6. Gerando Eventos (Calendário)...")
    count = 0
    titles = [
        "Reunião de Pais e Mestres", "Conselho de Classe", "Atendimento Individual com a Família", 
        "Planejamento Pedagógico Semestral", "Entrega de Laudo Atualizado", "Discussão de Caso com a Rede de Apoio",
        "Formação sobre Inclusão para Professores"
    ]
    
    for _ in range(25): # Aumentado para 25 eventos
        start = fake.date_time_between(start_date='-2M', end_date='+2M')
        duration = random.choice([30, 60, 90, 120])
        end = start + datetime.timedelta(minutes=duration)
        
        student_event = random.random() > 0.4
        student = random.choice(students) if student_event else None
        title = random.choice(titles)
        if student_event and "Individual" in title:
            title = f"Atendimento Individual - {student.name.split(' ')[0]}"

        try:
            with db.atomic():
                Event.create(
                    title=title,
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
        print("\n--- LIMPANDO DADOS ANTIGOS ---")
        with db.atomic():
            GeneralReport.delete().execute()
            DailyReport.delete().execute()
            Event.delete().execute()
            Attendance.delete().execute()
            Observation.delete().execute()
            Student.delete().execute()
            User.delete().where(User.role != 'admin').execute()
        print("--- DADOS ANTIGOS REMOVIDOS ---")

        peds = create_users_and_pedagogues(num=3)
        studs = create_students(peds, num=30)
        
        if studs and peds:
            create_attendance(studs)
            create_daily_reports(studs)
            create_general_reports(studs, peds)
            create_events(peds, studs)
            
        print("\n=== CONCLUÍDO ===")
    finally:
        if not db.is_closed():
            db.close()

if __name__ == "__main__":
    generate_all()
