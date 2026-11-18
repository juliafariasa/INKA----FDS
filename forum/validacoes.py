"""Validações usadas em mais de uma tela.

O projeto não usa Django Forms: cada tela lê o POST num dicionário, chama uma
destas funções e recebe um dicionário de erros por campo (vazio quando está
tudo certo). As mesmas regras valem para o estúdio, que cadastra itens só
para ele, e para a equipe, que cadastra itens para todos no painel.
"""
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email

from .models import Aula, ConteudoDescarte

MENSAGEM_LINK = 'Informe um link válido, começando com http:// ou https://.'
MINUTOS_MAXIMOS_AULA = 600


def link_valido(url, limite=500):
    """Aceita só links http ou https de até `limite` caracteres."""
    if len(url) > limite:
        return False
    try:
        URLValidator(schemes=['http', 'https'])(url)
    except ValidationError:
        return False
    return True


def texto_obrigatorio(erros, dados, campo, mensagem, limite):
    if not dados[campo]:
        erros[campo] = mensagem
    elif len(dados[campo]) > limite:
        erros[campo] = f'Use no máximo {limite} caracteres.'


def email_opcional(erros, dados, campo='email'):
    if dados[campo]:
        try:
            validate_email(dados[campo])
        except ValidationError:
            erros[campo] = 'Informe um e-mail válido.'


def site_opcional(erros, dados, campo='site', limite=200):
    if dados[campo] and not link_valido(dados[campo], limite=limite):
        erros[campo] = MENSAGEM_LINK


# Conteúdo sobre descarte

def ler_conteudo_descarte(post):
    return {
        'titulo': post.get('titulo', '').strip(),
        'formato': post.get('formato', '').strip(),
        'url': post.get('url', '').strip(),
        'descricao': post.get('descricao', '').strip(),
        'disponivel': post.get('disponivel') == 'on',
    }


def validar_conteudo_descarte(dados):
    erros = {}
    texto_obrigatorio(erros, dados, 'titulo',
                      'Informe o título do conteúdo.', 150)

    formatos = [codigo for codigo, _ in ConteudoDescarte.FORMATO_CHOICES]
    if dados['formato'] not in formatos:
        erros['formato'] = 'Escolha o formato: vídeo, podcast ou slides.'

    if not dados['url']:
        erros['url'] = 'Informe o link do conteúdo.'
    elif not link_valido(dados['url']):
        erros['url'] = MENSAGEM_LINK
    return erros


# Empresa de descarte

CAMPOS_EMPRESA = ['nome', 'cidade', 'telefone', 'email', 'site',
                  'tipos_residuo']


def ler_empresa_descarte(post):
    return {campo: post.get(campo, '').strip() for campo in CAMPOS_EMPRESA}


def validar_empresa_descarte(dados):
    erros = {}
    obrigatorios = {
        'nome': ('Informe o nome da empresa.', 150),
        'cidade': ('Informe a cidade.', 80),
        'telefone': ('Informe o telefone de contato.', 30),
        'tipos_residuo': ('Informe os tipos de resíduo que ela recolhe.',
                          200),
    }
    for campo, (mensagem, limite) in obrigatorios.items():
        texto_obrigatorio(erros, dados, campo, mensagem, limite)
    email_opcional(erros, dados)
    site_opcional(erros, dados)
    return erros


# Aula

def ler_aula(post):
    return {
        'titulo': post.get('titulo', '').strip(),
        'descricao': post.get('descricao', '').strip(),
        'url_video': post.get('url_video', '').strip(),
        'minutos': post.get('minutos', '').strip(),
        'segundos': post.get('segundos', '').strip(),
        # Opcional: sem categoria, a aula fica em inclusão (padrão do
        # modelo), como as aulas cadastradas antes das categorias.
        'categoria': post.get('categoria', '').strip(),
    }


def duracao_da_aula(dados):
    """Duração em segundos, para dados que já passaram por validar_aula."""
    return int(dados['minutos'] or 0) * 60 + int(dados['segundos'] or 0)


