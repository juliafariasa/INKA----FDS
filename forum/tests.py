from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Aula,
    CalculoResiduo,
    Contato,
    ConteudoDescarte,
    Diagnostico,
    EmpresaDescarte,
    Estudio,
    ItemEstoque,
    ItemLista,
    Material,
    MembroEquipe,
    Pilar,
    PraticaEstudio,
    ProgressoAula,
    Resposta,
    SecaoConteudo,
    Tecnologia,
    id_youtube,
)
from .views import EstudioNovoView


def criar_dono(estudio):
    """Liga uma conta de acesso ao estúdio.

    A conta é criada sem senha (o teste entra com force_login): o hash PBKDF2
    é lento de propósito e deixaria a suíte lenta. As senhas de verdade são
    testadas em ContaTest.
    """
    email = f'estudio{estudio.id}@example.com'
    usuario = get_user_model().objects.create_user(username=email, email=email)
    estudio.usuario = usuario
    estudio.save()
    return usuario


class ConteudoInicialTest(TestCase):

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


class DiagnosticoTest(TestCase):
    # Texto copiado da História 2.
    MENSAGEM_JA_REALIZADO = (
        'Seu estúdio já realizou o diagnóstico inicial. '
        'Acompanhe sua evolução pelo painel!'
    )

    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Agulha Verde', cidade='Recife'
        )
        self.client.force_login(criar_dono(self.estudio))
        self.url = reverse('forum:estudio_diagnostico', args=[self.estudio.id])

    def responder(self, valores_por_pilar):
        dados = {}
        for sigla, valores in valores_por_pilar.items():
            praticas = PraticaEstudio.objects.filter(pilar__sigla=sigla)
            for pratica, valor in zip(praticas, valores):
                dados[f'pratica_{pratica.id}'] = valor
        return dados

    def test_cadastro_de_estudio_leva_ao_diagnostico(self):
        self.client.logout()
        resposta = self.client.post(reverse('forum:estudio_novo'), {
            'nome': 'Tinta Viva', 'cidade': 'Olinda',
            'email': 'tintaviva@example.com',
            'senha': 'Tatuagem-Verde-2026', 'senha2': 'Tatuagem-Verde-2026',
        })
        estudio = Estudio.objects.get(nome='Tinta Viva')
        self.assertRedirects(
            resposta,
            reverse('forum:estudio_diagnostico', args=[estudio.id]),
        )

    def test_cadastro_sem_nome_e_rejeitado(self):
        self.client.logout()
        resposta = self.client.post(reverse('forum:estudio_novo'), {
            'nome': '', 'cidade': 'Olinda', 'email': 'semnome@example.com',
            'senha': 'Tatuagem-Verde-2026', 'senha2': 'Tatuagem-Verde-2026',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Estudio.objects.count(), 1)
        self.assertIn('nome', resposta.context['erros'])

    def test_lista_mostra_os_estudios(self):
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/estudios.html')
        self.assertContains(resposta, 'Agulha Verde')
        self.assertContains(resposta, 'Ainda sem diagnóstico')

    def test_menu_tem_link_para_estudios(self):
        resposta = self.client.get(reverse('forum:index'))
        self.assertContains(resposta, reverse('forum:estudios'))

    def test_questionario_mostra_as_12_praticas(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/diagnostico.html')
        self.assertEqual(len(resposta.context['praticas']), 12)
        self.assertContains(resposta, 'Descarte de perfurocortantes')
        self.assertContains(resposta, 'type="radio"', count=36)

    def test_estudio_inexistente_retorna_404(self):
        url = reverse('forum:estudio_diagnostico', args=[999])
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 404)

    def test_todas_sim_da_nota_maxima(self):
        dados = self.responder({
            'E': [2, 2, 2, 2], 'S': [2, 2, 2, 2], 'G': [2, 2, 2, 2],
        })
        resposta = self.client.post(self.url, dados)
        self.assertRedirects(resposta, self.url)

        diagnostico = Diagnostico.objects.get()
        self.assertEqual(diagnostico.respostas.count(), 12)
        self.assertEqual(diagnostico.nota_e, 10)
        self.assertEqual(diagnostico.indice(), 100)
        self.assertEqual(len(diagnostico.plano_de_acao()), 0)

    def test_notas_e_pilares_ativos(self):
        dados = self.responder({
            'E': [2, 2, 2, 1], 'S': [2, 1, 0, 0], 'G': [2, 2, 1, 1],
        })
        self.client.post(self.url, dados)

        diagnostico = Diagnostico.objects.get()
        self.assertEqual(diagnostico.nota_e, 8.75)
        self.assertEqual(diagnostico.nota_s, 3.75)
        self.assertEqual(diagnostico.nota_g, 7.5)
        self.assertTrue(diagnostico.pilar_ativo('E'))
        self.assertFalse(diagnostico.pilar_ativo('S'))
        self.assertTrue(diagnostico.pilar_ativo('G'))
        self.assertAlmostEqual(diagnostico.indice(), 66.67, places=2)

    def test_plano_de_acao_so_tem_pilares_abaixo_de_7(self):
        dados = self.responder({
            'E': [2, 2, 2, 1], 'S': [2, 1, 0, 0], 'G': [2, 2, 1, 1],
        })
        self.client.post(self.url, dados)

        plano = Diagnostico.objects.get().plano_de_acao()
        self.assertEqual(len(plano), 3)
        for item in plano:
            self.assertEqual(item.pratica.pilar.sigla, 'S')
            self.assertLess(item.valor, Resposta.SIM)

    def test_resultado_aparece_na_pagina(self):
        dados = self.responder({
            'E': [2, 2, 2, 1], 'S': [2, 1, 0, 0], 'G': [2, 2, 1, 1],
        })
        resposta = self.client.post(self.url, dados, follow=True)
        self.assertContains(resposta, 'Resultado do último diagnóstico')
        self.assertContains(resposta, '67 de 100')
        self.assertContains(resposta, 'Plano de ação')
        self.assertContains(resposta, 'Formação de novos profissionais')

    def test_resposta_faltando_nao_salva(self):
        dados = self.responder({
            'E': [2, 2, 2, 2], 'S': [2, 2, 2, 2], 'G': [2, 2, 2],
        })
        resposta = self.client.post(self.url, dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Diagnostico.objects.count(), 0)
        self.assertEqual(len(resposta.context['pendentes']), 1)
        self.assertContains(resposta, 'class="pendente"', count=1)

    def test_valor_invalido_conta_como_pendente(self):
        dados = self.responder({
            'E': [2, 2, 2, 5], 'S': [2, 2, 2, 2], 'G': [2, 2, 2, 2],
        })
        resposta = self.client.post(self.url, dados)
        self.assertEqual(Diagnostico.objects.count(), 0)
        self.assertEqual(len(resposta.context['pendentes']), 1)

    def test_erro_preserva_as_respostas_marcadas(self):
        dados = self.responder({'E': [2, 2, 2, 2]})
        resposta = self.client.post(self.url, dados)
        self.assertEqual(len(resposta.context['pendentes']), 8)
        self.assertContains(resposta, 'checked', count=4)

    # Cenário 2: tentar responder o diagnóstico pela segunda vez

    def test_segundo_diagnostico_nao_e_registrado(self):
        self.client.post(self.url, self.responder({
            'E': [2, 2, 2, 1], 'S': [2, 1, 0, 0], 'G': [2, 2, 1, 1],
        }))
        resposta = self.client.post(self.url, self.responder({
            'E': [2, 2, 2, 2], 'S': [2, 2, 2, 2], 'G': [2, 2, 2, 2],
        }))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, self.MENSAGEM_JA_REALIZADO)
        self.assertEqual(self.estudio.diagnosticos.count(), 1)
        self.assertAlmostEqual(self.estudio.ultimo_diagnostico().indice(),
                               66.67, places=2)

    def test_com_diagnostico_feito_a_pagina_esconde_o_questionario(self):
        Diagnostico.objects.create(
            estudio=self.estudio, nota_e=8, nota_s=5, nota_g=7
        )
        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'Resultado do último diagnóstico')
        self.assertContains(resposta, self.MENSAGEM_JA_REALIZADO)
        self.assertNotContains(resposta, 'type="radio"')
        self.assertNotContains(resposta, 'Salvar diagnóstico')

    def test_sem_diagnostico_nao_mostra_a_mensagem(self):
        resposta = self.client.get(self.url)
        self.assertNotContains(resposta, self.MENSAGEM_JA_REALIZADO)

    def test_diagnostico_de_outro_estudio_nao_bloqueia(self):
        outro = Estudio.objects.create(nome='Tinta Viva', cidade='Olinda')
        Diagnostico.objects.create(estudio=outro)
        resposta = self.client.post(self.url, self.responder({
            'E': [2, 2, 2, 2], 'S': [2, 2, 2, 2], 'G': [2, 2, 2, 2],
        }))
        self.assertRedirects(resposta, self.url)
        self.assertEqual(self.estudio.diagnosticos.count(), 1)

    def test_perfil_leva_a_fazer_ou_a_ver_o_diagnostico(self):
        perfil = reverse('forum:estudio_perfil', args=[self.estudio.id])
        self.assertContains(self.client.get(perfil), 'Fazer diagnóstico')

        Diagnostico.objects.create(estudio=self.estudio)
        resposta = self.client.get(perfil)
        self.assertContains(resposta, 'Ver diagnóstico')
        self.assertNotContains(resposta, 'Refazer')

    # Nota de cada pilar quando o admin muda as práticas

    def test_nota_se_ajusta_ao_numero_de_praticas_do_pilar(self):
        PraticaEstudio.objects.create(
            pilar=Pilar.objects.get(sigla='E'), titulo='Coleta seletiva',
            descricao='Separar recicláveis do resíduo comum.', ordem=9,
        )
        self.client.post(self.url, self.responder({
            'E': [2, 2, 2, 2, 0], 'S': [2, 2, 2, 2], 'G': [2, 2, 2, 2],
        }))
        diagnostico = Diagnostico.objects.get()
        self.assertEqual(diagnostico.nota_e, 8)
        self.assertEqual(diagnostico.nota_s, 10)

    def test_nota_maxima_e_10_com_uma_pratica_a_mais(self):
        PraticaEstudio.objects.create(
            pilar=Pilar.objects.get(sigla='E'), titulo='Coleta seletiva',
            descricao='Separar recicláveis do resíduo comum.', ordem=9,
        )
        self.client.post(self.url, self.responder({
            'E': [2, 2, 2, 2, 2], 'S': [2, 2, 2, 2], 'G': [2, 2, 2, 2],
        }))
        diagnostico = Diagnostico.objects.get()
        self.assertEqual(diagnostico.nota_e, 10)
        self.assertEqual(diagnostico.indice(), 100)

    def test_nota_maxima_e_10_com_uma_pratica_a_menos(self):
        PraticaEstudio.objects.filter(pilar__sigla='G').first().delete()
        self.client.post(self.url, self.responder({
            'E': [2, 2, 2, 2], 'S': [2, 2, 2, 2], 'G': [2, 2, 2],
        }))
        self.assertEqual(Diagnostico.objects.get().nota_g, 10)


