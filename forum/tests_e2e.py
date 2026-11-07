"""Testes E2E (Selenium) das histórias 3, 5 e 6.

Rodar só estes testes:      python manage.py test forum.tests_e2e
Rodar sem abrir a janela:   HEADLESS=1 python manage.py test forum.tests_e2e
Rodar só os unitários:      python manage.py test --exclude-tag e2e

O passo a passo do screencast está em screencast/README.md.
"""

import os
import unittest
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag
from django.urls import reverse

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait
except ImportError:  # pragma: no cover
    # Sem o Selenium instalado, a suíte unitária continua rodando normalmente.
    raise unittest.SkipTest(
        'Selenium não instalado: pip install -r requirements-dev.txt'
    )

from .e2e_narrador import narrar
from .models import (
    Aula,
    ConteudoDescarte,
    EmpresaDescarte,
    Estudio,
    ItemEstoque,
    ProgressoAula,
)

PASTA_ARQUIVOS_E2E = Path(__file__).resolve().parent / 'e2e_arquivos'
ESPERA_SEGUNDOS = int(os.environ.get('E2E_ESPERA', '10'))

MSG_DUPLICADO = (
    'Este material já está no seu estoque. '
    'Edite a quantidade do item existente!'
)
MSG_INDISPONIVEL = (
    'Este conteúdo está indisponível no momento. '
    'Tente outro conteúdo da lista!'
)
MSG_AULA_INCOMPLETA = 'Assista à aula até o final para concluí-la!'


def criar_navegador():
    opcoes = webdriver.ChromeOptions()
    if os.environ.get('HEADLESS', '').strip() == '1':
        opcoes.add_argument('--headless=new')
    opcoes.add_argument('--window-size=1366,900')
    opcoes.add_argument('--lang=pt-BR')
    # Deixa o vídeo da aula tocar sozinho, sem precisar de clique do usuário.
    opcoes.add_argument('--autoplay-policy=no-user-gesture-required')
    if os.environ.get('CHROME_BIN'):
        opcoes.binary_location = os.environ['CHROME_BIN']
    if os.environ.get('E2E_SEM_SANDBOX', '').strip() == '1':
        opcoes.add_argument('--no-sandbox')
    # O Selenium Manager acha o driver sozinho; CHROMEDRIVER força um caminho.
    servico = webdriver.ChromeService(
        executable_path=os.environ.get('CHROMEDRIVER') or None
    )
    navegador = webdriver.Chrome(options=opcoes, service=servico)
    navegador.set_page_load_timeout(30)
    return navegador


