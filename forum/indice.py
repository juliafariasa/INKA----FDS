"""Índice INKA: um número de 0 a 100 que junta o diagnóstico e a rotina.

Ele é separado do índice do diagnóstico (Diagnostico.indice) de propósito.
O selo Estúdio Consciente e as regras da História 1 continuam usando só o
diagnóstico, que é a avaliação formal do estúdio. O Índice INKA mostra, além
disso, se o estúdio mantém as boas práticas no dia a dia: checklist, resíduos,
materiais, aulas e campanhas.

Os pesos ficam nas constantes abaixo para a equipe ajustar sem mexer no
cálculo. A soma deles é 100.
"""
from datetime import timedelta

from django.utils import timezone

from .models import Aula

PESOS = {
    'diagnostico': 50,
    'checklist': 15,
    'residuos': 10,
    'materiais': 10,
    'aulas': 10,
    'campanhas': 5,
}
# Um checklist mais antigo que isso não conta mais como rotina.
DIAS_VALIDADE_CHECKLIST = 30

ROTULOS = {
    'diagnostico': 'Diagnóstico mais recente',
    'checklist': 'Checklist de boas práticas',
    'residuos': 'Resíduos em relação ao cálculo anterior',
    'materiais': 'Materiais de origem sustentável no estoque',
    'aulas': 'Aulas concluídas',
    'campanhas': 'Participação em campanha social aberta',
}


def nota_diagnostico(estudio):
    diagnostico = estudio.ultimo_diagnostico()
    if diagnostico is None:
        return 0, 'Ainda sem diagnóstico'
    return diagnostico.indice(), f'Índice {diagnostico.indice():.0f} de 100'


def nota_checklist(estudio):
    checklist = estudio.ultimo_checklist()
    if checklist is None:
        return 0, 'Nenhum checklist'
    limite = timezone.localdate() - timedelta(days=DIAS_VALIDADE_CHECKLIST)
    if checklist.data < limite:
        return 0, f'Último checklist há mais de {DIAS_VALIDADE_CHECKLIST} dias'
    return checklist.percentual(), f'{checklist.percentual()}% das práticas'


def nota_residuos(estudio):
    calculos = list(estudio.calculos_residuo.order_by('-id')[:2])
    if not calculos:
        return 0, 'Nenhum cálculo de resíduos'
    if len(calculos) == 1:
        return 50, 'Primeiro cálculo, ainda sem comparação'
    atual, anterior = calculos
    if atual.total() <= anterior.total():
        return 100, 'Diminuiu ou manteve em relação ao anterior'
    return 0, 'Aumentou em relação ao anterior'


def nota_materiais(estudio):
    itens = estudio.itens_estoque.count()
    if itens == 0:
        return 0, 'Estoque vazio'
    sustentaveis = estudio.itens_estoque.filter(
        origem_sustentavel=True
    ).count()
    return sustentaveis / itens * 100, f'{sustentaveis} de {itens} itens'


def nota_aulas(estudio):
    disponiveis = Aula.visiveis_para(estudio).count()
    if disponiveis == 0:
        return 0, 'Nenhuma aula disponível'
    concluidas = estudio.progressos_aula.filter(concluida=True).count()
    return (min(concluidas, disponiveis) / disponiveis * 100,
            f'{concluidas} de {disponiveis} aulas')


def nota_campanhas(estudio):
    hoje = timezone.localdate()
    participa = estudio.campanhas.filter(ativa=True).exclude(
        encerra_em__lt=hoje
    ).exists()
    if participa:
        return 100, 'Participa de campanha aberta'
    return 0, 'Nenhuma campanha aberta'


CALCULOS = {
    'diagnostico': nota_diagnostico,
    'checklist': nota_checklist,
    'residuos': nota_residuos,
    'materiais': nota_materiais,
    'aulas': nota_aulas,
    'campanhas': nota_campanhas,
}


def indice_inka(estudio):
    """Devolve o total (0 a 100) e o detalhamento de cada componente."""
    componentes = []
    total = 0
    for chave, peso in PESOS.items():
        nota, detalhe = CALCULOS[chave](estudio)
        pontos = nota * peso / 100
        total += pontos
        componentes.append({
            'chave': chave, 'rotulo': ROTULOS[chave], 'peso': peso,
            'nota': round(nota), 'pontos': round(pontos, 1),
            'detalhe': detalhe,
        })
    return {'total': round(total), 'componentes': componentes}

