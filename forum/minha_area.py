"""Minha Área: a tela inicial do estúdio depois de entrar.

Junta num lugar só o que está pendente, os indicadores e o caminho para cada
módulo, para a view ficar curta (como forum/evolucao.py faz com o diário).
"""
from django.urls import reverse
from django.utils import timezone

from .evolucao import diario_do_estudio
from .models import Aula

# Mesmo prazo do lembrete do painel de evolução.
DIAS_ENTRE_CHECKLISTS = 7
# Metas com prazo até aqui aparecem como "vencendo".
DIAS_AVISO_META = 7
ULTIMOS_REGISTROS = 5


def pendencia(texto, url, acao, destaque=False):
    return {'texto': texto, 'url': url, 'acao': acao, 'destaque': destaque}


def pendencias_do_estudio(estudio, diagnostico, checklist, calculo):
    """Lista do que o estúdio precisa fazer, na ordem de prioridade."""
    id_ = estudio.id
    hoje = timezone.localdate()
    lista = []

    if diagnostico is None:
        lista.append(pendencia(
            'Faça o diagnóstico ESG: é ele que dá a nota, o plano de ação e '
            'o selo do estúdio.',
            reverse('forum:estudio_diagnostico', args=[id_]),
            'Fazer o diagnóstico', destaque=True,
        ))
    elif estudio.reavaliacao_disponivel():
        lista.append(pendencia(
            'Reavaliação disponível: refaça o questionário para o selo '
            'acompanhar a evolução do estúdio.',
            reverse('forum:estudio_reavaliacao', args=[id_]),
            'Fazer a reavaliação',
        ))

    url_checklist = reverse('forum:estudio_evolucao', args=[id_]) + '#checklist'
    if checklist is None:
        lista.append(pendencia(
            'O estúdio ainda não fez nenhum checklist de boas práticas.',
            url_checklist, 'Fazer o checklist',
        ))
    elif (hoje - checklist.data).days >= DIAS_ENTRE_CHECKLISTS:
        lista.append(pendencia(
            f'O último checklist foi há {(hoje - checklist.data).days} dias.',
            url_checklist, 'Fazer o checklist',
        ))

    url_metas = reverse('forum:estudio_evolucao', args=[id_]) + '#metas'
    # Pelo prazo: a mais urgente (ou já vencida) aparece primeiro.
    for meta in estudio.metas.filter(
        atingida_em__isnull=True
    ).order_by('prazo'):
        if meta.vencida():
            lista.append(pendencia(
                f'Meta com prazo vencido em {meta.prazo:%d/%m/%Y}: '
                f'{meta.descricao()}.', url_metas, 'Ver as metas',
            ))
        elif (meta.prazo - hoje).days <= DIAS_AVISO_META:
            lista.append(pendencia(
                f'Meta vence em {meta.prazo:%d/%m/%Y}: {meta.descricao()}.',
                url_metas, 'Ver as metas',
            ))

    url_documentos = reverse('forum:estudio_documentos', args=[id_])
    for documento in estudio.documentos.all():
        situacao = documento.situacao()
        if situacao == 'vencido':
            lista.append(pendencia(
                f'Documento vencido em {documento.validade:%d/%m/%Y}: '
                f'{documento.get_tipo_display()}.',
                url_documentos, 'Atualizar documento',
            ))
        elif situacao == 'vencendo':
            lista.append(pendencia(
                f'Documento vence em {documento.validade:%d/%m/%Y}: '
                f'{documento.get_tipo_display()}.',
                url_documentos, 'Ver documentos',
            ))

    alertas_estoque = [item for item in estudio.itens_estoque.all()
                       if item.alertas()]
    if alertas_estoque:
        nomes = ', '.join(item.nome for item in alertas_estoque[:3])
        if len(alertas_estoque) > 3:
            nomes += f' e mais {len(alertas_estoque) - 3}'
        lista.append(pendencia(
            f'{len(alertas_estoque)} item(ns) do estoque pedem atenção: '
            f'{nomes}.',
            reverse('forum:estudio_estoque', args=[id_]), 'Ver o estoque',
        ))

    inicio_do_mes = hoje.replace(day=1)
    if (calculo is None
            or timezone.localtime(calculo.criado_em).date() < inicio_do_mes):
        lista.append(pendencia(
            'Nenhum cálculo de resíduos neste mês.',
            reverse('forum:estudio_residuos', args=[id_]),
            'Calcular os resíduos',
        ))

    comecadas = estudio.progressos_aula.filter(
        concluida=False, segundos_assistidos__gt=0
    ).select_related('aula')
    for progresso in comecadas:
        lista.append(pendencia(
            f'Aula começada e não concluída: {progresso.aula.titulo}.',
            reverse('forum:estudio_aula', args=[id_, progresso.aula_id]),
            'Continuar a aula',
        ))

    return lista


def dados_da_minha_area(estudio):
    """Tudo o que a tela da Minha Área mostra."""
    diagnostico = estudio.ultimo_diagnostico()
    checklist = estudio.ultimo_checklist()
    calculo = estudio.ultimo_calculo_residuo()

    variacao_residuos = None
    if calculo:
        total = calculo.resultado()[-1]
        if total['situacao']:
            variacao_residuos = total

    metas = list(estudio.metas.all())
    return {
        'estudio': estudio,
        'diagnostico': diagnostico,
        'checklist': checklist,
        'calculo': calculo,
        'variacao_residuos': variacao_residuos,
        'aulas_concluidas': estudio.aulas_concluidas(),
        'total_aulas': Aula.visiveis_para(estudio).count(),
        'metas_em_andamento': sum(1 for meta in metas if meta.em_andamento()),
        'metas_atingidas': sum(1 for meta in metas if meta.atingida_em),
        'total_campanhas': estudio.campanhas.count(),
        'pendencias': pendencias_do_estudio(estudio, diagnostico, checklist,
                                            calculo),
        'ultimos_registros': diario_do_estudio(estudio,
                                               limite=ULTIMOS_REGISTROS),
    }