class SeloTest(TestCase):
    # Textos copiados da História 1.
    MENSAGEM_SEM_SELO = (
        'Este estúdio ainda não possui o selo Estúdio Consciente'
    )
    MENSAGEM_SELO_INVALIDO = 'Selo não encontrado ou inválido!'

    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Agulha Verde', cidade='Recife'
        )
        # O perfil é público: os testes dele rodam sem login, como o cliente.
        self.dono = criar_dono(self.estudio)
        self.url = reverse('forum:estudio_perfil', args=[self.estudio.id])

    def criar_diagnostico(self, nota_e, nota_s, nota_g):
        return Diagnostico.objects.create(
            estudio=self.estudio, nota_e=nota_e, nota_s=nota_s, nota_g=nota_g
        )

    def test_tres_pilares_ativos_da_selo_ouro(self):
        diagnostico = self.criar_diagnostico(10, 7.5, 7)
        self.assertEqual(len(diagnostico.pilares_ativos()), 3)
        self.assertEqual(diagnostico.selo(), 'Ouro')

    def test_dois_pilares_ativos_da_selo_prata(self):
        diagnostico = self.criar_diagnostico(10, 7.5, 6.25)
        self.assertEqual(diagnostico.selo(), 'Prata')

    def test_um_pilar_ativo_da_selo_bronze(self):
        diagnostico = self.criar_diagnostico(8.75, 5, 2.5)
        self.assertEqual(diagnostico.selo(), 'Bronze')

    def test_nenhum_pilar_ativo_fica_sem_selo(self):
        diagnostico = self.criar_diagnostico(6.25, 5, 0)
        self.assertEqual(len(diagnostico.pilares_ativos()), 0)
        self.assertEqual(diagnostico.selo(), '')

    def test_perfil_mostra_selo_pilares_indice_e_data(self):
        diagnostico = self.criar_diagnostico(10, 7.5, 5)
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/estudio_perfil.html')
        self.assertContains(resposta, 'Selo Estúdio Consciente Prata')
        self.assertContains(resposta, 'Ambiental, ')
        self.assertContains(resposta, 'Social')
        self.assertContains(resposta, '75 de 100')
        data_local = timezone.localtime(diagnostico.data)
        self.assertContains(resposta, data_local.strftime('%d/%m/%Y'))

    def test_perfil_sem_diagnostico_mostra_que_nao_tem_selo(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertIsNone(resposta.context['diagnostico'])
        self.assertContains(resposta, self.MENSAGEM_SEM_SELO)
        self.assertContains(resposta, 'ainda não fez o diagnóstico')

    # Cenário 2: estúdio sem vertentes ESG ativas

    def test_perfil_com_zero_pilares_ativos_mostra_mensagem_e_nenhum_selo(self):
        self.criar_diagnostico(6.25, 5, 0)
        resposta = self.client.get(self.url)
        self.assertContains(resposta, self.MENSAGEM_SEM_SELO)
        for selo in ['Ouro', 'Prata', 'Bronze']:
            with self.subTest(selo=selo):
                self.assertNotContains(
                    resposta, f'Selo Estúdio Consciente {selo}'
                )

    def test_perfil_com_selo_nao_mostra_a_mensagem_de_sem_selo(self):
        self.criar_diagnostico(10, 10, 10)
        resposta = self.client.get(self.url)
        self.assertNotContains(resposta, self.MENSAGEM_SEM_SELO)

    def test_perfil_usa_o_diagnostico_mais_recente(self):
        self.criar_diagnostico(10, 10, 10)
        self.criar_diagnostico(8, 0, 0)
        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'Selo Estúdio Consciente Bronze')
        self.assertNotContains(resposta, 'Selo Estúdio Consciente Ouro')

    def test_perfil_de_estudio_inexistente_retorna_404(self):
        url = reverse('forum:estudio_perfil', args=[999])
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 404)

    # Cenário 4: QR Code de estúdio removido

    def test_qrcode_de_estudio_removido_mostra_selo_invalido(self):
        self.criar_diagnostico(10, 10, 10)
        self.estudio.delete()
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 404)
        self.assertTemplateUsed(resposta, 'forum/selo_invalido.html')
        self.assertContains(resposta, self.MENSAGEM_SELO_INVALIDO,
                            status_code=404)
        self.assertNotContains(resposta, 'Selo Estúdio Consciente',
                               status_code=404)

    def test_qrcode_aponta_para_o_perfil(self):
        self.client.force_login(self.dono)
        url = reverse('forum:estudio_qrcode', args=[self.estudio.id])
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/estudio_qrcode.html')
        self.assertEqual(
            resposta.context['url_perfil'], 'http://testserver' + self.url
        )
        self.assertContains(resposta, 'src="data:image/png;base64,')

    def test_qrcode_pode_ser_baixado_para_imprimir(self):
        self.client.force_login(self.dono)
        url = reverse('forum:estudio_qrcode', args=[self.estudio.id])
        resposta = self.client.get(url)
        self.assertContains(resposta, 'download="qrcode-agulha-verde.png"')

    def test_lista_mostra_o_selo_de_cada_estudio(self):
        Estudio.objects.create(nome='Tinta Viva', cidade='Olinda')
        self.criar_diagnostico(10, 10, 10)
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertContains(resposta, '<td>Ouro</td>', html=True)
        self.assertContains(resposta, '<td>Sem selo</td>', html=True)


