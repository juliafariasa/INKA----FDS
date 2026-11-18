"""Consultas que juntam dados de vários estúdios de uma vez.

Listas de estúdios não podem buscar o diagnóstico de cada um separadamente:
com 100 estúdios seriam centenas de consultas para montar uma página.
"""
from datetime import timedelta

from django.db.models import (
    Avg, Case, Count, ExpressionWrapper, F, FloatField, IntegerField,
    OuterRef, Q, Subquery, Sum, Value, When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (
    CalculoResiduo,
    Campanha,
    Checklist,
    Contato,
    ConteudoDescarte,
    Diagnostico,
    Estudio,
    ParticipacaoCampanha,
    Pilar,
    ProgressoAula,
)


def subconsulta_ultimo_diagnostico(campo='id'):
    """Valor do último diagnóstico do estúdio da linha (mesma ordem do modelo)."""
    return Subquery(
        Diagnostico.objects.filter(estudio=OuterRef('pk'))
        .order_by('-data', '-id')
        .values(campo)[:1]
    )


def anexar_ultimo_diagnostico(estudios):
    """Devolve a lista de estúdios já com o último diagnóstico de cada um.

    Faz no máximo três consultas, qualquer que seja o número de estúdios: os
    estúdios (com o id do último diagnóstico), os diagnósticos e os pilares.
    Depois disso, estudio.ultimo_diagnostico(), diagnostico.selo() e
    diagnostico.indice() não vão mais ao banco.
    """
    estudios = list(estudios.annotate(
        id_ultimo_diagnostico=subconsulta_ultimo_diagnostico()
    ))
    ids = [estudio.id_ultimo_diagnostico for estudio in estudios
           if estudio.id_ultimo_diagnostico]
    diagnosticos = Diagnostico.objects.in_bulk(ids) if ids else {}

    if diagnosticos:
        pilares = list(Pilar.objects.all())
        for diagnostico in diagnosticos.values():
            diagnostico.pilares = pilares

    for estudio in estudios:
        estudio._ultimo_diagnostico = diagnosticos.get(
            estudio.id_ultimo_diagnostico
        )
    return estudios


# Selos por número de pilares ativos, na mesma regra de Diagnostico.selo().
SELO_POR_PILARES = {3: 'ouro', 2: 'prata', 1: 'bronze', 0: 'sem_selo'}


def estudios_com_indicadores(estudios=None):
    """Estúdios anotados com as notas, o índice e o selo do último diagnóstico.

    Tudo é calculado pelo banco, numa consulta só, para o painel poder filtrar,
    ordenar e contar sem percorrer os estúdios em Python. Campos anotados:
    nota_e, nota_s, nota_g, data_diagnostico, pilares_ativos (0 a 3) e indice
    (0 a 100). Sem diagnóstico, todos ficam None.

    A regra é a mesma de Diagnostico: pilar ativo com nota a partir de
    NOTA_MINIMA_ATIVO e índice igual à média das três notas vezes 10.
    """
    if estudios is None:
        estudios = Estudio.objects.all()
    minimo = Diagnostico.NOTA_MINIMA_ATIVO

    def ativo(campo):
        return Case(When(**{f'{campo}__gte': minimo}, then=Value(1)),
                    default=Value(0), output_field=IntegerField())

    return estudios.annotate(
        nota_e=subconsulta_ultimo_diagnostico('nota_e'),
        nota_s=subconsulta_ultimo_diagnostico('nota_s'),
        nota_g=subconsulta_ultimo_diagnostico('nota_g'),
        data_diagnostico=subconsulta_ultimo_diagnostico('data'),
    ).annotate(
        pilares_ativos=Case(
            When(nota_e__isnull=True, then=Value(None)),
            default=ativo('nota_e') + ativo('nota_s') + ativo('nota_g'),
            output_field=IntegerField(),
        ),
        indice=ExpressionWrapper(
            (F('nota_e') + F('nota_s') + F('nota_g')) * 10 / 3,
            output_field=FloatField(),
        ),
    )


def filtro_de_selo(selo):
    """Condição para filtrar estudios_com_indicadores() por selo."""
    if selo == 'sem_diagnostico':
        return Q(pilares_ativos__isnull=True)
    for pilares, nome in SELO_POR_PILARES.items():
        if nome == selo:
            return Q(pilares_ativos=pilares)
    return Q()


def panorama_da_plataforma():
    """Números da visão geral do painel da equipe, todos contados no banco."""
    agora = timezone.now()
    hoje = timezone.localdate()
    # O mês começa à meia-noite do dia 1 no horário de Brasília, não em UTC.
    inicio_do_mes = timezone.localtime(agora).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    trinta_dias = agora - timedelta(days=30)

    estudios = Estudio.objects.all()
    selos = estudios_com_indicadores().aggregate(
        ouro=Count('id', filter=Q(pilares_ativos=3)),
        prata=Count('id', filter=Q(pilares_ativos=2)),
        bronze=Count('id', filter=Q(pilares_ativos=1)),
        sem_selo=Count('id', filter=Q(pilares_ativos=0)),
        sem_diagnostico=Count('id', filter=Q(pilares_ativos__isnull=True)),
        indice_medio=Avg('indice'),
    )
    residuos = CalculoResiduo.objects.filter(
        criado_em__gte=inicio_do_mes
    ).aggregate(
        calculos=Count('id'),
        perfurocortante=Sum('gramas_perfurocortante'),
        contaminado=Sum('gramas_contaminado'),
        comum=Sum('gramas_comum'),
    )
    parados = estudios.filter(
        ativo=True, criado_em__lt=trinta_dias,
    ).exclude(
        checklists__data__gte=hoje - timedelta(days=30),
    ).exclude(
        calculos_residuo__criado_em__gte=trinta_dias,
    ).order_by('nome')

    return {
        'estudios': estudios.count(),
        'estudios_ativos': estudios.filter(ativo=True).count(),
        'novos_30_dias': estudios.filter(criado_em__gte=trinta_dias).count(),
        'com_diagnostico': estudios.filter(
            diagnosticos__isnull=False
        ).distinct().count(),
        'selos': selos,
        'checklists_7_dias': Checklist.objects.filter(
            data__gt=hoje - timedelta(days=7)
        ).count(),
        'residuos_do_mes': {
            chave: valor or 0 for chave, valor in residuos.items()
        },
        'aulas_concluidas': ProgressoAula.objects.filter(
            concluida=True
        ).count(),
        'participacoes': ParticipacaoCampanha.objects.count(),
        'campanhas_abertas': Campanha.objects.filter(ativa=True).filter(
            Q(encerra_em__isnull=True) | Q(encerra_em__gte=hoje)
        ).count(),
        'contatos_sem_resposta': Contato.objects.filter(
            respondido=False
        ).count(),
        'conteudos_indisponiveis': ConteudoDescarte.objects.filter(
            disponivel=False
        ).count(),
        'parados': list(parados[:10]),
        'total_parados': parados.count(),
    }


def ultimo_valor(modelo, ordem, campo):
    """Valor de `campo` no registro mais recente do estúdio da linha."""
    return Subquery(
        modelo.objects.filter(estudio=OuterRef('pk'))
        .order_by(*ordem).values(campo)[:1]
    )


def contagem(modelo, **filtros):
    """Quantos registros do modelo o estúdio da linha tem.

    É uma subconsulta, e não Count() direto, para as várias contagens não se
    multiplicarem umas pelas outras nas junções.
    """
    return Coalesce(Subquery(
        modelo.objects.filter(estudio=OuterRef('pk'), **filtros)
        .order_by().values('estudio')
        .annotate(total=Count('pk')).values('total')
    ), 0)


def estudios_para_relatorio():
    """Estúdios com tudo o que vai para o relatório CSV, numa consulta só."""
    calculos = CalculoResiduo.objects.annotate(
        total=F('gramas_perfurocortante') + F('gramas_contaminado')
        + F('gramas_comum')
    )
    return estudios_com_indicadores().annotate(
        checklist_data=ultimo_valor(Checklist, ['-data', '-id'], 'data'),
        checklist_cumpridos=ultimo_valor(Checklist, ['-data', '-id'],
                                         'cumpridos'),
        checklist_total=ultimo_valor(Checklist, ['-data', '-id'],
                                     'total_itens'),
        calculo_data=Subquery(
            calculos.filter(estudio=OuterRef('pk'))
            .order_by('-id').values('criado_em')[:1]
        ),
        calculo_total=Subquery(
            calculos.filter(estudio=OuterRef('pk'))
            .order_by('-id').values('total')[:1]
        ),
        total_aulas_concluidas=contagem(ProgressoAula, concluida=True),
        total_campanhas=contagem(ParticipacaoCampanha),
    ).order_by('nome')