@tag('e2e')
@override_settings(
    # O hash de senha padrão é lento de propósito; nos testes não precisa.
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    # Vídeo curto de teste usado na aula, servido só durante os testes.
    STATICFILES_DIRS=[PASTA_ARQUIVOS_E2E],
)
class BaseE2E(StaticLiveServerTestCase):
    EMAIL = 'dono@tintaverde.com.br'
    SENHA = 'SenhaForte!2026'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.navegador = criar_navegador()
        cls.espera = WebDriverWait(cls.navegador, ESPERA_SEGUNDOS)

    @classmethod
    def tearDownClass(cls):
        cls.navegador.quit()
        super().tearDownClass()

    def setUp(self):
        # O LiveServerTestCase apaga o banco a cada teste (inclusive os dados
        # das migrations), então cada teste cria o que precisa.
        usuario = get_user_model().objects.create_user(
            username=self.EMAIL, email=self.EMAIL, password=self.SENHA
        )
        self.estudio = Estudio.objects.create(
            nome='Tinta Verde', cidade='Recife', usuario=usuario
        )
        # Cada teste começa deslogado.
        self.navegador.delete_all_cookies()

    # ----- ações -----

    def narrar(self, texto):
        narrar(self.navegador, texto)

    def abrir(self, nome_url, *args):
        self.navegador.get(self.live_server_url + reverse(nome_url, args=args))

    def entrar(self):
        self.abrir('forum:entrar')
        self.narrar('Entrando na área do estúdio Tinta Verde.')
        self.digitar(By.ID, 'email', self.EMAIL)
        self.digitar(By.ID, 'senha', self.SENHA)
        self.clicar(By.CSS_SELECTOR, 'input[name="entrar"]')
        # Depois do login o site leva ao perfil do estúdio.
        self.espera.until(EC.url_contains(
            reverse('forum:estudio_perfil', args=[self.estudio.id])
        ))
        self.espera.until(EC.presence_of_element_located(
            (By.XPATH, '//nav//button[normalize-space()="Sair"]')
        ))
        self.conferir_estaticos()

    def conferir_estaticos(self):
        """Garante que o estilo.css foi servido e aplicado pelo navegador."""
        regras = self.navegador.execute_script(
            "var f = [...document.styleSheets].find("
            "  s => (s.href || '').includes('/static/css/estilo.css'));"
            "return f ? f.cssRules.length : 0;"
        )
        self.assertGreater(regras, 0, 'O estilo.css não foi carregado.')

    def clicar(self, by, valor):
        elemento = self.espera.until(EC.element_to_be_clickable((by, valor)))
        elemento.click()
        return elemento

    def clicar_link(self, texto):
        return self.clicar(By.LINK_TEXT, texto)

    def digitar(self, by, valor, texto):
        campo = self.espera.until(EC.visibility_of_element_located((by, valor)))
        campo.clear()
        campo.send_keys(texto)
        return campo

    # ----- verificações -----

    def esperar_mensagem(self, texto, tipo='success'):
        """Espera o aviso do Django (p.aviso-success ou p.aviso-error).

        Os avisos de sucesso somem depois de 5 segundos (script.js), por isso
        a mensagem é conferida logo depois da ação, antes de narrar.
        """
        seletor = (By.CSS_SELECTOR, f'p.aviso.aviso-{tipo}')
        try:
            self.espera.until(EC.text_to_be_present_in_element(seletor, texto))
        except TimeoutException:
            avisos = [a.text for a in self.navegador.find_elements(
                By.CSS_SELECTOR, 'p.aviso')]
            self.fail(f'Mensagem "{texto}" não apareceu. Avisos: {avisos}')

    def linha_da_tabela(self, texto):
        return self.espera.until(EC.visibility_of_element_located(
            (By.XPATH, f'//table//tr[td[normalize-space()="{texto}"]]')
        ))

    def celulas(self, linha):
        return [td.text for td in linha.find_elements(By.TAG_NAME, 'td')]


