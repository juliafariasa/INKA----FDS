from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from .models import (
    Contato,
    ItemLista,
    MembroEquipe,
    Pilar,
    SecaoConteudo,
    Tecnologia,
)


class IndexView(View):
    """Pagina inicial.

    Le os textos de abertura, os pilares ESG com as praticas ligadas a cada um
    e a lista de ganhos para o estudio. O prefetch_related evita uma consulta
    por pilar ao montar as tabelas de praticas.
    """

    def get(self, request):
        contexto = {
            'secoes': SecaoConteudo.objects.filter(
                pagina=SecaoConteudo.PAGINA_INDEX
            ),
            'pilares': Pilar.objects.prefetch_related('praticas'),
            'beneficios': ItemLista.objects.filter(
                categoria=ItemLista.CATEGORIA_BENEFICIO
            ),
        }
        return render(request, 'forum/index.html', contexto)


class QuemSomosView(View):
    """Le os membros ativos da equipe e os textos da pagina."""

    def get(self, request):
        contexto = {
            'membros': MembroEquipe.objects.filter(ativo=True),
            'secoes': SecaoConteudo.objects.filter(
                pagina=SecaoConteudo.PAGINA_QUEM_SOMOS
            ),
        }
        return render(request, 'forum/quem_somos.html', contexto)


class SobreProjetoView(View):
    """Le objetivos, praticas de FDS, tecnologias e textos da pagina."""

    def get(self, request):
        contexto = {
            'secoes': SecaoConteudo.objects.filter(
                pagina=SecaoConteudo.PAGINA_SOBRE_PROJETO
            ),
            'objetivos': ItemLista.objects.filter(
                categoria=ItemLista.CATEGORIA_OBJETIVO
            ),
            'praticas': ItemLista.objects.filter(
                categoria=ItemLista.CATEGORIA_PRATICA_FDS
            ),
            'tecnologias': Tecnologia.objects.all(),
        }
        return render(request, 'forum/sobre_projeto.html', contexto)


class FaleConoscoView(View):
    """Exibe o formulario no GET e grava o contato no POST.

    A validacao e feita manualmente dentro da view, sem django forms.
    """

    TAMANHO_MINIMO_MENSAGEM = 20

    def get(self, request):
        contexto = {
            'assuntos': Contato.ASSUNTO_CHOICES,
            'dados': {'assunto': Contato.ASSUNTO_DUVIDA},
            'erros': {},
        }
        return render(request, 'forum/fale_conosco.html', contexto)

    def post(self, request):
        dados = {
            'nome': request.POST.get('nome', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'empresa': request.POST.get('empresa', '').strip(),
            'assunto': request.POST.get('assunto', '').strip(),
            'mensagem': request.POST.get('mensagem', '').strip(),
        }
        erros = self.validar(dados)

        if erros:
            messages.error(
                request, 'Confira os campos destacados e tente novamente.'
            )
            contexto = {
                'assuntos': Contato.ASSUNTO_CHOICES,
                'dados': dados,
                'erros': erros,
            }
            return render(request, 'forum/fale_conosco.html', contexto)

        contato = Contato(
            nome=dados['nome'],
            email=dados['email'],
            empresa=dados['empresa'],
            assunto=dados['assunto'],
            mensagem=dados['mensagem'],
            data_envio=timezone.now(),
        )
        contato.save()

        messages.success(
            request,
            f'Obrigado, {contato.nome}! Sua mensagem foi registrada e a '
            'equipe do INKA responde em até 3 dias úteis.',
        )
        return redirect(reverse('forum:fale_conosco'))

    def validar(self, dados):
        """Valida os dados enviados e devolve um dicionario campo -> erro."""
        erros = {}

        if not dados['nome']:
            erros['nome'] = 'Informe seu nome.'
        elif len(dados['nome']) < 3:
            erros['nome'] = 'O nome deve ter pelo menos 3 caracteres.'

        if not dados['email']:
            erros['email'] = 'Informe seu e-mail.'
        else:
            try:
                validate_email(dados['email'])
            except ValidationError:
                erros['email'] = 'Informe um e-mail válido.'

        assuntos_validos = [codigo for codigo, _ in Contato.ASSUNTO_CHOICES]
        if dados['assunto'] not in assuntos_validos:
            erros['assunto'] = 'Escolha um dos assuntos da lista.'

        if not dados['mensagem']:
            erros['mensagem'] = 'Escreva sua mensagem.'
        elif len(dados['mensagem']) < self.TAMANHO_MINIMO_MENSAGEM:
            erros['mensagem'] = (
                'Descreva sua mensagem com pelo menos '
                f'{self.TAMANHO_MINIMO_MENSAGEM} caracteres.'
            )

        return erros
