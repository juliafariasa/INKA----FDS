import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Value
from django.db.models.functions import Greatest

EXTENSOES_VIDEO = ('.mp4', '.webm', '.ogg', '.ogv')
EXTENSOES_AUDIO = ('.mp3', '.m4a', '.oga', '.ogg', '.wav')


def id_youtube(url):
    """Devolve o id do vídeo de um link do YouTube, ou '' se não for um."""
    partes = urlparse(url)
    host = partes.netloc.lower().removeprefix('www.').removeprefix('m.')
    video_id = ''

    if host == 'youtu.be':
        video_id = partes.path.strip('/').split('/')[0]
    elif host in ('youtube.com', 'youtube-nocookie.com'):
        if partes.path == '/watch':
            video_id = parse_qs(partes.query).get('v', [''])[0]
        elif partes.path.startswith(('/embed/', '/shorts/', '/live/')):
            video_id = partes.path.split('/')[2]

    # Ids do YouTube só têm letras sem acento, números, _ e -. (\w aceitaria
    # qualquer letra Unicode.)
    return video_id if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id) else ''


def embed_spotify(url):
    """Devolve o endereço do player do Spotify para um episódio ou podcast."""
    partes = urlparse(url)
    if partes.netloc.lower() != 'open.spotify.com':
        return ''
    achado = re.search(r'/(episode|show)/([A-Za-z0-9]+)', partes.path)
    if not achado:
        return ''
    return f'https://open.spotify.com/embed/{achado[1]}/{achado[2]}'


def formatar_tempo(segundos):
    """Escreve segundos como minutos:segundos, por exemplo 905 -> '15:05'."""
    return f'{segundos // 60}:{segundos % 60:02d}'


class SecaoConteudo(models.Model):

    PAGINA_INDEX = 'index'
    PAGINA_QUEM_SOMOS = 'quem_somos'
    PAGINA_SOBRE_PROJETO = 'sobre_projeto'

    PAGINA_CHOICES = [
        (PAGINA_INDEX, 'Início'),
        (PAGINA_QUEM_SOMOS, 'Quem Somos'),
        (PAGINA_SOBRE_PROJETO, 'Sobre o Projeto'),
    ]

    pagina = models.CharField('Página', max_length=20, choices=PAGINA_CHOICES)
    titulo = models.CharField('Título', max_length=150)
    texto = models.TextField('Texto')
    ordem = models.PositiveIntegerField('Ordem', default=0)

    class Meta:
        verbose_name = 'Seção de conteúdo'
        verbose_name_plural = 'Seções de conteúdo'
        ordering = ['pagina', 'ordem']

    def __str__(self):
        return f'{self.get_pagina_display()}: {self.titulo}'


class MembroEquipe(models.Model):

    nome = models.CharField('Nome completo', max_length=150)
    email = models.EmailField('E-mail da school')
    curso = models.CharField('Curso e turma', max_length=100,
                             default='Ciências da Computação - Turma A')
    ordem = models.PositiveIntegerField('Ordem', default=0)
    ativo = models.BooleanField('Membro ativo', default=True)

    class Meta:
        verbose_name = 'Membro da equipe'
        verbose_name_plural = 'Membros da equipe'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome

    @property
    def inicial(self):
        return self.nome[:1].upper()


class Pilar(models.Model):

    sigla = models.CharField('Sigla', max_length=2)
    nome = models.CharField('Nome', max_length=60)
    descricao = models.TextField('Descrição')
    ordem = models.PositiveIntegerField('Ordem', default=0)

    class Meta:
        verbose_name = 'Pilar ESG'
        verbose_name_plural = 'Pilares ESG'
        ordering = ['ordem']

    def __str__(self):
        return f'{self.sigla} - {self.nome}'


class ItemLista(models.Model):

    CATEGORIA_OBJETIVO = 'objetivo'
    CATEGORIA_PRATICA_FDS = 'pratica_fds'
    CATEGORIA_BENEFICIO = 'beneficio'

    CATEGORIA_CHOICES = [
        (CATEGORIA_OBJETIVO, 'Objetivo do produto'),
        (CATEGORIA_PRATICA_FDS, 'Conceito aplicado de FDS'),
        (CATEGORIA_BENEFICIO, 'Ganho para o estúdio'),
    ]

    categoria = models.CharField('Categoria', max_length=20,
                                 choices=CATEGORIA_CHOICES)
    texto = models.CharField('Texto', max_length=255)
    ordem = models.PositiveIntegerField('Ordem', default=0)

    class Meta:
        verbose_name = 'Item de lista'
        verbose_name_plural = 'Itens de lista'
        ordering = ['categoria', 'ordem']

    def __str__(self):
        return f'{self.get_categoria_display()}: {self.texto[:40]}'


