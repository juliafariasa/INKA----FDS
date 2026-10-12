from django.test import TestCase
from django.urls import reverse

from .models import (
    Contato,
    ItemLista,
    MembroEquipe,
    Pilar,
    PraticaEstudio,
    SecaoConteudo,
    Tecnologia,
)


class ConteudoInicialTest(TestCase):
    """A migration 0002 popula o banco com o conteúdo do README."""

    def test_equipe_foi_carregada(self):
        self.assertEqual(MembroEquipe.objects.count(), 6)
        self.assertTrue(
            MembroEquipe.objects.filter(email='mmd3@cesar.school').exists()
        )

    def test_pilares_foram_carregados(self):
        self.assertEqual(Pilar.objects.count(), 3)
        self.assertEqual(
            list(Pilar.objects.values_list('sigla', flat=True)),
            ['E', 'S', 'G'],
        )

    def test_listas_e_tecnologias_foram_carregadas(self):
        objetivos = ItemLista.objects.filter(
            categoria=ItemLista.CATEGORIA_OBJETIVO
        )
        praticas = ItemLista.objects.filter(
            categoria=ItemLista.CATEGORIA_PRATICA_FDS
        )
        self.assertEqual(objetivos.count(), 5)
        self.assertEqual(praticas.count(), 6)
        self.assertEqual(Tecnologia.objects.count(), 4)

    def test_praticas_do_estudio_foram_carregadas(self):
        self.assertEqual(PraticaEstudio.objects.count(), 12)
        for sigla in ['E', 'S', 'G']:
            with self.subTest(pilar=sigla):
                pilar = Pilar.objects.get(sigla=sigla)
                self.assertEqual(pilar.praticas.count(), 4)

    def test_secoes_foram_carregadas(self):
        self.assertTrue(
            SecaoConteudo.objects.filter(
                pagina=SecaoConteudo.PAGINA_SOBRE_PROJETO
            ).exists()
        )