class ResiduoTest(TestCase):
    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Agulha Verde', cidade='Recife'
        )
        self.client.force_login(criar_dono(self.estudio))
        self.url = reverse('forum:estudio_residuos', args=[self.estudio.id])
        self.agulha = Material.objects.create(
            nome='Agulha de teste', tipo=Material.PERFUROCORTANTE,
            gramas_por_atendimento=10,
        )
        self.luva = Material.objects.create(
            nome='Luva de teste', tipo=Material.CONTAMINADO,
            gramas_por_atendimento=20,
        )
        self.embalagem = Material.objects.create(
            nome='Embalagem de teste', tipo=Material.COMUM,
            gramas_por_atendimento=5,
        )
        self.todos = [self.agulha.id, self.luva.id, self.embalagem.id]

    def test_materiais_iniciais_foram_carregados(self):
        iniciais = Material.objects.exclude(nome__endswith='de teste')
        self.assertEqual(iniciais.count(), 10)
        for tipo, _ in Material.TIPO_CHOICES:
            with self.subTest(tipo=tipo):
                self.assertTrue(iniciais.filter(tipo=tipo).exists())

    def test_get_mostra_o_formulario(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/residuos.html')
        self.assertContains(resposta, 'name="atendimentos"')
        self.assertContains(resposta, 'Luva de teste')
        self.assertIsNone(resposta.context['calculo'])

    def test_calculo_valido_grava_gramas_por_tipo(self):
        resposta = self.client.post(
            self.url, {'atendimentos': '10', 'materiais': self.todos}
        )
        self.assertRedirects(resposta, self.url)

        calculo = CalculoResiduo.objects.get()
        self.assertEqual(calculo.atendimentos, 10)
        self.assertEqual(calculo.gramas_perfurocortante, 100)
        self.assertEqual(calculo.gramas_contaminado, 200)
        self.assertEqual(calculo.gramas_comum, 50)
        self.assertEqual(calculo.total(), 350)

    def test_material_nao_marcado_nao_entra_na_conta(self):
        self.client.post(
            self.url, {'atendimentos': '10', 'materiais': [self.luva.id]}
        )
        calculo = CalculoResiduo.objects.get()
        self.assertEqual(calculo.gramas_perfurocortante, 0)
        self.assertEqual(calculo.gramas_contaminado, 200)

    def test_atendimentos_vazio_e_rejeitado(self):
        resposta = self.client.post(
            self.url, {'atendimentos': '', 'materiais': self.todos}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(CalculoResiduo.objects.count(), 0)
        self.assertIn('atendimentos', resposta.context['erros'])

    def test_atendimentos_zero_e_rejeitado(self):
        resposta = self.client.post(
            self.url, {'atendimentos': '0', 'materiais': self.todos}
        )
        self.assertEqual(CalculoResiduo.objects.count(), 0)
        self.assertIn('atendimentos', resposta.context['erros'])

    def test_atendimentos_negativo_e_rejeitado(self):
        resposta = self.client.post(
            self.url, {'atendimentos': '-5', 'materiais': self.todos}
        )
        self.assertEqual(CalculoResiduo.objects.count(), 0)
        self.assertIn('atendimentos', resposta.context['erros'])

    def test_atendimentos_que_nao_e_numero_e_rejeitado(self):
        resposta = self.client.post(
            self.url, {'atendimentos': 'dez', 'materiais': self.todos}
        )
        self.assertEqual(CalculoResiduo.objects.count(), 0)
        self.assertIn('atendimentos', resposta.context['erros'])

    def test_sem_material_marcado_e_rejeitado(self):
        resposta = self.client.post(self.url, {'atendimentos': '10'})
        self.assertEqual(CalculoResiduo.objects.count(), 0)
        self.assertIn('materiais', resposta.context['erros'])

    def test_material_com_digito_unicode_nao_derruba_a_pagina(self):
        # '²'.isdigit() é verdadeiro, mas int('²') dava erro 500.
        resposta = self.client.post(
            self.url, {'atendimentos': '10', 'materiais': ['²']}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('materiais', resposta.context['erros'])

    # Cenário 2: nenhum material selecionado (texto copiado da História 4)

    def test_sem_material_mostra_a_mensagem_da_historia(self):
        resposta = self.client.post(self.url, {'atendimentos': '40'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(CalculoResiduo.objects.count(), 0)
        self.assertContains(resposta,
                            'Selecione pelo menos um material utilizado!')

    def test_atendimentos_acima_do_limite_sao_rejeitados(self):
        for valor in ['10001', '99999999999999999999']:
            with self.subTest(valor=valor):
                resposta = self.client.post(
                    self.url, {'atendimentos': valor, 'materiais': self.todos}
                )
                self.assertEqual(resposta.status_code, 200)
                self.assertIn('atendimentos', resposta.context['erros'])
        self.assertEqual(CalculoResiduo.objects.count(), 0)

    def test_limite_de_atendimentos_e_aceito(self):
        resposta = self.client.post(
            self.url, {'atendimentos': '10000', 'materiais': self.todos}
        )
        self.assertRedirects(resposta, self.url)

    # Materiais guardados e formulário preenchido com o último mês

    def test_calculo_guarda_os_materiais_usados(self):
        self.client.post(
            self.url,
            {'atendimentos': '10', 'materiais': [self.agulha.id, self.luva.id]},
        )
        calculo = CalculoResiduo.objects.get()
        self.assertEqual(set(calculo.materiais.all()),
                         {self.agulha, self.luva})

    def test_resultado_lista_os_materiais_usados(self):
        resposta = self.client.post(
            self.url, {'atendimentos': '10', 'materiais': [self.luva.id]},
            follow=True,
        )
        self.assertContains(resposta, 'Materiais usados:')
        self.assertContains(resposta, 'Luva de teste')

    def test_formulario_vem_preenchido_com_ultimo_calculo(self):
        self.client.post(
            self.url, {'atendimentos': '12', 'materiais': [self.luva.id]}
        )
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.context['dados']['atendimentos'], '12')
        self.assertEqual(resposta.context['dados']['materiais'],
                         [self.luva.id])
        self.assertContains(resposta, 'value="12"')
        self.assertContains(resposta, 'checked', count=1)
        self.assertContains(resposta, 'Editar dados do mês')

    def test_calculo_antigo_sem_materiais_preenche_so_os_atendimentos(self):
        CalculoResiduo.objects.create(estudio=self.estudio, atendimentos=7)
        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'value="7"')
        self.assertNotContains(resposta, 'checked')
        self.assertNotContains(resposta, 'Materiais usados:')

    def test_erro_preserva_os_materiais_marcados(self):
        resposta = self.client.post(
            self.url, {'atendimentos': '0', 'materiais': [self.luva.id]}
        )
        self.assertEqual(resposta.context['dados']['materiais'],
                         [self.luva.id])
        self.assertContains(resposta, 'checked', count=1)

    def test_resultado_mostra_recomendacoes_ambientais(self):
        resposta = self.client.post(
            self.url, {'atendimentos': '10', 'materiais': self.todos},
            follow=True,
        )
        self.assertContains(resposta, 'Resultado do último cálculo')
        self.assertContains(resposta, '350 g')
        self.assertEqual(len(resposta.context['recomendacoes']), 4)
        self.assertContains(resposta, 'Redução de descartáveis')
        self.assertNotContains(resposta, 'Licença sanitária em dia')

    def test_primeiro_calculo_nao_tem_comparacao(self):
        self.client.post(
            self.url, {'atendimentos': '10', 'materiais': self.todos}
        )
        calculo = CalculoResiduo.objects.get()
        self.assertIsNone(calculo.anterior())
        self.assertEqual(calculo.resultado()[0]['situacao'], '')

    def test_segundo_calculo_mostra_que_diminuiu(self):
        self.client.post(
            self.url, {'atendimentos': '10', 'materiais': self.todos}
        )
        resposta = self.client.post(
            self.url, {'atendimentos': '6', 'materiais': self.todos},
            follow=True,
        )
        total = resposta.context['calculo'].resultado()[-1]
        self.assertEqual(total['situacao'], 'Diminuiu')
        self.assertEqual(total['diferenca'], 140)
        self.assertContains(resposta, 'Diminuiu 140 g')

    def test_segundo_calculo_mostra_que_aumentou(self):
        self.client.post(
            self.url, {'atendimentos': '10', 'materiais': [self.luva.id]}
        )
        self.client.post(
            self.url, {'atendimentos': '10', 'materiais': self.todos}
        )
        linhas = self.estudio.ultimo_calculo_residuo().resultado()
        self.assertEqual(linhas[0]['situacao'], 'Aumentou')
        self.assertEqual(linhas[0]['diferenca'], 100)
        self.assertEqual(linhas[1]['situacao'], 'Igual')

    def test_comparacao_e_so_com_o_mesmo_estudio(self):
        outro = Estudio.objects.create(nome='Tinta Viva', cidade='Olinda')
        CalculoResiduo.objects.create(estudio=outro, atendimentos=1)
        self.client.post(
            self.url, {'atendimentos': '10', 'materiais': self.todos}
        )
        self.assertIsNone(self.estudio.ultimo_calculo_residuo().anterior())

    def test_estudio_inexistente_retorna_404(self):
        url = reverse('forum:estudio_residuos', args=[999])
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 404)


class EstoqueTest(TestCase):
    # Texto copiado da História 3, e não da view: um erro de digitação no
    # código tem que quebrar o teste.
    MENSAGEM_DUPLICADO = (
        'Este material já está no seu estoque. '
        'Edite a quantidade do item existente!'
    )

    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Tinta Verde', cidade='Recife'
        )
        self.outro = Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        self.client.force_login(criar_dono(self.estudio))
        self.url_lista = reverse('forum:estudio_estoque',
                                 args=[self.estudio.id])
        self.url_novo = reverse('forum:estudio_estoque_novo',
                                args=[self.estudio.id])

    def dados(self, **campos):
        dados = {
            'nome': 'Copinho de tinta',
            'tipo': ItemEstoque.MATERIAL,
            'quantidade': '50',
            'fornecedor': 'EcoTattoo',
        }
        dados.update(campos)
        return dados

    def criar_item(self, estudio=None, **campos):
        valores = {
            'nome': 'Copinho de tinta',
            'tipo': ItemEstoque.MATERIAL,
            'quantidade': 50,
            'fornecedor': 'EcoTattoo',
        }
        valores.update(campos)
        return ItemEstoque.objects.create(
            estudio=estudio or self.estudio, **valores
        )

    def url_editar(self, item, estudio=None):
        estudio = estudio or self.estudio
        return reverse('forum:estudio_estoque_editar',
                       args=[estudio.id, item.id])

    def url_remover(self, item, estudio=None):
        estudio = estudio or self.estudio
        return reverse('forum:estudio_estoque_remover',
                       args=[estudio.id, item.id])

    # Cenário 1: cadastrar, editar e remover

    def test_cadastro_valido_entra_no_estoque(self):
        resposta = self.client.post(self.url_novo, self.dados())
        self.assertRedirects(resposta, self.url_lista)

        item = ItemEstoque.objects.get()
        self.assertEqual(item.estudio, self.estudio)
        self.assertEqual(item.nome, 'Copinho de tinta')
        self.assertEqual(item.tipo, ItemEstoque.MATERIAL)
        self.assertEqual(item.quantidade, 50)
        self.assertEqual(item.fornecedor, 'EcoTattoo')

    def test_cadastro_de_equipamento(self):
        self.client.post(self.url_novo, self.dados(
            nome='Autoclave', tipo=ItemEstoque.EQUIPAMENTO, quantidade='1',
            fornecedor='Cristófoli',
        ))
        item = ItemEstoque.objects.get()
        self.assertEqual(item.tipo, ItemEstoque.EQUIPAMENTO)

    def test_cadastro_mostra_aviso_e_o_item_na_lista(self):
        resposta = self.client.post(self.url_novo, self.dados(), follow=True)
        self.assertContains(resposta, 'aviso-success')
        self.assertContains(resposta, 'Copinho de tinta')
        self.assertContains(resposta, 'EcoTattoo')

    def test_lista_mostra_itens_com_links_de_editar_e_remover(self):
        item = self.criar_item()
        resposta = self.client.get(self.url_lista)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/estoque.html')
        self.assertContains(resposta, 'Copinho de tinta')
        self.assertContains(resposta, 'Material')
        self.assertContains(resposta, self.url_editar(item))
        self.assertContains(resposta, self.url_remover(item))

    def test_lista_vazia_mostra_aviso(self):
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Nenhum item no estoque ainda')

    def test_item_sem_quantidade_aparece_em_falta(self):
        self.criar_item(quantidade=0)
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, '(em falta)')
        self.assertContains(resposta, 'class="pendente"', count=1)

    def test_formulario_de_edicao_vem_preenchido(self):
        item = self.criar_item()
        resposta = self.client.get(self.url_editar(item))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/estoque_form.html')
        self.assertContains(resposta, 'value="Copinho de tinta"')
        self.assertContains(resposta, 'value="50"')
        self.assertContains(resposta, 'value="EcoTattoo"')

    def test_edicao_mostra_quantidade_zero(self):
        item = self.criar_item(quantidade=0)
        resposta = self.client.get(self.url_editar(item))
        self.assertContains(resposta, 'value="0"')

    def test_editar_altera_o_item(self):
        item = self.criar_item()
        resposta = self.client.post(
            self.url_editar(item), self.dados(quantidade='80')
        )
        self.assertRedirects(resposta, self.url_lista)
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 80)
        self.assertEqual(ItemEstoque.objects.count(), 1)

    def test_editar_sem_mudar_nome_nem_fornecedor_nao_acusa_duplicado(self):
        item = self.criar_item()
        resposta = self.client.post(
            self.url_editar(item), self.dados(quantidade='10')
        )
        self.assertRedirects(resposta, self.url_lista)
        self.assertNotIn(self.MENSAGEM_DUPLICADO,
                         resposta.content.decode())

    def test_get_remover_pede_confirmacao_e_nao_apaga(self):
        item = self.criar_item()
        resposta = self.client.get(self.url_remover(item))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/estoque_remover.html')
        self.assertContains(resposta, 'Tem certeza')
        self.assertEqual(ItemEstoque.objects.count(), 1)

    def test_post_remover_apaga_o_item(self):
        item = self.criar_item()
        resposta = self.client.post(self.url_remover(item))
        self.assertRedirects(resposta, self.url_lista)
        self.assertEqual(ItemEstoque.objects.count(), 0)

    # Cenário 2: material já cadastrado

    def test_material_duplicado_nao_e_criado(self):
        self.criar_item()
        resposta = self.client.post(self.url_novo, self.dados())
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(ItemEstoque.objects.count(), 1)
        self.assertContains(resposta, self.MENSAGEM_DUPLICADO)

    def test_duplicado_ignora_maiusculas_e_espacos_nas_pontas(self):
        self.criar_item()
        resposta = self.client.post(self.url_novo, self.dados(
            nome='  COPINHO DE TINTA ', fornecedor='ecotattoo  '
        ))
        self.assertEqual(ItemEstoque.objects.count(), 1)
        self.assertContains(resposta, self.MENSAGEM_DUPLICADO)

    def test_duplicado_ignora_maiusculas_em_letras_com_acento(self):
        self.criar_item(nome='Máquina rotativa', fornecedor='Eletrônica Sul')
        resposta = self.client.post(self.url_novo, self.dados(
            nome='MÁQUINA ROTATIVA', fornecedor='ELETRÔNICA SUL'
        ))
        self.assertEqual(ItemEstoque.objects.count(), 1)
        self.assertContains(resposta, self.MENSAGEM_DUPLICADO)

    def test_duplicado_vale_para_equipamento(self):
        self.criar_item(nome='Autoclave', tipo=ItemEstoque.EQUIPAMENTO)
        resposta = self.client.post(self.url_novo, self.dados(
            nome='Autoclave', tipo=ItemEstoque.EQUIPAMENTO
        ))
        self.assertEqual(ItemEstoque.objects.count(), 1)
        self.assertContains(resposta, self.MENSAGEM_DUPLICADO)

    def test_edicao_que_fica_igual_a_outro_item_e_rejeitada(self):
        self.criar_item()
        outro_item = self.criar_item(fornecedor='Tinta Brasil')
        resposta = self.client.post(
            self.url_editar(outro_item), self.dados(fornecedor='EcoTattoo')
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, self.MENSAGEM_DUPLICADO)
        outro_item.refresh_from_db()
        self.assertEqual(outro_item.fornecedor, 'Tinta Brasil')

    def test_mesmo_material_de_outro_fornecedor_e_aceito(self):
        self.criar_item()
        resposta = self.client.post(
            self.url_novo, self.dados(fornecedor='Tinta Brasil')
        )
        self.assertRedirects(resposta, self.url_lista)
        self.assertEqual(ItemEstoque.objects.count(), 2)

    def test_mesmo_material_em_outro_estudio_e_aceito(self):
        self.criar_item(estudio=self.outro)
        resposta = self.client.post(self.url_novo, self.dados())
        self.assertRedirects(resposta, self.url_lista)
        self.assertEqual(self.estudio.itens_estoque.count(), 1)
        self.assertEqual(self.outro.itens_estoque.count(), 1)

    # Validações do formulário

    def test_campos_invalidos_sao_rejeitados(self):
        casos = [
            ('nome', {'nome': ''}),
            ('nome', {'nome': '   '}),
            ('tipo', {'tipo': 'insumo'}),
            ('quantidade', {'quantidade': ''}),
            ('quantidade', {'quantidade': '-1'}),
            ('quantidade', {'quantidade': 'dez'}),
            ('quantidade', {'quantidade': '2.5'}),
            ('quantidade', {'quantidade': '1000001'}),
            ('fornecedor', {'fornecedor': ''}),
            ('nome', {'nome': 'x' * 121}),
            ('fornecedor', {'fornecedor': 'x' * 121}),
        ]
        for campo, invalido in casos:
            with self.subTest(campo=campo, valor=invalido):
                resposta = self.client.post(
                    self.url_novo, self.dados(**invalido)
                )
                self.assertEqual(resposta.status_code, 200)
                self.assertIn(campo, resposta.context['erros'])
                self.assertContains(resposta, 'Confira os campos destacados')
        self.assertEqual(ItemEstoque.objects.count(), 0)

    def test_quantidade_zero_e_aceita(self):
        self.client.post(self.url_novo, self.dados(quantidade='0'))
        self.assertEqual(ItemEstoque.objects.get().quantidade, 0)

    def test_erro_preserva_o_que_foi_digitado(self):
        resposta = self.client.post(
            self.url_novo, self.dados(quantidade='-3')
        )
        self.assertContains(resposta, 'value="Copinho de tinta"')
        self.assertContains(resposta, 'value="EcoTattoo"')

    def test_edicao_invalida_nao_altera_o_item(self):
        item = self.criar_item()
        resposta = self.client.post(
            self.url_editar(item), self.dados(nome='', quantidade='9')
        )
        self.assertIn('nome', resposta.context['erros'])
        item.refresh_from_db()
        self.assertEqual(item.nome, 'Copinho de tinta')
        self.assertEqual(item.quantidade, 50)

    # 404 e isolamento entre estúdios

    def test_estudio_inexistente_retorna_404(self):
        for nome in ['forum:estudio_estoque', 'forum:estudio_estoque_novo']:
            with self.subTest(url=nome):
                resposta = self.client.get(reverse(nome, args=[999]))
                self.assertEqual(resposta.status_code, 404)

    def test_item_inexistente_retorna_404(self):
        for nome in ['forum:estudio_estoque_editar',
                     'forum:estudio_estoque_remover']:
            with self.subTest(url=nome):
                url = reverse(nome, args=[self.estudio.id, 999])
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url).status_code, 404)

    def test_item_de_outro_estudio_retorna_404(self):
        item = self.criar_item(estudio=self.outro)
        self.assertEqual(
            self.client.get(self.url_editar(item)).status_code, 404
        )
        self.assertEqual(
            self.client.post(self.url_editar(item),
                             self.dados(quantidade='1')).status_code, 404
        )
        self.assertEqual(
            self.client.post(self.url_remover(item)).status_code, 404
        )
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 50)

    def test_lista_nao_mostra_itens_de_outro_estudio(self):
        self.criar_item(estudio=self.outro, nome='Luva do vizinho')
        resposta = self.client.get(self.url_lista)
        self.assertNotContains(resposta, 'Luva do vizinho')
        self.assertContains(resposta, 'Nenhum item no estoque ainda')

    def test_perfil_tem_link_para_o_estoque(self):
        resposta = self.client.get(
            reverse('forum:estudio_perfil', args=[self.estudio.id])
        )
        self.assertContains(resposta, self.url_lista)


