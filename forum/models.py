from django.db import models


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
    PONTOS_MAXIMOS_PILAR = 8
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
        pontos = {'E': 0, 'S': 0, 'G': 0}
        for resposta in self.respostas.select_related('pratica__pilar'):
            pontos[resposta.pratica.pilar.sigla] += resposta.valor

        self.nota_e = pontos['E'] / self.PONTOS_MAXIMOS_PILAR * 10
        self.nota_s = pontos['S'] / self.PONTOS_MAXIMOS_PILAR * 10
        self.nota_g = pontos['G'] / self.PONTOS_MAXIMOS_PILAR * 10
        self.save()

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
