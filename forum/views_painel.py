"""Painel da equipe INKA: o trabalho do dia a dia dos administradores.

O /admin/ do Django continua existindo para os cadastros completos. O painel
mostra o que a equipe precisa acompanhar (números da plataforma, estúdios) com
a identidade visual do site, e grava em RegistroEquipe cada ação feita nele.
"""
import csv
from urllib.parse import quote

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, F, Prefetch, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views import View

from .consultas import (
    SELO_POR_PILARES,
    estudios_com_indicadores,
    estudios_para_relatorio,
    filtro_de_selo,
    panorama_da_plataforma,
)
from .evolucao import diario_do_estudio
from .models import (
    Aula,
    Campanha,
    Contato,
    ConteudoDescarte,
    EmpresaDescarte,
    Estudio,
    ItemChecklist,
    Material,
    PraticaEstudio,
    RegistroEquipe,
    Resposta,
)
from .validacoes import (
    CAMPOS_EMPRESA,
    dados_para_campanha,
    duracao_da_aula,
    ler_aula,
    ler_campanha,
    ler_conteudo_descarte,
    ler_empresa_descarte,
    validar_aula,
    validar_campanha,
    validar_conteudo_descarte,
    validar_empresa_descarte,
)
from .views import LoginObrigatorioMixin

ROTULOS_SELO = {
    'ouro': 'Ouro', 'prata': 'Prata', 'bronze': 'Bronze',
    'sem_selo': 'Sem selo', 'sem_diagnostico': 'Sem diagnóstico',
}


