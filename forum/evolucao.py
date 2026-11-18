"""Diário de evolução ESG: a linha do tempo do que o estúdio registrou.

O diário não tem tabela própria. Ele é montado a partir do que as outras
áreas já guardam (diagnóstico, cálculos de resíduos, checklists, metas, aulas
e campanhas), então nada precisa ser digitado duas vezes.
"""

from django.utils import timezone

LIMITE_DO_DIARIO = 40


def diario_do_estudio(estudio, limite=LIMITE_DO_DIARIO):
    """Devolve os eventos do estúdio, do mais recente para o mais antigo.

    Cada evento é um dicionário com 'quando' (data e hora), 'tipo' (usado
    como rótulo na tela) e 'texto'.
    """
    eventos = [{
        'quando': estudio.criado_em,
        'tipo': 'Conta',
        'texto': 'Estúdio cadastrado no INKA.',
    }]

    indice_anterior = None
    for diagnostico in estudio.diagnosticos.order_by('data', 'id'):
        selo = diagnostico.selo()
        final = f'selo {selo}.' if selo else 'ainda sem selo.'
        indice = diagnostico.indice()
        if diagnostico.tipo == diagnostico.REAVALIACAO:
            texto = f'Reavaliação ESG: índice {indice:.0f} de 100'
            if indice_anterior is not None:
                variacao = round(indice - indice_anterior)
                if variacao:
                    texto += f' ({variacao:+d} em relação à anterior)'
                else:
                    texto += ' (igual à anterior)'
            texto += f', {final}'
            rotulo = 'Reavaliação'
        else:
            texto = (f'Diagnóstico de maturidade ESG: índice {indice:.0f} '
                     f'de 100, {final}')
            rotulo = 'Diagnóstico'
        indice_anterior = indice
        eventos.append({'quando': diagnostico.data, 'tipo': rotulo,
                        'texto': texto})

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

    for documento in estudio.documentos.all():
        texto = f'Documento cadastrado: {documento.get_tipo_display()}'
        if documento.validade:
            texto += f', válido até {documento.validade:%d/%m/%Y}'
        eventos.append({
            'quando': documento.criado_em,
            'tipo': 'Documento',
            'texto': texto + '.',
        })

    eventos.sort(key=lambda evento: evento['quando'], reverse=True)
    # limite=None devolve o diário inteiro (usado no painel da equipe).
    return eventos[:limite]


def marcar_metas_atingidas(estudio):
    """Marca as metas que os indicadores de hoje já alcançaram.

    Devolve as metas marcadas agora, para a tela avisar o estúdio. É chamada
    pelo painel de evolução e pela Minha Área, para as duas mostrarem a
    situação certa, seja qual for a página que o estúdio abrir primeiro.
    """
    atingidas = []
    # Cada indicador é medido uma vez só, mesmo com várias metas nele.
    valores = {}
    for meta in estudio.metas.filter(atingida_em__isnull=True):
        if not meta.em_andamento():
            continue
        if meta.indicador not in valores:
            valores[meta.indicador] = meta.valor_do_indicador(
                estudio, meta.indicador
            )
        if meta.alcanca(meta.indicador, valores[meta.indicador], meta.alvo):
            meta.atingida_em = timezone.now()
            meta.save(update_fields=['atingida_em'])
            atingidas.append(meta)
    return atingidas
