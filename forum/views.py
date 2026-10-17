from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
import segno

from .models import (
    CalculoResiduo,
    Contato,
    Diagnostico,
    Estudio,
    ItemLista,
    Material,
    MembroEquipe,
    Pilar,
    PraticaEstudio,
    Resposta,
    SecaoConteudo,
    Tecnologia,
)


class IndexView(View):

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

    def get(self, request):
        contexto = {
            'membros': MembroEquipe.objects.filter(ativo=True),
            'secoes': SecaoConteudo.objects.filter(
                pagina=SecaoConteudo.PAGINA_QUEM_SOMOS
            ),
        }
        return render(request, 'forum/quem_somos.html', contexto)


class SobreProjetoView(View):

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


class EstudiosView(View):
    def get(self, request):
        contexto = {'estudios': Estudio.objects.all()}
        return render(request, 'forum/estudios.html', contexto)


class EstudioNovoView(View):
    def get(self, request):
        contexto = {'dados': {}, 'erros': {}}
        return render(request, 'forum/estudio_novo.html', contexto)

    def post(self, request):
        dados = {
            'nome': request.POST.get('nome', '').strip(),
            'cidade': request.POST.get('cidade', '').strip(),
        }
        erros = self.validar(dados)

        if erros:
            messages.error(
                request, 'Confira os campos destacados e tente novamente.'
            )
            contexto = {'dados': dados, 'erros': erros}
            return render(request, 'forum/estudio_novo.html', contexto)

        estudio = Estudio.objects.create(
            nome=dados['nome'], cidade=dados['cidade']
        )
        messages.success(
            request,
            f'Estúdio {estudio.nome} cadastrado. Agora responda o diagnóstico.',
        )
        return redirect(reverse('forum:estudio_diagnostico', args=[estudio.id]))

    def validar(self, dados):
        erros = {}

        if not dados['nome']:
            erros['nome'] = 'Informe o nome do estúdio.'
        elif len(dados['nome']) < 3:
            erros['nome'] = 'O nome deve ter pelo menos 3 caracteres.'

        if not dados['cidade']:
            erros['cidade'] = 'Informe a cidade do estúdio.'

        return erros


class EstudioPerfilView(View):
    def get(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        contexto = {
            'estudio': estudio,
            'diagnostico': estudio.ultimo_diagnostico(),
        }
        return render(request, 'forum/estudio_perfil.html', contexto)


class EstudioQrCodeView(View):
    def get(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        url_perfil = request.build_absolute_uri(
            reverse('forum:estudio_perfil', args=[estudio.id])
        )
        qrcode = segno.make(url_perfil)
        contexto = {
            'estudio': estudio,
            'url_perfil': url_perfil,
            'qrcode': qrcode.png_data_uri(scale=8),
        }
        return render(request, 'forum/estudio_qrcode.html', contexto)


class DiagnosticoView(View):
    def get(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        praticas = PraticaEstudio.objects.select_related('pilar')
        contexto = self.contexto(estudio, praticas, [])
        return render(request, 'forum/diagnostico.html', contexto)

    def post(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        praticas = list(PraticaEstudio.objects.select_related('pilar'))
        pendentes = self.validar(request.POST, praticas)

        if pendentes:
            messages.error(
                request,
                f'Faltou responder {len(pendentes)} prática(s). '
                'Elas estão destacadas abaixo.',
            )
            contexto = self.contexto(estudio, praticas, pendentes)
            return render(request, 'forum/diagnostico.html', contexto)

        diagnostico = Diagnostico.objects.create(estudio=estudio)
        for pratica in praticas:
            Resposta.objects.create(
                diagnostico=diagnostico, pratica=pratica, valor=pratica.valor
            )
        diagnostico.calcular_notas()

        messages.success(request, 'Diagnóstico salvo. Veja o resultado abaixo.')
        return redirect(reverse('forum:estudio_diagnostico', args=[estudio.id]))

    def contexto(self, estudio, praticas, pendentes):
        return {
            'estudio': estudio,
            'diagnostico': estudio.ultimo_diagnostico(),
            'praticas': praticas,
            'opcoes': Resposta.VALOR_CHOICES,
            'pendentes': pendentes,
        }

    def validar(self, dados, praticas):
        valores_validos = [str(valor) for valor, _ in Resposta.VALOR_CHOICES]
        pendentes = []

        for pratica in praticas:
            valor = dados.get(f'pratica_{pratica.id}', '')
            if valor in valores_validos:
                pratica.valor = int(valor)
                pratica.pendente = False
            else:
                pratica.valor = None
                pratica.pendente = True
                pendentes.append(pratica)

        return pendentes


class ResiduosView(View):
    def get(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        contexto = self.contexto(estudio, {'materiais': []}, {})
        return render(request, 'forum/residuos.html', contexto)

    def post(self, request, estudio_id):
        estudio = get_object_or_404(Estudio, id=estudio_id)
        dados = {
            'atendimentos': request.POST.get('atendimentos', '').strip(),
            'materiais': [
                int(valor) for valor in request.POST.getlist('materiais')
                if valor.isdigit()
            ],
        }
        erros = self.validar(dados)

        if erros:
            messages.error(
                request, 'Confira os campos destacados e tente novamente.'
            )
            contexto = self.contexto(estudio, dados, erros)
            return render(request, 'forum/residuos.html', contexto)

        calculo = CalculoResiduo(
            estudio=estudio, atendimentos=int(dados['atendimentos'])
        )
        calculo.calcular(Material.objects.filter(id__in=dados['materiais']))
        calculo.save()

        messages.success(request, 'Cálculo salvo. Veja o resultado abaixo.')
        return redirect(reverse('forum:estudio_residuos', args=[estudio.id]))

    def contexto(self, estudio, dados, erros):
        return {
            'estudio': estudio,
            'calculo': estudio.ultimo_calculo_residuo(),
            'materiais': Material.objects.all(),
            'recomendacoes': PraticaEstudio.objects.filter(pilar__sigla='E'),
            'dados': dados,
            'erros': erros,
        }

    def validar(self, dados):
        erros = {}

        if not dados['atendimentos']:
            erros['atendimentos'] = 'Informe o número de atendimentos.'
        else:
            try:
                atendimentos = int(dados['atendimentos'])
            except ValueError:
                erros['atendimentos'] = 'Informe um número inteiro.'
            else:
                if atendimentos <= 0:
                    erros['atendimentos'] = (
                        'O número de atendimentos deve ser maior que zero.'
                    )

        if not Material.objects.filter(id__in=dados['materiais']).exists():
            erros['materiais'] = 'Marque pelo menos um material usado.'

        return erros
