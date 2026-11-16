"""Redefinição de senha por código enviado ao e-mail ("esqueci minha senha").

O fluxo tem três passos, um para cada função pública deste módulo:

1. pedir_codigo: gera um código de 6 dígitos e envia por e-mail.
2. conferir_codigo: confere o código e devolve um token de uso único.
3. redefinir_senha: com o token, grava a senha nova.

Nem o código, nem o token, nem a senha aparecem em logs ou ficam no banco em
texto puro.
"""
import hashlib
import hmac
import logging
import secrets
import threading
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F, Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import PasswordResetCode, PasswordResetToken

logger = logging.getLogger(__name__)

VALIDADE_CODIGO = timedelta(minutes=10)
VALIDADE_TOKEN = timedelta(minutes=15)

# Política de limite de pedidos: (máximo de pedidos, janela em segundos).
# O limite por e-mail vale para o texto digitado, exista a conta ou não, para
# a resposta não revelar quais e-mails têm conta.
JANELA = 15 * 60
LIMITES = {
    'request': {'email': (3, JANELA), 'ip': (10, JANELA)},
    'verify': {'email': (10, JANELA), 'ip': (20, JANELA)},
}


class TokenInvalido(Exception):
    """O reset_token não existe, já foi usado ou expirou."""


class SenhaRecusada(Exception):
    """A senha nova não passou nos validadores. Guarda as mensagens."""

    def __init__(self, mensagens):
        super().__init__(' '.join(mensagens))
        self.mensagens = mensagens


def buscar_conta(email):
    """Acha a conta pelo e-mail digitado.

    Nas contas de estúdio o nome de usuário é o próprio e-mail. Contas
    criadas no admin podem ter outro nome de usuário; para elas vale o
    campo e-mail.
    """
    contas = get_user_model().objects
    return (contas.filter(username__iexact=email).first()
            or contas.filter(email__iexact=email).order_by('pk').first())


def ip_do_pedido(request):
    """IP de quem fez o pedido.

    Atrás do proxy do Render, REMOTE_ADDR é o proxy; o IP do visitante vem no
    cabeçalho X-Forwarded-For.
    """
    if getattr(settings, 'IP_VEM_DO_PROXY', False):
        encaminhado = request.META.get('HTTP_X_FORWARDED_FOR', '')
        primeiro = encaminhado.split(',')[0].strip()
        if primeiro:
            return primeiro
    return request.META.get('REMOTE_ADDR') or None


def limite_excedido(etapa, email, ip):
    """Conta este pedido e diz se passou do limite por e-mail ou por IP."""
    excedeu = False
    for tipo, valor in (('email', email), ('ip', ip)):
        if not valor:
            continue
        maximo, janela = LIMITES[etapa][tipo]
        resumo = hashlib.sha256(valor.encode()).hexdigest()
        chave = f'redefinir-senha:{etapa}:{tipo}:{resumo}'
        # add e incr são atômicos: pedidos em paralelo também são contados.
        cache.add(chave, 0, janela)
        if cache.incr(chave) > maximo:
            excedeu = True
    return excedeu


def gerar_hash(finalidade, valor):
    """HMAC-SHA256 com a SECRET_KEY.

    Um código de 6 dígitos só tem um milhão de combinações: com um SHA-256
    simples, quem copiasse o banco testaria todas em segundos. Com o HMAC é
    preciso ter também a chave do servidor.
    """
    return salted_hmac(
        f'forum.redefinicao_senha.{finalidade}', valor, algorithm='sha256'
    ).hexdigest()


def hash_do_codigo(conta, codigo):
    # O id da conta entra no hash: o mesmo código em contas diferentes gera
    # hashes diferentes.
    return gerar_hash('codigo', f'{conta.pk}:{codigo}')


def em_segundo_plano(funcao):
    """Roda a função numa thread, para a resposta não esperar o e-mail.

    Assim o tempo de resposta é parecido para e-mail com e sem conta.
    """
    threading.Thread(target=funcao, daemon=True).start()


def enviar_email(assunto, modelo, contexto, destinatario):
    """Monta o e-mail (texto + HTML) e envia em segundo plano."""
    mensagem = EmailMultiAlternatives(
        subject=assunto,
        body=render_to_string(f'forum/emails/{modelo}.txt', contexto),
        to=[destinatario],
    )
    mensagem.attach_alternative(
        render_to_string(f'forum/emails/{modelo}.html', contexto), 'text/html'
    )

    def enviar():
        try:
            mensagem.send()
        except Exception as erro:
            # Só o tipo do erro vai para o log, nunca o conteúdo do e-mail.
            logger.error('Falha ao enviar e-mail de redefinição de senha (%s).',
                         type(erro).__name__)

    em_segundo_plano(enviar)


