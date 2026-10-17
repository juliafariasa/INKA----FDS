from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    CalculoResiduo,
    Contato,
    Diagnostico,
    Estudio,
    ItemLista,
    Material,
    MembroEquipe,
    Pilar,
    PraticaEstudio,
    Resposta,
    SecaoConteudo,
    Tecnologia,
)


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
    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Agulha Verde', cidade='Recife'
        )
        self.url = reverse('forum:estudio_diagnostico', args=[self.estudio.id])

    def responder(self, valores_por_pilar):
        dados = {}
        for sigla, valores in valores_por_pilar.items():
            praticas = PraticaEstudio.objects.filter(pilar__sigla=sigla)
            for pratica, valor in zip(praticas, valores):
                dados[f'pratica_{pratica.id}'] = valor
        return dados

    def test_cadastro_de_estudio_leva_ao_diagnostico(self):
        resposta = self.client.post(
            reverse('forum:estudio_novo'),
            {'nome': 'Tinta Viva', 'cidade': 'Olinda'},
        )
        estudio = Estudio.objects.get(nome='Tinta Viva')
        self.assertRedirects(
            resposta,
            reverse('forum:estudio_diagnostico', args=[estudio.id]),
        )

    def test_cadastro_sem_nome_e_rejeitado(self):
        resposta = self.client.post(
            reverse('forum:estudio_novo'), {'nome': '', 'cidade': 'Olinda'}
        )
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

    def test_refazer_cria_novo_diagnostico_e_usa_o_mais_recente(self):
        self.client.post(self.url, self.responder({
            'E': [0, 0, 0, 0], 'S': [0, 0, 0, 0], 'G': [0, 0, 0, 0],
        }))
        self.client.post(self.url, self.responder({
            'E': [2, 2, 2, 2], 'S': [2, 2, 2, 2], 'G': [2, 2, 2, 2],
        }))
        self.assertEqual(self.estudio.diagnosticos.count(), 2)
        self.assertEqual(self.estudio.ultimo_diagnostico().indice(), 100)


class SeloTest(TestCase):
    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Agulha Verde', cidade='Recife'
        )
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
        self.assertContains(resposta, 'Ainda sem selo')
        self.assertContains(resposta, 'ainda não fez o diagnóstico')

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

    def test_qrcode_aponta_para_o_perfil(self):
        url = reverse('forum:estudio_qrcode', args=[self.estudio.id])
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/estudio_qrcode.html')
        self.assertEqual(
            resposta.context['url_perfil'], 'http://testserver' + self.url
        )
        self.assertContains(resposta, 'src="data:image/png;base64,')


class ResiduoTest(TestCase):
    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Agulha Verde', cidade='Recife'
        )
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
