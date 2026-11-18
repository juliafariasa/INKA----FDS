import re
from datetime import timedelta
from functools import cached_property
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Value
from django.db.models.functions import Greatest
from django.utils import timezone

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


def da_plataforma_ou_do_estudio(modelo, estudio):
    """Itens cadastrados no admin (sem estúdio) e os do próprio estúdio."""
    return modelo.objects.filter(
        models.Q(estudio__isnull=True) | models.Q(estudio=estudio)
    )


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
    # A calculadora destaca primeiro as práticas ligadas ao tipo de resíduo
    # que mais pesou no cálculo do estúdio.
    tipos_residuo = models.CharField(
        'Tipos de resíduo ligados', max_length=60, blank=True,
        help_text='Separados por vírgula: perfurocortante, contaminado, '
                  'comum. Vazio para práticas sem ligação com resíduos.',
    )

    class Meta:
        verbose_name = 'Prática do estúdio'
        verbose_name_plural = 'Práticas do estúdio'
        ordering = ['pilar', 'ordem']

    def __str__(self):
        return f'{self.pilar.sigla} - {self.titulo}'

    def ligada_ao_residuo(self, tipo):
        tipos = [parte.strip() for parte in self.tipos_residuo.split(',')]
        return tipo in tipos


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
    # Desativar substitui apagar: o estúdio some da lista e o selo deixa de
    # valer, mas o histórico continua guardado e a equipe pode reativar.
    ativo = models.BooleanField(
        'Ativo', default=True,
        help_text='Desmarque para suspender o estúdio: ele some da lista '
                  'pública e o selo deixa de ser exibido.',
    )
    reavaliacao_liberada = models.BooleanField(
        'Reavaliação liberada antes do prazo', default=False,
        help_text='A equipe libera uma reavaliação antes dos 90 dias. '
                  'Volta a ser desmarcado quando o estúdio a faz.',
    )
    # Dados do perfil público, todos opcionais ("Perfil ESG").
    descricao = models.CharField('Sobre o estúdio', max_length=300,
                                 blank=True)
    bairro = models.CharField('Bairro', max_length=80, blank=True)
    instagram = models.CharField('Instagram', max_length=30, blank=True,
                                 help_text='Sem o @.')
    whatsapp = models.CharField('WhatsApp', max_length=13, blank=True,
                                help_text='Só os dígitos, com o DDD.')
    site = models.URLField('Site', max_length=200, blank=True)
    acessibilidade = models.CharField(
        'Acessibilidade', max_length=200, blank=True,
        help_text='Ex.: rampa na entrada, banheiro adaptado.',
    )

    class Meta:
        verbose_name = 'Estúdio'
        verbose_name_plural = 'Estúdios'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def ultimo_diagnostico(self):
        # A lista de estúdios traz o último diagnóstico de todos de uma vez
        # (forum/consultas.py). Sem isso, busca só o deste estúdio.
        if hasattr(self, '_ultimo_diagnostico'):
            return self._ultimo_diagnostico
        return self.diagnosticos.order_by('-data', '-id').first()

    def ultimo_calculo_residuo(self):
        return self.calculos_residuo.order_by('-id').first()

    def ultimo_checklist(self):
        # Como em ultimo_diagnostico(): quem já buscou o checklist pode
        # guardá-lo aqui para as próximas chamadas não irem ao banco.
        if hasattr(self, '_ultimo_checklist'):
            return self._ultimo_checklist
        return self.checklists.first()

    def aulas_concluidas(self):
        return self.progressos_aula.filter(concluida=True).count()

    # Intervalo mínimo entre um diagnóstico e a reavaliação seguinte. É
    # o tempo para as mudanças do plano de ação aparecerem na rotina.
    DIAS_ENTRE_REAVALIACOES = 90

    def reavaliacao_disponivel_em(self):
        """Data a partir da qual o estúdio pode se reavaliar.

        None quando ainda não fez o diagnóstico inicial (precisa fazê-lo
        primeiro). Hoje, se a equipe liberou a reavaliação antes do prazo.
        """
        ultimo = self.ultimo_diagnostico()
        if ultimo is None:
            return None
        if self.reavaliacao_liberada:
            return timezone.localdate()
        return (timezone.localtime(ultimo.data).date()
                + timedelta(days=self.DIAS_ENTRE_REAVALIACOES))

    def reavaliacao_disponivel(self):
        data = self.reavaliacao_disponivel_em()
        return data is not None and data <= timezone.localdate()

    def aulas_de_inclusao_concluidas(self):
        # A meta "Aulas de inclusão concluídas" conta só essa categoria.
        return self.progressos_aula.filter(
            concluida=True, aula__categoria=Aula.INCLUSAO
        ).count()

    def instagram_url(self):
        return f'https://www.instagram.com/{self.instagram}/'

    def whatsapp_url(self):
        # wa.me espera o número com o código do país (55, Brasil).
        return f'https://wa.me/55{self.whatsapp}'


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
    # O diagnóstico inicial é único (História 2). As reavaliações vêm
    # depois e, como o selo usa sempre o diagnóstico mais recente, fazem o
    # selo acompanhar a evolução do estúdio.
    INICIAL = 'inicial'
    REAVALIACAO = 'reavaliacao'
    TIPO_CHOICES = [(INICIAL, 'Diagnóstico inicial'),
                    (REAVALIACAO, 'Reavaliação')]
    tipo = models.CharField('Tipo', max_length=12, choices=TIPO_CHOICES,
                            default=INICIAL)

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

    @cached_property
    def pilares(self):
        # selo(), pilares_ativos() e notas_por_pilar() chamam uns aos outros
        # e o template usa os três: sem guardar, cada chamada repetia a
        # mesma consulta dos pilares.
        return list(Pilar.objects.all())

    def notas_por_pilar(self):
        resultado = []
        for pilar in self.pilares:
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
    quantidade_minima = models.PositiveIntegerField(
        'Quantidade mínima', default=0,
        help_text='Abaixo disso o item aparece como pendência.',
    )
    validade = models.DateField('Validade', null=True, blank=True)
    origem_sustentavel = models.BooleanField(
        'Origem sustentável', default=False,
        help_text='Fornecedor com certificação, material biodegradável ou '
                  'reutilizável.',
    )

    DIAS_AVISO_VALIDADE = 30

    class Meta:
        verbose_name = 'Item de estoque'
        verbose_name_plural = 'Itens de estoque'
        ordering = ['tipo', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.fornecedor})'

    def abaixo_do_minimo(self):
        return self.quantidade < self.quantidade_minima

    def situacao_validade(self):
        """'vencido', 'vencendo' (até 30 dias) ou '' (em dia ou sem data)."""
        if self.validade is None:
            return ''
        hoje = timezone.localdate()
        if self.validade < hoje:
            return 'vencido'
        if (self.validade - hoje).days <= self.DIAS_AVISO_VALIDADE:
            return 'vencendo'
        return ''

    def alertas(self):
        """Avisos do item para a página de estoque e a Minha Área."""
        avisos = []
        if self.abaixo_do_minimo():
            avisos.append(f'Abaixo do mínimo ({self.quantidade_minima})')
        situacao = self.situacao_validade()
        if situacao == 'vencido':
            avisos.append(f'Vencido em {self.validade:%d/%m/%Y}')
        elif situacao == 'vencendo':
            avisos.append(f'Vence em {self.validade:%d/%m/%Y}')
        return avisos

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
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='conteudos_descarte',
        verbose_name='Cadastrado pelo estúdio',
        help_text='Deixe vazio para o conteúdo aparecer para todos os '
                  'estúdios.',
    )

    class Meta:
        verbose_name = 'Conteúdo sobre descarte'
        verbose_name_plural = 'Conteúdos sobre descarte'
        ordering = ['formato', 'titulo']

    def __str__(self):
        return f'{self.get_formato_display()}: {self.titulo}'

    @classmethod
    def visiveis_para(cls, estudio):
        return da_plataforma_ou_do_estudio(cls, estudio)

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
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='empresas_descarte',
        verbose_name='Cadastrada pelo estúdio',
        help_text='Deixe vazio para a empresa aparecer para todos os '
                  'estúdios.',
    )

    class Meta:
        verbose_name = 'Empresa de descarte'
        verbose_name_plural = 'Empresas de descarte'
        ordering = ['cidade', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.cidade})'

    @classmethod
    def visiveis_para(cls, estudio):
        return da_plataforma_ou_do_estudio(cls, estudio)

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
    INCLUSAO = 'inclusao'
    BIOSSEGURANCA = 'biosseguranca'
    GOVERNANCA = 'governanca'
    CATEGORIA_CHOICES = [
        (INCLUSAO, 'Inclusão e acessibilidade'),
        (BIOSSEGURANCA, 'Biossegurança'),
        (GOVERNANCA, 'Governança e gestão'),
    ]
    categoria = models.CharField('Categoria', max_length=20,
                                 choices=CATEGORIA_CHOICES,
                                 default=INCLUSAO)
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
        return da_plataforma_ou_do_estudio(cls, estudio)

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
    concluida_em = models.DateTimeField('Concluída em', null=True,
                                        blank=True)

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