class PaginasLeemDoBancoTest(TestCase):
    """Cada página lê os dados que exibe direto do banco de dados."""

    def test_index_lista_os_pilares(self):
        resposta = self.client.get(reverse('forum:index'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/index.html')
        self.assertEqual(len(resposta.context['pilares']), 3)
        self.assertContains(resposta, 'Governança')

    def test_index_mostra_praticas_de_cada_pilar(self):
        resposta = self.client.get(reverse('forum:index'))
        self.assertContains(resposta, 'Descarte de perfurocortantes')
        self.assertContains(resposta, 'Biossegurança da equipe e do cliente')
        self.assertContains(resposta, 'Licença sanitária em dia')

    def test_index_mostra_ganhos_para_o_estudio(self):
        resposta = self.client.get(reverse('forum:index'))
        self.assertEqual(len(resposta.context['beneficios']), 5)
        self.assertContains(resposta, 'vigilância sanitária')

    def test_index_explica_esg_para_estudio_de_tatuagem(self):
        resposta = self.client.get(reverse('forum:index'))
        self.assertContains(resposta, 'estúdio de tatuagem')
        titulos = [secao.titulo for secao in resposta.context['secoes']]
        self.assertIn(
            'Por que ESG importa para um estúdio de tatuagem', titulos
        )
        self.assertEqual(titulos[-1], 'A metáfora da tatuagem')

    def test_pratica_nova_aparece_no_pilar_certo(self):
        pilar = Pilar.objects.get(sigla='E')
        PraticaEstudio.objects.create(
            pilar=pilar, titulo='Coleta seletiva no estúdio',
            descricao='Separar recicláveis do resíduo comum.', ordem=9
        )
        resposta = self.client.get(reverse('forum:index'))
        self.assertContains(resposta, 'Coleta seletiva no estúdio')

    def test_quem_somos_lista_a_equipe(self):
        resposta = self.client.get(reverse('forum:quem_somos'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/quem_somos.html')
        self.assertEqual(len(resposta.context['membros']), 6)
        self.assertContains(resposta, 'mmd3@cesar.school')

    def test_quem_somos_esconde_membro_inativo(self):
        membro = MembroEquipe.objects.first()
        membro.ativo = False
        membro.save()

        resposta = self.client.get(reverse('forum:quem_somos'))
        self.assertEqual(len(resposta.context['membros']), 5)
        self.assertNotContains(resposta, membro.email)

    def test_sobre_projeto_lista_objetivos_e_tecnologias(self):
        resposta = self.client.get(reverse('forum:sobre_projeto'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/sobre_projeto.html')
        self.assertEqual(len(resposta.context['objetivos']), 5)
        self.assertEqual(len(resposta.context['tecnologias']), 4)
        self.assertContains(resposta, 'Deloitte')

    def test_conteudo_editado_aparece_na_pagina(self):
        tecnologia = Tecnologia.objects.create(
            nome='PostgreSQL', descricao='Banco de dados de produção.', ordem=9
        )
        resposta = self.client.get(reverse('forum:sobre_projeto'))
        self.assertContains(resposta, tecnologia.nome)

    def test_navegacao_aparece_em_todas_as_paginas(self):
        for nome in ['index', 'quem_somos', 'sobre_projeto', 'fale_conosco']:
            with self.subTest(pagina=nome):
                resposta = self.client.get(reverse(f'forum:{nome}'))
                self.assertEqual(resposta.status_code, 200)
                self.assertContains(resposta, reverse('forum:quem_somos'))
                self.assertContains(resposta, reverse('forum:fale_conosco'))


class FaleConoscoEscreveNoBancoTest(TestCase):
    """O formulário grava a mensagem no banco, sem usar django forms."""

    def setUp(self):
        self.url = reverse('forum:fale_conosco')
        self.dados = {
            'nome': 'Maria Souza',
            'email': 'maria@pme.com.br',
            'empresa': 'PME Verde',
            'assunto': Contato.ASSUNTO_PARCERIA,
            'mensagem': 'Gostaria de entender como o INKA funciona na prática.',
        }

    def test_get_exibe_o_formulario(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/fale_conosco.html')
        self.assertContains(resposta, 'csrfmiddlewaretoken')
        self.assertContains(resposta, 'name="mensagem"')

    def test_post_valido_grava_e_redireciona(self):
        resposta = self.client.post(self.url, self.dados)
        self.assertRedirects(resposta, self.url)
        self.assertEqual(Contato.objects.count(), 1)

        contato = Contato.objects.get()
        self.assertEqual(contato.nome, 'Maria Souza')
        self.assertEqual(contato.assunto, Contato.ASSUNTO_PARCERIA)
        self.assertFalse(contato.respondido)
        self.assertIsNotNone(contato.data_envio)

    def test_post_valido_mostra_aviso_de_sucesso(self):
        resposta = self.client.post(self.url, self.dados, follow=True)
        self.assertContains(resposta, 'aviso-success')
        self.assertContains(resposta, 'Maria Souza')

    def test_mensagem_curta_e_rejeitada(self):
        resposta = self.client.post(self.url, dict(self.dados, mensagem='Oi'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Contato.objects.count(), 0)
        self.assertIn('mensagem', resposta.context['erros'])

    def test_email_invalido_e_rejeitado(self):
        resposta = self.client.post(
            self.url, dict(self.dados, email='nao-e-email')
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Contato.objects.count(), 0)
        self.assertIn('email', resposta.context['erros'])

    def test_nome_vazio_e_rejeitado(self):
        resposta = self.client.post(self.url, dict(self.dados, nome='   '))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Contato.objects.count(), 0)
        self.assertIn('nome', resposta.context['erros'])

    def test_assunto_fora_da_lista_e_rejeitado(self):
        resposta = self.client.post(
            self.url, dict(self.dados, assunto='qualquer-coisa')
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Contato.objects.count(), 0)
        self.assertIn('assunto', resposta.context['erros'])

    def test_erro_preserva_o_que_foi_digitado(self):
        resposta = self.client.post(self.url, dict(self.dados, mensagem='Oi'))
        self.assertEqual(resposta.context['dados']['nome'], 'Maria Souza')
        self.assertContains(resposta, 'value="Maria Souza"')

    def test_str_do_contato(self):
        contato = Contato.objects.create(
            nome='João', email='joao@pme.com', assunto=Contato.ASSUNTO_DUVIDA,
            mensagem='Mensagem de teste com tamanho suficiente.',
            data_envio='2026-09-19 10:00:00+00:00',
        )
        self.assertEqual(str(contato), 'João - Dúvida sobre a plataforma')