class EquipeObrigatoriaMixin(LoginObrigatorioMixin):
    """Páginas do painel: só para contas da equipe (is_staff).

    Quem não é da equipe recebe 404, e não 403, para não revelar que o
    painel existe, como a área exclusiva faz com o estúdio dos outros.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


def percentual(parte, total):
    return round(parte / total * 100) if total else 0


class PainelView(EquipeObrigatoriaMixin, View):
    """Visão geral da plataforma."""

    def get(self, request):
        panorama = panorama_da_plataforma()
        total = panorama['estudios']

        selos = [
            {'rotulo': ROTULOS_SELO[chave], 'quantidade':
             panorama['selos'][chave],
             'percentual': percentual(panorama['selos'][chave], total),
             'filtro': chave}
            for chave in ('ouro', 'prata', 'bronze', 'sem_selo',
                          'sem_diagnostico')
        ]
        residuos = panorama['residuos_do_mes']
        total_gramas = (residuos['perfurocortante'] + residuos['contaminado']
                        + residuos['comum'])
        tipos_residuo = [
            {'rotulo': rotulo, 'gramas': residuos[chave],
             'percentual': percentual(residuos[chave], total_gramas)}
            for chave, rotulo in (('perfurocortante', 'Perfurocortante'),
                                  ('contaminado', 'Contaminado'),
                                  ('comum', 'Comum'))
        ]

        contexto = {
            'panorama': panorama,
            'selos': selos,
            'tipos_residuo': tipos_residuo,
            'total_gramas': total_gramas,
        }
        return render(request, 'forum/painel/visao_geral.html', contexto)


class PainelEstudiosView(EquipeObrigatoriaMixin, View):
    """Lista de estúdios com busca, filtros, ordenação e paginação."""

    POR_PAGINA = 20
    ORDENS = {
        'nome': ('Nome', ['nome']),
        'recentes': ('Cadastro mais recente', ['-criado_em', 'nome']),
        'indice': ('Maior índice', [F('indice').desc(nulls_last=True),
                                    'nome']),
    }

    def get(self, request):
        filtros = {
            'busca': request.GET.get('busca', '').strip(),
            'cidade': request.GET.get('cidade', '').strip(),
            'selo': request.GET.get('selo', ''),
            'situacao': request.GET.get('situacao', ''),
            'ordem': request.GET.get('ordem', 'nome'),
        }
        if filtros['ordem'] not in self.ORDENS:
            filtros['ordem'] = 'nome'
        if filtros['selo'] not in ROTULOS_SELO:
            filtros['selo'] = ''

        estudios = estudios_com_indicadores(
            Estudio.objects.select_related('usuario')
        )
        if filtros['busca']:
            busca = filtros['busca']
            estudios = estudios.filter(
                Q(nome__icontains=busca) | Q(cidade__icontains=busca)
                | Q(usuario__email__icontains=busca)
            )
        if filtros['cidade']:
            estudios = estudios.filter(cidade__iexact=filtros['cidade'])
        if filtros['selo']:
            estudios = estudios.filter(filtro_de_selo(filtros['selo']))
        if filtros['situacao'] == 'ativos':
            estudios = estudios.filter(ativo=True)
        elif filtros['situacao'] == 'desativados':
            estudios = estudios.filter(ativo=False)
        estudios = estudios.order_by(*self.ORDENS[filtros['ordem']][1])

        pagina = Paginator(estudios, self.POR_PAGINA).get_page(
            request.GET.get('pagina')
        )
        for estudio in pagina:
            estudio.selo_rotulo = self.rotulo_do_selo(estudio.pilares_ativos)

        # Os links de página levam os filtros junto.
        ativos = {chave: valor for chave, valor in filtros.items()
                  if valor and not (chave == 'ordem' and valor == 'nome')}
        contexto = {
            'pagina': pagina,
            'filtros': filtros,
            'filtros_url': urlencode(ativos),
            'cidades': (Estudio.objects.order_by('cidade')
                        .values_list('cidade', flat=True).distinct()),
            'selos': ROTULOS_SELO,
            'ordens': {chave: rotulo
                       for chave, (rotulo, _) in self.ORDENS.items()},
        }
        return render(request, 'forum/painel/estudios.html', contexto)

    @staticmethod
    def rotulo_do_selo(pilares_ativos):
        if pilares_ativos is None:
            return ROTULOS_SELO['sem_diagnostico']
        return ROTULOS_SELO[SELO_POR_PILARES[pilares_ativos]]


class PainelEstudioView(EquipeObrigatoriaMixin, View):
    """Tudo o que a equipe precisa saber de um estúdio, só para leitura."""

    def get(self, request, estudio_id):
        estudio = get_object_or_404(
            Estudio.objects.select_related('usuario'), id=estudio_id
        )
        diagnosticos = list(
            estudio.diagnosticos.order_by('-data', '-id').prefetch_related(
                Prefetch('respostas', queryset=Resposta.objects
                         .select_related('pratica__pilar')
                         .order_by('pratica__pilar__ordem', 'pratica__ordem'))
            )
        )
        contexto = {
            'estudio': estudio,
            'conta': estudio.usuario,
            'diagnostico': diagnosticos[0] if diagnosticos else None,
            'diagnosticos': diagnosticos,
            'checklist': estudio.ultimo_checklist(),
            'calculo': estudio.ultimo_calculo_residuo(),
            'aulas_concluidas': estudio.aulas_concluidas(),
            'total_aulas': Aula.visiveis_para(estudio).count(),
            'metas': estudio.metas.all(),
            'itens_estoque': estudio.itens_estoque.all(),
            'campanhas': estudio.campanhas.all(),
            'diario': diario_do_estudio(estudio, limite=None),
            'reavaliacao_em': estudio.reavaliacao_disponivel_em(),
            'reavaliacao_disponivel': estudio.reavaliacao_disponivel(),
        }
        return render(request, 'forum/painel/estudio.html', contexto)


class PainelLiberarReavaliacaoView(EquipeObrigatoriaMixin, View):
    """Deixa o estúdio fazer a reavaliação antes dos 90 dias."""

    def post(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        if estudio.ultimo_diagnostico() is None:
            messages.error(request, 'O estúdio ainda não fez o '
                                    'diagnóstico inicial.')
        else:
            estudio.reavaliacao_liberada = True
            estudio.save(update_fields=['reavaliacao_liberada'])
            RegistroEquipe.registrar(request.user, 'Liberou reavaliação',
                                     f'{estudio.nome} (#{estudio.id})')
            messages.success(request, f'Reavaliação liberada para '
                                      f'{estudio.nome}.')
        return redirect(reverse('forum:painel_estudio',
                                args=[estudio.id]))


class PainelEstudioSituacaoView(EquipeObrigatoriaMixin, View):
    """Desativa ou reativa um estúdio, depois de uma página de confirmação.

    Só superusuários podem: desativar tira o selo do ar para os clientes.
    """

    MENSAGEM_SEM_PERMISSAO = (
        'Só administradores principais podem desativar ou reativar estúdios.'
    )

    def get(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        contexto = {
            'estudio': estudio,
            'pode_alterar': request.user.is_superuser,
            'mensagem_sem_permissao': self.MENSAGEM_SEM_PERMISSAO,
        }
        return render(request, 'forum/painel/estudio_situacao.html', contexto)

    def post(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        detalhe = redirect(reverse('forum:painel_estudio', args=[estudio.id]))

        if not request.user.is_superuser:
            messages.error(request, self.MENSAGEM_SEM_PERMISSAO)
            return detalhe

        estudio.ativo = not estudio.ativo
        estudio.save(update_fields=['ativo'])
        acao = ('Reativou o estúdio' if estudio.ativo
                else 'Desativou o estúdio')
        RegistroEquipe.registrar(request.user, acao,
                                 f'{estudio.nome} (#{estudio.id})')

        if estudio.ativo:
            messages.success(request, f'{estudio.nome} foi reativado.')
        else:
            messages.success(
                request,
                f'{estudio.nome} foi desativado: saiu da lista pública e o '
                'selo deixou de ser exibido.',
            )
        return detalhe


# ---------------------------------------------------------------------------
# Peças comuns da segunda parte do painel
# ---------------------------------------------------------------------------

MENSAGEM_CONFIRA = 'Confira os campos destacados e tente novamente.'


def registrar(request, acao, alvo):
    RegistroEquipe.registrar(request.user, acao, alvo)


class PainelFormularioView(EquipeObrigatoriaMixin, View):
    """Cadastro e edição de um item da plataforma pelo painel.

    Cada subclasse diz o modelo, o template, como ler e validar o POST (as
    mesmas funções de validacoes.py usadas pelos estúdios) e como montar os
    campos. Itens de estúdios não são editados aqui: o filtro limita aos da
    plataforma, e os outros respondem 404.
    """

    modelo = None
    template = None
    nome_da_lista = None
    rotulo = 'item'
    filtro = {}

    def ler(self, post):
        raise NotImplementedError

    def validar(self, dados):
        raise NotImplementedError

    def dados_iniciais(self):
        return {}

    def dados_do_item(self, item):
        raise NotImplementedError

    def campos(self, dados):
        return dados

    def contexto_extra(self):
        return {}

    def buscar(self, item_id):
        if item_id is None:
            return None
        return get_object_or_404(self.modelo, id=item_id, **self.filtro)

    def mostrar(self, request, item, dados, erros):
        contexto = {'item': item, 'dados': dados, 'erros': erros,
                    'url_lista': reverse(self.nome_da_lista)}
        contexto.update(self.contexto_extra())
        return render(request, self.template, contexto)

    def get(self, request, item_id=None):
        item = self.buscar(item_id)
        dados = self.dados_do_item(item) if item else self.dados_iniciais()
        return self.mostrar(request, item, dados, {})

    def post(self, request, item_id=None):
        item = self.buscar(item_id)
        dados = self.ler(request.POST)
        erros = self.validar(dados)
        if erros:
            messages.error(request, MENSAGEM_CONFIRA)
            return self.mostrar(request, item, dados, erros)

        campos = self.campos(dados)
        if item is None:
            item = self.modelo.objects.create(**campos, **self.filtro)
            acao = f'Cadastrou {self.rotulo}'
        else:
            for campo, valor in campos.items():
                setattr(item, campo, valor)
            item.save()
            acao = f'Editou {self.rotulo}'
        registrar(request, acao, item)
        messages.success(request, f'{acao}: {item}.')
        return redirect(reverse(self.nome_da_lista))


class PainelRemoverView(EquipeObrigatoriaMixin, View):
    """Remove um item da plataforma depois de uma página de confirmação."""

    modelo = None
    nome_da_lista = None
    rotulo = 'item'
    aviso = ''
    filtro = {}

    def get(self, request, item_id):
        item = get_object_or_404(self.modelo, id=item_id, **self.filtro)
        contexto = {'item': item, 'rotulo': self.rotulo, 'aviso': self.aviso,
                    'url_lista': reverse(self.nome_da_lista)}
        return render(request, 'forum/painel/remover.html', contexto)

    def post(self, request, item_id):
        item = get_object_or_404(self.modelo, id=item_id, **self.filtro)
        descricao = str(item)
        item.delete()
        registrar(request, f'Removeu {self.rotulo}', descricao)
        messages.success(request, f'Removido: {descricao}.')
        return redirect(reverse(self.nome_da_lista))


# ---------------------------------------------------------------------------
# Contatos do Fale Conosco
# ---------------------------------------------------------------------------

def link_de_resposta(contato):
    """mailto: já com o assunto, para responder pelo programa de e-mail."""
    assunto = f'Re: {contato.get_assunto_display()} - INKA'
    return f'mailto:{contato.email}?subject={quote(assunto)}'


class PainelContatosView(EquipeObrigatoriaMixin, View):
    POR_PAGINA = 20
    SITUACOES = {'pendentes': 'Sem resposta', 'respondidos': 'Respondidos',
                 'todos': 'Todos'}

    def get(self, request):
        situacao = request.GET.get('situacao', 'pendentes')
        if situacao not in self.SITUACOES:
            situacao = 'pendentes'
        assunto = request.GET.get('assunto', '')
        if assunto not in dict(Contato.ASSUNTO_CHOICES):
            assunto = ''

        contatos = Contato.objects.order_by('-data_envio')
        if situacao == 'pendentes':
            contatos = contatos.filter(respondido=False)
        elif situacao == 'respondidos':
            contatos = contatos.filter(respondido=True)
        if assunto:
            contatos = contatos.filter(assunto=assunto)

        pagina = Paginator(contatos, self.POR_PAGINA).get_page(
            request.GET.get('pagina')
        )
        for contato in pagina:
            contato.mailto = link_de_resposta(contato)

        filtros = {'situacao': situacao, 'assunto': assunto}
        contexto = {
            'pagina': pagina,
            'filtros': filtros,
            'filtros_url': urlencode({c: v for c, v in filtros.items() if v}),
            'situacoes': self.SITUACOES,
            'assuntos': Contato.ASSUNTO_CHOICES,
        }
        return render(request, 'forum/painel/contatos.html', contexto)


class PainelContatoRespondidoView(EquipeObrigatoriaMixin, View):
    """Marca a mensagem como respondida, ou como pendente de novo."""

    def post(self, request, item_id):
        contato = get_object_or_404(Contato, id=item_id)
        contato.respondido = not contato.respondido
        contato.save(update_fields=['respondido'])
        if contato.respondido:
            acao = 'Marcou contato como respondido'
        else:
            acao = 'Marcou contato como pendente'
        registrar(request, acao, f'{contato.nome} <{contato.email}>')
        messages.success(request, f'{acao}: {contato.nome}.')

        # Volta para a mesma lista, com os mesmos filtros.
        filtros = {campo: request.POST.get(campo, '')
                   for campo in ('situacao', 'assunto', 'pagina')}
        filtros = {campo: valor for campo, valor in filtros.items() if valor}
        url = reverse('forum:painel_contatos')
        return redirect(f'{url}?{urlencode(filtros)}' if filtros else url)


# ---------------------------------------------------------------------------
# Campanhas sociais
# ---------------------------------------------------------------------------

class PainelCampanhasView(EquipeObrigatoriaMixin, View):
    def get(self, request):
        campanhas = Campanha.objects.prefetch_related('estudios').order_by(
            '-ativa', 'encerra_em', 'titulo'
        )
        return render(request, 'forum/painel/campanhas.html',
                      {'campanhas': campanhas})


class PainelCampanhaFormularioView(PainelFormularioView):
    modelo = Campanha
    template = 'forum/painel/campanha_form.html'
    nome_da_lista = 'forum:painel_campanhas'
    rotulo = 'campanha'

    def ler(self, post):
        return ler_campanha(post)

    def validar(self, dados):
        return validar_campanha(dados)

    def campos(self, dados):
        return dados_para_campanha(dados)

    def dados_iniciais(self):
        return {'ativa': True}

    def dados_do_item(self, item):
        return {
            'titulo': item.titulo, 'ong': item.ong,
            'descricao': item.descricao, 'cidade': item.cidade,
            'email': item.email, 'site': item.site,
            'encerra_em': (item.encerra_em.isoformat()
                           if item.encerra_em else ''),
            'ativa': item.ativa,
        }


class PainelCampanhaSituacaoView(EquipeObrigatoriaMixin, View):
    """Encerra uma campanha aberta, ou reabre uma encerrada."""

    def post(self, request, item_id):
        campanha = get_object_or_404(Campanha, id=item_id)
        campanha.ativa = not campanha.ativa
        campanha.save(update_fields=['ativa'])
        acao = 'Reabriu campanha' if campanha.ativa else 'Encerrou campanha'
        registrar(request, acao, campanha)
        messages.success(request, f'{acao}: {campanha.titulo}.')
        return redirect(reverse('forum:painel_campanhas'))


# ---------------------------------------------------------------------------
# Aulas da plataforma
# ---------------------------------------------------------------------------

class PainelAulasView(EquipeObrigatoriaMixin, View):
    def get(self, request):
        aulas = Aula.objects.filter(estudio=None).annotate(
            concluidas=Count('progressos',
                             filter=Q(progressos__concluida=True))
        )
        return render(request, 'forum/painel/aulas.html', {'aulas': aulas})


class PainelAulaFormularioView(PainelFormularioView):
    modelo = Aula
    template = 'forum/painel/aula_form.html'
    nome_da_lista = 'forum:painel_aulas'
    rotulo = 'aula'
    filtro = {'estudio': None}

    def ler(self, post):
        return ler_aula(post)

    def validar(self, dados):
        return validar_aula(dados)

    def campos(self, dados):
        return {'titulo': dados['titulo'], 'descricao': dados['descricao'],
                'url_video': dados['url_video'],
                'categoria': dados['categoria'] or Aula.INCLUSAO,
                'duracao_segundos': duracao_da_aula(dados)}

    def contexto_extra(self):
        return {'categorias': Aula.CATEGORIA_CHOICES}

    def dados_do_item(self, item):
        return {'titulo': item.titulo, 'descricao': item.descricao,
                'url_video': item.url_video,
                'categoria': item.categoria,
                'minutos': str(item.duracao_segundos // 60),
                'segundos': str(item.duracao_segundos % 60)}


class PainelAulaRemoverView(PainelRemoverView):
    modelo = Aula
    nome_da_lista = 'forum:painel_aulas'
    rotulo = 'aula'
    filtro = {'estudio': None}
    aviso = ('A aula sai da lista de todos os estúdios, e o progresso de quem '
             'já começou ou concluiu essa aula também é apagado.')


# ---------------------------------------------------------------------------
# Conteúdos e empresas de descarte da plataforma
# ---------------------------------------------------------------------------

class PainelDescarteView(EquipeObrigatoriaMixin, View):
    def get(self, request):
        contexto = {
            'conteudos': ConteudoDescarte.objects.filter(estudio=None),
            'empresas': EmpresaDescarte.objects.filter(estudio=None),
        }
        return render(request, 'forum/painel/descarte.html', contexto)


class PainelConteudoFormularioView(PainelFormularioView):
    modelo = ConteudoDescarte
    template = 'forum/painel/conteudo_form.html'
    nome_da_lista = 'forum:painel_descarte'
    rotulo = 'conteúdo de descarte'
    filtro = {'estudio': None}

    def ler(self, post):
        return ler_conteudo_descarte(post)

    def validar(self, dados):
        return validar_conteudo_descarte(dados)

    def dados_iniciais(self):
        return {'disponivel': True}

    def dados_do_item(self, item):
        return {'titulo': item.titulo, 'formato': item.formato,
                'url': item.url, 'descricao': item.descricao,
                'disponivel': item.disponivel}

    def contexto_extra(self):
        return {'formatos': ConteudoDescarte.FORMATO_CHOICES}


class PainelConteudoRemoverView(PainelRemoverView):
    modelo = ConteudoDescarte
    nome_da_lista = 'forum:painel_descarte'
    rotulo = 'conteúdo de descarte'
    filtro = {'estudio': None}
    aviso = 'O conteúdo sai da área de descarte de todos os estúdios.'


class PainelConteudoDisponivelView(EquipeObrigatoriaMixin, View):
    """Liga e desliga o aviso de link fora do ar (História 5, cenário 2).

    Vale também para conteúdos cadastrados pelos estúdios: a moderação usa a
    mesma ação para marcar links quebrados.
    """

    DESTINOS = {'descarte': 'forum:painel_descarte',
                'moderacao': 'forum:painel_moderacao'}

    def post(self, request, item_id):
        conteudo = get_object_or_404(ConteudoDescarte, id=item_id)
        conteudo.disponivel = not conteudo.disponivel
        conteudo.save(update_fields=['disponivel'])
        if conteudo.disponivel:
            acao = 'Marcou conteúdo como disponível'
        else:
            acao = 'Marcou conteúdo como indisponível'
        registrar(request, acao, conteudo)
        messages.success(request, f'{acao}: {conteudo.titulo}.')
        destino = self.DESTINOS.get(request.POST.get('voltar'),
                                    'forum:painel_descarte')
        return redirect(reverse(destino))


class PainelEmpresaFormularioView(PainelFormularioView):
    modelo = EmpresaDescarte
    template = 'forum/painel/empresa_form.html'
    nome_da_lista = 'forum:painel_descarte'
    rotulo = 'empresa de descarte'
    filtro = {'estudio': None}

    def ler(self, post):
        return ler_empresa_descarte(post)

    def validar(self, dados):
        return validar_empresa_descarte(dados)

    def dados_do_item(self, item):
        return {campo: getattr(item, campo) for campo in CAMPOS_EMPRESA}


class PainelEmpresaRemoverView(PainelRemoverView):
    modelo = EmpresaDescarte
    nome_da_lista = 'forum:painel_descarte'
    rotulo = 'empresa de descarte'
    filtro = {'estudio': None}
    aviso = 'A empresa sai da rede de coleta de todos os estúdios.'


# ---------------------------------------------------------------------------
# Checklist, diagnóstico e calculadora
# ---------------------------------------------------------------------------

class PainelChecklistView(EquipeObrigatoriaMixin, View):
    def get(self, request):
        itens = ItemChecklist.objects.order_by('ordem', 'id')
        return render(request, 'forum/painel/checklist.html',
                      {'itens': itens})


class PainelChecklistItemView(EquipeObrigatoriaMixin, View):
    """Muda a ordem do item e se ele aparece no checklist dos estúdios."""

    ORDEM_MAXIMA = 999

    def post(self, request, item_id):
        item = get_object_or_404(ItemChecklist, id=item_id)
        ordem = request.POST.get('ordem', '').strip()
        if not ordem.isdecimal() or int(ordem) > self.ORDEM_MAXIMA:
            messages.error(request,
                           f'Use uma ordem de 0 a {self.ORDEM_MAXIMA}.')
            return redirect(reverse('forum:painel_checklist'))

        item.ordem = int(ordem)
        item.ativo = request.POST.get('ativo') == 'on'
        item.save(update_fields=['ordem', 'ativo'])
        situacao = 'ativo' if item.ativo else 'inativo'
        registrar(request, 'Alterou item do checklist',
                  f'{item.texto} (ordem {item.ordem}, {situacao})')
        messages.success(request, f'Item atualizado: {item.texto}.')
        return redirect(reverse('forum:painel_checklist'))


class PainelReferenciasView(EquipeObrigatoriaMixin, View):
    """Práticas do diagnóstico e materiais da calculadora, só para consulta.

    Mudar esses cadastros altera notas, selos e cálculos já feitos, então a
    edição fica no /admin/, com o aviso na tela.
    """

    def get(self, request):
        contexto = {
            'praticas': PraticaEstudio.objects.select_related('pilar'),
            'materiais': Material.objects.all(),
        }
        return render(request, 'forum/painel/referencias.html', contexto)


# ---------------------------------------------------------------------------
# Moderação do que os estúdios cadastraram
# ---------------------------------------------------------------------------

class PainelModeracaoView(EquipeObrigatoriaMixin, View):
    def get(self, request):
        contexto = {
            'aulas': (Aula.objects.exclude(estudio=None)
                      .select_related('estudio')),
            'conteudos': (ConteudoDescarte.objects.exclude(estudio=None)
                          .select_related('estudio')),
            'empresas': (EmpresaDescarte.objects.exclude(estudio=None)
                         .select_related('estudio')),
        }
        return render(request, 'forum/painel/moderacao.html', contexto)


class PainelPublicarView(EquipeObrigatoriaMixin, View):
    """Publica para todos os estúdios um item que um estúdio cadastrou.

    Cria uma cópia sem estúdio, em vez de mudar o item original: assim o
    estúdio continua com o dele e pode removê-lo sem tirar a cópia do ar.
    """

    MENSAGEM_JA_PUBLICADO = 'Já existe um item igual publicado para todos.'
    TIPOS = {
        'aula': (Aula, ['titulo', 'descricao', 'url_video',
                        'duracao_segundos', 'ordem']),
        'conteudo': (ConteudoDescarte, ['titulo', 'formato', 'url',
                                        'descricao', 'disponivel']),
        'empresa': (EmpresaDescarte, CAMPOS_EMPRESA),
    }

    def post(self, request, tipo, item_id):
        if tipo not in self.TIPOS:
            raise Http404
        modelo, campos = self.TIPOS[tipo]
        original = get_object_or_404(modelo.objects.exclude(estudio=None),
                                     id=item_id)

        if self.ja_publicado(tipo, original):
            messages.error(request, self.MENSAGEM_JA_PUBLICADO)
        else:
            copia = modelo.objects.create(
                **{campo: getattr(original, campo) for campo in campos}
            )
            registrar(request, 'Publicou para todos',
                      f'{copia} (do estúdio {original.estudio.nome})')
            messages.success(request, f'Publicado para todos: {copia}.')
        return redirect(reverse('forum:painel_moderacao'))

    @staticmethod
    def ja_publicado(tipo, original):
        if tipo == 'aula':
            return Aula.objects.filter(
                estudio=None, url_video=original.url_video
            ).exists()
        if tipo == 'conteudo':
            return ConteudoDescarte.objects.filter(
                estudio=None, url=original.url
            ).exists()
        return EmpresaDescarte.objects.filter(
            estudio=None, nome__iexact=original.nome,
            cidade__iexact=original.cidade,
        ).exists()


# ---------------------------------------------------------------------------
# Registro de ações e relatório
# ---------------------------------------------------------------------------

class PainelRegistrosView(EquipeObrigatoriaMixin, View):
    POR_PAGINA = 30

    def get(self, request):
        pagina = Paginator(
            RegistroEquipe.objects.select_related('usuario'), self.POR_PAGINA
        ).get_page(request.GET.get('pagina'))
        return render(request, 'forum/painel/registros.html',
                      {'pagina': pagina})


def celula_segura(valor):
    """Impede que um texto vire fórmula ao abrir o CSV numa planilha.

    Nome e cidade são digitados por quem cria a conta: um nome começando
    com =, +, - ou @ seria executado como fórmula pelo Excel. O apóstrofo
    na frente faz a planilha mostrar o texto como texto.
    """
    if isinstance(valor, str) and valor[:1] in ('=', '+', '-', '@',
                                                '\t', '\r'):
        return "'" + valor
    return valor


class PainelRelatorioEstudiosView(EquipeObrigatoriaMixin, View):
    """Planilha CSV com um estúdio por linha.

    Separada por ponto e vírgula e com BOM, para o Excel em português abrir
    com as colunas e os acentos certos (com vírgula, ele junta tudo numa
    coluna só, porque a vírgula é o separador decimal).
    """

    NOME_DO_ARQUIVO = 'estudios-inka.csv'
    CABECALHO = [
        'Estúdio', 'Cidade', 'Cadastro', 'Situação', 'Selo', 'Índice',
        'Nota Ambiental', 'Nota Social', 'Nota Governança',
        'Último diagnóstico', 'Último checklist', 'Checklist (%)',
        'Último cálculo de resíduos', 'Resíduos (g)', 'Aulas concluídas',
        'Campanhas',
    ]

    def get(self, request):
        resposta = HttpResponse(content_type='text/csv; charset=utf-8')
        resposta['Content-Disposition'] = (
            f'attachment; filename="{self.NOME_DO_ARQUIVO}"'
        )
        resposta.write('\ufeff')
        planilha = csv.writer(resposta, delimiter=';')
        planilha.writerow(self.CABECALHO)
        for estudio in estudios_para_relatorio():
            planilha.writerow(
                [celula_segura(valor) for valor in self.linha(estudio)]
            )
        registrar(request, 'Baixou o relatório de estúdios',
                  self.NOME_DO_ARQUIVO)
        return resposta

    @staticmethod
    def numero(valor, casas=1):
        if valor is None:
            return ''
        return f'{valor:.{casas}f}'.replace('.', ',')

    @staticmethod
    def data(valor):
        if valor is None:
            return ''
        if hasattr(valor, 'hour'):
            valor = timezone.localtime(valor)
        return valor.strftime('%d/%m/%Y')

    def linha(self, estudio):
        percentual_checklist = ''
        if estudio.checklist_total:
            percentual_checklist = str(round(
                estudio.checklist_cumpridos / estudio.checklist_total * 100
            ))
        return [
            estudio.nome,
            estudio.cidade,
            self.data(estudio.criado_em),
            'Ativo' if estudio.ativo else 'Desativado',
            PainelEstudiosView.rotulo_do_selo(estudio.pilares_ativos),
            self.numero(estudio.indice, casas=0),
            self.numero(estudio.nota_e),
            self.numero(estudio.nota_s),
            self.numero(estudio.nota_g),
            self.data(estudio.data_diagnostico),
            self.data(estudio.checklist_data),
            percentual_checklist,
            self.data(estudio.calculo_data),
            '' if estudio.calculo_total is None else estudio.calculo_total,
            estudio.total_aulas_concluidas,
            estudio.total_campanhas,
        ]
