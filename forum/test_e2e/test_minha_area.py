from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from forum.models import Checklist, ItemChecklist
from .base import BaseE2E

PENDENCIA_CHECKLIST = 'O estúdio ainda não fez nenhum checklist de boas práticas.'


class MinhaAreaTest(BaseE2E):
    """Minha Área: entrar, ver a pendência, resolver e vê-la sumir."""

    def setUp(self):
        super().setUp()
        # O banco dos testes E2E é esvaziado entre um teste e outro, então
        # os itens do checklist da migration não existem aqui.
        for ordem, texto in enumerate([
            'Bancada desinfetada a cada atendimento',
            'Agulhas de uso único',
            'Autoclave com manutenção em dia',
            'Perfurocortantes na caixa coletora',
        ], start=1):
            ItemChecklist.objects.create(
                categoria=ItemChecklist.HIGIENE, texto=texto, ordem=ordem
            )

    def test_resolver_uma_pendencia_pela_minha_area(self):
        # DADO que entrei com a conta do estúdio
        self.entrar()
        self.espera.until(EC.text_to_be_present_in_element(
            (By.ID, 'db-passos'), PENDENCIA_CHECKLIST
        ))
        self.narrar('Depois de entrar, o estúdio cai na Minha Área, com a '
                    'lista do que fazer')

        # QUANDO clico na pendência do checklist
        self.clicar_link('Fazer o checklist')
        self.esperar_titulo('Evolução de Tinta Verde')
        self.narrar('O link leva direto ao checklist do painel de evolução')

        # E marco as práticas que o estúdio cumpre hoje
        caixas = self.navegador.find_elements(
            By.CSS_SELECTOR, '.ifs-stencil input[type="checkbox"]'
        )
        for caixa in caixas[:3]:
            self.navegador.execute_script('arguments[0].click();', caixa)
        self.clicar(By.CSS_SELECTOR, '[name="salvar_checklist"]')
        self.esperar_mensagem('Checklist de hoje salvo: 3 de '
                              f'{ItemChecklist.objects.filter(ativo=True).count()}'
                              ' práticas cumpridas.')
        self.assertEqual(Checklist.objects.get().cumpridos, 3)

        # ENTÃO, de volta à Minha Área, a pendência não aparece mais
        self.clicar_link('← Voltar para a Minha Área')
        self.espera.until(EC.url_contains(reverse('forum:minha_area')))
        proximos = self.navegador.find_element(By.ID, 'db-passos')
        self.assertNotIn(PENDENCIA_CHECKLIST, proximos.text)
        percentual = round(3 / len(caixas) * 100)
        indicadores = self.navegador.find_element(
            By.CSS_SELECTOR, '.db-stat--checklist'
        ).text
        self.assertIn(f'{percentual}%', indicadores.replace('\n', ''))
        self.narrar('A pendência sumiu e o indicador do checklist foi '
                    'atualizado. Teste da Minha Área finalizado!')
