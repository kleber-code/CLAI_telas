import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY='SENHA_DO_APP'
    DATABASE = os.path.join(os.getcwd(), 'clai.db')
    APP_BASE_NAME = "CLAI"
    APP_SUFFIX = "App"
    PAGINATION_PER_PAGE = 10

    DAILY_LOG_ACTIVITY_CHOICES = [
        ('adaptacao_braille', 'Adaptação de textos para transcrição Braille'),
        ('transcricao_braille', 'Transcrição de textos para Sistema Braille'),
        ('revisao_braille', 'Revisão de textos em Braille'),
        ('conducao_sala', 'Condução a salas de aula'),
        ('conducao_laboratorio', 'Condução ao laboratório'),
        ('conducao_evento', 'Condução a evento'),
        ('acomp_aulas_vagas', 'Acompanhamento em aulas vagas'),
        ('acomp_banheiro', 'Acompanhamento ao banheiro'),
        ('acomp_visita_tecnica', 'Acompanhamento a visita técnica'),
        ('acomp_setores', 'Acompanhamento a setores da instituição'),
        ('auxilio_higiene', 'Auxílio na higiene pessoal'),
        ('atividades_extras', 'Acompanhamento em atividades extraescolares'),
        ('sala_recursos', 'Atendimento na Sala de Recursos Multifuncionais'),
        ('nucleo_aprendizagem', 'Acompanhamento no Núcleo de Aprendizagem'),
        ('monitoria_pedagogica', 'Acompanhamento ou mediação pedagógica na monitoria'),
        ('sala_aula', 'Acompanhamento pedagógico em sala de aula'),
        ('biblioteca', 'Atendimento Educacional Especializado (Biblioteca)'),
        ('leitura_material', 'Leitura de material para o estudante'),
        ('elaboracao_atividades', 'Elaboração de atividades para o estudante'),
        ('orientacoes_estudo', 'Orientações básicas para estudos'),
        ('desenvolvimento_leitura', 'Atividades para o desenvolvimento da leitura'),
        ('escrita', 'Aplicação de atividades para escrita'),
        ('logico_matematica', 'Aplicação de atividades lógico-matemáticas'),
        ('descricao_multimidia', 'Descrições (filme, imagem, gráfico, situações, etc)'),
        ('relatorios', 'Elaboração de relatórios'),
        ('planejamento_estudos', 'Planejamento/Pesquisas/Estudos na área de atuação'),
        ('construcao_jogos', 'Elaboração e construção de jogos pedagógicos'),
        ('analise_fichas', 'Análise de fichas cadastrais'),
        ('reunioes_familia', 'Reunião com a família'),
        ('pareceres_psicopedagogicos', 'Pareceres psicopedagogicos'),
        ('linhas_intervencao', 'Planejamento de linhas interventivas'),
        ('atendimento_estudante', 'Atendimento individualizado com o estudante'),
        ('atendimento_docente', 'Atendimento individualizado com o docente'),
        ('atendimento_braille', 'Atendimento individualizado com transcritor(a) Braille'),
        ('atendimento_vedor', 'Atendimento individualizado com ledor(a)'),
        ('atendimento_alfabetizador', 'Atendimento individualizado com alfabetizador(a)'),
        ('atendimento_cuidador', 'Atendimento individualizado com cuidador(a)'),
        ('atendimento_libras', 'Atendimento individualizado com intérprete LIBRAS'),
        ('comunicacao_psicologo', 'Comunicação com psicólogo'),
        ('comunicacao_pedagogo', 'Comunicação com pedagogo'),
        ('comunicacao_tae', 'Comunicação com TAE'),
        ('resolucao_setor', 'Resoluções com coordenação de setor'),
        ('impressao_braille', 'Impressão Braille'),
        ('apoio_intervalos', 'Apoio nos intervalos (lanches e almoço)'),
        ('conducao_auditorio', 'Condução ao auditório'),
    ]