class Tecnologia(models.Model):

    nome = models.CharField('Nome', max_length=60)
    descricao = models.TextField('Descrição')
    ordem = models.PositiveIntegerField('Ordem', default=0)

    class Meta:
        verbose_name = 'Tecnologia'
        verbose_name_plural = 'Tecnologias'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class PraticaEstudio(models.Model):

    pilar = models.ForeignKey(
        Pilar,
        on_delete=models.CASCADE,
        related_name='praticas',
        verbose_name='Pilar',
    )
    titulo = models.CharField('Título', max_length=120)
    descricao = models.TextField('Por que importa')
    ordem = models.PositiveIntegerField('Ordem', default=0)

    class Meta:
        verbose_name = 'Prática do estúdio'
        verbose_name_plural = 'Práticas do estúdio'
        ordering = ['pilar', 'ordem']

    def __str__(self):
        return f'{self.pilar.sigla} - {self.titulo}'


class Contato(models.Model):

    ASSUNTO_DUVIDA = 'duvida'
    ASSUNTO_PARCERIA = 'parceria'
    ASSUNTO_SUGESTAO = 'sugestao'
    ASSUNTO_SUPORTE = 'suporte'
    ASSUNTO_OUTRO = 'outro'

    ASSUNTO_CHOICES = [
        (ASSUNTO_DUVIDA, 'Dúvida sobre a plataforma'),
        (ASSUNTO_PARCERIA, 'Proposta de parceria'),
        (ASSUNTO_SUGESTAO, 'Sugestão de melhoria'),
        (ASSUNTO_SUPORTE, 'Suporte técnico'),
        (ASSUNTO_OUTRO, 'Outro assunto'),
    ]

    nome = models.CharField('Nome', max_length=120)
    email = models.EmailField('E-mail')
    empresa = models.CharField('Empresa', max_length=120, blank=True)
    assunto = models.CharField('Assunto', max_length=20,
                               choices=ASSUNTO_CHOICES,
                               default=ASSUNTO_DUVIDA)
    mensagem = models.TextField('Mensagem')
    data_envio = models.DateTimeField('Data de envio')
    respondido = models.BooleanField('Respondido', default=False)

    class Meta:
        verbose_name = 'Contato recebido'
        verbose_name_plural = 'Contatos recebidos'
        ordering = ['-data_envio']

    def __str__(self):
        return f'{self.nome} - {self.get_assunto_display()}'


class Estudio(models.Model):
    nome = models.CharField('Nome', max_length=120)
    cidade = models.CharField('Cidade', max_length=80)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudio',
        verbose_name='Conta de acesso',
        help_text='Conta que entra na área exclusiva deste estúdio.',
    )

    class Meta:
        verbose_name = 'Estúdio'
        verbose_name_plural = 'Estúdios'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def ultimo_diagnostico(self):
        return self.diagnosticos.order_by('-data', '-id').first()

    def ultimo_calculo_residuo(self):
        return self.calculos_residuo.order_by('-id').first()