class EstoqueE2ETest(BaseE2E):
    """História 3 - Gerenciamento de estoque e equipamentos."""

    def ir_para_o_estoque(self):
        self.entrar()
        self.narrar('No perfil do estúdio, abro o estoque.')
        self.clicar_link('Estoque')
        self.espera.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, 'h2'), 'Estoque de Tinta Verde'
        ))

    def preencher_item(self, nome, tipo, quantidade, fornecedor):
        self.digitar(By.ID, 'nome', nome)
        Select(self.navegador.find_element(By.ID, 'tipo')).select_by_value(tipo)
        self.digitar(By.ID, 'quantidade', str(quantidade))
        self.digitar(By.ID, 'fornecedor', fornecedor)

    def test_cenario1_cadastrar_editar_e_remover_material(self):
        self.narrar('História 3, cenário 1: cadastrar um material no estoque '
                    'e depois editar e remover.')
        self.ir_para_o_estoque()

        # Cadastrar
        self.clicar_link('Cadastrar item')
        self.narrar('Cadastro o material Copinho de tinta, com quantidade '
                    '50, do fornecedor EcoTattoo.')
        self.preencher_item('Copinho de tinta', 'material', 50, 'EcoTattoo')
        self.clicar(By.CSS_SELECTOR, 'input[name="salvar"]')

        self.esperar_mensagem('Copinho de tinta entrou no estoque.')
        linha = self.linha_da_tabela('Copinho de tinta')
        self.assertEqual(
            self.celulas(linha)[:4],
            ['Copinho de tinta', 'Material', '50', 'EcoTattoo'],
        )
        self.narrar('O material entrou no estoque com quantidade e fornecedor.')

        # Editar
        linha.find_element(By.LINK_TEXT, 'Editar').click()
        self.espera.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, 'h2'), 'Editar Copinho de tinta'
        ))
        self.narrar('Agora edito o item e mudo a quantidade para 80.')
        self.digitar(By.ID, 'quantidade', '80')
        self.clicar(By.CSS_SELECTOR, 'input[name="salvar"]')

        self.esperar_mensagem('Copinho de tinta atualizado no estoque.')
        linha = self.linha_da_tabela('Copinho de tinta')
        self.assertEqual(self.celulas(linha)[2], '80')
        self.assertEqual(ItemEstoque.objects.get().quantidade, 80)
        self.narrar('A quantidade foi atualizada para 80.')

        # Remover
        linha.find_element(By.LINK_TEXT, 'Remover').click()
        self.espera.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, 'h2'), 'Remover item do estoque'
        ))
        self.narrar('Por fim, removo o item e confirmo.')
        self.clicar(By.CSS_SELECTOR, 'input[name="remover"]')

        self.esperar_mensagem('Copinho de tinta saiu do estoque.')
        self.assertFalse(self.navegador.find_elements(
            By.XPATH, '//td[normalize-space()="Copinho de tinta"]'
        ))
        self.assertFalse(ItemEstoque.objects.exists())
        self.narrar('O item saiu do estoque. Cenário 1 aprovado.')

    def test_cenario2_material_ja_cadastrado_nao_e_duplicado(self):
        ItemEstoque.objects.create(
            estudio=self.estudio, nome='Copinho de tinta',
            tipo=ItemEstoque.MATERIAL, quantidade=50, fornecedor='EcoTattoo',
        )
        self.narrar('História 3, cenário 2: o estoque do Tinta Verde já tem '
                    'o Copinho de tinta da EcoTattoo.')
        self.ir_para_o_estoque()
        self.linha_da_tabela('Copinho de tinta')

        self.clicar_link('Cadastrar item')
        self.narrar('Tento cadastrar o mesmo material, do mesmo fornecedor.')
        self.preencher_item('Copinho de tinta', 'material', 30, 'EcoTattoo')
        self.clicar(By.CSS_SELECTOR, 'input[name="salvar"]')

        self.esperar_mensagem(MSG_DUPLICADO, tipo='error')
        self.assertEqual(ItemEstoque.objects.count(), 1)
        self.assertEqual(ItemEstoque.objects.get().quantidade, 50)
        self.narrar('A plataforma avisa que o material já está no estoque '
                    'e nenhum item novo é criado.')

        self.clicar_link('Voltar ao estoque')
        self.linha_da_tabela('Copinho de tinta')
        self.assertEqual(len(self.navegador.find_elements(
            By.XPATH, '//td[normalize-space()="Copinho de tinta"]'
        )), 1)
        self.narrar('O estoque continua com um único Copinho de tinta. '
                    'Cenário 2 aprovado.')