class DescarteTest(TestCase):
    # Texto copiado da História 5.
    MENSAGEM_INDISPONIVEL = (
        'Este conteúdo está indisponível no momento. '
        'Tente outro conteúdo da lista!'
    )

    # Os links abaixo usam domínios de exemplo: os testes nunca acessam a
    # internet, só conferem o HTML gerado.
    def setUp(self):
        # O Descarte é exclusivo dos estúdios: os testes entram numa conta.
        estudio = Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        self.client.force_login(criar_dono(estudio))
        self.url = reverse('forum:descarte')
        self.video = ConteudoDescarte.objects.create(
            titulo='Como descartar agulhas corretamente',
            formato=ConteudoDescarte.VIDEO,
            url='https://www.youtube.com/watch?v=abcdefghijk',
            descricao='Passo a passo do coletor de perfurocortantes.',
        )
        self.podcast = ConteudoDescarte.objects.create(
            titulo='Resíduo de estúdio em 20 minutos',
            formato=ConteudoDescarte.PODCAST,
            url='https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk',
        )
        self.slides = ConteudoDescarte.objects.create(
            titulo='Separação de resíduos de serviços de saúde',
            formato=ConteudoDescarte.SLIDES,
            url='https://example.com/slides/separacao.pdf',
        )
        self.empresa = EmpresaDescarte.objects.create(
            nome='Coleta Exemplo', cidade='Recife',
            telefone='(81) 3333-4444', email='contato@example.com',
            site='https://example.com', tipos_residuo='Perfurocortante',
        )

    def url_conteudo(self, conteudo):
        return reverse('forum:descarte_conteudo', args=[conteudo.id])

    # Cenário 1: área de descarte

    def test_lista_agrupa_conteudos_por_formato(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/descarte.html')

        formatos = resposta.context['formatos']
        self.assertEqual([f['titulo'] for f in formatos],
                         ['Vídeos', 'Podcasts', 'Slides'])
        self.assertEqual(formatos[0]['conteudos'], [self.video])
        self.assertEqual(formatos[1]['conteudos'], [self.podcast])
        self.assertEqual(formatos[2]['conteudos'], [self.slides])

        self.assertContains(resposta, 'Como descartar agulhas corretamente')
        self.assertContains(resposta, self.url_conteudo(self.podcast))
        self.assertContains(resposta, self.url_conteudo(self.slides))

    def test_lista_mostra_empresas_com_contatos(self):
        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'Coleta Exemplo')
        self.assertContains(resposta, 'Recife')
        self.assertContains(resposta, 'Perfurocortante')
        self.assertContains(resposta, 'href="tel:8133334444"')
        self.assertContains(resposta, '(81) 3333-4444')
        self.assertContains(resposta, 'mailto:contato@example.com')
        self.assertContains(resposta, 'href="https://example.com"')

    def test_sem_conteudo_nem_empresa_mostra_estado_vazio(self):
        ConteudoDescarte.objects.all().delete()
        EmpresaDescarte.objects.all().delete()
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Ainda não há conteúdos sobre descarte')
        self.assertContains(resposta, 'Nenhuma empresa de descarte')

    def test_formato_sem_conteudo_mostra_aviso(self):
        self.podcast.delete()
        self.slides.delete()
        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'Nada cadastrado neste formato ainda.',
                            count=2)

    def test_lista_marca_conteudo_indisponivel(self):
        self.video.disponivel = False
        self.video.save()
        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'Como descartar agulhas corretamente')
        self.assertContains(resposta, '(indisponível no momento)', count=1)

    def test_video_do_youtube_e_incorporado(self):
        resposta = self.client.get(self.url_conteudo(self.video))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/descarte_conteudo.html')
        self.assertContains(
            resposta, 'src="https://www.youtube.com/embed/abcdefghijk"'
        )
        self.assertContains(
            resposta, 'referrerpolicy="strict-origin-when-cross-origin"'
        )
        self.assertContains(resposta, 'Passo a passo do coletor')

    def test_video_em_arquivo_usa_o_player_do_navegador(self):
        self.video.url = 'https://example.com/videos/descarte.mp4'
        self.video.save()
        resposta = self.client.get(self.url_conteudo(self.video))
        self.assertContains(
            resposta, '<video src="https://example.com/videos/descarte.mp4"'
        )

    def test_podcast_do_spotify_usa_o_player_do_spotify(self):
        resposta = self.client.get(self.url_conteudo(self.podcast))
        self.assertContains(
            resposta,
            'https://open.spotify.com/embed/episode/4rOoJ6Egrf8K2IrywzwOMk',
        )

    def test_podcast_em_arquivo_usa_audio(self):
        self.podcast.url = 'https://example.com/podcast/episodio-1.mp3'
        self.podcast.save()
        resposta = self.client.get(self.url_conteudo(self.podcast))
        self.assertContains(
            resposta, '<audio src="https://example.com/podcast/episodio-1.mp3"'
        )

    def test_slides_mostram_o_link(self):
        resposta = self.client.get(self.url_conteudo(self.slides))
        self.assertContains(
            resposta, 'href="https://example.com/slides/separacao.pdf"'
        )
        self.assertContains(resposta, 'Abrir slides')
        self.assertNotContains(resposta, '<iframe')

    def test_video_que_nao_e_do_youtube_vira_link(self):
        self.video.url = 'https://example.com/pagina-do-video'
        self.video.save()
        resposta = self.client.get(self.url_conteudo(self.video))
        self.assertNotContains(resposta, '<iframe')
        self.assertContains(resposta, 'Abrir vídeo')

    # Cenário 2: conteúdo com link indisponível

    def test_conteudo_indisponivel_nao_e_reproduzido(self):
        self.video.disponivel = False
        self.video.save()
        resposta = self.client.get(self.url_conteudo(self.video))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, self.MENSAGEM_INDISPONIVEL)
        self.assertNotContains(resposta, '<iframe')
        self.assertNotContains(resposta, 'youtube.com')
        self.assertNotContains(resposta, 'abcdefghijk')

    def test_slides_indisponiveis_nao_mostram_o_link(self):
        self.slides.disponivel = False
        self.slides.save()
        resposta = self.client.get(self.url_conteudo(self.slides))
        self.assertContains(resposta, self.MENSAGEM_INDISPONIVEL)
        self.assertNotContains(resposta, 'example.com/slides')

    def test_conteudo_disponivel_nao_mostra_a_mensagem(self):
        resposta = self.client.get(self.url_conteudo(self.video))
        self.assertNotContains(resposta, self.MENSAGEM_INDISPONIVEL)

    # 404, menu e leitura dos links

    def test_conteudo_inexistente_retorna_404(self):
        url = reverse('forum:descarte_conteudo', args=[999])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_menu_tem_link_para_descarte_marcado_como_ativo(self):
        link_ativo = '<a class="ativo" href="/descarte/">Descarte</a>'
        for url in [self.url, self.url_conteudo(self.video)]:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertContains(resposta, link_ativo, html=True)

        resposta = self.client.get(reverse('forum:quem_somos'))
        self.assertContains(resposta, reverse('forum:descarte'))
        self.assertNotContains(resposta, link_ativo, html=True)

    def test_id_youtube_reconhece_os_formatos_de_link(self):
        casos = {
            'https://www.youtube.com/watch?v=abcdefghijk': 'abcdefghijk',
            'https://youtube.com/watch?v=abcdefghijk&t=30s': 'abcdefghijk',
            'https://m.youtube.com/watch?v=abcdefghijk': 'abcdefghijk',
            'https://youtu.be/abcdefghijk?si=xyz': 'abcdefghijk',
            'https://www.youtube.com/shorts/abcdefghijk': 'abcdefghijk',
            'https://www.youtube.com/embed/abcdefghijk': 'abcdefghijk',
            'https://www.youtube.com/channel/abcdefghijk': '',
            'https://www.youtube.com/watch?v=curto': '',
            'https://www.youtube.com/watch?v=ááááááááááá': '',
            'https://example.com/watch?v=abcdefghijk': '',
        }
        for url, esperado in casos.items():
            with self.subTest(url=url):
                self.assertEqual(id_youtube(url), esperado)