class Diagnostico(models.Model):
    NOTA_MINIMA_ATIVO = 7
    SELOS = {3: 'Ouro', 2: 'Prata', 1: 'Bronze'}

    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='diagnosticos',
        verbose_name='Estúdio',
    )
    data = models.DateTimeField('Data', auto_now_add=True)
    nota_e = models.FloatField('Nota Ambiental', default=0)
    nota_s = models.FloatField('Nota Social', default=0)
    nota_g = models.FloatField('Nota Governança', default=0)

    class Meta:
        verbose_name = 'Diagnóstico'
        verbose_name_plural = 'Diagnósticos'
        ordering = ['-data']

    def __str__(self):
        return f'{self.estudio} - {self.data:%d/%m/%Y}'

    def calcular_notas(self):
        # O máximo de cada pilar sai das práticas respondidas, porque o admin
        # pode cadastrar ou remover práticas.
        pontos = {'E': 0, 'S': 0, 'G': 0}
        maximo = {'E': 0, 'S': 0, 'G': 0}
        for resposta in self.respostas.select_related('pratica__pilar'):
            sigla = resposta.pratica.pilar.sigla
            pontos[sigla] += resposta.valor
            maximo[sigla] += Resposta.SIM

        self.nota_e = self.calcular_nota(pontos['E'], maximo['E'])
        self.nota_s = self.calcular_nota(pontos['S'], maximo['S'])
        self.nota_g = self.calcular_nota(pontos['G'], maximo['G'])
        self.save()

    def calcular_nota(self, pontos, maximo):
        if maximo == 0:
            return 0
        return pontos / maximo * 10

    def nota_do_pilar(self, sigla):
        notas = {'E': self.nota_e, 'S': self.nota_s, 'G': self.nota_g}
        return notas[sigla]

    def pilar_ativo(self, sigla):
        return self.nota_do_pilar(sigla) >= self.NOTA_MINIMA_ATIVO

    def notas_por_pilar(self):
        resultado = []
        for pilar in Pilar.objects.all():
            resultado.append({
                'pilar': pilar,
                'nota': self.nota_do_pilar(pilar.sigla),
                'ativo': self.pilar_ativo(pilar.sigla),
            })
        return resultado

    def pilares_ativos(self):
        return [item['pilar'] for item in self.notas_por_pilar()
                if item['ativo']]

    def selo(self):
        return self.SELOS.get(len(self.pilares_ativos()), '')

    def indice(self):
        return (self.nota_e + self.nota_s + self.nota_g) / 3 * 10

    def plano_de_acao(self):
        pilares_fracos = [
            sigla for sigla in ['E', 'S', 'G'] if not self.pilar_ativo(sigla)
        ]
        return self.respostas.filter(
            valor__lt=Resposta.SIM,
            pratica__pilar__sigla__in=pilares_fracos,
        ).select_related('pratica__pilar')


class Resposta(models.Model):
    NAO = 0
    PARCIAL = 1
    SIM = 2

    VALOR_CHOICES = [
        (SIM, 'Sim'),
        (PARCIAL, 'Parcial'),
        (NAO, 'Não'),
    ]

    diagnostico = models.ForeignKey(
        Diagnostico,
        on_delete=models.CASCADE,
        related_name='respostas',
        verbose_name='Diagnóstico',
    )
    pratica = models.ForeignKey(
        PraticaEstudio,
        on_delete=models.CASCADE,
        related_name='respostas',
        verbose_name='Prática',
    )
    valor = models.PositiveSmallIntegerField('Valor', choices=VALOR_CHOICES)

    class Meta:
        verbose_name = 'Resposta'
        verbose_name_plural = 'Respostas'
        ordering = ['pratica']

    def __str__(self):
        return f'{self.pratica} - {self.get_valor_display()}'


class Material(models.Model):
    PERFUROCORTANTE = 'perfurocortante'
    CONTAMINADO = 'contaminado'
    COMUM = 'comum'

    TIPO_CHOICES = [
        (PERFUROCORTANTE, 'Perfurocortante'),
        (CONTAMINADO, 'Contaminado'),
        (COMUM, 'Comum'),
    ]

    nome = models.CharField('Nome', max_length=120)
    tipo = models.CharField('Tipo de resíduo', max_length=20,
                            choices=TIPO_CHOICES)
    gramas_por_atendimento = models.PositiveIntegerField(
        'Gramas por atendimento'
    )

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiais'
        ordering = ['tipo', 'nome']

    def __str__(self):
        return self.nome