class DescarteE2ETest(BaseE2E):
    """História 5 - Conteúdo sobre descarte de resíduos."""

    def lista_do_formato(self, titulo_formato):
        return self.navegador.find_element(
            By.XPATH,
            f'//h4[normalize-space()="{titulo_formato}"]'
            '/following-sibling::ul[1]',
        )

    def ir_para_o_descarte(self):
        self.entrar()
        self.narrar('Pelo menu, abro a área de descarte.')
        self.clicar(By.XPATH, '//nav//a[normalize-space()="Descarte"]')
        self.espera.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, 'h2'), 'Descarte de resíduos'
        ))

    def test_cenario1_lista_conteudos_por_formato_e_empresas(self):
        ConteudoDescarte.objects.create(
            titulo='Separação de perfurocortantes',
            formato=ConteudoDescarte.VIDEO,
            url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        )
        ConteudoDescarte.objects.create(
            titulo='Papo sobre lixo hospitalar',
            formato=ConteudoDescarte.PODCAST,
            url='https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk',
        )
        ConteudoDescarte.objects.create(
            titulo='Guia de descarte do estúdio',
            formato=ConteudoDescarte.SLIDES,
            url='https://example.com/guia-descarte.pdf',
        )
        EmpresaDescarte.objects.create(
            nome='Coleta Segura', cidade='Recife',
            telefone='(81) 99999-0000', email='contato@coletasegura.com.br',
            tipos_residuo='perfurocortante, contaminado',
        )

        self.narrar('História 5, cenário 1: acessar os conteúdos sobre '
                    'descarte de resíduos.')
        self.ir_para_o_descarte()

        esperado = {
            'Vídeos': 'Separação de perfurocortantes',
            'Podcasts': 'Papo sobre lixo hospitalar',
            'Slides': 'Guia de descarte do estúdio',
        }
        for formato, titulo in esperado.items():
            lista = self.lista_do_formato(formato)
            self.assertTrue(lista.find_elements(By.LINK_TEXT, titulo),
                            f'{titulo} não está em {formato}')
        self.narrar('Os conteúdos aparecem separados por formato: vídeos, '
                    'podcasts e slides.')

        linha = self.linha_da_tabela('Coleta Segura')
        self.assertTrue(linha.find_elements(
            By.CSS_SELECTOR, 'a[href="tel:81999990000"]'))
        self.assertTrue(linha.find_elements(
            By.CSS_SELECTOR, 'a[href="mailto:contato@coletasegura.com.br"]'))
        self.narrar('E as empresas de descarte aparecem com telefone e e-mail.')

        self.lista_do_formato('Vídeos').find_element(
            By.LINK_TEXT, 'Separação de perfurocortantes').click()
        player = self.espera.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '.player iframe')
        ))
        self.assertIn('youtube.com/embed/dQw4w9WgXcQ',
                      player.get_attribute('src'))
        self.narrar('Ao abrir o vídeo, o player é exibido. Cenário 1 aprovado.')

    def test_cenario2_conteudo_com_link_indisponivel(self):
        ConteudoDescarte.objects.create(
            titulo='Como descartar agulhas corretamente',
            formato=ConteudoDescarte.VIDEO,
            url='https://www.youtube.com/watch?v=xxxxxxxxxxx',
            disponivel=False,
        )
        ConteudoDescarte.objects.create(
            titulo='Separação de perfurocortantes',
            formato=ConteudoDescarte.VIDEO,
            url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        )

        self.narrar('História 5, cenário 2: o vídeo Como descartar agulhas '
                    'corretamente está com o link fora do ar.')
        self.ir_para_o_descarte()

        item = self.navegador.find_element(
            By.XPATH,
            '//li[a[normalize-space()="Como descartar agulhas corretamente"]]',
        )
        self.assertIn('(indisponível no momento)', item.text)
        self.narrar('Tento abrir esse vídeo.')
        item.find_element(By.TAG_NAME, 'a').click()

        self.esperar_mensagem(MSG_INDISPONIVEL, tipo='error')
        self.assertFalse(self.navegador.find_elements(
            By.CSS_SELECTOR, 'iframe, video, audio'))
        self.assertFalse(self.navegador.find_elements(
            By.PARTIAL_LINK_TEXT, 'Abrir'))
        self.narrar('O vídeo não é reproduzido e a plataforma pede para '
                    'tentar outro conteúdo. Cenário 2 aprovado.')