def pedir_codigo(email, ip=None):
    """Passo 1: gera e envia o código, se o e-mail for de uma conta ativa.

    Não devolve nada: quem chama responde igual nos dois casos.
    """
    conta = buscar_conta(email)
    if conta is None or not conta.is_active or not conta.email:
        return

    agora = timezone.now()
    codigo = f'{secrets.randbelow(10 ** 6):06d}'
    with transaction.atomic():
        # Um pedido novo invalida os códigos e tokens anteriores da conta.
        PasswordResetCode.objects.filter(
            user=conta, used_at__isnull=True, expires_at__gt=agora
        ).update(expires_at=agora)
        PasswordResetToken.objects.filter(
            user=conta, used_at__isnull=True
        ).delete()
        PasswordResetCode.objects.create(
            user=conta,
            code_hash=hash_do_codigo(conta, codigo),
            expires_at=agora + VALIDADE_CODIGO,
            ip=ip,
        )

    enviar_email(
        'Seu código para redefinir a senha do INKA',
        'codigo_redefinicao',
        {'codigo': codigo,
         'validade_minutos': int(VALIDADE_CODIGO.total_seconds() // 60)},
        conta.email,
    )


def conferir_codigo(email, codigo):
    """Passo 2: devolve um reset_token se o código estiver certo, ou None."""
    conta = buscar_conta(email)
    if conta is None:
        return None

    agora = timezone.now()
    with transaction.atomic():
        registro = PasswordResetCode.objects.select_for_update().filter(
            user=conta,
            used_at__isnull=True,
            expires_at__gt=agora,
            attempts__lt=PasswordResetCode.TENTATIVAS_MAXIMAS,
        ).first()
        if registro is None:
            return None

        # A tentativa é contada antes da comparação. Na quinta tentativa
        # errada o código deixa de passar no filtro acima: está invalidado.
        PasswordResetCode.objects.filter(pk=registro.pk).update(
            attempts=F('attempts') + 1
        )
        # compare_digest leva o mesmo tempo acerte ou erre, e não dá pistas
        # sobre quantos caracteres estão certos.
        if not hmac.compare_digest(registro.code_hash,
                                   hash_do_codigo(conta, codigo)):
            return None

        PasswordResetCode.objects.filter(pk=registro.pk).update(used_at=agora)
        token = secrets.token_urlsafe(32)
        PasswordResetToken.objects.create(
            user=conta,
            token_hash=gerar_hash('token', token),
            expires_at=agora + VALIDADE_TOKEN,
        )
    return token


def redefinir_senha(token, nova_senha):
    """Passo 3: troca a senha da conta dona do token e devolve a conta.

    Levanta TokenInvalido ou SenhaRecusada. Uma senha recusada não gasta o
    token: a pessoa pode tentar outra senha.
    """
    agora = timezone.now()
    registro = PasswordResetToken.objects.select_related('user').filter(
        token_hash=gerar_hash('token', token),
        used_at__isnull=True,
        expires_at__gt=agora,
    ).first()
    if registro is None:
        raise TokenInvalido()

    conta = registro.user
    try:
        validate_password(nova_senha, user=conta)
    except ValidationError as erro:
        raise SenhaRecusada(erro.messages)
    if conta.check_password(nova_senha):
        raise SenhaRecusada(['A nova senha precisa ser diferente da atual.'])

    with transaction.atomic():
        # O UPDATE condicional garante o uso único: se dois pedidos chegarem
        # juntos com o mesmo token, só um deles altera a linha.
        usados = PasswordResetToken.objects.filter(
            pk=registro.pk, used_at__isnull=True
        ).update(used_at=agora)
        if usados != 1:
            raise TokenInvalido()

        # set_password grava só o hash (PBKDF2 com sal). Como o cookie de
        # sessão é conferido contra esse hash, todas as sessões abertas da
        # conta deixam de valer.
        conta.set_password(nova_senha)
        conta.save()
        PasswordResetCode.objects.filter(
            user=conta, used_at__isnull=True, expires_at__gt=agora
        ).update(expires_at=agora)

    enviar_email(
        'A senha da sua conta no INKA foi alterada',
        'senha_alterada',
        {'data_hora': timezone.localtime(agora)},
        conta.email,
    )
    return conta


def limpar_expirados():
    """Apaga códigos e tokens vencidos ou já usados. Devolve quantos."""
    vencido = Q(expires_at__lte=timezone.now()) | Q(used_at__isnull=False)
    codigos, _ = PasswordResetCode.objects.filter(vencido).delete()
    tokens, _ = PasswordResetToken.objects.filter(vencido).delete()
    return codigos, tokens