class CalculoResiduo(models.Model):
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='calculos_residuo',
        verbose_name='Estúdio',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atendimentos = models.PositiveIntegerField('Atendimentos')
    gramas_perfurocortante = models.PositiveIntegerField(
        'Gramas de perfurocortante', default=0
    )
    gramas_contaminado = models.PositiveIntegerField(
        'Gramas de contaminado', default=0
    )
    gramas_comum = models.PositiveIntegerField('Gramas de comum', default=0)
    materiais = models.ManyToManyField(
        Material,
        related_name='calculos',
        verbose_name='Materiais usados',
        blank=True,
    )

    class Meta:
        verbose_name = 'Cálculo de resíduo'
        verbose_name_plural = 'Cálculos de resíduo'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.estudio} - {self.criado_em:%d/%m/%Y}'

    def calcular(self, materiais):
        gramas = {
            Material.PERFUROCORTANTE: 0,
            Material.CONTAMINADO: 0,
            Material.COMUM: 0,
        }
        for material in materiais:
            gramas[material.tipo] += (
                material.gramas_por_atendimento * self.atendimentos
            )

        self.gramas_perfurocortante = gramas[Material.PERFUROCORTANTE]
        self.gramas_contaminado = gramas[Material.CONTAMINADO]
        self.gramas_comum = gramas[Material.COMUM]

    def total(self):
        return (self.gramas_perfurocortante + self.gramas_contaminado
                + self.gramas_comum)

    def gramas_por_tipo(self):
        return {
            Material.PERFUROCORTANTE: self.gramas_perfurocortante,
            Material.CONTAMINADO: self.gramas_contaminado,
            Material.COMUM: self.gramas_comum,
            'total': self.total(),
        }

    def anterior(self):
        return self.estudio.calculos_residuo.filter(
            id__lt=self.id
        ).order_by('-id').first()

    def resultado(self):
        atual = self.gramas_por_tipo()
        anterior = self.anterior()
        linhas = []

        for tipo, rotulo in Material.TIPO_CHOICES + [('total', 'Total')]:
            linha = {'tipo': rotulo, 'gramas': atual[tipo], 'situacao': ''}
            if anterior:
                diferenca = atual[tipo] - anterior.gramas_por_tipo()[tipo]
                linha['diferenca'] = abs(diferenca)
                if diferenca > 0:
                    linha['situacao'] = 'Aumentou'
                elif diferenca < 0:
                    linha['situacao'] = 'Diminuiu'
                else:
                    linha['situacao'] = 'Igual'
            linhas.append(linha)

        return linhas


class ItemEstoque(models.Model):
    MATERIAL = 'material'
    EQUIPAMENTO = 'equipamento'

    TIPO_CHOICES = [
        (MATERIAL, 'Material'),
        (EQUIPAMENTO, 'Equipamento'),
    ]

    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='itens_estoque',
        verbose_name='Estúdio',
    )
    nome = models.CharField('Nome', max_length=120)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    quantidade = models.PositiveIntegerField('Quantidade', default=0)
    fornecedor = models.CharField('Fornecedor', max_length=120)

    class Meta:
        verbose_name = 'Item de estoque'
        verbose_name_plural = 'Itens de estoque'
        ordering = ['tipo', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.fornecedor})'

    def chave(self):
        return (self.nome.strip().casefold(),
                self.fornecedor.strip().casefold())

    @classmethod
    def existe_no_estudio(cls, estudio, nome, fornecedor, exceto=None):
        # A comparação é feita em Python porque no SQLite o iexact só ignora
        # maiúsculas em letras sem acento: "LÂMINA" e "lâmina" passariam.
        chave = (nome.strip().casefold(), fornecedor.strip().casefold())
        outros = estudio.itens_estoque.exclude(id=exceto)
        return any(item.chave() == chave for item in outros)


class ConteudoDescarte(models.Model):
    VIDEO = 'video'
    PODCAST = 'podcast'
    SLIDES = 'slides'

    FORMATO_CHOICES = [
        (VIDEO, 'Vídeo'),
        (PODCAST, 'Podcast'),
        (SLIDES, 'Slides'),
    ]

    titulo = models.CharField('Título', max_length=150)
    formato = models.CharField('Formato', max_length=10,
                               choices=FORMATO_CHOICES)
    url = models.URLField('URL', max_length=500)
    descricao = models.TextField('Descrição', blank=True)
    disponivel = models.BooleanField(
        'Disponível', default=True,
        help_text='Desmarque quando o link estiver fora do ar.',
    )

    class Meta:
        verbose_name = 'Conteúdo sobre descarte'
        verbose_name_plural = 'Conteúdos sobre descarte'
        ordering = ['formato', 'titulo']

    def __str__(self):
        return f'{self.get_formato_display()}: {self.titulo}'

    def exibicao(self):
        """Diz como a página do conteúdo mostra o link.

        Devolve o tipo ('youtube', 'spotify', 'video', 'audio' ou 'link') e o
        endereço que o template usa.
        """
        caminho = urlparse(self.url).path.lower()

        if self.formato == self.VIDEO:
            video_id = id_youtube(self.url)
            if video_id:
                return 'youtube', f'https://www.youtube.com/embed/{video_id}'
            if caminho.endswith(EXTENSOES_VIDEO):
                return 'video', self.url

        if self.formato == self.PODCAST:
            player = embed_spotify(self.url)
            if player:
                return 'spotify', player
            if caminho.endswith(EXTENSOES_AUDIO):
                return 'audio', self.url

        return 'link', self.url


