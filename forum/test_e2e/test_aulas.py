from pathlib import Path

from django.test import override_settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from forum.models import Aula, ProgressoAula
from .base import BaseE2E

MSG_INCOMPLETA = 'Assista à aula até o final para concluí-la!'
AULA_CURTA = 'Libras básica para o atendimento'
AULA_LGBT = 'Acolhimento de pessoas LGBTQIA+'

# Pasta com o vídeo de teste (arquivos/video/aula-teste.webm, 12 segundos).
# Ela só é servida durante os testes, não vai para o site de verdade.
PASTA_ARQUIVOS = Path(__file__).resolve().parent / 'arquivos'


@override_settings(STATICFILES_DIRS=[PASTA_ARQUIVOS])
class AulasTest(BaseE2E):
    """História 6 - Aulas de inclusão e acessibilidade.

    Um teste só, na ordem: ver a lista de aulas, assistir uma aula até o fim
    e concluí-la (cenário 1), e tentar concluir uma aula assistida só até os
    10 de 15 minutos (cenário 2).
    """

    def setUp(self):
        super().setUp()
        # DADO que existem aulas cadastradas
        self.aula_curta = Aula.objects.create(
            titulo=AULA_CURTA, ordem=1, duracao_segundos=12,
            url_video=f'{self.live_server_url}/static/video/aula-teste.webm',
            descricao='Aula curta usada para assistir até o final.',
        )
        self.aula_lgbt = Aula.objects.create(
            titulo=AULA_LGBT, ordem=2, duracao_segundos=15 * 60,
            url_video='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        )
        # E o tatuador assistiu apenas 10 dos 15 minutos dessa aula
        ProgressoAula.objects.create(
            estudio=self.estudio, aula=self.aula_lgbt,
            segundos_assistidos=10 * 60,
        )

    def ir_para_as_aulas(self):
        self.clicar(By.LINK_TEXT, 'Aulas de inclusão')
        self.esperar_titulo('Aulas de inclusão e acessibilidade')

    def esperar_titulo(self, texto):
        self.espera.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, 'h2'), texto
        ))

    def linha_da_aula(self, titulo):
        return self.espera.until(EC.visibility_of_element_located(
            (By.XPATH, f'//table//tr[td/a[normalize-space()="{titulo}"]]')
        ))

    def test_aulas_listar_assistir_e_concluir_sem_assistir(self):
        # DADO que estou logado
        self.entrar()
        self.narrar('US 6: aulas de inclusão e acessibilidade')

        # 1) ASSISTIR UMA AULA (cenário 1)
        # QUANDO acesso a área de aulas sociais
        self.ir_para_as_aulas()

        # ENTÃO a plataforma lista as aulas disponíveis
        self.assertIn('Não iniciada', self.linha_da_aula(AULA_CURTA).text)
        self.assertIn('Assistida até 10:00',
                      self.linha_da_aula(AULA_LGBT).text)
        self.narrar('Cenário 1: a plataforma lista as aulas disponíveis')

        # E permite assistir ao conteúdo escolhido
        self.clicar(By.LINK_TEXT, AULA_CURTA)
        self.esperar_titulo(AULA_CURTA)
        video = self.espera.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'video#aula-video')
        ))
        self.narrar('O vídeo da aula abre na página. Dando play e assistindo '
                    'até o final')
        self.navegador.execute_script(
            'arguments[0].muted = true; arguments[0].play();', video
        )
        # Espera o vídeo terminar (12 s) e o aula.js registrar o progresso
        WebDriverWait(self.navegador, 40).until(
            lambda d: d.execute_script('return arguments[0].ended;', video)
        )
        WebDriverWait(self.navegador, 10).until(
            lambda d: int(d.find_element(By.ID, 'campo-segundos')
                          .get_attribute('value')) >= 7
        )
        self.narrar('Aula assistida até o final. Marcando como concluída')
        self.clicar(By.CSS_SELECTOR, 'input[name="concluir"]')

        self.esperar_mensagem(f'Aula concluída: {AULA_CURTA}.')
        self.assertIn('Concluída', self.linha_da_aula(AULA_CURTA).text)
        self.assertTrue(
            ProgressoAula.objects.get(aula=self.aula_curta).concluida
        )
        self.narrar('A aula aparece como concluída na lista')

        # 2) MARCAR COMO CONCLUÍDA SEM ASSISTIR (cenário 2)
        self.narrar('Cenário 2: o tatuador assistiu só 10 dos 15 minutos da '
                    'aula Acolhimento de pessoas LGBTQIA+')
        self.clicar(By.LINK_TEXT, AULA_LGBT)
        self.esperar_titulo(AULA_LGBT)
        self.espera.until(EC.text_to_be_present_in_element(
            (By.ID, 'texto-assistido'), '10:00'
        ))

        # QUANDO ele clica em "Marcar como concluída"
        self.clicar(By.CSS_SELECTOR, 'input[name="concluir"]')

        # ENTÃO é exibida a mensagem pedindo para assistir até o final
        self.esperar_mensagem(MSG_INCOMPLETA, tipo='error')

        # E a aula NÃO é marcada como concluída
        self.assertTrue(self.navegador.find_elements(By.ID, 'form-concluir'))
        self.assertFalse(
            ProgressoAula.objects.get(aula=self.aula_lgbt).concluida
        )
        self.narrar('A aula não foi concluída. Teste da US 6 finalizado!')