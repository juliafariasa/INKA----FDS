from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from forum.models import ItemEstoque
from .base import BaseE2E

MSG_DUPLICADO = (
    'Este material já está no seu estoque. '
    'Edite a quantidade do item existente!'
)


class EstoqueTest(BaseE2E):
    """História 3 - Gerenciamento de estoque e equipamentos.

    Um teste só, na ordem: adicionar (cenário 1), tentar adicionar de novo
    (cenário 2), editar e, por último, remover (cenário 1).
    """

    def ir_para_o_estoque(self):
        self.entrar()
        self.clicar(By.LINK_TEXT, 'Estoque')
        self.esperar_titulo('Estoque de Tinta Verde')

    def esperar_titulo(self, texto):
        self.espera.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, 'h2'), texto
        ))

    def preencher_item(self, nome, tipo, quantidade, fornecedor):
        self.preencher(By.ID, 'nome', nome)
        Select(self.navegador.find_element(By.ID, 'tipo')).select_by_value(tipo)
        self.preencher(By.ID, 'quantidade', str(quantidade))
        self.preencher(By.ID, 'fornecedor', fornecedor)

    def linha_do_item(self, nome):
        return self.espera.until(EC.visibility_of_element_located(
            (By.XPATH, f'//table//tr[td[normalize-space()="{nome}"]]')
        ))

    def test_estoque_adicionar_duplicar_editar_e_remover(self):
        # DADO que estou logado no painel do estúdio
        self.ir_para_o_estoque()
        self.narrar('US 3: gerenciamento de estoque do estúdio Tinta Verde')

        # 1) ADICIONAR (cenário 1)
        # QUANDO cadastro um material com quantidade e fornecedor
        self.clicar(By.LINK_TEXT, 'Cadastrar item')
        self.narrar('Cenário 1: cadastrando Copinho de tinta, 50 unidades, '
                    'da EcoTattoo')
        self.preencher_item('Copinho de tinta', 'material', 50, 'EcoTattoo')
        self.clicar(By.CSS_SELECTOR, 'input[name="salvar"]')

        # ENTÃO a plataforma adiciona o item ao estoque
        self.esperar_mensagem('Copinho de tinta entrou no estoque.')
        linha = self.linha_do_item('Copinho de tinta')
        celulas = [td.text for td in linha.find_elements(By.TAG_NAME, 'td')]
        self.assertEqual(celulas[:4],
                         ['Copinho de tinta', 'Material', '50', 'EcoTattoo'])
        self.assertEqual(ItemEstoque.objects.count(), 1)
        self.narrar('O material entrou no estoque')

        # 2) TENTAR ADICIONAR DE NOVO (cenário 2)
        # QUANDO o dono tenta cadastrar o mesmo material do mesmo fornecedor
        self.clicar(By.LINK_TEXT, 'Cadastrar item')
        self.narrar('Cenário 2: tentando cadastrar de novo o mesmo material '
                    'do mesmo fornecedor')
        self.preencher_item('Copinho de tinta', 'material', 30, 'EcoTattoo')
        self.clicar(By.CSS_SELECTOR, 'input[name="salvar"]')

        # ENTÃO é exibida a mensagem de material já cadastrado
        self.esperar_mensagem(MSG_DUPLICADO, tipo='error')
        self.narrar('A plataforma avisa que o material já está no estoque')

        # E um novo item NÃO é criado
        self.assertEqual(ItemEstoque.objects.count(), 1)
        self.assertEqual(ItemEstoque.objects.get().quantidade, 50)
        self.clicar(By.LINK_TEXT, 'Voltar ao estoque')
        self.esperar_titulo('Estoque de Tinta Verde')
        self.assertEqual(len(self.navegador.find_elements(
            By.XPATH, '//td[normalize-space()="Copinho de tinta"]'
        )), 1)
        self.narrar('O estoque continua com um único Copinho de tinta')

        # 3) EDITAR (cenário 1: permitir editar o item depois)
        linha = self.linha_do_item('Copinho de tinta')
        self.pausar()
        linha.find_element(By.LINK_TEXT, 'Editar').click()
        self.esperar_titulo('Editar Copinho de tinta')
        self.narrar('Editando o item: a quantidade passa para 80')
        self.preencher(By.ID, 'quantidade', '80')
        self.clicar(By.CSS_SELECTOR, 'input[name="salvar"]')

        self.esperar_mensagem('Copinho de tinta atualizado no estoque.')
        linha = self.linha_do_item('Copinho de tinta')
        self.assertEqual(linha.find_elements(By.TAG_NAME, 'td')[2].text, '80')
        self.assertEqual(ItemEstoque.objects.get().quantidade, 80)
        self.narrar('A quantidade foi atualizada para 80')

        # 4) REMOVER (cenário 1: permitir remover o item depois)
        self.pausar()
        linha.find_element(By.LINK_TEXT, 'Remover').click()
        self.esperar_titulo('Remover item do estoque')
        self.narrar('Por fim, removendo o item do estoque')
        self.clicar(By.CSS_SELECTOR, 'input[name="remover"]')

        self.esperar_mensagem('Copinho de tinta saiu do estoque.')
        self.assertFalse(self.navegador.find_elements(
            By.XPATH, '//td[normalize-space()="Copinho de tinta"]'
        ))
        self.assertFalse(ItemEstoque.objects.exists())
        self.narrar('O item saiu do estoque. Teste da US 3 finalizado!')
