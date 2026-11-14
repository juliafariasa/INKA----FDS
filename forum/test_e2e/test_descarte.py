from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from forum.models import ConteudoDescarte, EmpresaDescarte
from .base import BaseE2E

MSG_INDISPONIVEL = (
    'Este conteúdo está indisponível no momento. '
    'Tente outro conteúdo da lista!'
)
VIDEO_OK = 'Separação de perfurocortantes'
VIDEO_FORA_DO_AR = 'Como descartar agulhas corretamente'


class DescarteTest(BaseE2E):
    """História 5 - Conteúdo sobre descarte de resíduos."""

    def setUp(self):
        super().setUp()
        # DADO que existem conteúdos cadastrados na plataforma
        ConteudoDescarte.objects.create(
            titulo=VIDEO_OK, formato=ConteudoDescarte.VIDEO,
            url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            descricao='Como separar agulhas e lâminas usadas.',
        )
        # E o vídeo "Como descartar agulhas corretamente" está fora do ar
        ConteudoDescarte.objects.create(
            titulo=VIDEO_FORA_DO_AR, formato=ConteudoDescarte.VIDEO,
            url='https://www.youtube.com/watch?v=aaaaaaaaaaa',
            disponivel=False,
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

    def ir_para_o_descarte(self):
        self.abrir_menu()
        self.clicar(By.XPATH, '//nav//a[normalize-space()="Descarte"]')
        self.esperar_titulo('Descarte de resíduos')

    def esperar_titulo(self, texto):
        self.espera.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, 'h2'), texto
        ))

    def lista_do_formato(self, formato):
        return self.navegador.find_element(
            By.XPATH,
            f'//h4[normalize-space()="{formato}"]/following-sibling::ul[1]',
        )

    def test_descarte_listar_abrir_e_conteudo_indisponivel(self):
        # DADO que estou logado
        self.entrar()
        self.narrar('US 5: conteúdo sobre descarte de resíduos')

        # CENÁRIO 1 - QUANDO acesso a área de descarte
        self.ir_para_o_descarte()

        # ENTÃO a plataforma lista os conteúdos por formato
        esperado = {
            'Vídeos': VIDEO_OK,
            'Podcasts': 'Papo sobre lixo hospitalar',
            'Slides': 'Guia de descarte do estúdio',
        }
        for formato, titulo in esperado.items():
            lista = self.lista_do_formato(formato)
            self.assertTrue(lista.find_elements(By.LINK_TEXT, titulo),
                            f'"{titulo}" não está em {formato}')
        self.narrar('Os conteúdos aparecem por formato')

        # E exibe as empresas de descarte com seus contatos
        empresa = self.espera.until(EC.visibility_of_element_located(
            (By.XPATH, '//table//tr[td[normalize-space()="Coleta Segura"]]')
        ))
        self.navegador.execute_script(
            'arguments[0].scrollIntoView({block: "center"});', empresa
        )
        self.assertTrue(empresa.find_elements(
            By.CSS_SELECTOR, 'a[href="tel:81999990000"]'))
        self.assertTrue(empresa.find_elements(
            By.CSS_SELECTOR, 'a[href="mailto:contato@coletasegura.com.br"]'))
        self.narrar('As empresas aparecem com telefone e e-mail')

        # E o conteúdo pode ser aberto
        self.navegador.execute_script('window.scrollTo(0, 0);')
        self.pausar()
        self.lista_do_formato('Vídeos').find_element(
            By.LINK_TEXT, VIDEO_OK).click()
        self.esperar_titulo(VIDEO_OK)
        player = self.espera.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '.player iframe')
        ))
        self.assertIn('youtube.com/embed/dQw4w9WgXcQ',
                      player.get_attribute('src'))
        self.narrar('Ao abrir o vídeo, o player aparece')

        # CENÁRIO 2 - conteúdo com link indisponível
        self.clicar(By.LINK_TEXT, 'Voltar aos conteúdos sobre descarte')
        self.esperar_titulo('Descarte de resíduos')
        item = self.navegador.find_element(
            By.XPATH, f'//li[a[normalize-space()="{VIDEO_FORA_DO_AR}"]]'
        )
        self.assertIn('(indisponível no momento)', item.text)
        self.narrar('Este vídeo está com o link fora do ar')

        # QUANDO tento abrir esse vídeo
        self.clicar(By.LINK_TEXT, VIDEO_FORA_DO_AR)

        # ENTÃO aparece a mensagem de conteúdo indisponível
        self.esperar_mensagem(MSG_INDISPONIVEL, tipo='error')

        # E o vídeo não é reproduzido
        self.assertFalse(self.navegador.find_elements(
            By.CSS_SELECTOR, 'iframe, video, audio'))
        self.assertFalse(self.navegador.find_elements(
            By.PARTIAL_LINK_TEXT, 'Abrir'))
        self.narrar('Teste da US 5 finalizado!')