class PasswordResetCode(models.Model):
    """Código de 6 dígitos enviado por e-mail para redefinir a senha.

    O código em si nunca é guardado, só o hash (HMAC com a SECRET_KEY).
    """

    TENTATIVAS_MAXIMAS = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_codes',
        verbose_name='Conta',
    )
    code_hash = models.CharField('Hash do código', max_length=64)
    expires_at = models.DateTimeField('Expira em')
    attempts = models.PositiveSmallIntegerField('Tentativas', default=0)
    used_at = models.DateTimeField('Usado em', null=True, blank=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    ip = models.GenericIPAddressField('IP do pedido', null=True, blank=True)

    class Meta:
        verbose_name = 'Código de redefinição de senha'
        verbose_name_plural = 'Códigos de redefinição de senha'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'Código de {self.user} ({self.created_at:%d/%m/%Y %H:%M})'


class PasswordResetToken(models.Model):
    """Token de uso único entregue a quem acertou o código.

    É ele que autoriza a troca da senha. Também só o hash fica no banco.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name='Conta',
    )
    token_hash = models.CharField('Hash do token', max_length=64, unique=True)
    expires_at = models.DateTimeField('Expira em')
    used_at = models.DateTimeField('Usado em', null=True, blank=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Token de redefinição de senha'
        verbose_name_plural = 'Tokens de redefinição de senha'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'Token de {self.user} ({self.created_at:%d/%m/%Y %H:%M})'


class ItemChecklist(models.Model):
    """Prática de rotina que o estúdio confere no checklist."""

    HIGIENE = 'higiene'
    SEGURANCA = 'seguranca'
    RESIDUOS = 'residuos'

    CATEGORIA_CHOICES = [
        (HIGIENE, 'Higiene'),
        (SEGURANCA, 'Segurança'),
        (RESIDUOS, 'Gestão de resíduos'),
    ]

    categoria = models.CharField('Categoria', max_length=20,
                                 choices=CATEGORIA_CHOICES)
    texto = models.CharField('Prática', max_length=200)
    ordem = models.PositiveIntegerField('Ordem', default=0)
    ativo = models.BooleanField(
        'Ativo', default=True,
        help_text='Desmarque para o item deixar de aparecer no checklist.',
    )

    class Meta:
        verbose_name = 'Item do checklist'
        verbose_name_plural = 'Itens do checklist'
        ordering = ['ordem', 'id']

    def __str__(self):
        return f'{self.get_categoria_display()}: {self.texto}'


class Checklist(models.Model):
    """Uma verificação das práticas de rotina, feita pelo estúdio num dia.

    Os totais ficam gravados: o histórico não muda se o admin apagar ou criar
    itens depois.
    """

    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='checklists',
        verbose_name='Estúdio',
    )
    data = models.DateField('Data')
    salvo_em = models.DateTimeField('Salvo em', auto_now=True)
    itens_cumpridos = models.ManyToManyField(
        ItemChecklist,
        related_name='+',
        verbose_name='Práticas cumpridas',
        blank=True,
    )
    cumpridos = models.PositiveSmallIntegerField('Práticas cumpridas',
                                                 default=0)
    total_itens = models.PositiveSmallIntegerField('Práticas conferidas',
                                                   default=0)

    class Meta:
        verbose_name = 'Checklist'
        verbose_name_plural = 'Checklists'
        ordering = ['-data', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['estudio', 'data'],
                name='checklist_unico_por_estudio_e_dia',
            ),
        ]

    def __str__(self):
        return f'{self.estudio} - {self.data:%d/%m/%Y}'

    def percentual(self):
        if self.total_itens == 0:
            return 0
        return round(self.cumpridos / self.total_itens * 100)


class MetaEsg(models.Model):
    """Objetivo que o estúdio escolhe e acompanha por um indicador."""

    CHECKLIST = 'checklist'
    RESIDUOS = 'residuos'
    AULAS = 'aulas'

    INDICADOR_CHOICES = [
        (CHECKLIST, 'Práticas cumpridas no checklist'),
        (RESIDUOS, 'Resíduos gerados por mês'),
        (AULAS, 'Aulas de inclusão concluídas'),
    ]
    UNIDADES = {CHECKLIST: '%', RESIDUOS: 'g', AULAS: 'aula(s)'}

    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='metas',
        verbose_name='Estúdio',
    )
    indicador = models.CharField('Indicador', max_length=20,
                                 choices=INDICADOR_CHOICES)
    alvo = models.PositiveIntegerField('Valor a alcançar')
    prazo = models.DateField('Prazo')
    valor_inicial = models.PositiveIntegerField(
        'Valor quando a meta foi criada', null=True, blank=True
    )
    criada_em = models.DateTimeField('Criada em', auto_now_add=True)
    atingida_em = models.DateTimeField('Atingida em', null=True, blank=True)

    class Meta:
        verbose_name = 'Meta ESG'
        verbose_name_plural = 'Metas ESG'
        ordering = ['-criada_em', '-id']

    def __str__(self):
        return f'{self.estudio} - {self.descricao()}'

    @staticmethod
    def valor_do_indicador(estudio, indicador):
        """Valor de hoje do indicador, ou None se ainda não há medição."""
        if indicador == MetaEsg.CHECKLIST:
            checklist = estudio.ultimo_checklist()
            return checklist.percentual() if checklist else None
        if indicador == MetaEsg.RESIDUOS:
            calculo = estudio.ultimo_calculo_residuo()
            return calculo.total() if calculo else None
        return estudio.aulas_de_inclusao_concluidas()

    @staticmethod
    def alcanca(indicador, valor, alvo):
        """Nos resíduos a meta é diminuir; nos outros, aumentar."""
        if valor is None:
            return False
        if indicador == MetaEsg.RESIDUOS:
            return valor <= alvo
        return valor >= alvo

    def unidade(self):
        return self.UNIDADES[self.indicador]

    def descricao(self):
        if self.indicador == self.CHECKLIST:
            return f'Cumprir {self.alvo}% do checklist'
        if self.indicador == self.RESIDUOS:
            return f'Gerar no máximo {self.alvo} g de resíduos por mês'
        return f'Concluir {self.alvo} aula(s) de inclusão'

    def valor_atual(self):
        return self.valor_do_indicador(self.estudio, self.indicador)

    def vencida(self):
        return (self.atingida_em is None
                and self.prazo < timezone.localdate())

    def em_andamento(self):
        return self.atingida_em is None and not self.vencida()

    def situacao(self):
        if self.atingida_em:
            return 'Atingida'
        if self.vencida():
            return 'Prazo vencido'
        return 'Em andamento'

    def progresso(self):
        """De 0 a 100: quanto do caminho até o alvo já foi percorrido."""
        if self.atingida_em:
            return 100
        atual = self.valor_atual()
        if atual is None:
            return 0
        if self.indicador == self.RESIDUOS:
            inicial = self.valor_inicial
            if inicial is None or inicial <= self.alvo:
                return 100 if atual <= self.alvo else 0
            percorrido = (inicial - atual) / (inicial - self.alvo) * 100
        else:
            percorrido = atual / self.alvo * 100
        return max(0, min(100, round(percorrido)))


class Campanha(models.Model):
    """Ação social de uma ONG parceira da qual os estúdios podem participar."""

    titulo = models.CharField('Título', max_length=150)
    ong = models.CharField('ONG ou projeto parceiro', max_length=150)
    descricao = models.TextField('Descrição')
    cidade = models.CharField('Cidade', max_length=80, blank=True)
    email = models.EmailField('E-mail de contato', blank=True)
    site = models.URLField('Site', blank=True)
    encerra_em = models.DateField(
        'Encerra em', null=True, blank=True,
        help_text='Deixe vazio para uma campanha sem data para acabar.',
    )
    ativa = models.BooleanField(
        'Ativa', default=True,
        help_text='Desmarque para encerrar a campanha antes da data.',
    )
    criada_em = models.DateTimeField('Criada em', auto_now_add=True)
    estudios = models.ManyToManyField(
        Estudio,
        through='ParticipacaoCampanha',
        related_name='campanhas',
        verbose_name='Estúdios participantes',
        blank=True,
    )

    class Meta:
        verbose_name = 'Campanha social'
        verbose_name_plural = 'Campanhas sociais'
        ordering = ['-ativa', 'encerra_em', 'titulo']

    def __str__(self):
        return f'{self.titulo} ({self.ong})'

    def aberta(self):
        return self.ativa and (self.encerra_em is None
                               or self.encerra_em >= timezone.localdate())


class ParticipacaoCampanha(models.Model):
    campanha = models.ForeignKey(
        Campanha,
        on_delete=models.CASCADE,
        related_name='participacoes',
        verbose_name='Campanha',
    )
    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='participacoes_campanha',
        verbose_name='Estúdio',
    )
    desde = models.DateTimeField('Participa desde', auto_now_add=True)

    class Meta:
        verbose_name = 'Participação em campanha'
        verbose_name_plural = 'Participações em campanhas'
        ordering = ['-desde']
        constraints = [
            models.UniqueConstraint(
                fields=['campanha', 'estudio'],
                name='participacao_unica_por_campanha_e_estudio',
            ),
        ]

    def __str__(self):
        return f'{self.estudio} em {self.campanha}'


class RegistroEquipe(models.Model):
    """Ação feita por alguém da equipe no painel, para consulta posterior."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_equipe',
        verbose_name='Quem fez',
    )
    # O nome fica gravado à parte para o registro continuar legível mesmo se
    # a conta for apagada depois.
    nome_usuario = models.CharField('Nome da conta', max_length=150)
    acao = models.CharField('Ação', max_length=120)
    alvo = models.CharField('Alvo', max_length=200)
    criado_em = models.DateTimeField('Quando', auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de ação da equipe'
        verbose_name_plural = 'Registros de ações da equipe'
        ordering = ['-criado_em', '-id']

    def __str__(self):
        return f'{self.nome_usuario}: {self.acao} ({self.alvo})'

    @classmethod
    def registrar(cls, usuario, acao, alvo):
        return cls.objects.create(
            usuario=usuario, nome_usuario=usuario.get_username(),
            acao=acao, alvo=str(alvo)[:200],
        )


class DocumentoEstudio(models.Model):
    """Licença, alvará, contrato ou laudo do estúdio (Hub de Biossegurança).

    Não há upload de arquivo: o disco do Render é apagado a cada deploy. O
    estúdio guarda, se quiser, um link para o documento (Google Drive etc.).
    O perfil público mostra só a situação ("em dia"), nunca o documento.
    """

    LICENCA_SANITARIA = 'licenca_sanitaria'
    ALVARA = 'alvara'
    CONTRATO_COLETA = 'contrato_coleta'
    AUTOCLAVE = 'autoclave'
    CURSO_BIOSSEGURANCA = 'curso_biosseguranca'
    OUTRO = 'outro'

    TIPO_CHOICES = [
        (LICENCA_SANITARIA, 'Licença sanitária'),
        (ALVARA, 'Alvará de funcionamento'),
        (CONTRATO_COLETA, 'Contrato com empresa de coleta de resíduos'),
        (AUTOCLAVE, 'Laudo de manutenção ou validação da autoclave'),
        (CURSO_BIOSSEGURANCA, 'Certificado de curso de biossegurança'),
        (OUTRO, 'Outro documento'),
    ]
    # Como cada tipo aparece no perfil público quando está em dia.
    SELOS_PUBLICOS = {
        LICENCA_SANITARIA: 'Licença sanitária em dia',
        ALVARA: 'Alvará de funcionamento em dia',
        CONTRATO_COLETA: 'Coleta de resíduos contratada',
        AUTOCLAVE: 'Autoclave com manutenção em dia',
        CURSO_BIOSSEGURANCA: 'Equipe com curso de biossegurança',
    }
    DIAS_AVISO = 30

    estudio = models.ForeignKey(
        Estudio,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name='Estúdio',
    )
    tipo = models.CharField('Tipo', max_length=30, choices=TIPO_CHOICES)
    descricao = models.CharField('Descrição', max_length=150, blank=True)
    emitido_em = models.DateField('Emitido em')
    validade = models.DateField('Válido até', null=True, blank=True)
    link = models.URLField('Link do documento', max_length=500, blank=True,
                           help_text='Opcional: Google Drive, Dropbox etc.')
    criado_em = models.DateTimeField('Cadastrado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Documento do estúdio'
        verbose_name_plural = 'Documentos do estúdio'
        ordering = ['validade', 'tipo']

    def __str__(self):
        return self.descricao or self.get_tipo_display()

    def situacao(self):
        """'vencido', 'vencendo', 'em_dia' ou 'sem_validade'."""
        if self.validade is None:
            return 'sem_validade'
        hoje = timezone.localdate()
        if self.validade < hoje:
            return 'vencido'
        if (self.validade - hoje).days <= self.DIAS_AVISO:
            return 'vencendo'
        return 'em_dia'

    def situacao_display(self):
        return {
            'vencido': 'Vencido',
            'vencendo': 'Vence em breve',
            'em_dia': 'Em dia',
            'sem_validade': 'Sem validade',
        }[self.situacao()]

    def vale_hoje(self):
        return self.situacao() != 'vencido'
