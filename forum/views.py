import hashlib

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.db import IntegrityError, models, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
import segno

from .models import (
    Aula,
    CalculoResiduo,
    Contato,
    ConteudoDescarte,
    Diagnostico,
    EmpresaDescarte,
    Estudio,
    ItemEstoque,
    ItemLista,
    Material,
    MembroEquipe,
    Pilar,
    PraticaEstudio,
    ProgressoAula,
    Resposta,
    SecaoConteudo,
    Tecnologia,
    formatar_tempo,
)


class LoginObrigatorioMixin:
    """Manda para a tela de login quem não está logado."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.sem_login(request)
        return super().dispatch(request, *args, **kwargs)

    def sem_login(self, request):
        return redirect_to_login(request.get_full_path())


class AreaDoEstudioMixin(LoginObrigatorioMixin):
    """Páginas exclusivas: só a conta dona do estúdio entra.

    A view recebe o estúdio pronto em self.estudio. Para a conta de outro
    estúdio a página responde 404, para não revelar que o estúdio existe.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.estudio = get_object_or_404(
                Estudio, id=kwargs['estudio_id'], usuario=request.user
            )
        return super().dispatch(request, *args, **kwargs)


def validar_nova_senha(erros, senha, confirmacao, usuario, campo='senha'):
    """Confere a senha nova com os validadores do Django (settings.py)."""
    if not senha:
        erros[campo] = 'Crie uma senha.'
    elif senha != confirmacao:
        erros[campo + '2'] = 'As senhas não são iguais.'
    else:
        try:
            validate_password(senha, user=usuario)
        except ValidationError as erro:
            erros[campo] = ' '.join(erro.messages)