def validar_aula(dados):
    erros = {}
    texto_obrigatorio(erros, dados, 'titulo', 'Informe o título da aula.', 150)

    if not dados['url_video']:
        erros['url_video'] = 'Informe o link do vídeo.'
    elif not link_valido(dados['url_video']) or (
        Aula(url_video=dados['url_video']).video()[0] == 'link'
    ):
        erros['url_video'] = Aula.MENSAGEM_URL_VIDEO

    try:
        minutos = int(dados['minutos'] or 0)
        segundos = int(dados['segundos'] or 0)
    except ValueError:
        erros['duracao'] = 'Informe a duração com números inteiros.'
    else:
        if (not 0 <= minutos <= MINUTOS_MAXIMOS_AULA
                or not 0 <= segundos <= 59):
            erros['duracao'] = (
                f'Use de 0 a {MINUTOS_MAXIMOS_AULA} minutos e de 0 a 59 '
                'segundos.'
            )
        elif minutos * 60 + segundos == 0:
            erros['duracao'] = 'Informe a duração do vídeo.'

    if dados.get('categoria') and (
        dados['categoria'] not in dict(Aula.CATEGORIA_CHOICES)
    ):
        erros['categoria'] = 'Escolha uma das categorias da lista.'
    return erros


# Campanha social

def ler_campanha(post):
    return {
        'titulo': post.get('titulo', '').strip(),
        'ong': post.get('ong', '').strip(),
        'descricao': post.get('descricao', '').strip(),
        'cidade': post.get('cidade', '').strip(),
        'email': post.get('email', '').strip(),
        'site': post.get('site', '').strip(),
        'encerra_em': post.get('encerra_em', '').strip(),
        'ativa': post.get('ativa') == 'on',
    }


def validar_campanha(dados):
    erros = {}
    texto_obrigatorio(erros, dados, 'titulo',
                      'Informe o título da campanha.', 150)
    texto_obrigatorio(erros, dados, 'ong',
                      'Informe a ONG ou o projeto parceiro.', 150)
    if not dados['descricao']:
        erros['descricao'] = 'Descreva a campanha.'
    if len(dados['cidade']) > 80:
        erros['cidade'] = 'Use no máximo 80 caracteres.'
    email_opcional(erros, dados)
    site_opcional(erros, dados)
    if dados['encerra_em']:
        try:
            date.fromisoformat(dados['encerra_em'])
        except ValueError:
            erros['encerra_em'] = 'Informe uma data válida.'
    return erros


def dados_para_campanha(dados):
    """Converte os dados validados para os campos do modelo Campanha."""
    campos = dict(dados)
    campos['encerra_em'] = (date.fromisoformat(dados['encerra_em'])
                            if dados['encerra_em'] else None)
    return campos


def data_opcional(texto):
    """Converte 'AAAA-MM-DD' (o formato do <input type=date>) ou devolve None.

    Levanta ValueError se o texto não for uma data válida.
    """
    return date.fromisoformat(texto) if texto else None


# Documentos e licenças do estúdio

MENSAGEM_VALIDADE_ANTES_DA_EMISSAO = (
    'A validade não pode ser anterior à data de emissão!'
)


def ler_documento(post):
    return {
        'tipo': post.get('tipo', '').strip(),
        'descricao': post.get('descricao', '').strip(),
        'emitido_em': post.get('emitido_em', '').strip(),
        'validade': post.get('validade', '').strip(),
        'link': post.get('link', '').strip(),
    }


def validar_documento(dados):
    from .models import DocumentoEstudio

    erros = {}
    if dados['tipo'] not in dict(DocumentoEstudio.TIPO_CHOICES):
        erros['tipo'] = 'Escolha o tipo do documento.'
    if len(dados['descricao']) > 150:
        erros['descricao'] = 'Use no máximo 150 caracteres.'
    elif dados['tipo'] == DocumentoEstudio.OUTRO and not dados['descricao']:
        erros['descricao'] = 'Descreva o documento.'

    emitido_em = validade = None
    if not dados['emitido_em']:
        erros['emitido_em'] = 'Informe a data de emissão.'
    else:
        try:
            emitido_em = data_opcional(dados['emitido_em'])
        except ValueError:
            erros['emitido_em'] = 'Informe uma data válida.'
    try:
        validade = data_opcional(dados['validade'])
    except ValueError:
        erros['validade'] = 'Informe uma data válida.'
    if emitido_em and validade and validade < emitido_em:
        erros['validade'] = MENSAGEM_VALIDADE_ANTES_DA_EMISSAO

    if dados['link'] and not link_valido(dados['link']):
        erros['link'] = MENSAGEM_LINK
    return erros