class DescarteCadastroTest(TestCase):
    """Os estúdios cadastram conteúdos e empresas do Descarte pelo site."""

    # Texto copiado da História 5.
    MENSAGEM_INDISPONIVEL = (
        'Este conteúdo está indisponível no momento. '
        'Tente outro conteúdo da lista!'
    )

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.outro = Estudio.objects.create(nome='Agulha Viva',
                                            cidade='Olinda')
        self.dono = criar_dono(self.estudio)
        self.dono_outro = criar_dono(self.outro)
        self.client.force_login(self.dono)
        self.url_lista = reverse('forum:descarte')
        self.url_novo_conteudo = reverse('forum:descarte_conteudo_novo',
                                         args=[self.estudio.id])
        self.url_nova_empresa = reverse('forum:descarte_empresa_nova',
                                        args=[self.estudio.id])

    def dados_conteudo(self, **campos):
        dados = {
            'titulo': 'Como descartar agulhas corretamente',
            'formato': ConteudoDescarte.VIDEO,
            'url': 'https://www.youtube.com/watch?v=abcdefghijk',
            'descricao': 'Passo a passo do coletor.',
            'disponivel': 'on',
        }
        dados.update(campos)
        return dados

    def dados_empresa(self, **campos):
        dados = {
            'nome': 'Coleta Exemplo', 'cidade': 'Recife',
            'telefone': '(81) 3333-4444', 'email': 'contato@example.com',
            'site': 'https://example.com',
            'tipos_residuo': 'perfurocortante, contaminado',
        }
        dados.update(campos)
        return dados

    def conteudo_do_estudio(self, estudio=None, **campos):
        valores = {
            'titulo': 'Conteúdo do estúdio', 'formato': ConteudoDescarte.SLIDES,
            'url': 'https://example.com/slides.pdf',
        }
        valores.update(campos)
        return ConteudoDescarte.objects.create(
            estudio=estudio or self.estudio, **valores
        )

    # Cadastro de conteúdo

    def test_lista_tem_os_links_para_cadastrar(self):
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, self.url_novo_conteudo)
        self.assertContains(resposta, self.url_nova_empresa)

    def test_formulario_de_conteudo_vem_com_link_funcionando_marcado(self):
        resposta = self.client.get(self.url_novo_conteudo)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/descarte_conteudo_form.html')
        self.assertContains(resposta, 'name="disponivel" checked')

    def test_estudio_cadastra_conteudo(self):
        resposta = self.client.post(self.url_novo_conteudo,
                                    self.dados_conteudo())
        self.assertRedirects(resposta, self.url_lista)

        conteudo = ConteudoDescarte.objects.get()
        self.assertEqual(conteudo.estudio, self.estudio)
        self.assertTrue(conteudo.disponivel)

        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Como descartar agulhas corretamente')
        self.assertContains(resposta, 'Cadastrado pelo seu estúdio')

    def test_conteudo_cadastrado_abre_o_player(self):
        self.client.post(self.url_novo_conteudo, self.dados_conteudo())
        conteudo = ConteudoDescarte.objects.get()
        resposta = self.client.get(
            reverse('forum:descarte_conteudo', args=[conteudo.id])
        )
        self.assertContains(resposta, 'youtube.com/embed/abcdefghijk')

    def test_conteudo_cadastrado_com_link_fora_do_ar_mostra_a_mensagem(self):
        # Cenário 2 feito pelo próprio site: a caixa "link funcionando" fica
        # desmarcada (o navegador não envia o campo).
        dados = self.dados_conteudo()
        del dados['disponivel']
        self.client.post(self.url_novo_conteudo, dados)

        conteudo = ConteudoDescarte.objects.get()
        self.assertFalse(conteudo.disponivel)
        resposta = self.client.get(
            reverse('forum:descarte_conteudo', args=[conteudo.id])
        )
        self.assertContains(resposta, self.MENSAGEM_INDISPONIVEL)
        self.assertNotContains(resposta, '<iframe')

    def test_campos_invalidos_do_conteudo_sao_rejeitados(self):
        casos = [
            ('titulo', {'titulo': ''}),
            ('titulo', {'titulo': 'x' * 151}),
            ('formato', {'formato': 'livro'}),
            ('url', {'url': ''}),
            ('url', {'url': 'nao-e-um-link'}),
            ('url', {'url': 'ftp://example.com/guia.pdf'}),
        ]
        for campo, invalido in casos:
            with self.subTest(campo=campo, valor=invalido):
                resposta = self.client.post(self.url_novo_conteudo,
                                            self.dados_conteudo(**invalido))
                self.assertEqual(resposta.status_code, 200)
                self.assertIn(campo, resposta.context['erros'])
                self.assertContains(resposta, 'Confira os campos destacados')
        self.assertEqual(ConteudoDescarte.objects.count(), 0)

    # Cadastro de empresa

    def test_estudio_cadastra_empresa(self):
        resposta = self.client.post(self.url_nova_empresa,
                                    self.dados_empresa())
        self.assertRedirects(resposta, self.url_lista)

        empresa = EmpresaDescarte.objects.get()
        self.assertEqual(empresa.estudio, self.estudio)
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Coleta Exemplo')
        self.assertContains(resposta, 'href="tel:8133334444"')

    def test_empresa_sem_email_e_sem_site_e_aceita(self):
        self.client.post(self.url_nova_empresa,
                         self.dados_empresa(email='', site=''))
        self.assertEqual(EmpresaDescarte.objects.count(), 1)

    def test_campos_invalidos_da_empresa_sao_rejeitados(self):
        casos = [
            ('nome', {'nome': ''}),
            ('nome', {'nome': 'x' * 151}),
            ('cidade', {'cidade': ''}),
            ('telefone', {'telefone': ''}),
            ('tipos_residuo', {'tipos_residuo': ''}),
            ('email', {'email': 'nao-e-email'}),
            ('site', {'site': 'nao-e-um-link'}),
        ]
        for campo, invalido in casos:
            with self.subTest(campo=campo, valor=invalido):
                resposta = self.client.post(self.url_nova_empresa,
                                            self.dados_empresa(**invalido))
                self.assertEqual(resposta.status_code, 200)
                self.assertIn(campo, resposta.context['erros'])
        self.assertEqual(EmpresaDescarte.objects.count(), 0)

    # Remoção

    def test_estudio_remove_o_proprio_conteudo(self):
        conteudo = self.conteudo_do_estudio()
        url = reverse('forum:descarte_conteudo_remover',
                      args=[self.estudio.id, conteudo.id])
        self.assertContains(self.client.get(url), 'Tem certeza')
        self.assertTrue(ConteudoDescarte.objects.exists())

        resposta = self.client.post(url)
        self.assertRedirects(resposta, self.url_lista)
        self.assertFalse(ConteudoDescarte.objects.exists())

    def test_estudio_remove_a_propria_empresa(self):
        empresa = EmpresaDescarte.objects.create(
            estudio=self.estudio, nome='Coleta Exemplo', cidade='Recife',
            telefone='(81) 3333-4444', tipos_residuo='perfurocortante',
        )
        url = reverse('forum:descarte_empresa_remover',
                      args=[self.estudio.id, empresa.id])
        self.assertRedirects(self.client.post(url), self.url_lista)
        self.assertFalse(EmpresaDescarte.objects.exists())

    def test_estudio_nao_remove_conteudo_da_plataforma(self):
        conteudo = ConteudoDescarte.objects.create(
            titulo='Conteúdo do admin', formato=ConteudoDescarte.SLIDES,
            url='https://example.com/admin.pdf',
        )
        url = reverse('forum:descarte_conteudo_remover',
                      args=[self.estudio.id, conteudo.id])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(ConteudoDescarte.objects.filter(id=conteudo.id)
                        .exists())
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Conteúdo do admin')
        self.assertNotContains(resposta, url)

    # Acesso e isolamento entre estúdios

    def test_o_que_um_estudio_cadastra_nao_aparece_para_outro(self):
        conteudo = self.conteudo_do_estudio()
        EmpresaDescarte.objects.create(
            estudio=self.estudio, nome='Coleta da Tinta Verde',
            cidade='Recife', telefone='(81) 3333-4444',
            tipos_residuo='perfurocortante',
        )
        self.client.force_login(self.dono_outro)

        resposta = self.client.get(self.url_lista)
        self.assertNotContains(resposta, 'Conteúdo do estúdio')
        self.assertNotContains(resposta, 'Coleta da Tinta Verde')
        self.assertEqual(self.client.get(
            reverse('forum:descarte_conteudo', args=[conteudo.id])
        ).status_code, 404)
        self.assertEqual(self.client.post(
            reverse('forum:descarte_conteudo_remover',
                    args=[self.outro.id, conteudo.id])
        ).status_code, 404)
        self.assertTrue(ConteudoDescarte.objects.filter(id=conteudo.id)
                        .exists())

    def test_conta_de_outro_estudio_nao_usa_o_formulario(self):
        self.client.force_login(self.dono_outro)
        self.assertEqual(self.client.get(self.url_novo_conteudo).status_code,
                         404)
        self.assertEqual(self.client.post(self.url_nova_empresa,
                                          self.dados_empresa()).status_code,
                         404)
        self.assertEqual(EmpresaDescarte.objects.count(), 0)

    def test_cadastro_exige_login(self):
        self.client.logout()
        for url in [self.url_novo_conteudo, self.url_nova_empresa]:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertRedirects(
                    resposta, f"{reverse('forum:entrar')}?next={url}"
                )

    def test_conta_sem_estudio_ve_so_a_plataforma(self):
        ConteudoDescarte.objects.create(
            titulo='Conteúdo do admin', formato=ConteudoDescarte.SLIDES,
            url='https://example.com/admin.pdf',
        )
        self.conteudo_do_estudio()
        sem_estudio = get_user_model().objects.create_user(
            username='equipe@example.com', email='equipe@example.com'
        )
        self.client.force_login(sem_estudio)

        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Conteúdo do admin')
        self.assertNotContains(resposta, 'Conteúdo do estúdio')
        self.assertNotContains(resposta, 'Cadastrar um conteúdo')


