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
        # Usa o vídeo local (e não o YouTube): no GitHub Actions o player do
        # YouTube carrega devagar ou nem carrega, e o teste falhava às vezes.
        self.aula_lgbt = Aula.objects.create(
            titulo=AULA_LGBT, ordem=2, duracao_segundos=15 * 60,
            url_video=f'{self.live_server_url}/static/video/aula-teste.webm',
        )
        # E o tatuador assistiu apenas 10 dos 15 minutos dessa aula
        ProgressoAula.objects.create(
            estudio=self.estudio, aula=self.aula_lgbt,
            segundos_assistidos=10 * 60,
        )

    def ir_para_as_aulas(self):
        # O módulo na Minha Área se chama só "Aulas": há outras categorias.
        self.clicar_link('Aulas')
        self.esperar_pagina('Aulas de inclusão')

    def cartao_da_aula(self, titulo):
        """Cartão da aula na lista. O cartão inteiro é o link para a aula."""
        return self.espera.until(EC.visibility_of_element_located((
            By.XPATH,
            '//a[contains(@class, "aula-card")]'
            f'[.//h4[normalize-space()="{titulo}"]]',
        )))

    def abrir_aula(self, titulo):
        cartao = self.cartao_da_aula(titulo)
        self.navegador.execute_script(
            'arguments[0].scrollIntoView({block: "center"});', cartao
        )
        self.pausar()
        cartao.click()
        self.esperar_titulo(titulo)

    def assistir_ate_o_fim(self, video):
        """Dá play e espera o vídeo (12 s) terminar.

        O play é dado por script, sem clique, e o Chrome trata isso como
        autoplay: às vezes pausa o vídeo no meio. E às vezes o servidor dos
        testes não entrega o arquivo. A cada leitura: recarrega se nada
        chegou em 5 s e retoma se pausou antes do fim. O aula.js continua
        contando, porque a retomada parte do ponto já assistido.
        """
        self.navegador.execute_script(
            'arguments[0].scrollIntoView({block: "center"});', video
        )
        WebDriverWait(self.navegador, 60).until(lambda d: d.execute_script(
            'const v = arguments[0]; v.muted = true;'
            'if (v.ended) { return true; }'
            'v.inicioEspera = v.inicioEspera || Date.now();'
            'if (v.readyState === 0 && Date.now() - v.inicioEspera > 5000) {'
            '    v.inicioEspera = Date.now(); v.load();'
            '}'
            'if (v.paused) { v.play().catch(() => {}); }'
            'return false;', video
        ))

    def test_aulas_listar_assistir_e_concluir_sem_assistir(self):
        # DADO que estou logado
        self.entrar()
        self.narrar('US 6: aulas de inclusão e acessibilidade')

        # 1) ASSISTIR UMA AULA (cenário 1)
        # QUANDO acesso a área de aulas sociais
        self.ir_para_as_aulas()

        # ENTÃO a plataforma lista as aulas disponíveis
        self.assertIn('Não iniciada', self.cartao_da_aula(AULA_CURTA).text)
        self.assertIn('Assistida até 10:00',
                      self.cartao_da_aula(AULA_LGBT).text)
        self.narrar('Cenário 1: a plataforma lista as aulas disponíveis')

        # E permite assistir ao conteúdo escolhido
        self.abrir_aula(AULA_CURTA)
        video = self.espera.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'video#aula-video')
        ))
        self.narrar('O vídeo da aula abre na página. Dando play e assistindo '
                    'até o final')
        self.assistir_ate_o_fim(video)
        # Espera o aula.js registrar o progresso
        WebDriverWait(self.navegador, 10).until(
            lambda d: int(d.find_element(By.ID, 'campo-segundos')
                          .get_attribute('value')) >= 7
        )
        self.narrar('Aula assistida até o final. Marcando como concluída')
        self.clicar(By.CSS_SELECTOR, 'input[name="concluir"]')

        self.esperar_mensagem(f'Aula concluída: {AULA_CURTA}.')
        self.assertIn('Concluída', self.cartao_da_aula(AULA_CURTA).text)
        self.assertTrue(
            ProgressoAula.objects.get(aula=self.aula_curta).concluida
        )
        self.narrar('A aula aparece como concluída na lista')

        # 2) MARCAR COMO CONCLUÍDA SEM ASSISTIR (cenário 2)
        self.narrar('Cenário 2: o tatuador assistiu só 10 dos 15 minutos da '
                    'aula Acolhimento de pessoas LGBTQIA+')
        self.abrir_aula(AULA_LGBT)
        self.espera.until(EC.text_to_be_present_in_element(
            (By.ID, 'texto-assistido'), '10:00'
        ))

        # QUANDO ele clica em "Marcar como concluída"
        self.clicar(By.CSS_SELECTOR, 'input[name="concluir"]')

        # ENTÃO é exibida a mensagem pedindo para assistir até o final
        # Espera até 30 s (o CI é mais lento que o computador da gente)
        WebDriverWait(self.navegador, 30).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, 'p.aviso-error'), MSG_INCOMPLETA
            )
        )

        # E a aula NÃO é marcada como concluída
        self.assertTrue(self.navegador.find_elements(By.ID, 'form-concluir'))
        self.assertFalse(
            ProgressoAula.objects.get(aula=self.aula_lgbt).concluida
        )
        self.narrar('A aula não foi concluída. Teste da US 6 finalizado!')