def campos_do_documento(dados):
    return {
        'tipo': dados['tipo'],
        'descricao': dados['descricao'],
        'emitido_em': data_opcional(dados['emitido_em']),
        'validade': data_opcional(dados['validade']),
        'link': dados['link'],
    }


# Dados do estúdio (perfil público)

def ler_dados_do_estudio(post):
    return {
        'nome': post.get('nome', '').strip(),
        'cidade': post.get('cidade', '').strip(),
        'bairro': post.get('bairro', '').strip(),
        'descricao': post.get('descricao', '').strip(),
        # Aceita com ou sem @, e com o endereço inteiro do perfil.
        'instagram': (post.get('instagram', '').strip()
                      .removeprefix('https://').removeprefix('http://')
                      .removeprefix('www.').removeprefix('instagram.com/')
                      .strip('/').lstrip('@')),
        # Guarda só os dígitos, como o telefone das empresas de descarte.
        'whatsapp': ''.join(letra for letra in post.get('whatsapp', '')
                            if letra.isdigit()),
        'site': post.get('site', '').strip(),
        'acessibilidade': post.get('acessibilidade', '').strip(),
    }


def validar_dados_do_estudio(dados):
    erros = {}
    if not dados['nome']:
        erros['nome'] = 'Informe o nome do estúdio.'
    elif len(dados['nome']) < 3:
        erros['nome'] = 'O nome deve ter pelo menos 3 caracteres.'
    elif len(dados['nome']) > 120:
        erros['nome'] = 'Use no máximo 120 caracteres.'
    texto_obrigatorio(erros, dados, 'cidade',
                      'Informe a cidade do estúdio.', 80)

    for campo, limite in (('bairro', 80), ('descricao', 300),
                          ('acessibilidade', 200)):
        if len(dados[campo]) > limite:
            erros[campo] = f'Use no máximo {limite} caracteres.'

    instagram = dados['instagram']
    if instagram and (len(instagram) > 30 or not all(
        letra.isascii() and (letra.isalnum() or letra in '._')
        for letra in instagram
    )):
        erros['instagram'] = (
            'Informe só o nome de usuário do Instagram: letras, números, '
            'ponto ou sublinhado.'
        )
    if dados['whatsapp'] and len(dados['whatsapp']) not in (10, 11):
        erros['whatsapp'] = (
            'Informe o WhatsApp com DDD: 10 ou 11 números.'
        )
    site_opcional(erros, dados)
    return erros


# Campos de alerta do estoque

def ler_alertas_do_estoque(post):
    return {
        'quantidade_minima': post.get('quantidade_minima', '').strip(),
        'validade': post.get('validade', '').strip(),
        'origem_sustentavel': post.get('origem_sustentavel') == 'on',
    }


def validar_alertas_do_estoque(dados, maximo):
    """Os três campos são opcionais: vazio vale 0, sem validade e não."""
    erros = {}
    if dados['quantidade_minima']:
        if not dados['quantidade_minima'].isdecimal():
            erros['quantidade_minima'] = 'Informe um número inteiro.'
        elif int(dados['quantidade_minima']) > maximo:
            erros['quantidade_minima'] = f'Use no máximo {maximo}.'
    try:
        data_opcional(dados['validade'])
    except ValueError:
        erros['validade'] = 'Informe uma data válida.'
    return erros


def campos_de_alerta_do_estoque(dados):
    return {
        'quantidade_minima': int(dados['quantidade_minima'] or 0),
        'validade': data_opcional(dados['validade']),
        'origem_sustentavel': dados['origem_sustentavel'],
    }