class AulasE2ETest(BaseE2E):
    """História 6 - Aulas de inclusão e acessibilidade."""

    def ir_para_as_aulas(self):
        self.entrar()
        self.narrar('No perfil do estúdio, abro as aulas de inclusão.')
        self.clicar_link('Aulas de inclusão')
        self.espera.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, 'h2'), 'Aulas de inclusão e acessibilidade'
        ))

    def linha_da_aula(self, titulo):
        return self.espera.until(EC.visibility_of_element_located(
            (By.XPATH, f'//table//tr[td/a[normalize-space()="{titulo}"]]')
        ))

    def test_cenario1_lista_as_aulas_e_assiste_a_escolhida(self):
        # Vídeo de 12 segundos em e2e_arquivos/video, servido pelo servidor
        # de testes. Assim o teste assiste a aula de verdade, sem internet.
        aula = Aula.objects.create(
            titulo='Libras básica para o atendimento',
            url_video=f'{self.live_server_url}/static/video/aula-teste.webm',
            duracao_segundos=12, ordem=1,
        )
        Aula.objects.create(
            titulo='Acolhimento de pessoas LGBTQIA+',
            url_video='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            duracao_segundos=900, ordem=2,
        )

        self.narrar('História 6, cenário 1: assistir uma aula de inclusão '
                    'e acessibilidade.')
        self.ir_para_as_aulas()

        for titulo in ('Libras básica para o atendimento',
                       'Acolhimento de pessoas LGBTQIA+'):
            self.assertIn('Não iniciada', self.linha_da_aula(titulo).text)
        self.narrar('A plataforma lista as aulas disponíveis. Escolho a aula '
                    'de Libras.')

        self.clicar_link('Libras básica para o atendimento')
        video = self.espera.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'video#aula-video')
        ))
        self.narrar('O vídeo da aula abre na própria página. Dou o play e '
                    'assisto até o final.')
        self.navegador.execute_script(
            'arguments[0].muted = true; arguments[0].play();', video
        )

        # O aula.js mede o trecho assistido e atualiza o campo escondido.
        WebDriverWait(self.navegador, 30).until(
            lambda d: d.execute_script('return arguments[0].ended;', video)
        )
        WebDriverWait(self.navegador, 5).until(
            lambda d: int(d.find_element(By.ID, 'campo-segundos')
                          .get_attribute('value')) >= 7
        )
        self.narrar('Terminei de assistir. Agora marco a aula como concluída.')
        self.clicar(By.CSS_SELECTOR, 'input[name="concluir"]')

        self.esperar_mensagem(
            'Aula concluída: Libras básica para o atendimento.')
        self.assertIn('Concluída',
                      self.linha_da_aula('Libras básica para o atendimento')
                      .text)
        self.assertTrue(ProgressoAula.objects.get(aula=aula).concluida)
        self.narrar('A aula aparece como concluída na lista. '
                    'Cenário 1 aprovado.')

    def test_cenario2_nao_conclui_aula_sem_assistir_ate_o_final(self):
        aula = Aula.objects.create(
            titulo='Acolhimento de pessoas LGBTQIA+',
            url_video='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            duracao_segundos=15 * 60,
        )
        # O tatuador já assistiu 10 dos 15 minutos.
        ProgressoAula.objects.create(
            estudio=self.estudio, aula=aula, segundos_assistidos=10 * 60
        )

        self.narrar('História 6, cenário 2: o tatuador assistiu só 10 dos 15 '
                    'minutos da aula Acolhimento de pessoas LGBTQIA+.')
        self.ir_para_as_aulas()
        self.assertIn('Assistida até 10:00',
                      self.linha_da_aula(aula.titulo).text)

        self.clicar_link(aula.titulo)
        self.espera.until(EC.text_to_be_present_in_element(
            (By.ID, 'texto-assistido'), '10:00'
        ))
        self.narrar('Ele clica em Marcar como concluída.')
        self.clicar(By.CSS_SELECTOR, 'input[name="concluir"]')

        self.esperar_mensagem(MSG_AULA_INCOMPLETA, tipo='error')
        self.assertTrue(self.navegador.find_elements(By.ID, 'form-concluir'))
        self.assertFalse(ProgressoAula.objects.get(aula=aula).concluida)
        self.narrar('A aula não é marcada como concluída e a plataforma pede '
                    'para assistir até o final. Cenário 2 aprovado.')