class AulasTest(TestCase):
    # Texto copiado da História 6.
    MENSAGEM_INCOMPLETA = 'Assista à aula até o final para concluí-la!'

    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Tinta Verde', cidade='Recife'
        )
        self.outro = Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        self.dono = criar_dono(self.estudio)
        self.dono_outro = criar_dono(self.outro)
        self.client.force_login(self.dono)
        # Aula da plataforma (sem estúdio), como as cadastradas no admin.
        self.aula = Aula.objects.create(
            titulo='Acolhimento de pessoas LGBTQIA+',
            url_video='https://www.youtube.com/watch?v=abcdefghijk',
            duracao_segundos=900,
            ordem=1,
        )
        self.url_lista = reverse('forum:estudio_aulas', args=[self.estudio.id])
        self.url_nova = reverse('forum:estudio_aula_nova',
                                args=[self.estudio.id])

    def url_aula(self, aula=None, estudio=None):
        estudio = estudio or self.estudio
        return reverse('forum:estudio_aula',
                       args=[estudio.id, (aula or self.aula).id])

    def url_progresso(self, aula=None, estudio=None):
        estudio = estudio or self.estudio
        return reverse('forum:estudio_aula_progresso',
                       args=[estudio.id, (aula or self.aula).id])

    def url_remover(self, aula, estudio=None):
        estudio = estudio or self.estudio
        return reverse('forum:estudio_aula_remover', args=[estudio.id, aula.id])

    def assistir(self, segundos, estudio=None, aula=None):
        return ProgressoAula.objects.create(
            estudio=estudio or self.estudio, aula=aula or self.aula,
            segundos_assistidos=segundos,
        )

    def dados_aula(self, **campos):
        dados = {
            'titulo': 'Atendimento a pessoas surdas',
            'descricao': 'Comunicação básica em Libras na recepção.',
            'url_video': 'https://youtu.be/zyxwvutsrqp',
            'minutos': '12',
            'segundos': '30',
        }
        dados.update(campos)
        return dados

    # Cenário 1: listar e assistir

    def test_lista_mostra_as_aulas_disponiveis(self):
        resposta = self.client.get(self.url_lista)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/aulas.html')
        self.assertContains(resposta, 'Acolhimento de pessoas LGBTQIA+')
        self.assertContains(resposta, '15:00')
        self.assertContains(resposta, 'Não iniciada')
        self.assertContains(resposta, self.url_aula())

    def test_lista_vazia_mostra_aviso(self):
        Aula.objects.all().delete()
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Ainda não há aulas cadastradas')

    def test_pagina_da_aula_incorpora_o_video_do_youtube(self):
        resposta = self.client.get(self.url_aula())
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/aula.html')
        self.assertContains(
            resposta, 'https://www.youtube.com/embed/abcdefghijk?enablejsapi=1'
        )
        self.assertContains(
            resposta, 'referrerpolicy="strict-origin-when-cross-origin"'
        )
        self.assertContains(resposta, 'js/aula.js')
        self.assertContains(resposta, 'csrfmiddlewaretoken')
        self.assertContains(resposta, 'value="Marcar como concluída"')
        self.assertContains(
            resposta, f'data-url-progresso="{self.url_progresso()}"'
        )
        self.assertContains(resposta, 'data-duracao="900"')

    def test_video_em_arquivo_usa_o_player_do_navegador(self):
        self.aula.url_video = 'https://example.com/aulas/libras.mp4'
        self.aula.save()
        resposta = self.client.get(self.url_aula())
        self.assertContains(resposta, 'data-tipo="arquivo"')
        self.assertContains(
            resposta,
            '<video id="aula-video" '
            'src="https://example.com/aulas/libras.mp4"',
        )

    def test_pagina_retoma_de_onde_parou(self):
        self.assistir(300)
        resposta = self.client.get(self.url_aula())
        self.assertContains(resposta, 'data-assistidos="300"')
        self.assertContains(resposta, 'start=300')
        self.assertContains(resposta, '5:00')

    # Progresso enviado pela página

    def test_progresso_guarda_o_maior_valor(self):
        resposta = self.client.post(self.url_progresso(), {'segundos': '300'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(),
                         {'segundos_assistidos': 300, 'concluida': False})

        self.client.post(self.url_progresso(), {'segundos': '120'})
        progresso = ProgressoAula.objects.get()
        self.assertEqual(progresso.segundos_assistidos, 300)

    def test_progresso_e_limitado_a_duracao_da_aula(self):
        self.client.post(self.url_progresso(), {'segundos': '5000'})
        self.assertEqual(ProgressoAula.objects.get().segundos_assistidos, 900)

    def test_progresso_invalido_e_rejeitado(self):
        self.assistir(100)
        for valor in ['', 'abc', '-10', '12.5']:
            with self.subTest(valor=valor):
                resposta = self.client.post(self.url_progresso(),
                                            {'segundos': valor})
                self.assertEqual(resposta.status_code, 400)
        self.assertEqual(ProgressoAula.objects.get().segundos_assistidos, 100)

    def test_progresso_nao_desfaz_conclusao_gravada_ao_mesmo_tempo(self):
        # A requisição de progresso leu a linha antes de o clique em
        # "Marcar como concluída" gravar; ela trabalha com a cópia velha.
        copia_velha = self.assistir(100)
        ProgressoAula.objects.filter(pk=copia_velha.pk).update(
            segundos_assistidos=900, concluida=True
        )
        with mock.patch.object(ProgressoAula.objects, 'get_or_create',
                               return_value=(copia_velha, False)):
            self.client.post(self.url_progresso(), {'segundos': '500'})
        no_banco = ProgressoAula.objects.get(pk=copia_velha.pk)
        self.assertTrue(no_banco.concluida)
        self.assertEqual(no_banco.segundos_assistidos, 900)

    def test_progresso_nao_volta_com_envio_atrasado(self):
        progresso = self.assistir(100)
        ProgressoAula.objects.filter(pk=progresso.pk).update(
            segundos_assistidos=300
        )
        progresso.registrar(200)
        self.assertEqual(progresso.segundos_assistidos, 300)

    def test_progresso_so_aceita_post(self):
        resposta = self.client.get(self.url_progresso())
        self.assertEqual(resposta.status_code, 405)

    def test_ha_um_unico_progresso_por_estudio_e_aula(self):
        for segundos in ['10', '20', '30']:
            self.client.post(self.url_progresso(), {'segundos': segundos})
        self.assertEqual(ProgressoAula.objects.count(), 1)
        with self.assertRaises(IntegrityError):
            ProgressoAula.objects.create(estudio=self.estudio, aula=self.aula)

    # Conclusão: quem decide é o servidor

    def test_concluir_depois_de_assistir_tudo(self):
        self.assistir(900)
        resposta = self.client.post(self.url_aula())
        self.assertRedirects(resposta, self.url_lista)
        self.assertTrue(ProgressoAula.objects.get().concluida)

    def test_aula_concluida_aparece_na_lista(self):
        self.assistir(900)
        resposta = self.client.post(self.url_aula(), follow=True)
        self.assertContains(resposta, 'aviso-success')
        self.assertContains(resposta, '<b>Concluída</b>', html=True)
        self.assertEqual(resposta.context['concluidas'], 1)

    def test_aula_concluida_nao_mostra_mais_o_botao(self):
        ProgressoAula.objects.create(
            estudio=self.estudio, aula=self.aula,
            segundos_assistidos=900, concluida=True,
        )
        resposta = self.client.get(self.url_aula())
        self.assertContains(resposta, 'Aula concluída.')
        self.assertNotContains(resposta, 'Marcar como concluída')

    def test_conclusao_aceita_folga_de_5_segundos(self):
        casos = [(895, True), (894, False)]
        for segundos, conclui in casos:
            with self.subTest(segundos=segundos):
                ProgressoAula.objects.all().delete()
                self.assistir(segundos)
                self.client.post(self.url_aula())
                self.assertEqual(ProgressoAula.objects.get().concluida,
                                 conclui)

    def test_conclusao_usa_os_segundos_enviados_pelo_formulario(self):
        self.assistir(600)
        resposta = self.client.post(self.url_aula(), {'segundos': '900'})
        self.assertRedirects(resposta, self.url_lista)
        progresso = ProgressoAula.objects.get()
        self.assertEqual(progresso.segundos_assistidos, 900)
        self.assertTrue(progresso.concluida)

    # Cenário 2: marcar como concluída sem assistir até o final

    def test_assistiu_10_de_15_minutos_nao_conclui(self):
        self.assistir(600)
        resposta = self.client.post(self.url_aula())
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, self.MENSAGEM_INCOMPLETA)
        self.assertFalse(ProgressoAula.objects.get().concluida)

    def test_sem_assistir_nada_nao_conclui(self):
        resposta = self.client.post(self.url_aula())
        self.assertContains(resposta, self.MENSAGEM_INCOMPLETA)
        self.assertFalse(ProgressoAula.objects.get().concluida)

    def test_segundos_parciais_no_formulario_nao_concluem(self):
        resposta = self.client.post(self.url_aula(), {'segundos': '600'})
        self.assertContains(resposta, self.MENSAGEM_INCOMPLETA)
        progresso = ProgressoAula.objects.get()
        self.assertEqual(progresso.segundos_assistidos, 600)
        self.assertFalse(progresso.concluida)

    # Cadastro de aula pelo estúdio e validações do formulário

    def test_estudio_cadastra_aula(self):
        resposta = self.client.post(self.url_nova, self.dados_aula())
        self.assertRedirects(resposta, self.url_lista)

        aula = Aula.objects.get(titulo='Atendimento a pessoas surdas')
        self.assertEqual(aula.estudio, self.estudio)
        self.assertEqual(aula.duracao_segundos, 750)
        self.assertEqual(aula.video(), ('youtube', 'zyxwvutsrqp'))

    def test_aula_do_estudio_aparece_na_lista_dele(self):
        self.client.post(self.url_nova, self.dados_aula())
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Atendimento a pessoas surdas')
        self.assertContains(resposta, 'Cadastrada pelo estúdio')

    def test_formulario_de_cadastro_aparece(self):
        resposta = self.client.get(self.url_nova)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/aula_form.html')
        self.assertContains(resposta, 'name="url_video"')

    def test_campos_invalidos_da_aula_sao_rejeitados(self):
        casos = [
            ('titulo', {'titulo': ''}),
            ('url_video', {'url_video': ''}),
            ('url_video', {'url_video': 'https://vimeo.com/123456'}),
            ('url_video', {'url_video': 'aula.mp4'}),
            ('url_video', {'url_video': 'ftp://example.com/aula.mp4'}),
            ('duracao', {'minutos': '', 'segundos': ''}),
            ('duracao', {'minutos': '0', 'segundos': '0'}),
            ('duracao', {'minutos': 'dez'}),
            ('duracao', {'segundos': '75'}),
            ('duracao', {'minutos': '-1'}),
            ('duracao', {'minutos': '601'}),
            ('titulo', {'titulo': 'x' * 151}),
        ]
        for campo, invalido in casos:
            with self.subTest(campo=campo, valor=invalido):
                resposta = self.client.post(
                    self.url_nova, self.dados_aula(**invalido)
                )
                self.assertEqual(resposta.status_code, 200)
                self.assertIn(campo, resposta.context['erros'])
                self.assertContains(resposta, 'Confira os campos destacados')
        self.assertEqual(Aula.objects.count(), 1)

    def test_erro_preserva_o_que_foi_digitado_na_aula(self):
        resposta = self.client.post(
            self.url_nova, self.dados_aula(segundos='75')
        )
        self.assertContains(resposta, 'value="Atendimento a pessoas surdas"')
        self.assertContains(resposta, 'Comunicação básica em Libras')

    def test_admin_rejeita_link_que_nao_permite_medir_o_progresso(self):
        aula = Aula(titulo='Aula externa', duracao_segundos=60,
                    url_video='https://example.com/pagina-da-aula')
        with self.assertRaises(ValidationError) as erro:
            aula.full_clean()
        self.assertIn('url_video', erro.exception.message_dict)

    def test_admin_rejeita_duracao_zero(self):
        aula = Aula(titulo='Aula vazia', duracao_segundos=0,
                    url_video='https://youtu.be/abcdefghijk')
        with self.assertRaises(ValidationError) as erro:
            aula.full_clean()
        self.assertIn('duracao_segundos', erro.exception.message_dict)

    # Remoção de aula pelo estúdio

    def test_estudio_remove_a_propria_aula(self):
        aula = Aula.objects.create(
            titulo='Aula do estúdio', estudio=self.estudio,
            url_video='https://youtu.be/zyxwvutsrqp', duracao_segundos=60,
        )
        resposta = self.client.get(self.url_remover(aula))
        self.assertContains(resposta, 'Tem certeza')
        self.assertTrue(Aula.objects.filter(id=aula.id).exists())

        resposta = self.client.post(self.url_remover(aula))
        self.assertRedirects(resposta, self.url_lista)
        self.assertFalse(Aula.objects.filter(id=aula.id).exists())

    def test_estudio_nao_remove_aula_da_plataforma(self):
        self.assertEqual(
            self.client.post(self.url_remover(self.aula)).status_code, 404
        )
        self.assertTrue(Aula.objects.filter(id=self.aula.id).exists())
        resposta = self.client.get(self.url_aula())
        self.assertNotContains(resposta, 'Remover esta aula')

    # 404 e isolamento entre estúdios

    def test_estudio_inexistente_retorna_404(self):
        urls = [
            reverse('forum:estudio_aulas', args=[999]),
            reverse('forum:estudio_aula_nova', args=[999]),
            reverse('forum:estudio_aula', args=[999, self.aula.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        url = reverse('forum:estudio_aula_progresso', args=[999, self.aula.id])
        self.assertEqual(
            self.client.post(url, {'segundos': '10'}).status_code, 404
        )

    def test_aula_inexistente_retorna_404(self):
        url = reverse('forum:estudio_aula', args=[self.estudio.id, 999])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)
        url = reverse('forum:estudio_aula_progresso',
                      args=[self.estudio.id, 999])
        self.assertEqual(
            self.client.post(url, {'segundos': '10'}).status_code, 404
        )

    def test_progresso_de_um_estudio_nao_vale_para_outro(self):
        self.assistir(900)
        self.client.post(self.url_aula())

        self.client.force_login(self.dono_outro)
        resposta = self.client.get(
            reverse('forum:estudio_aulas', args=[self.outro.id])
        )
        self.assertContains(resposta, 'Não iniciada')
        self.assertEqual(resposta.context['concluidas'], 0)

        resposta = self.client.post(self.url_aula(estudio=self.outro))
        self.assertContains(resposta, self.MENSAGEM_INCOMPLETA)
        self.assertFalse(
            ProgressoAula.objects.get(estudio=self.outro).concluida
        )

    def test_aula_cadastrada_por_um_estudio_nao_aparece_para_outro(self):
        aula = Aula.objects.create(
            titulo='Aula só da Tinta Verde', estudio=self.estudio,
            url_video='https://youtu.be/zyxwvutsrqp', duracao_segundos=60,
        )
        self.client.force_login(self.dono_outro)
        resposta = self.client.get(
            reverse('forum:estudio_aulas', args=[self.outro.id])
        )
        self.assertNotContains(resposta, 'Aula só da Tinta Verde')
        self.assertContains(resposta, 'Acolhimento de pessoas LGBTQIA+')

        self.assertEqual(
            self.client.get(self.url_aula(aula, self.outro)).status_code, 404
        )
        self.assertEqual(
            self.client.post(self.url_progresso(aula, self.outro),
                             {'segundos': '60'}).status_code, 404
        )
        self.assertEqual(
            self.client.post(self.url_remover(aula, self.outro)).status_code,
            404,
        )
        self.assertTrue(Aula.objects.filter(id=aula.id).exists())

    def test_perfil_tem_link_para_as_aulas(self):
        resposta = self.client.get(
            reverse('forum:estudio_perfil', args=[self.estudio.id])
        )
        self.assertContains(resposta, self.url_lista)


class ContaTest(TestCase):
    """Login dos estúdios: senha com hash, acesso exclusivo e bloqueio."""

    EMAIL = 'contato@tintaverde.com'
    SENHA = 'Tatuagem-Verde-2026'

    def setUp(self):
        # O contador de senhas erradas fica no cache; zera entre os testes.
        cache.clear()
        self.estudio = Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        self.usuario = get_user_model().objects.create_user(
            username=self.EMAIL, email=self.EMAIL, password=self.SENHA
        )
        self.estudio.usuario = self.usuario
        self.estudio.save()
        self.url_entrar = reverse('forum:entrar')
        self.url_novo = reverse('forum:estudio_novo')
        self.url_minha_area = reverse('forum:minha_area')
        self.url_perfil = reverse('forum:estudio_perfil', args=[self.estudio.id])
        self.url_estoque = reverse('forum:estudio_estoque',
                                   args=[self.estudio.id])

    def entrar(self, email=None, senha=None, **extra):
        dados = {
            'email': self.EMAIL if email is None else email,
            'senha': self.SENHA if senha is None else senha,
        }
        dados.update(extra)
        return self.client.post(self.url_entrar, dados)

    def logado(self):
        return '_auth_user_id' in self.client.session

    def dados_conta(self, **campos):
        dados = {
            'nome': 'Agulha Nova', 'cidade': 'Olinda',
            'email': 'Dono@AgulhaNova.com',
            'senha': 'Agulha-Nova-Recife-26', 'senha2': 'Agulha-Nova-Recife-26',
        }
        dados.update(campos)
        return dados

    def urls_exclusivas(self):
        aula = Aula.objects.create(
            titulo='Aula de teste', url_video='https://youtu.be/abcdefghijk',
            duracao_segundos=60,
        )
        item = ItemEstoque.objects.create(
            estudio=self.estudio, nome='Luva', tipo=ItemEstoque.MATERIAL,
            quantidade=1, fornecedor='EcoTattoo',
        )
        id_ = self.estudio.id
        return [
            reverse('forum:estudio_diagnostico', args=[id_]),
            reverse('forum:estudio_residuos', args=[id_]),
            reverse('forum:estudio_qrcode', args=[id_]),
            reverse('forum:estudio_estoque', args=[id_]),
            reverse('forum:estudio_estoque_novo', args=[id_]),
            reverse('forum:estudio_estoque_editar', args=[id_, item.id]),
            reverse('forum:estudio_estoque_remover', args=[id_, item.id]),
            reverse('forum:estudio_aulas', args=[id_]),
            reverse('forum:estudio_aula_nova', args=[id_]),
            reverse('forum:estudio_aula', args=[id_, aula.id]),
        ]

    # Criar conta

    def test_criar_conta_cria_estudio_e_usuario_e_ja_entra(self):
        resposta = self.client.post(self.url_novo, self.dados_conta())
        estudio = Estudio.objects.get(nome='Agulha Nova')
        self.assertRedirects(
            resposta, reverse('forum:estudio_diagnostico', args=[estudio.id])
        )
        self.assertEqual(estudio.usuario.email, 'dono@agulhanova.com')
        self.assertEqual(int(self.client.session['_auth_user_id']),
                         estudio.usuario.id)

    def test_senha_e_guardada_com_hash(self):
        self.client.post(self.url_novo, self.dados_conta())
        usuario = get_user_model().objects.get(email='dono@agulhanova.com')
        self.assertTrue(usuario.password.startswith('pbkdf2_sha256$'))
        self.assertNotIn('Agulha-Nova-Recife-26', usuario.password)
        self.assertTrue(usuario.check_password('Agulha-Nova-Recife-26'))

    def test_campos_invalidos_da_conta_sao_rejeitados(self):
        casos = [
            ('nome', {'nome': ''}),
            ('nome', {'nome': 'x' * 121}),
            ('cidade', {'cidade': ''}),
            ('cidade', {'cidade': 'x' * 81}),
            ('email', {'email': ''}),
            ('email', {'email': 'nao-e-um-email'}),
            ('email', {'email': 'CONTATO@TintaVerde.com'}),
            ('senha', {'senha': '', 'senha2': ''}),
            ('senha2', {'senha2': 'Outra-Senha-Forte-26'}),
            ('senha', {'senha': 'curta1', 'senha2': 'curta1'}),
            ('senha', {'senha': '12345678901', 'senha2': '12345678901'}),
            ('senha', {'senha': 'password', 'senha2': 'password'}),
            ('senha', {'senha': 'dono@agulhanova', 'senha2': 'dono@agulhanova'}),
        ]
        for campo, invalido in casos:
            with self.subTest(campo=campo, valor=invalido):
                resposta = self.client.post(self.url_novo,
                                            self.dados_conta(**invalido))
                self.assertEqual(resposta.status_code, 200)
                self.assertIn(campo, resposta.context['erros'])
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(Estudio.objects.count(), 1)
        self.assertFalse(self.logado())

    def test_erros_de_senha_aparecem_em_portugues(self):
        resposta = self.client.post(
            self.url_novo, self.dados_conta(senha='curta1', senha2='curta1')
        )
        self.assertContains(resposta, 'muito curta')

    def test_senhas_nunca_voltam_para_o_formulario(self):
        resposta = self.client.post(self.url_novo, self.dados_conta(nome=''))
        self.assertNotContains(resposta, 'Agulha-Nova-Recife-26')
        self.assertContains(resposta, 'value="dono@agulhanova.com"')

    def test_quem_ja_entrou_nao_ve_o_cadastro(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(self.url_novo)
        self.assertRedirects(resposta, self.url_minha_area,
                             fetch_redirect_response=False)

    # Entrar

    def test_entrar_com_senha_certa_leva_ao_perfil_do_estudio(self):
        resposta = self.entrar()
        self.assertRedirects(resposta, self.url_minha_area,
                             fetch_redirect_response=False)
        self.assertTrue(self.logado())
        resposta = self.client.get(self.url_minha_area)
        self.assertRedirects(resposta, self.url_perfil)

    def test_email_no_login_ignora_maiusculas_e_espacos(self):
        self.entrar(email='  CONTATO@TintaVerde.com ')
        self.assertTrue(self.logado())

    def test_senha_errada_nao_entra(self):
        resposta = self.entrar(senha='senha-errada')
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'E-mail ou senha incorretos.')
        self.assertFalse(self.logado())

    def test_email_sem_conta_recebe_a_mesma_mensagem(self):
        resposta = self.entrar(email='ninguem@example.com')
        self.assertContains(resposta, 'E-mail ou senha incorretos.')
        self.assertFalse(self.logado())

    def test_conta_criada_no_admin_entra_pelo_email(self):
        # No admin, o nome de usuário pode ser diferente do e-mail.
        conta = get_user_model().objects.create_user(
            username='inkflow', email='Contato@InkFlow.com',
            password='Conta-Do-Admin-2026',
        )
        outro = Estudio.objects.create(nome='INKFLOW', cidade='Recife',
                                       usuario=conta)
        resposta = self.entrar(email='contato@inkflow.com',
                               senha='Conta-Do-Admin-2026')
        self.assertTrue(self.logado())
        resposta = self.client.get(self.url_minha_area)
        self.assertRedirects(
            resposta, reverse('forum:estudio_perfil', args=[outro.id])
        )

    def test_email_e_nome_de_usuario_somam_no_mesmo_contador(self):
        get_user_model().objects.create_user(
            username='inkflow', email='contato@inkflow.com',
            password='Conta-Do-Admin-2026',
        )
        for _ in range(3):
            self.entrar(email='contato@inkflow.com', senha='errada')
        for _ in range(2):
            self.entrar(email='inkflow', senha='errada')
        resposta = self.entrar(email='contato@inkflow.com',
                               senha='Conta-Do-Admin-2026')
        self.assertContains(resposta, 'Muitas tentativas com a senha errada.')
        self.assertFalse(self.logado())

    def test_email_repetido_no_admin_nao_tira_o_acesso_do_estudio(self):
        # O admin criou antes (pk menor) uma conta com o mesmo e-mail.
        get_user_model().objects.create_user(
            username='equipe', email='dono@novo.com', password='Outra-Senha-2026'
        )
        conta = get_user_model().objects.create_user(
            username='dono@novo.com', email='dono@novo.com',
            password='Senha-Do-Estudio-26',
        )
        Estudio.objects.create(nome='Novo', cidade='Recife', usuario=conta)
        self.entrar(email='dono@novo.com', senha='Senha-Do-Estudio-26')
        self.assertEqual(int(self.client.session['_auth_user_id']), conta.pk)

    def test_clique_duplo_no_cadastro_nao_da_erro_500(self):
        # Simula o segundo envio: a checagem já passou, mas o primeiro envio
        # acabou de criar a conta com este e-mail.
        with mock.patch.object(EstudioNovoView, 'validar', return_value={}):
            resposta = self.client.post(self.url_novo,
                                        self.dados_conta(email=self.EMAIL))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('email', resposta.context['erros'])
        self.assertEqual(Estudio.objects.count(), 1)
        self.assertFalse(self.logado())

    def test_email_de_conta_do_admin_nao_pode_ser_reusado(self):
        get_user_model().objects.create_user(
            username='inkflow', email='contato@inkflow.com'
        )
        resposta = self.client.post(
            self.url_novo, self.dados_conta(email='contato@inkflow.com')
        )
        self.assertIn('email', resposta.context['erros'])

    def test_campos_vazios_no_login(self):
        resposta = self.entrar(email='', senha='')
        self.assertContains(resposta, 'Informe o e-mail e a senha.')

    def test_bloqueia_depois_de_5_senhas_erradas(self):
        for _ in range(5):
            self.entrar(senha='senha-errada')
        resposta = self.entrar()
        self.assertContains(resposta, 'Muitas tentativas com a senha errada.')
        self.assertFalse(self.logado())

    def test_bloqueio_vale_so_para_o_email_atacado(self):
        for _ in range(5):
            self.entrar(email='outro@example.com', senha='senha-errada')
        self.entrar()
        self.assertTrue(self.logado())

    def test_entrar_volta_para_a_pagina_pedida(self):
        resposta = self.entrar(next=self.url_estoque)
        self.assertRedirects(resposta, self.url_estoque)

    def test_entrar_ignora_endereco_de_outro_site(self):
        resposta = self.entrar(next='https://site-malicioso.example/')
        self.assertRedirects(resposta, self.url_minha_area,
                             fetch_redirect_response=False)

    def test_sessao_troca_de_identificador_no_login(self):
        sessao = self.client.session
        sessao['visitou'] = True
        sessao.save()
        antes = sessao.session_key
        self.entrar()
        self.assertNotEqual(self.client.session.session_key, antes)

    # Sair e alterar senha

    def test_sair_so_por_post(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse('forum:sair')).status_code,
                         405)
        self.assertTrue(self.logado())

        resposta = self.client.post(reverse('forum:sair'))
        self.assertRedirects(resposta, reverse('forum:index'))
        self.assertFalse(self.logado())

    def test_alterar_senha_mantem_a_sessao(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse('forum:alterar_senha'), {
            'senha_atual': self.SENHA,
            'senha': 'Nova-Senha-Inka-2026', 'senha2': 'Nova-Senha-Inka-2026',
        })
        self.assertRedirects(resposta, self.url_minha_area,
                             fetch_redirect_response=False)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('Nova-Senha-Inka-2026'))
        self.assertEqual(self.client.get(self.url_estoque).status_code, 200)

    def test_alterar_senha_com_senha_atual_errada(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse('forum:alterar_senha'), {
            'senha_atual': 'nao-e-a-senha',
            'senha': 'Nova-Senha-Inka-2026', 'senha2': 'Nova-Senha-Inka-2026',
        })
        self.assertIn('senha_atual', resposta.context['erros'])
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.SENHA))

    def test_alterar_senha_exige_login(self):
        url = reverse('forum:alterar_senha')
        resposta = self.client.get(url)
        self.assertRedirects(resposta, f'{self.url_entrar}?next={url}')

    # Acesso à área exclusiva

    def test_paginas_exclusivas_exigem_login(self):
        for url in self.urls_exclusivas():
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertRedirects(resposta, f'{self.url_entrar}?next={url}')

    def test_conta_de_outro_estudio_recebe_404(self):
        outro = Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        self.client.force_login(criar_dono(outro))
        for url in self.urls_exclusivas():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url).status_code, 404)

    def test_progresso_da_aula_sem_login_responde_403_em_json(self):
        aula = Aula.objects.create(
            titulo='Aula de teste', url_video='https://youtu.be/abcdefghijk',
            duracao_segundos=60,
        )
        url = reverse('forum:estudio_aula_progresso',
                      args=[self.estudio.id, aula.id])
        resposta = self.client.post(url, {'segundos': '10'})
        self.assertEqual(resposta.status_code, 403)
        self.assertIn('erro', resposta.json())
        self.assertEqual(ProgressoAula.objects.count(), 0)

    def test_minha_area_sem_login_vai_para_o_login(self):
        resposta = self.client.get(self.url_minha_area)
        self.assertRedirects(
            resposta, f'{self.url_entrar}?next={self.url_minha_area}'
        )

    def test_conta_sem_estudio_ligado(self):
        sem_estudio = get_user_model().objects.create_user(
            username='solto@example.com', email='solto@example.com'
        )
        self.client.force_login(sem_estudio)
        resposta = self.client.get(self.url_minha_area, follow=True)
        self.assertContains(resposta, 'não está ligada a nenhum estúdio')

    # Perfil público e menu

    def test_perfil_continua_publico_sem_os_links_exclusivos(self):
        resposta = self.client.get(self.url_perfil)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Tinta Verde')
        self.assertNotContains(resposta, self.url_estoque)
        self.assertNotContains(resposta, 'Área do estúdio')

    def test_dono_ve_os_links_exclusivos_no_perfil(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(self.url_perfil)
        self.assertContains(resposta, self.url_estoque)
        self.assertContains(resposta, reverse('forum:alterar_senha'))

    def test_conta_de_outro_estudio_nao_ve_os_links_no_perfil(self):
        outro = Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        self.client.force_login(criar_dono(outro))
        resposta = self.client.get(self.url_perfil)
        self.assertNotContains(resposta, self.url_estoque)

    def test_paginas_publicas_continuam_abertas(self):
        publicas = [
            'forum:index', 'forum:quem_somos', 'forum:sobre_projeto',
            'forum:fale_conosco', 'forum:estudios',
        ]
        for nome in publicas:
            with self.subTest(url=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code,
                                 200)
        self.assertEqual(self.client.get(self.url_perfil).status_code, 200)

    def test_descarte_e_exclusivo_dos_estudios(self):
        conteudo = ConteudoDescarte.objects.create(
            titulo='Como descartar agulhas corretamente',
            formato=ConteudoDescarte.VIDEO,
            url='https://www.youtube.com/watch?v=abcdefghijk',
        )
        urls = [reverse('forum:descarte'),
                reverse('forum:descarte_conteudo', args=[conteudo.id])]
        for url in urls:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertRedirects(resposta, f'{self.url_entrar}?next={url}')

        self.client.force_login(self.usuario)
        for url in urls:
            with self.subTest(url=url, logado=True):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_menu_mostra_entrar_ou_minha_area_e_sair(self):
        url_descarte = reverse('forum:descarte')
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertContains(resposta, f'href="{self.url_entrar}"')
        self.assertNotContains(resposta, 'class="form-sair"')
        self.assertNotContains(resposta, f'href="{url_descarte}"')

        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertContains(resposta, f'href="{self.url_minha_area}"')
        self.assertContains(resposta, 'class="form-sair"')
        self.assertContains(resposta, f'href="{url_descarte}"')
