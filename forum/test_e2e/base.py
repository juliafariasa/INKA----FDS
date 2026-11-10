import os
import time

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from forum.models import Estudio

# Segundos de pausa entre os passos, só para dar tempo de ver (e gravar).
# Padrão: 3.5. Para rodar rápido no PowerShell: $env:E2E_PAUSA="0"
PAUSA = float(os.environ.get('E2E_PAUSA', '3.5'))


# O hash de senha padrão é lento de propósito; nos testes não precisa ser.
@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class BaseE2E(StaticLiveServerTestCase):
    EMAIL = 'dono@tintaverde.com.br'
    SENHA = 'SenhaForte!2026'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        options = webdriver.ChromeOptions()

        if "CI" in os.environ:
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1366,900")

        cls.navegador = webdriver.Chrome(options=options)
        cls.navegador.set_window_size(1366, 900)
        cls.espera = WebDriverWait(cls.navegador, 10)

    @classmethod
    def tearDownClass(cls):
        cls.navegador.quit()
        super().tearDownClass()

    def setUp(self):
        # O banco é apagado a cada teste, então cada teste cria o que precisa.
        usuario = get_user_model().objects.create_user(
            username=self.EMAIL, email=self.EMAIL, password=self.SENHA
        )
        self.estudio = Estudio.objects.create(
            nome='Tinta Verde', cidade='Recife', usuario=usuario
        )
        self.navegador.delete_all_cookies()  # começa deslogado

    def entrar(self):
        """Faz login pelo formulário e espera chegar ao perfil do estúdio."""
        self.navegador.get(self.live_server_url + reverse('forum:entrar'))
        self.preencher(By.ID, 'email', self.EMAIL)
        self.preencher(By.ID, 'senha', self.SENHA)
        self.clicar(By.CSS_SELECTOR, 'input[name="entrar"]')
        self.espera.until(EC.url_contains(
            reverse('forum:estudio_perfil', args=[self.estudio.id])
        ))

    def pausar(self, vezes=1):
        # Pausa só para visualização. Para ESPERAR a página, use self.espera.
        if PAUSA > 0:
            time.sleep(PAUSA * vezes)

    def narrar(self, texto):
        """Marca um passo do teste e pausa para dar tempo de ver.

        O texto não aparece na tela; serve de comentário do passo (e de
        roteiro para você narrar no screencast).
        """
        self.pausar(2)

    def clicar(self, by, valor):
        elemento = self.espera.until(EC.element_to_be_clickable((by, valor)))
        self.pausar()  # pausa ANTES do clique, para ver o que vai ser clicado
        elemento.click()

    def preencher(self, by, valor, texto):
        campo = self.espera.until(EC.visibility_of_element_located((by, valor)))
        campo.clear()
        if PAUSA > 0:
            for letra in texto:  # digita letra por letra, como uma pessoa
                campo.send_keys(letra)
                time.sleep(0.15)
        else:
            campo.send_keys(texto)

    def esperar_mensagem(self, texto, tipo='success'):
        """Espera o aviso do Django (p.aviso-success ou p.aviso-error)."""
        self.espera.until(EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, f'p.aviso-{tipo}'), texto
        ))
        # A pausa vem DEPOIS de conferir: os avisos verdes somem em 5 s.
        self.pausar()
