"""Diário de evolução ESG: a linha do tempo do que o estúdio registrou.

O diário não tem tabela própria. Ele é montado a partir do que as outras
áreas já guardam (diagnóstico, cálculos de resíduos, checklists, metas, aulas
e campanhas), então nada precisa ser digitado duas vezes.
"""

LIMITE_DO_DIARIO = 40


def diario_do_estudio(estudio):
    """Devolve os eventos do estúdio, do mais recente para o mais antigo.

    Cada evento é um dicionário com 'quando' (data e hora), 'tipo' (usado
    como rótulo na tela) e 'texto'.
    """
    eventos = [{
        'quando': estudio.criado_em,
        'tipo': 'Conta',
        'texto': 'Estúdio cadastrado no INKA.',
    }]

    for diagnostico in estudio.diagnosticos.all():
        selo = diagnostico.selo()
        eventos.append({
            'quando': diagnostico.data,
            'tipo': 'Diagnóstico',
            'texto': (
                f'Diagnóstico de maturidade ESG: índice '
                f'{diagnostico.indice():.0f} de 100, '
                + (f'selo {selo}.' if selo else 'ainda sem selo.')
            ),
        })

    anterior = None
    for calculo in estudio.calculos_residuo.order_by('id'):
        texto = (f'Cálculo de resíduos: {calculo.total()} g em '
                 f'{calculo.atendimentos} atendimento(s)')
        if anterior is not None:
            diferenca = calculo.total() - anterior
            if diferenca < 0:
                texto += f', {-diferenca} g a menos que no cálculo anterior'
            elif diferenca > 0:
                texto += f', {diferenca} g a mais que no cálculo anterior'
        anterior = calculo.total()
        eventos.append({
            'quando': calculo.criado_em, 'tipo': 'Resíduos',
            'texto': texto + '.',
        })

    for checklist in estudio.checklists.all():
        eventos.append({
            'quando': checklist.salvo_em,
            'tipo': 'Checklist',
            'texto': (
                f'Checklist de boas práticas: {checklist.cumpridos} de '
                f'{checklist.total_itens} cumpridas '
                f'({checklist.percentual()}%).'
            ),
        })

    for meta in estudio.metas.all():
        eventos.append({
            'quando': meta.criada_em,
            'tipo': 'Meta',
            'texto': (f'Meta definida: {meta.descricao()}, '
                      f'até {meta.prazo:%d/%m/%Y}.'),
        })
        if meta.atingida_em:
            eventos.append({
                'quando': meta.atingida_em,
                'tipo': 'Meta',
                'texto': f'Meta atingida: {meta.descricao()}.',
            })

    concluidas = estudio.progressos_aula.filter(
        concluida_em__isnull=False
    ).select_related('aula')
    for progresso in concluidas:
        eventos.append({
            'quando': progresso.concluida_em,
            'tipo': 'Aula',
            'texto': f'Aula concluída: {progresso.aula.titulo}.',
        })

    participacoes = estudio.participacoes_campanha.select_related('campanha')
    for participacao in participacoes:
        campanha = participacao.campanha
        eventos.append({
            'quando': participacao.desde,
            'tipo': 'Campanha',
            'texto': (f'Entrou na campanha {campanha.titulo}, '
                      f'com {campanha.ong}.'),
        })

    eventos.sort(key=lambda evento: evento['quando'], reverse=True)
    return eventos[:LIMITE_DO_DIARIO]