class EmpresaDescarte(models.Model):
    nome = models.CharField('Nome', max_length=150)
    cidade = models.CharField('Cidade', max_length=80)
    telefone = models.CharField('Telefone', max_length=30)
    email = models.EmailField('E-mail', blank=True)
    site = models.URLField('Site', blank=True)
    tipos_residuo = models.CharField(
        'Tipos de resíduo que recolhe', max_length=200,
        help_text='Ex.: perfurocortante, contaminado, comum.',
    )

    class Meta:
        verbose_name = 'Empresa de descarte'
        verbose_name_plural = 'Empresas de descarte'
        ordering = ['cidade', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.cidade})'

    def telefone_link(self):
        return re.sub(r'[^\d+]', '', self.telefone)


class Aula(models.Model):
    MENSAGEM_URL_VIDEO = (
        'Use um link do YouTube ou de um arquivo de vídeo '
        '(.mp4, .webm ou .ogg).'
    )

    titulo = models.CharField('Título', max_length=150)
    descricao = models.TextField('Descrição', blank=True)
    url_video = models.URLField('URL do vídeo', max_length=500,
                                help_text=MENSAGEM_URL_VIDEO)
    duracao_segundos = models.PositiveIntegerField(
        'Duração em segundos', validators=[MinValueValidator(1)],
        help_text='Ex.: 900 para uma aula de 15 minutos.',
    )
    ordem = models.PositiveIntegerField('Ordem', default=0)
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='aulas_cadastradas',
        verbose_name='Cadastrada pelo estúdio',
        help_text='Deixe vazio para a aula aparecer para todos os estúdios.',
    )

    class Meta:
        verbose_name = 'Aula'
        verbose_name_plural = 'Aulas'
        ordering = ['ordem', 'titulo']

    def __str__(self):
        return self.titulo

    @classmethod
    def visiveis_para(cls, estudio):
        """Aulas da plataforma (sem estúdio) e as cadastradas pelo estúdio."""
        return cls.objects.filter(
            models.Q(estudio__isnull=True) | models.Q(estudio=estudio)
        )

    def video(self):
        """Devolve ('youtube', id), ('arquivo', url) ou ('link', url)."""
        video_id = id_youtube(self.url_video)
        if video_id:
            return 'youtube', video_id
        if urlparse(self.url_video).path.lower().endswith(EXTENSOES_VIDEO):
            return 'arquivo', self.url_video
        return 'link', self.url_video

    def clean(self):
        # Só YouTube e arquivo de vídeo deixam a página medir o progresso.
        if self.url_video and self.video()[0] == 'link':
            raise ValidationError({'url_video': self.MENSAGEM_URL_VIDEO})

    def duracao_formatada(self):
        return formatar_tempo(self.duracao_segundos)


class ProgressoAula(models.Model):
    FOLGA_SEGUNDOS = 5

    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='progressos_aula',
        verbose_name='Estúdio',
    )
    aula = models.ForeignKey(
        Aula,
        on_delete=models.CASCADE,
        related_name='progressos',
        verbose_name='Aula',
    )
    segundos_assistidos = models.PositiveIntegerField(
        'Segundos assistidos', default=0
    )
    concluida = models.BooleanField('Concluída', default=False)

    class Meta:
        verbose_name = 'Progresso em aula'
        verbose_name_plural = 'Progressos em aulas'
        constraints = [
            models.UniqueConstraint(
                fields=['estudio', 'aula'],
                name='progresso_unico_por_estudio_e_aula',
            ),
        ]

    def __str__(self):
        return f'{self.estudio} - {self.aula}'

    def registrar(self, segundos):
        """Guarda o maior valor já recebido, sem passar da duração da aula.

        O MAX é feito pelo banco num UPDATE só desta coluna. Assim dois envios
        ao mesmo tempo não fazem o progresso voltar, e o envio do progresso
        não desfaz um "concluída" gravado no mesmo instante.
        """
        limite = min(segundos, self.aula.duracao_segundos)
        ProgressoAula.objects.filter(pk=self.pk).update(
            segundos_assistidos=Greatest('segundos_assistidos', Value(limite))
        )
        self.refresh_from_db(fields=['segundos_assistidos'])

    def pode_concluir(self):
        minimo = self.aula.duracao_segundos - self.FOLGA_SEGUNDOS
        return self.segundos_assistidos >= minimo

    def assistido_formatado(self):
        return formatar_tempo(self.segundos_assistidos)