class EntrarView(View):
    TENTATIVAS_MAXIMAS = 5
    BLOQUEIO_SEGUNDOS = 15 * 60
    MENSAGEM_ERRO = 'E-mail ou senha incorretos.'
    MENSAGEM_BLOQUEIO = (
        'Muitas tentativas com a senha errada. Aguarde 15 minutos e tente '
        'de novo.'
    )

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(reverse('forum:minha_area'))
        contexto = {'email': '', 'proxima': request.GET.get('next', '')}
        return render(request, 'forum/entrar.html', contexto)

    def post(self, request):
        email = request.POST.get('email', '').strip().lower()
        senha = request.POST.get('senha', '')
        proxima = request.POST.get('next', '')

        if not email or not senha:
            messages.error(request, 'Informe o e-mail e a senha.')
            return self.responder_erro(request, email, proxima)

        conta = self.buscar_conta(email)
        chave = self.chave_tentativas(conta, email)

        # A tentativa é contada antes de conferir a senha (add e incr são
        # atômicos), para que vários envios em paralelo também sejam contados.
        cache.add(chave, 0, self.BLOQUEIO_SEGUNDOS)
        if cache.incr(chave) > self.TENTATIVAS_MAXIMAS:
            messages.error(request, self.MENSAGEM_BLOQUEIO)
            return self.responder_erro(request, email, proxima)

        nome_de_usuario = conta.get_username() if conta else email
        usuario = authenticate(request, username=nome_de_usuario,
                               password=senha)
        if usuario is None:
            # A mensagem não diz se o erro foi no e-mail ou na senha, para
            # não revelar quais e-mails têm conta.
            messages.error(request, self.MENSAGEM_ERRO)
            return self.responder_erro(request, email, proxima)

        cache.delete(chave)
        login(request, usuario)

        # Só volta para endereços deste site, nunca para um link externo.
        if not url_has_allowed_host_and_scheme(
            proxima, allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            proxima = reverse('forum:minha_area')
        return redirect(proxima)

    def buscar_conta(self, email):
        """Acha a conta pelo e-mail digitado.

        Nas contas de estúdio o nome de usuário é o próprio e-mail. Contas
        criadas no admin podem ter outro nome de usuário; para elas vale o
        campo e-mail.
        """
        contas = get_user_model().objects
        return (contas.filter(username__iexact=email).first()
                or contas.filter(email__iexact=email).order_by('pk').first())

    def chave_tentativas(self, conta, email):
        # O contador é da conta, e não do texto digitado: entrar pelo e-mail
        # ou pelo nome de usuário da mesma conta soma no mesmo contador.
        identificador = f'conta:{conta.pk}' if conta else f'email:{email}'
        return ('login-falhas:'
                + hashlib.sha256(identificador.encode()).hexdigest())

    def responder_erro(self, request, email, proxima):
        contexto = {'email': email, 'proxima': proxima}
        return render(request, 'forum/entrar.html', contexto)


class SairView(View):
    """Só aceita POST, com o token CSRF, para um link não deslogar ninguém."""

    def post(self, request):
        logout(request)
        messages.success(request, 'Você saiu da conta do estúdio.')
        return redirect(reverse('forum:index'))


class MinhaAreaView(LoginObrigatorioMixin, View):
    def get(self, request):
        estudio = Estudio.objects.filter(usuario=request.user).first()
        if estudio is None:
            messages.error(
                request, 'Esta conta ainda não está ligada a nenhum estúdio.'
            )
            return redirect(reverse('forum:index'))
        return redirect(reverse('forum:estudio_perfil', args=[estudio.id]))


class AlterarSenhaView(LoginObrigatorioMixin, View):
    def get(self, request):
        return render(request, 'forum/alterar_senha.html', {'erros': {}})

    def post(self, request):
        atual = request.POST.get('senha_atual', '')
        nova = request.POST.get('senha', '')
        confirmacao = request.POST.get('senha2', '')

        erros = {}
        if not request.user.check_password(atual):
            erros['senha_atual'] = 'A senha atual está incorreta.'
        validar_nova_senha(erros, nova, confirmacao, request.user)

        if erros:
            messages.error(
                request, 'Confira os campos destacados e tente novamente.'
            )
            return render(request, 'forum/alterar_senha.html',
                          {'erros': erros})

        request.user.set_password(nova)
        request.user.save()
        # Mantém esta sessão aberta; as outras sessões da conta são encerradas.
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Senha alterada.')
        return redirect(reverse('forum:minha_area'))


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

    # Ordem de apresentação da equipe. Quem é de Computação vem do banco pelo
    # e-mail e aparece com a foto; a equipe de design aparece pela credencial,
    # com o texto da própria imagem repetido no alt.
    APRESENTACAO = [
        {'credencial': 'images/Brenda-oliveira.jpg', 'nome': 'Brenda Oliveira',
         'role': 'Design', 'email': 'bro2@cesar.school'},
        {'membro': 'lesm@cesar.school', 'foto': 'images/luiz eduardo.png'},
        {'membro': 'thsm@cesar.school', 'foto': 'images/thiago-monte.png'},
        {'credencial': 'images/Maria-Beatriz.png', 'nome': 'Maria Beatriz Leão',
         'role': 'Design', 'email': 'mbldm@cesar.school'},
        {'credencial': 'images/camila-dias.jpg', 'nome': 'Camila Dias',
         'role': 'Design', 'email': 'cdsa@cesar.school'},
        {'membro': 'br@cesar.school', 'foto': 'images/bruna.png'},
        {'membro': 'mmd3@cesar.school', 'foto': 'images/miguel.png'},
        {'credencial': 'images/eduardo-miranda.jpg', 'nome': 'Eduardo Miranda',
         'role': 'Design', 'email': 'edcm@cesar.school'},
        {'membro': 'jfa@cesar.school', 'foto': 'images/julia-farias.png'},
        {'membro': 'afsb2@cesar.school', 'foto': 'images/burgos.png'},
    ]

    def get(self, request):
        membros = MembroEquipe.objects.filter(ativo=True)
        contexto = {
            'membros': membros,
            'integrantes': self.integrantes(membros),
            'secoes': SecaoConteudo.objects.filter(
                pagina=SecaoConteudo.PAGINA_QUEM_SOMOS
            ),
        }
        return render(request, 'forum/quem_somos.html', contexto)

    def integrantes(self, membros):
        por_email = {membro.email: membro for membro in membros}
        integrantes = []
        for item in self.APRESENTACAO:
            if 'membro' not in item:
                integrantes.append(item)
            elif item['membro'] in por_email:
                # Membro inativo ou removido no admin some da página.
                integrantes.append({
                    'membro': por_email.pop(item['membro']),
                    'foto': item['foto'],
                })
        # Quem for cadastrado depois no admin aparece no fim, sem foto.
        integrantes.extend({'membro': membro} for membro in por_email.values())
        return integrantes


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
    """Cria a conta do estúdio: o estúdio e o login dele de uma vez."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(reverse('forum:minha_area'))
        contexto = {'dados': {}, 'erros': {}}
        return render(request, 'forum/estudio_novo.html', contexto)

    def post(self, request):
        if request.user.is_authenticated:
            return redirect(reverse('forum:minha_area'))

        dados = {
            'nome': request.POST.get('nome', '').strip(),
            'cidade': request.POST.get('cidade', '').strip(),
            'email': request.POST.get('email', '').strip().lower(),
        }
        senha = request.POST.get('senha', '')
        confirmacao = request.POST.get('senha2', '')
        erros = self.validar(dados, senha, confirmacao)

        if not erros:
            try:
                with transaction.atomic():
                    # create_user guarda só o hash da senha (PBKDF2 com sal).
                    usuario = get_user_model().objects.create_user(
                        username=dados['email'], email=dados['email'],
                        password=senha,
                    )
                    estudio = Estudio.objects.create(
                        nome=dados['nome'], cidade=dados['cidade'],
                        usuario=usuario,
                    )
            except IntegrityError:
                # Clique duplo: o primeiro envio já criou a conta.
                erros = {'email': 'Já existe uma conta com este e-mail.'}

        if erros:
            messages.error(
                request, 'Confira os campos destacados e tente novamente.'
            )
            # As senhas nunca voltam para o formulário.
            contexto = {'dados': dados, 'erros': erros}
            return render(request, 'forum/estudio_novo.html', contexto)

        login(request, usuario)

        messages.success(
            request,
            f'Conta do estúdio {estudio.nome} criada. Agora responda o '
            'diagnóstico.',
        )
        return redirect(reverse('forum:estudio_diagnostico', args=[estudio.id]))

    def validar(self, dados, senha, confirmacao):
        erros = {}

        if not dados['nome']:
            erros['nome'] = 'Informe o nome do estúdio.'
        elif len(dados['nome']) < 3:
            erros['nome'] = 'O nome deve ter pelo menos 3 caracteres.'
        elif len(dados['nome']) > 120:
            erros['nome'] = 'Use no máximo 120 caracteres.'

        if not dados['cidade']:
            erros['cidade'] = 'Informe a cidade do estúdio.'
        elif len(dados['cidade']) > 80:
            erros['cidade'] = 'Use no máximo 80 caracteres.'

        if not dados['email']:
            erros['email'] = 'Informe o e-mail.'
        else:
            try:
                validate_email(dados['email'])
            except ValidationError:
                erros['email'] = 'Informe um e-mail válido.'
            else:
                if len(dados['email']) > 150:
                    erros['email'] = 'Use um e-mail com até 150 caracteres.'
                elif get_user_model().objects.filter(
                    models.Q(username__iexact=dados['email'])
                    | models.Q(email__iexact=dados['email'])
                ).exists():
                    erros['email'] = 'Já existe uma conta com este e-mail.'

        # O usuário provisório deixa o Django recusar senha parecida com o
        # e-mail.
        provisorio = get_user_model()(
            username=dados['email'], email=dados['email']
        )
        validar_nova_senha(erros, senha, confirmacao, provisorio)

        return erros


class EstudioPerfilView(View):
    MENSAGEM_SELO_INVALIDO = 'Selo não encontrado ou inválido!'

    def get(self, request, estudio_id):
        estudio = Estudio.objects.filter(id=estudio_id).first()
        if estudio is None:
            # Este é o endereço gravado no QR Code. Se o estúdio foi removido,
            # a verificação responde 404, mas com a mensagem da História 1.
            messages.error(request, self.MENSAGEM_SELO_INVALIDO)
            return render(request, 'forum/selo_invalido.html', status=404)

        contexto = {
            'estudio': estudio,
            'diagnostico': estudio.ultimo_diagnostico(),
            # O perfil é público (o cliente chega pelo QR Code); os links da
            # área exclusiva só aparecem para a conta dona do estúdio.
            'eh_dono': (request.user.is_authenticated
                        and estudio.usuario_id == request.user.id),
        }
        return render(request, 'forum/estudio_perfil.html', contexto)


class EstudioQrCodeView(AreaDoEstudioMixin, View):
    def get(self, request, estudio_id):
        estudio = self.estudio
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


class DiagnosticoView(AreaDoEstudioMixin, View):
    MENSAGEM_JA_REALIZADO = (
        'Seu estúdio já realizou o diagnóstico inicial. '
        'Acompanhe sua evolução pelo painel!'
    )

    def get(self, request, estudio_id):
        estudio = self.estudio
        praticas = PraticaEstudio.objects.select_related('pilar')
        contexto = self.contexto(estudio, praticas, [])
        return render(request, 'forum/diagnostico.html', contexto)

    def post(self, request, estudio_id):
        estudio = self.estudio

        # O diagnóstico inicial é feito uma vez só. A página mostra o
        # resultado e a mensagem no lugar do questionário.
        if estudio.ultimo_diagnostico():
            praticas = PraticaEstudio.objects.select_related('pilar')
            contexto = self.contexto(estudio, praticas, [])
            return render(request, 'forum/diagnostico.html', contexto)

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
            'mensagem_ja_realizado': self.MENSAGEM_JA_REALIZADO,
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


class ResiduosView(AreaDoEstudioMixin, View):
    ATENDIMENTOS_MAXIMOS = 10000

    def get(self, request, estudio_id):
        estudio = self.estudio
        dados = {'materiais': []}

        # O formulário já vem com os dados do último mês, para só ajustar.
        calculo = estudio.ultimo_calculo_residuo()
        if calculo:
            dados = {
                'atendimentos': str(calculo.atendimentos),
                'materiais': list(
                    calculo.materiais.values_list('id', flat=True)
                ),
            }

        contexto = self.contexto(estudio, dados, {})
        return render(request, 'forum/residuos.html', contexto)

    def post(self, request, estudio_id):
        estudio = self.estudio
        dados = {
            'atendimentos': request.POST.get('atendimentos', '').strip(),
            'materiais': [
                int(valor) for valor in request.POST.getlist('materiais')
                if valor.isdecimal()
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
        materiais = Material.objects.filter(id__in=dados['materiais'])
        calculo.calcular(materiais)
        calculo.save()
        calculo.materiais.set(materiais)

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
                elif atendimentos > self.ATENDIMENTOS_MAXIMOS:
                    erros['atendimentos'] = (
                        f'Informe no máximo {self.ATENDIMENTOS_MAXIMOS} '
                        'atendimentos por mês.'
                    )

        if not Material.objects.filter(id__in=dados['materiais']).exists():
            erros['materiais'] = 'Selecione pelo menos um material utilizado!'

        return erros


class EstoqueView(AreaDoEstudioMixin, View):
    def get(self, request, estudio_id):
        estudio = self.estudio
        contexto = {'estudio': estudio, 'itens': estudio.itens_estoque.all()}
        return render(request, 'forum/estoque.html', contexto)


class ItemEstoqueFormularioView(AreaDoEstudioMixin, View):
    """Base do cadastro e da edição, que usam o mesmo formulário e regras."""

    MENSAGEM_DUPLICADO = (
        'Este material já está no seu estoque. '
        'Edite a quantidade do item existente!'
    )
    QUANTIDADE_MAXIMA = 1000000

    def ler_dados(self, post):
        return {
            'nome': post.get('nome', '').strip(),
            'tipo': post.get('tipo', '').strip(),
            'quantidade': post.get('quantidade', '').strip(),
            'fornecedor': post.get('fornecedor', '').strip(),
        }

    def contexto(self, estudio, item, dados, erros):
        return {
            'estudio': estudio,
            'item': item,
            'tipos': ItemEstoque.TIPO_CHOICES,
            'dados': dados,
            'erros': erros,
        }

    def responder_erro(self, request, estudio, item, dados, erros):
        if 'duplicado' in erros:
            messages.error(request, erros['duplicado'])
        else:
            messages.error(
                request, 'Confira os campos destacados e tente novamente.'
            )
        contexto = self.contexto(estudio, item, dados, erros)
        return render(request, 'forum/estoque_form.html', contexto)

    def validar(self, estudio, dados, exceto=None):
        erros = {}

        if not dados['nome']:
            erros['nome'] = 'Informe o nome do item.'
        elif len(dados['nome']) > 120:
            erros['nome'] = 'Use no máximo 120 caracteres.'

        tipos_validos = [codigo for codigo, _ in ItemEstoque.TIPO_CHOICES]
        if dados['tipo'] not in tipos_validos:
            erros['tipo'] = 'Escolha se o item é material ou equipamento.'

        if not dados['quantidade']:
            erros['quantidade'] = 'Informe a quantidade.'
        else:
            try:
                quantidade = int(dados['quantidade'])
            except ValueError:
                erros['quantidade'] = 'Informe um número inteiro.'
            else:
                if quantidade < 0:
                    erros['quantidade'] = 'A quantidade não pode ser negativa.'
                elif quantidade > self.QUANTIDADE_MAXIMA:
                    erros['quantidade'] = (
                        'A quantidade deve ser de no máximo '
                        f'{self.QUANTIDADE_MAXIMA}.'
                    )

        if not dados['fornecedor']:
            erros['fornecedor'] = 'Informe o fornecedor.'
        elif len(dados['fornecedor']) > 120:
            erros['fornecedor'] = 'Use no máximo 120 caracteres.'

        if not erros and ItemEstoque.existe_no_estudio(
            estudio, dados['nome'], dados['fornecedor'], exceto=exceto
        ):
            erros['duplicado'] = self.MENSAGEM_DUPLICADO

        return erros


class ItemEstoqueNovoView(ItemEstoqueFormularioView):
    def get(self, request, estudio_id):
        estudio = self.estudio
        dados = {'tipo': ItemEstoque.MATERIAL}
        contexto = self.contexto(estudio, None, dados, {})
        return render(request, 'forum/estoque_form.html', contexto)

    def post(self, request, estudio_id):
        estudio = self.estudio
        dados = self.ler_dados(request.POST)
        erros = self.validar(estudio, dados)

        if erros:
            return self.responder_erro(request, estudio, None, dados, erros)

        item = ItemEstoque.objects.create(
            estudio=estudio,
            nome=dados['nome'],
            tipo=dados['tipo'],
            quantidade=int(dados['quantidade']),
            fornecedor=dados['fornecedor'],
        )
        messages.success(request, f'{item.nome} entrou no estoque.')
        return redirect(reverse('forum:estudio_estoque', args=[estudio.id]))


class ItemEstoqueEditarView(ItemEstoqueFormularioView):
    def get(self, request, estudio_id, item_id):
        estudio = self.estudio
        item = get_object_or_404(ItemEstoque, id=item_id, estudio=estudio)
        dados = {
            'nome': item.nome,
            'tipo': item.tipo,
            'quantidade': str(item.quantidade),
            'fornecedor': item.fornecedor,
        }
        contexto = self.contexto(estudio, item, dados, {})
        return render(request, 'forum/estoque_form.html', contexto)

    def post(self, request, estudio_id, item_id):
        estudio = self.estudio
        item = get_object_or_404(ItemEstoque, id=item_id, estudio=estudio)
        dados = self.ler_dados(request.POST)
        erros = self.validar(estudio, dados, exceto=item.id)

        if erros:
            return self.responder_erro(request, estudio, item, dados, erros)

        item.nome = dados['nome']
        item.tipo = dados['tipo']
        item.quantidade = int(dados['quantidade'])
        item.fornecedor = dados['fornecedor']
        item.save()
        messages.success(request, f'{item.nome} atualizado no estoque.')
        return redirect(reverse('forum:estudio_estoque', args=[estudio.id]))


class ItemEstoqueRemoverView(AreaDoEstudioMixin, View):
    def get(self, request, estudio_id, item_id):
        estudio = self.estudio
        item = get_object_or_404(ItemEstoque, id=item_id, estudio=estudio)
        contexto = {'estudio': estudio, 'item': item}
        return render(request, 'forum/estoque_remover.html', contexto)

    def post(self, request, estudio_id, item_id):
        estudio = self.estudio
        item = get_object_or_404(ItemEstoque, id=item_id, estudio=estudio)
        item.delete()
        messages.success(request, f'{item.nome} saiu do estoque.')
        return redirect(reverse('forum:estudio_estoque', args=[estudio.id]))


class DescarteView(LoginObrigatorioMixin, View):
    TITULOS_FORMATO = {
        ConteudoDescarte.VIDEO: 'Vídeos',
        ConteudoDescarte.PODCAST: 'Podcasts',
        ConteudoDescarte.SLIDES: 'Slides',
    }

    def get(self, request):
        conteudos = list(ConteudoDescarte.objects.all())
        formatos = [
            {
                'titulo': self.TITULOS_FORMATO[codigo],
                'conteudos': [c for c in conteudos if c.formato == codigo],
            }
            for codigo, _ in ConteudoDescarte.FORMATO_CHOICES
        ]
        contexto = {
            'tem_conteudo': bool(conteudos),
            'formatos': formatos,
            'empresas': EmpresaDescarte.objects.all(),
        }
        return render(request, 'forum/descarte.html', contexto)


class DescarteConteudoView(LoginObrigatorioMixin, View):
    MENSAGEM_INDISPONIVEL = (
        'Este conteúdo está indisponível no momento. '
        'Tente outro conteúdo da lista!'
    )

    def get(self, request, conteudo_id):
        conteudo = get_object_or_404(ConteudoDescarte, id=conteudo_id)
        contexto = {'conteudo': conteudo}

        if conteudo.disponivel:
            contexto['tipo_player'], contexto['url_player'] = (
                conteudo.exibicao()
            )
        else:
            messages.error(request, self.MENSAGEM_INDISPONIVEL)

        return render(request, 'forum/descarte_conteudo.html', contexto)


def buscar_aula(estudio, aula_id):
    """Só acha a aula se ela for da plataforma ou do próprio estúdio."""
    return get_object_or_404(Aula.visiveis_para(estudio), id=aula_id)


def ler_segundos(dados):
    """Lê os segundos assistidos enviados pela página; None se inválidos."""
    try:
        segundos = int(dados.get('segundos', ''))
    except ValueError:
        return None
    return segundos if segundos >= 0 else None


class AulasView(AreaDoEstudioMixin, View):
    def get(self, request, estudio_id):
        estudio = self.estudio
        aulas = list(Aula.visiveis_para(estudio))
        progressos = {p.aula_id: p for p in estudio.progressos_aula.all()}
        for aula in aulas:
            aula.progresso = progressos.get(aula.id)

        contexto = {
            'estudio': estudio,
            'aulas': aulas,
            'concluidas': sum(
                1 for aula in aulas
                if aula.progresso and aula.progresso.concluida
            ),
        }
        return render(request, 'forum/aulas.html', contexto)


class AulaView(AreaDoEstudioMixin, View):
    MENSAGEM_INCOMPLETA = 'Assista à aula até o final para concluí-la!'

    def get(self, request, estudio_id, aula_id):
        estudio = self.estudio
        aula = buscar_aula(estudio, aula_id)
        progresso = ProgressoAula.objects.filter(
            estudio=estudio, aula=aula
        ).first()
        contexto = self.contexto(request, estudio, aula, progresso)
        return render(request, 'forum/aula.html', contexto)

    def post(self, request, estudio_id, aula_id):
        estudio = self.estudio
        aula = buscar_aula(estudio, aula_id)
        progresso, _ = ProgressoAula.objects.get_or_create(
            estudio=estudio, aula=aula
        )

        # O formulário leva os segundos que a página mediu até o clique.
        segundos = ler_segundos(request.POST)
        if segundos is not None:
            progresso.registrar(segundos)

        if not progresso.pode_concluir():
            messages.error(request, self.MENSAGEM_INCOMPLETA)
            contexto = self.contexto(request, estudio, aula, progresso)
            return render(request, 'forum/aula.html', contexto)

        progresso.concluida = True
        progresso.save(update_fields=['concluida'])
        messages.success(request, f'Aula concluída: {aula.titulo}.')
        return redirect(reverse('forum:estudio_aulas', args=[estudio.id]))

    def contexto(self, request, estudio, aula, progresso):
        assistidos = progresso.segundos_assistidos if progresso else 0
        concluida = bool(progresso and progresso.concluida)
        tipo_video, fonte_video = aula.video()

        # Retoma o vídeo de onde parou, a não ser que já tenha chegado ao fim.
        limite = aula.duracao_segundos - ProgressoAula.FOLGA_SEGUNDOS
        inicio = assistidos if not concluida and assistidos < limite else 0

        return {
            'estudio': estudio,
            'aula': aula,
            'concluida': concluida,
            'segundos_assistidos': assistidos,
            'assistido_formatado': formatar_tempo(assistidos),
            'inicio': inicio,
            'tipo_video': tipo_video,
            'fonte_video': fonte_video,
            'origem': request.build_absolute_uri('/').rstrip('/'),
        }


class AulaProgressoView(AreaDoEstudioMixin, View):
    """Recebe da página da aula os segundos assistidos e responde em JSON."""

    def sem_login(self, request):
        # Quem chama é o JavaScript: redirecionar para o login não serve.
        return JsonResponse(
            {'erro': 'Entre na conta do estúdio para registrar o progresso.'},
            status=403,
        )

    def post(self, request, estudio_id, aula_id):
        estudio = self.estudio
        aula = buscar_aula(estudio, aula_id)
        segundos = ler_segundos(request.POST)

        if segundos is None:
            return JsonResponse(
                {'erro': 'Envie os segundos assistidos como número inteiro.'},
                status=400,
            )

        progresso, _ = ProgressoAula.objects.get_or_create(
            estudio=estudio, aula=aula
        )
        progresso.registrar(segundos)
        return JsonResponse({
            'segundos_assistidos': progresso.segundos_assistidos,
            'concluida': progresso.concluida,
        })


class AulaNovaView(AreaDoEstudioMixin, View):
    MINUTOS_MAXIMOS = 600

    def get(self, request, estudio_id):
        estudio = self.estudio
        contexto = {'estudio': estudio, 'dados': {}, 'erros': {}}
        return render(request, 'forum/aula_form.html', contexto)

    def post(self, request, estudio_id):
        estudio = self.estudio
        dados = {
            'titulo': request.POST.get('titulo', '').strip(),
            'descricao': request.POST.get('descricao', '').strip(),
            'url_video': request.POST.get('url_video', '').strip(),
            'minutos': request.POST.get('minutos', '').strip(),
            'segundos': request.POST.get('segundos', '').strip(),
        }
        erros = self.validar(dados)

        if erros:
            messages.error(
                request, 'Confira os campos destacados e tente novamente.'
            )
            contexto = {'estudio': estudio, 'dados': dados, 'erros': erros}
            return render(request, 'forum/aula_form.html', contexto)

        aula = Aula.objects.create(
            estudio=estudio,
            titulo=dados['titulo'],
            descricao=dados['descricao'],
            url_video=dados['url_video'],
            duracao_segundos=(int(dados['minutos'] or 0) * 60
                              + int(dados['segundos'] or 0)),
        )
        messages.success(request, f'Aula cadastrada: {aula.titulo}.')
        return redirect(reverse('forum:estudio_aulas', args=[estudio.id]))

    def validar(self, dados):
        erros = {}

        if not dados['titulo']:
            erros['titulo'] = 'Informe o título da aula.'
        elif len(dados['titulo']) > 150:
            erros['titulo'] = 'Use no máximo 150 caracteres.'

        if not dados['url_video']:
            erros['url_video'] = 'Informe o link do vídeo.'
        else:
            try:
                URLValidator(schemes=['http', 'https'])(dados['url_video'])
                url_valida = len(dados['url_video']) <= 500
            except ValidationError:
                url_valida = False
            if not url_valida or (
                Aula(url_video=dados['url_video']).video()[0] == 'link'
            ):
                erros['url_video'] = Aula.MENSAGEM_URL_VIDEO

        try:
            minutos = int(dados['minutos'] or 0)
            segundos = int(dados['segundos'] or 0)
        except ValueError:
            erros['duracao'] = 'Informe a duração com números inteiros.'
        else:
            if (not 0 <= minutos <= self.MINUTOS_MAXIMOS
                    or not 0 <= segundos <= 59):
                erros['duracao'] = (
                    f'Use de 0 a {self.MINUTOS_MAXIMOS} minutos e de 0 a 59 '
                    'segundos.'
                )
            elif minutos * 60 + segundos == 0:
                erros['duracao'] = 'Informe a duração do vídeo.'

        return erros


class AulaRemoverView(AreaDoEstudioMixin, View):
    """Remove só aulas cadastradas pelo próprio estúdio, nunca as do admin."""

    def get(self, request, estudio_id, aula_id):
        estudio = self.estudio
        aula = get_object_or_404(Aula, id=aula_id, estudio=estudio)
        contexto = {'estudio': estudio, 'aula': aula}
        return render(request, 'forum/aula_remover.html', contexto)

    def post(self, request, estudio_id, aula_id):
        estudio = self.estudio
        aula = get_object_or_404(Aula, id=aula_id, estudio=estudio)
        aula.delete()
        messages.success(request, f'Aula removida: {aula.titulo}.')
        return redirect(reverse('forum:estudio_aulas', args=[estudio.id]))
