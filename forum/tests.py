import csv
import json
import os
import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import (
    Aula,
    CalculoResiduo,
    Campanha,
    Checklist,
    Contato,
    ConteudoDescarte,
    Diagnostico,
    DocumentoEstudio,
    EmpresaDescarte,
    Estudio,
    ItemChecklist,
    ItemEstoque,
    ItemLista,
    Material,
    MembroEquipe,
    MetaEsg,
    ParticipacaoCampanha,
    PasswordResetCode,
    PasswordResetToken,
    Pilar,
    PraticaEstudio,
    ProgressoAula,
    RegistroEquipe,
    Resposta,
    SecaoConteudo,
    Tecnologia,
    id_youtube,
)
from .indice import PESOS as PESOS_INDICE, indice_inka
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
        self.assertContains(resposta, 'DIAGNÓSTICO CONCLUÍDO')
        self.assertContains(
            resposta,
            '<div class="inka-resultado-numero">67 <span>/100</span></div>',
            html=True,
        )
        self.assertContains(resposta, 'Seu plano de ação')
        self.assertContains(resposta, 'Formação de novos profissionais')

    def test_resposta_faltando_nao_salva(self):
        dados = self.responder({
            'E': [2, 2, 2, 2], 'S': [2, 2, 2, 2], 'G': [2, 2, 2],
        })
        resposta = self.client.post(self.url, dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Diagnostico.objects.count(), 0)
        self.assertEqual(len(resposta.context['pendentes']), 1)
        self.assertContains(resposta, 'class="diagnostico-erro"', count=1)

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
        self.assertContains(resposta, 'DIAGNÓSTICO CONCLUÍDO')
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
        self.assertContains(resposta, 'MATERIAIS UTILIZADOS')
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
        self.assertNotContains(resposta, 'MATERIAIS UTILIZADOS')

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
        self.assertContains(resposta, 'Panorama do mês')
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
        self.assertContains(
            resposta,
            '<span class="inka-residuos-situacao">Diminuiu</span>',
            html=True,
        )
        self.assertContains(resposta, '<small>140 g</small>', html=True)

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
        self.assertContains(resposta, 'class="is-warning"', count=1)

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
        self.assertContains(resposta, 'Nenhuma empresa por aqui ainda')

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
        self.assertContains(resposta, 'Indisponível no momento', count=1)

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
        self.assertContains(resposta, 'CADASTRADO PELO SEU ESTÚDIO')

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
        self.assertContains(
            resposta, '<b class="status-concluida">Concluída ✓</b>', html=True
        )
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

    def test_entrar_com_senha_certa_leva_a_minha_area(self):
        resposta = self.entrar()
        self.assertRedirects(resposta, self.url_minha_area,
                             fetch_redirect_response=False)
        self.assertTrue(self.logado())
        # A Minha Área agora é uma página, e não um redirecionamento
        # para o perfil público.
        resposta = self.client.get(self.url_minha_area)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/minha_area.html')
        self.assertEqual(resposta.context['estudio'], self.estudio)

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
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/minha_area.html')
        self.assertEqual(resposta.context['estudio'], outro)

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


class RedefinirSenhaTest(TestCase):
    """Esqueci minha senha: código por e-mail, token de uso único e limites."""

    EMAIL = 'contato@tintaverde.com'
    SENHA = 'Tatuagem-Verde-2026'
    NOVA_SENHA = 'Agulha-Nova-Recife-26'
    ERRO_CODIGO = 'Código inválido ou expirado.'

    def setUp(self):
        # Os contadores de limite ficam no cache; zera entre os testes.
        cache.clear()
        # No site o e-mail sai numa thread. No teste ele é enviado na hora,
        # para a caixa de saída (mail.outbox) já estar preenchida.
        envio_na_hora = mock.patch(
            'forum.redefinicao_senha.em_segundo_plano',
            lambda funcao: funcao(),
        )
        envio_na_hora.start()
        self.addCleanup(envio_na_hora.stop)

        self.usuario = get_user_model().objects.create_user(
            username=self.EMAIL, email=self.EMAIL, password=self.SENHA
        )
        self.url_pedir = reverse('forum:api_redefinir_pedir')
        self.url_conferir = reverse('forum:api_redefinir_conferir')
        self.url_confirmar = reverse('forum:api_redefinir_confirmar')

    def postar(self, url, **dados):
        return self.client.post(url, json.dumps(dados),
                                content_type='application/json')

    def pedir(self, email=None):
        return self.postar(self.url_pedir, email=email or self.EMAIL)

    def conferir(self, codigo, email=None):
        return self.postar(self.url_conferir, email=email or self.EMAIL,
                           code=codigo)

    def confirmar(self, token, senha=None):
        return self.postar(self.url_confirmar, reset_token=token,
                           new_password=senha or self.NOVA_SENHA)

    def codigo_do_email(self):
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body)[1]

    def outro_codigo(self, codigo):
        return f'{(int(codigo) + 1) % 10 ** 6:06d}'

    def obter_token(self):
        self.pedir()
        return self.conferir(self.codigo_do_email()).json()['reset_token']

    # Endereços e telas

    def test_enderecos_da_api(self):
        self.assertEqual(self.url_pedir, '/api/auth/password-reset/request')
        self.assertEqual(self.url_conferir, '/api/auth/password-reset/verify')
        self.assertEqual(self.url_confirmar,
                         '/api/auth/password-reset/confirm')

    def test_as_tres_telas_abrem(self):
        for nome in ('esqueci_senha', 'esqueci_senha_codigo',
                     'esqueci_senha_nova'):
            resposta = self.client.get(reverse(f'forum:{nome}'))
            self.assertEqual(resposta.status_code, 200)
            self.assertContains(resposta, 'id="form-redefinir"')

    def test_tela_de_entrada_tem_link_esqueci_minha_senha(self):
        resposta = self.client.get(reverse('forum:entrar'))
        self.assertContains(
            resposta, f'href="{reverse("forum:esqueci_senha")}"'
        )

    # Passo 1: pedir o código

    def test_pedido_envia_codigo_de_6_digitos_e_guarda_so_o_hash(self):
        resposta = self.pedir()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.EMAIL])

        codigo = self.codigo_do_email()
        self.assertIn(codigo, mail.outbox[0].alternatives[0].content)
        self.assertIn('ignore este e-mail', mail.outbox[0].body)

        registro = PasswordResetCode.objects.get(user=self.usuario)
        self.assertNotIn(codigo, registro.code_hash)
        self.assertEqual(len(registro.code_hash), 64)
        validade = registro.expires_at - registro.created_at
        self.assertAlmostEqual(validade.total_seconds(), 600, delta=5)
        self.assertEqual(registro.ip, '127.0.0.1')

    def test_email_inexistente_recebe_a_mesma_resposta_e_nenhum_email(self):
        existente = self.pedir()
        mail.outbox.clear()

        inexistente = self.pedir('ninguem@example.com')
        self.assertEqual(inexistente.status_code, 200)
        self.assertEqual(inexistente.json(), existente.json())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PasswordResetCode.objects.count(), 1)

    def test_novo_pedido_invalida_o_codigo_anterior(self):
        self.pedir()
        primeiro = self.codigo_do_email()
        self.pedir()
        segundo = self.codigo_do_email()

        if primeiro != segundo:
            self.assertEqual(self.conferir(primeiro).status_code, 400)
        self.assertEqual(self.conferir(segundo).status_code, 200)

    # Passo 2: conferir o código

    def test_codigo_errado_e_recusado_e_conta_tentativa(self):
        self.pedir()
        resposta = self.conferir(self.outro_codigo(self.codigo_do_email()))
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'erro': self.ERRO_CODIGO})
        self.assertEqual(PasswordResetCode.objects.get().attempts, 1)
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_codigo_de_email_inexistente_tem_a_mesma_resposta(self):
        resposta = self.conferir('123456', email='ninguem@example.com')
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'erro': self.ERRO_CODIGO})

    def test_codigo_expirado_e_recusado(self):
        self.pedir()
        PasswordResetCode.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        resposta = self.conferir(self.codigo_do_email())
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'erro': self.ERRO_CODIGO})

    def test_cinco_tentativas_erradas_invalidam_o_codigo(self):
        self.pedir()
        codigo = self.codigo_do_email()
        for _ in range(5):
            self.assertEqual(
                self.conferir(self.outro_codigo(codigo)).status_code, 400
            )
        # Agora nem o código certo passa.
        self.assertEqual(self.conferir(codigo).status_code, 400)
        self.assertEqual(PasswordResetCode.objects.get().attempts, 5)

    def test_codigo_certo_devolve_token_e_nao_pode_ser_usado_de_novo(self):
        self.pedir()
        codigo = self.codigo_do_email()
        resposta = self.conferir(codigo)
        self.assertEqual(resposta.status_code, 200)

        token = resposta.json()['reset_token']
        self.assertGreaterEqual(len(token), 43)  # 32 bytes em base64
        registro = PasswordResetToken.objects.get(user=self.usuario)
        self.assertNotEqual(registro.token_hash, token)
        validade = registro.expires_at - registro.created_at
        self.assertAlmostEqual(validade.total_seconds(), 900, delta=5)
        self.assertIsNotNone(PasswordResetCode.objects.get().used_at)

        self.assertEqual(self.conferir(codigo).status_code, 400)

    # Passo 3: gravar a senha nova

    def test_confirmar_troca_a_senha_e_guarda_com_hash(self):
        resposta = self.confirmar(self.obter_token())
        self.assertEqual(resposta.status_code, 200)

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.NOVA_SENHA))
        self.assertFalse(self.usuario.check_password(self.SENHA))
        self.assertTrue(self.usuario.password.startswith('pbkdf2_sha256$'))

    def test_token_reutilizado_e_recusado(self):
        token = self.obter_token()
        self.assertEqual(self.confirmar(token).status_code, 200)

        resposta = self.confirmar(token, 'Outra-Senha-Forte-27')
        self.assertEqual(resposta.status_code, 400)
        self.assertTrue(resposta.json()['token_invalido'])
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.NOVA_SENHA))

    def test_token_expirado_ou_inventado_e_recusado(self):
        self.assertEqual(self.confirmar('token-inventado').status_code, 400)

        token = self.obter_token()
        PasswordResetToken.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.confirmar(token).status_code, 400)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.SENHA))

    def test_senha_fraca_ou_igual_a_atual_e_recusada_sem_gastar_o_token(self):
        token = self.obter_token()
        for senha in ('curta1', '12345678', self.SENHA):
            resposta = self.confirmar(token, senha)
            self.assertEqual(resposta.status_code, 400, senha)
            self.assertNotIn('token_invalido', resposta.json())
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.SENHA))

        # O mesmo token ainda serve para uma senha boa.
        self.assertEqual(self.confirmar(token).status_code, 200)

    def test_sessoes_abertas_sao_encerradas_apos_a_troca(self):
        url_minha_area = reverse('forum:minha_area')
        outro_navegador = Client()
        outro_navegador.login(username=self.EMAIL, password=self.SENHA)
        # Logada, a conta sem estúdio é mandada para a página inicial.
        self.assertRedirects(outro_navegador.get(url_minha_area),
                             reverse('forum:index'))

        self.confirmar(self.obter_token())

        resposta = outro_navegador.get(url_minha_area)
        self.assertRedirects(
            resposta, f'{reverse("forum:entrar")}?next={url_minha_area}'
        )
        self.assertTrue(
            Client().login(username=self.EMAIL, password=self.NOVA_SENHA)
        )

    def test_email_avisa_que_a_senha_foi_alterada_com_data_e_hora(self):
        token = self.obter_token()
        mail.outbox.clear()
        self.confirmar(token)

        self.assertEqual(len(mail.outbox), 1)
        aviso = mail.outbox[0]
        self.assertEqual(aviso.to, [self.EMAIL])
        self.assertIn('foi alterada', aviso.subject)
        agora = timezone.localtime()
        self.assertIn(agora.strftime('%d/%m/%Y'), aviso.body)
        self.assertRegex(aviso.body, r'às \d{2}:\d{2}')
        self.assertNotIn(self.NOVA_SENHA, aviso.body)

    def test_troca_de_senha_libera_o_bloqueio_de_login(self):
        url_entrar = reverse('forum:entrar')
        for _ in range(6):
            self.client.post(url_entrar,
                             {'email': self.EMAIL, 'senha': 'senha-errada'})
        self.confirmar(self.obter_token())

        self.client.post(url_entrar,
                         {'email': self.EMAIL, 'senha': self.NOVA_SENHA})
        self.assertIn('_auth_user_id', self.client.session)

    # Limites e segurança

    def test_limite_de_3_pedidos_por_email(self):
        for _ in range(3):
            self.assertEqual(self.pedir().status_code, 200)
        self.assertEqual(self.pedir().status_code, 429)
        self.assertEqual(len(mail.outbox), 3)

        # O limite é por e-mail digitado: vale igual para quem não tem conta.
        for _ in range(3):
            self.assertEqual(self.pedir('ninguem@example.com').status_code,
                             200)
        self.assertEqual(self.pedir('ninguem@example.com').status_code, 429)

    def test_limite_de_pedidos_por_ip(self):
        for numero in range(10):
            resposta = self.pedir(f'pessoa{numero}@example.com')
            self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.pedir('pessoa10@example.com').status_code, 429)

    def test_limite_de_conferencias_por_email(self):
        for _ in range(10):
            self.assertEqual(self.conferir('000000').status_code, 400)
        self.assertEqual(self.conferir('000000').status_code, 429)

    def test_fluxo_completo_nao_escreve_nada_nos_logs(self):
        with self.assertNoLogs(level='INFO'):
            self.confirmar(self.obter_token())

    def test_dados_fora_do_formato_sao_recusados(self):
        resposta = self.client.post(self.url_pedir, 'isto não é json',
                                    content_type='application/json')
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(self.postar(self.url_pedir).status_code, 400)
        self.assertEqual(self.client.get(self.url_pedir).status_code, 405)

    # Limpeza

    def test_comando_apaga_codigos_e_tokens_vencidos(self):
        token = self.obter_token()          # código usado + token válido
        outra = get_user_model().objects.create_user(
            username='outra@example.com', email='outra@example.com'
        )
        self.pedir('outra@example.com')     # código ainda válido
        vencido = PasswordResetCode.objects.create(
            user=outra, code_hash='x' * 64,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        call_command('limpar_codigos_expirados', stdout=mock.MagicMock())

        self.assertFalse(
            PasswordResetCode.objects.filter(user=self.usuario).exists()
        )
        self.assertFalse(
            PasswordResetCode.objects.filter(pk=vencido.pk).exists()
        )
        self.assertEqual(PasswordResetCode.objects.filter(user=outra).count(),
                         1)
        # O token ainda válido continua funcionando.
        self.assertEqual(self.confirmar(token).status_code, 200)


class EvolucaoTest(TestCase):
    """Painel de evolução: checklist de rotina, metas e diário."""

    MENSAGEM_META_DUPLICADA = (
        'Seu estúdio já tem uma meta em andamento para este indicador. '
        'Conclua ou remova a meta atual!'
    )
    MENSAGEM_META_JA_ALCANCADA = (
        'Seu estúdio já alcançou esse valor. '
        'Escolha uma meta mais desafiadora!'
    )

    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Tinta Verde', cidade='Recife'
        )
        self.outro = Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        self.client.force_login(criar_dono(self.estudio))
        id_ = self.estudio.id
        self.url_painel = reverse('forum:estudio_evolucao', args=[id_])
        self.url_checklist = reverse('forum:estudio_checklist', args=[id_])
        self.url_meta_nova = reverse('forum:estudio_meta_nova', args=[id_])
        self.itens = list(ItemChecklist.objects.all())
        self.hoje = timezone.localdate()

    def marcar(self, quantidade):
        ids = [item.id for item in self.itens[:quantidade]]
        return self.client.post(self.url_checklist, {'itens': ids})

    def dados_meta(self, **campos):
        dados = {
            'indicador': MetaEsg.CHECKLIST,
            'alvo': '80',
            'prazo': (self.hoje + timedelta(days=30)).isoformat(),
        }
        dados.update(campos)
        return dados

    def calcular_residuos(self, atendimentos):
        material = Material.objects.create(
            nome=f'Luva {atendimentos}', tipo=Material.CONTAMINADO,
            gramas_por_atendimento=10,
        )
        calculo = CalculoResiduo(estudio=self.estudio,
                                 atendimentos=atendimentos)
        calculo.calcular([material])
        calculo.save()
        return calculo

    # Acesso

    def test_painel_e_exclusivo_da_conta_do_estudio(self):
        url_do_outro = reverse('forum:estudio_evolucao', args=[self.outro.id])
        self.assertEqual(self.client.get(url_do_outro).status_code, 404)

        self.client.logout()
        resposta = self.client.get(self.url_painel)
        self.assertRedirects(
            resposta, f'{reverse("forum:entrar")}?next={self.url_painel}'
        )

    def test_perfil_e_diagnostico_levam_ao_painel(self):
        url_perfil = reverse('forum:estudio_perfil', args=[self.estudio.id])
        self.assertContains(self.client.get(url_perfil),
                            f'href="{self.url_painel}"')

        Diagnostico.objects.create(estudio=self.estudio, nota_e=8, nota_s=5,
                                   nota_g=7)
        url_diagnostico = reverse('forum:estudio_diagnostico',
                                  args=[self.estudio.id])
        self.assertContains(self.client.get(url_diagnostico),
                            f'href="{self.url_painel}"')

    # Checklist

    def test_checklist_inicial_tem_as_tres_categorias(self):
        self.assertEqual(len(self.itens), 9)
        resposta = self.client.get(self.url_painel)
        for rotulo in ('Higiene', 'Segurança', 'Gestão de resíduos'):
            self.assertContains(resposta, f'<legend>{rotulo}</legend>',
                                html=True)
        self.assertContains(resposta, 'type="checkbox"', count=9)
        self.assertContains(resposta, 'ainda não fez nenhuma verificação')

    def test_salvar_checklist_registra_as_praticas_cumpridas(self):
        resposta = self.marcar(6)
        self.assertRedirects(resposta, self.url_painel)

        checklist = Checklist.objects.get(estudio=self.estudio)
        self.assertEqual(checklist.data, self.hoje)
        self.assertEqual(checklist.cumpridos, 6)
        self.assertEqual(checklist.total_itens, 9)
        self.assertEqual(checklist.percentual(), 67)
        self.assertEqual(checklist.itens_cumpridos.count(), 6)

        resposta = self.client.get(self.url_painel)
        self.assertContains(resposta, 'checked', count=6)
        self.assertContains(resposta, 'Conferido hoje')
        self.assertNotContains(resposta, 'evo-lembrete')

    def test_refazer_no_mesmo_dia_atualiza_em_vez_de_duplicar(self):
        self.marcar(2)
        self.marcar(9)
        checklist = Checklist.objects.get(estudio=self.estudio)
        self.assertEqual(checklist.cumpridos, 9)
        self.assertEqual(checklist.percentual(), 100)

    def test_checklist_ignora_item_inexistente_ou_desativado(self):
        desativado = self.itens[0]
        desativado.ativo = False
        desativado.save()
        self.client.post(self.url_checklist, {
            'itens': [desativado.id, self.itens[1].id, '99999', 'abc'],
        })
        checklist = Checklist.objects.get(estudio=self.estudio)
        self.assertEqual(checklist.cumpridos, 1)
        self.assertEqual(checklist.total_itens, 8)

    def test_painel_lembra_quando_o_checklist_esta_atrasado(self):
        Checklist.objects.create(
            estudio=self.estudio, data=self.hoje - timedelta(days=7),
            cumpridos=9, total_itens=9,
        )
        resposta = self.client.get(self.url_painel)
        self.assertContains(resposta, 'A última verificação foi há 7 dias')

        Checklist.objects.update(data=self.hoje - timedelta(days=6))
        resposta = self.client.get(self.url_painel)
        self.assertNotContains(resposta, 'evo-lembrete')

    def test_checklist_de_outro_estudio_responde_404(self):
        url = reverse('forum:estudio_checklist', args=[self.outro.id])
        self.assertEqual(self.client.post(url, {}).status_code, 404)
        self.assertEqual(Checklist.objects.count(), 0)

    # Metas

    def test_definir_meta_guarda_o_valor_inicial(self):
        self.marcar(3)   # 33%
        resposta = self.client.post(self.url_meta_nova, self.dados_meta())
        self.assertRedirects(resposta, self.url_painel)

        meta = MetaEsg.objects.get(estudio=self.estudio)
        self.assertEqual(meta.alvo, 80)
        self.assertEqual(meta.valor_inicial, 33)
        self.assertEqual(meta.situacao(), 'Em andamento')
        self.assertEqual(meta.progresso(), 41)   # 33 de 80

        resposta = self.client.get(self.url_painel)
        self.assertContains(resposta, 'Cumprir 80% do checklist')

    def test_meta_repetida_para_o_mesmo_indicador_nao_e_criada(self):
        self.client.post(self.url_meta_nova, self.dados_meta())
        resposta = self.client.post(self.url_meta_nova,
                                    self.dados_meta(alvo='90'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, self.MENSAGEM_META_DUPLICADA)
        self.assertEqual(MetaEsg.objects.count(), 1)

        # Outro indicador pode.
        self.client.post(self.url_meta_nova,
                         self.dados_meta(indicador=MetaEsg.AULAS, alvo='2'))
        self.assertEqual(MetaEsg.objects.count(), 2)

    def test_meta_que_o_estudio_ja_alcancou_nao_e_criada(self):
        self.marcar(9)   # 100%
        resposta = self.client.post(self.url_meta_nova, self.dados_meta())
        self.assertContains(resposta, self.MENSAGEM_META_JA_ALCANCADA)
        self.assertEqual(MetaEsg.objects.count(), 0)

    def test_meta_com_dados_invalidos_nao_e_criada(self):
        ontem = (self.hoje - timedelta(days=1)).isoformat()
        casos = [
            self.dados_meta(indicador='outro'),
            self.dados_meta(alvo=''),
            self.dados_meta(alvo='0'),
            self.dados_meta(alvo='-5'),
            self.dados_meta(alvo='abc'),
            self.dados_meta(alvo='101'),
            self.dados_meta(prazo=''),
            self.dados_meta(prazo=ontem),
            self.dados_meta(prazo=self.hoje.isoformat()),
            self.dados_meta(prazo='31/12/2099'),
        ]
        for dados in casos:
            resposta = self.client.post(self.url_meta_nova, dados)
            self.assertEqual(resposta.status_code, 200, dados)
            self.assertContains(resposta, 'class="erro"')
        self.assertEqual(MetaEsg.objects.count(), 0)

    def test_meta_e_marcada_como_atingida_ao_abrir_o_painel(self):
        self.client.post(self.url_meta_nova, self.dados_meta())
        self.marcar(8)   # 89%
        resposta = self.client.get(self.url_painel)

        meta = MetaEsg.objects.get()
        self.assertIsNotNone(meta.atingida_em)
        self.assertEqual(meta.situacao(), 'Atingida')
        self.assertEqual(meta.progresso(), 100)
        self.assertContains(resposta,
                            'Meta atingida: Cumprir 80% do checklist.')

        # Com a meta concluída, o indicador aceita uma nova meta.
        self.client.post(self.url_meta_nova, self.dados_meta(alvo='100'))
        self.assertEqual(MetaEsg.objects.count(), 2)

    def test_meta_de_residuos_e_atingida_quando_o_total_diminui(self):
        self.calcular_residuos(50)   # 500 g
        self.client.post(self.url_meta_nova, self.dados_meta(
            indicador=MetaEsg.RESIDUOS, alvo='300'))
        meta = MetaEsg.objects.get()
        self.assertEqual(meta.valor_inicial, 500)
        self.assertEqual(meta.progresso(), 0)

        self.calcular_residuos(40)   # 400 g: metade do caminho
        self.assertEqual(meta.progresso(), 50)
        self.client.get(self.url_painel)
        self.assertIsNone(MetaEsg.objects.get().atingida_em)

        self.calcular_residuos(30)   # 300 g
        self.client.get(self.url_painel)
        self.assertIsNotNone(MetaEsg.objects.get().atingida_em)

    def test_meta_com_prazo_vencido_nao_e_marcada_como_atingida(self):
        meta = MetaEsg.objects.create(
            estudio=self.estudio, indicador=MetaEsg.CHECKLIST, alvo=50,
            prazo=self.hoje - timedelta(days=1),
        )
        self.marcar(9)
        resposta = self.client.get(self.url_painel)
        meta.refresh_from_db()
        self.assertIsNone(meta.atingida_em)
        self.assertEqual(meta.situacao(), 'Prazo vencido')
        self.assertContains(resposta, 'Prazo vencido')

    def test_remover_meta(self):
        meta = MetaEsg.objects.create(
            estudio=self.estudio, indicador=MetaEsg.AULAS, alvo=3,
            prazo=self.hoje + timedelta(days=10),
        )
        url = reverse('forum:estudio_meta_remover',
                      args=[self.estudio.id, meta.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertTrue(MetaEsg.objects.exists())

        self.assertRedirects(self.client.post(url), self.url_painel)
        self.assertFalse(MetaEsg.objects.exists())

    def test_nao_remove_meta_de_outro_estudio(self):
        meta = MetaEsg.objects.create(
            estudio=self.outro, indicador=MetaEsg.AULAS, alvo=3,
            prazo=self.hoje + timedelta(days=10),
        )
        url = reverse('forum:estudio_meta_remover',
                      args=[self.estudio.id, meta.id])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(MetaEsg.objects.exists())

    # Diário

    def test_diario_junta_o_que_o_estudio_registrou(self):
        Diagnostico.objects.create(estudio=self.estudio, nota_e=8, nota_s=5,
                                   nota_g=7)
        self.calcular_residuos(50)
        self.calcular_residuos(30)
        self.marcar(6)
        self.client.post(self.url_meta_nova, self.dados_meta())

        resposta = self.client.get(self.url_painel)
        textos = [evento['texto'] for evento in resposta.context['diario']]
        self.assertEqual(textos[-1], 'Estúdio cadastrado no INKA.')
        self.assertIn('Diagnóstico de maturidade ESG: índice 67 de 100, '
                      'selo Prata.', textos)
        self.assertIn('Cálculo de resíduos: 500 g em 50 atendimento(s).',
                      textos)
        self.assertIn('Cálculo de resíduos: 300 g em 30 atendimento(s), '
                      '200 g a menos que no cálculo anterior.', textos)
        self.assertIn('Checklist de boas práticas: 6 de 9 cumpridas (67%).',
                      textos)
        self.assertTrue(any(
            texto.startswith('Meta definida: Cumprir 80% do checklist')
            for texto in textos
        ))
        datas = [evento['quando'] for evento in resposta.context['diario']]
        self.assertEqual(datas, sorted(datas, reverse=True))
        self.assertContains(resposta, 'Estúdio cadastrado no INKA.')

    def test_diario_nao_mostra_registros_de_outro_estudio(self):
        Diagnostico.objects.create(estudio=self.outro, nota_e=9, nota_s=9,
                                   nota_g=9)
        resposta = self.client.get(self.url_painel)
        self.assertEqual(len(resposta.context['diario']), 1)

    def test_concluir_aula_guarda_a_data_e_entra_no_diario(self):
        aula = Aula.objects.create(
            titulo='Libras básica', url_video='https://youtu.be/abcdefghijk',
            duracao_segundos=60,
        )
        ProgressoAula.objects.create(estudio=self.estudio, aula=aula,
                                     segundos_assistidos=60)
        self.client.post(
            reverse('forum:estudio_aula', args=[self.estudio.id, aula.id])
        )
        progresso = ProgressoAula.objects.get()
        self.assertTrue(progresso.concluida)
        self.assertIsNotNone(progresso.concluida_em)

        resposta = self.client.get(self.url_painel)
        self.assertContains(resposta, 'Aula concluída: Libras básica.')
        self.assertEqual(resposta.context['aulas_concluidas'], 1)


class CampanhaTest(TestCase):
    """Vitrine de campanhas sociais com ONGs e projetos parceiros."""

    MENSAGEM_ENCERRADA = (
        'Esta campanha já foi encerrada. Veja as campanhas abertas!'
    )

    def setUp(self):
        self.estudio = Estudio.objects.create(
            nome='Tinta Verde', cidade='Recife'
        )
        self.outro = Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        self.usuario = criar_dono(self.estudio)
        self.campanha = Campanha.objects.create(
            titulo='Cobertura gratuita de cicatrizes', ong='Instituto Renascer',
            descricao='Tatuagens para cobrir cicatrizes de mastectomia.',
            cidade='Recife', email='contato@renascer.example',
        )
        self.url_lista = reverse('forum:campanhas')
        self.url_participar = self.url('participar', self.campanha)
        self.url_sair = self.url('sair', self.campanha)

    def url(self, acao, campanha, estudio=None):
        return reverse(f'forum:estudio_campanha_{acao}',
                       args=[(estudio or self.estudio).id, campanha.id])

    def test_vitrine_e_publica_e_mostra_os_estudios_participantes(self):
        ParticipacaoCampanha.objects.create(campanha=self.campanha,
                                            estudio=self.outro)
        resposta = self.client.get(self.url_lista)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Cobertura gratuita de cicatrizes')
        self.assertContains(resposta, 'Instituto Renascer')
        self.assertContains(resposta, 'mailto:contato@renascer.example')
        url_perfil = reverse('forum:estudio_perfil', args=[self.outro.id])
        self.assertContains(resposta, f'href="{url_perfil}"')
        # Sem login não há botão de participar, só o convite para entrar.
        self.assertNotContains(resposta, 'camp-botao')
        self.assertContains(resposta, 'Entre com a conta do estúdio')

    def test_sem_campanhas_mostra_estado_vazio(self):
        Campanha.objects.all().delete()
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Nenhuma campanha por aqui ainda.')

    def test_menu_tem_link_para_as_campanhas(self):
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertContains(resposta, f'href="{self.url_lista}"')

    def test_estudio_participa_e_a_campanha_aparece_no_perfil_publico(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, f'action="{self.url_participar}"')

        resposta = self.client.post(self.url_participar)
        self.assertRedirects(resposta, self.url_lista)
        self.assertEqual(list(self.campanha.estudios.all()), [self.estudio])

        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, f'action="{self.url_sair}"')
        self.assertNotContains(resposta, f'action="{self.url_participar}"')

        # O perfil é público: o cliente vê as ações sociais sem login.
        self.client.logout()
        url_perfil = reverse('forum:estudio_perfil', args=[self.estudio.id])
        resposta = self.client.get(url_perfil)
        self.assertContains(resposta, 'Ações sociais')
        self.assertContains(resposta, 'Cobertura gratuita de cicatrizes')

    def test_perfil_sem_campanhas_nao_mostra_acoes_sociais(self):
        url_perfil = reverse('forum:estudio_perfil', args=[self.estudio.id])
        self.assertNotContains(self.client.get(url_perfil), 'Ações sociais')

    def test_participar_duas_vezes_nao_duplica(self):
        self.client.force_login(self.usuario)
        self.client.post(self.url_participar)
        self.client.post(self.url_participar)
        self.assertEqual(ParticipacaoCampanha.objects.count(), 1)

    def test_campanha_encerrada_nao_aceita_participacao(self):
        self.client.force_login(self.usuario)
        ontem = timezone.localdate() - timedelta(days=1)
        vencida = Campanha.objects.create(
            titulo='Flash day', ong='Projeto Luz', descricao='Encerrada.',
            encerra_em=ontem,
        )
        desativada = Campanha.objects.create(
            titulo='Mutirão', ong='Projeto Luz', descricao='Desativada.',
            ativa=False,
        )
        for campanha in (vencida, desativada):
            resposta = self.client.post(
                self.url('participar', campanha), follow=True
            )
            self.assertContains(resposta, self.MENSAGEM_ENCERRADA)
        self.assertEqual(ParticipacaoCampanha.objects.count(), 0)

        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'camp-encerrada', count=2)
        self.assertNotContains(resposta,
                               f'action="{self.url("participar", vencida)}"')

    def test_campanha_que_encerra_hoje_ainda_esta_aberta(self):
        self.campanha.encerra_em = timezone.localdate()
        self.campanha.save()
        self.assertTrue(self.campanha.aberta())

    def test_sair_da_campanha(self):
        self.client.force_login(self.usuario)
        self.client.post(self.url_participar)
        self.assertRedirects(self.client.post(self.url_sair), self.url_lista)
        self.assertEqual(ParticipacaoCampanha.objects.count(), 0)

    def test_participar_exige_a_conta_dona_do_estudio(self):
        resposta = self.client.post(self.url_participar)
        self.assertRedirects(
            resposta, f'{reverse("forum:entrar")}?next={self.url_participar}'
        )

        self.client.force_login(self.usuario)
        url_do_outro = self.url('participar', self.campanha, self.outro)
        self.assertEqual(self.client.post(url_do_outro).status_code, 404)
        self.assertEqual(self.client.get(self.url_participar).status_code,
                         405)
        self.assertEqual(ParticipacaoCampanha.objects.count(), 0)

    def test_participacao_entra_no_diario_e_no_painel(self):
        self.client.force_login(self.usuario)
        self.client.post(self.url_participar)
        resposta = self.client.get(
            reverse('forum:estudio_evolucao', args=[self.estudio.id])
        )
        self.assertContains(
            resposta,
            'Entrou na campanha Cobertura gratuita de cicatrizes, '
            'com Instituto Renascer.',
        )
        self.assertEqual(resposta.context['total_campanhas'], 1)


class MelhoriasTest(TestCase):
    """Aviso do Fale Conosco, filtro de estúdios e perfil público."""

    def setUp(self):
        # No site o e-mail sai numa thread; no teste ele é enviado na hora.
        envio_na_hora = mock.patch(
            'forum.redefinicao_senha.em_segundo_plano',
            lambda funcao: funcao(),
        )
        envio_na_hora.start()
        self.addCleanup(envio_na_hora.stop)

    def enviar_contato(self):
        return self.client.post(reverse('forum:fale_conosco'), {
            'nome': 'Marina Souza', 'email': 'marina@example.com',
            'empresa': 'Estúdio Aurora', 'assunto': Contato.ASSUNTO_PARCERIA,
            'mensagem': 'Quero levar o INKA para o meu estúdio em Olinda.',
        })

    # Fale Conosco

    @override_settings(EMAIL_CONTATO='equipe@example.com')
    def test_fale_conosco_avisa_a_equipe_por_email(self):
        self.enviar_contato()
        self.assertEqual(Contato.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

        aviso = mail.outbox[0]
        self.assertEqual(aviso.to, ['equipe@example.com'])
        # Responder ao aviso escreve para quem mandou a mensagem.
        self.assertEqual(aviso.reply_to, ['marina@example.com'])
        self.assertEqual(aviso.subject, 'Fale Conosco: Proposta de parceria')
        self.assertIn('Marina Souza <marina@example.com>', aviso.body)
        self.assertIn('Estúdio Aurora', aviso.body)
        self.assertIn('Quero levar o INKA para o meu estúdio em Olinda.',
                      aviso.body)

    @override_settings(EMAIL_CONTATO='')
    def test_sem_email_da_equipe_a_mensagem_so_e_guardada(self):
        self.enviar_contato()
        self.assertEqual(Contato.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_CONTATO='equipe@example.com')
    def test_mensagem_invalida_nao_avisa_a_equipe(self):
        self.client.post(reverse('forum:fale_conosco'), {'nome': 'Ma'})
        self.assertEqual(len(mail.outbox), 0)

    # Lista de estúdios

    def test_lista_de_estudios_filtra_por_cidade(self):
        Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        Estudio.objects.create(nome='Agulha Viva', cidade='São Paulo')
        Estudio.objects.create(nome='Traço Fino', cidade='SÃO PAULO')
        url = reverse('forum:estudios')

        resposta = self.client.get(url)
        self.assertEqual(len(resposta.context['estudios']), 3)
        # Cidades escritas com maiúsculas diferentes viram uma opção só.
        self.assertEqual(resposta.context['cidades'], ['Recife', 'São Paulo'])

        resposta = self.client.get(url, {'cidade': 'são paulo'})
        nomes = [estudio.nome for estudio in resposta.context['estudios']]
        self.assertEqual(nomes, ['Agulha Viva', 'Traço Fino'])
        self.assertEqual(resposta.context['cidade'], 'São Paulo')
        self.assertContains(resposta, '2 estúdio(s) em São Paulo.')
        self.assertNotContains(resposta, 'Tinta Verde')

    def test_cidade_desconhecida_mostra_todos_os_estudios(self):
        Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        resposta = self.client.get(reverse('forum:estudios'),
                                   {'cidade': 'Manaus'})
        self.assertEqual(len(resposta.context['estudios']), 2)
        self.assertEqual(resposta.context['cidade'], '')

    def test_filtro_so_aparece_com_mais_de_uma_cidade(self):
        Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        url = reverse('forum:estudios')
        self.assertNotContains(self.client.get(url), 'estudios-filtro')

        Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        self.assertContains(self.client.get(url), 'class="estudios-filtro"')

    # Perfil público

    def test_perfil_publico_mostra_rotina_e_formacao(self):
        estudio = Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        url = reverse('forum:estudio_perfil', args=[estudio.id])
        self.assertNotContains(self.client.get(url), 'Rotina e formação')

        Checklist.objects.create(
            estudio=estudio, data=timezone.localdate(), cumpridos=8,
            total_itens=9,
        )
        aula = Aula.objects.create(
            titulo='Libras básica', url_video='https://youtu.be/abcdefghijk',
            duracao_segundos=60,
        )
        ProgressoAula.objects.create(estudio=estudio, aula=aula,
                                     concluida=True)

        resposta = self.client.get(url)
        self.assertContains(resposta, 'Rotina e formação')
        self.assertContains(resposta, '89% das práticas cumpridas')
        self.assertContains(resposta, '<b>1</b>', html=True)


class AjustesTecnicosTest(TestCase):
    """Correções da Fase 3: botão da lista, consultas, cache e deploy."""

    def criar_estudios(self, quantidade, inicio=0):
        for numero in range(inicio, inicio + quantidade):
            estudio = Estudio.objects.create(nome=f'Estúdio {numero}',
                                             cidade='Recife')
            Diagnostico.objects.create(estudio=estudio, nota_e=8, nota_s=5,
                                       nota_g=7)

    # Botão "Cadastrar meu estúdio"

    def test_visitante_vai_para_o_cadastro(self):
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertContains(
            resposta, f'href="{reverse("forum:estudio_novo")}"'
        )
        self.assertContains(resposta, 'Cadastrar meu estúdio')
        self.assertNotContains(resposta, 'Ir para a Minha Área')

    def test_estudio_logado_vai_para_a_minha_area(self):
        estudio = Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        self.client.force_login(criar_dono(estudio))
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertContains(resposta, 'Ir para a Minha Área')
        self.assertNotContains(resposta, 'Cadastrar meu estúdio')
        self.assertNotContains(
            resposta, f'href="{reverse("forum:estudio_novo")}"'
        )

    # Consultas

    def test_lista_de_estudios_nao_cresce_com_o_numero_de_estudios(self):
        url = reverse('forum:estudios')
        self.criar_estudios(2)
        with CaptureQueriesContext(connection) as poucos:
            self.client.get(url)
        self.criar_estudios(8, inicio=2)
        with CaptureQueriesContext(connection) as muitos:
            resposta = self.client.get(url)
        self.assertEqual(len(resposta.context['estudios']), 10)
        self.assertEqual(len(muitos), len(poucos))
        # Estúdios, últimos diagnósticos e pilares.
        self.assertEqual(len(muitos), 3)

    def test_lista_usa_o_diagnostico_mais_recente(self):
        estudio = Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        Diagnostico.objects.create(estudio=estudio, nota_e=9, nota_s=9,
                                   nota_g=9)
        recente = Diagnostico.objects.create(estudio=estudio, nota_e=8,
                                             nota_s=5, nota_g=2)
        Estudio.objects.create(nome='Sem diagnóstico', cidade='Recife')

        resposta = self.client.get(reverse('forum:estudios'))
        por_nome = {e.nome: e for e in resposta.context['estudios']}
        self.assertEqual(por_nome['Tinta Verde'].ultimo_diagnostico().id,
                         recente.id)
        self.assertEqual(por_nome['Tinta Verde'].ultimo_diagnostico().selo(),
                         'Bronze')
        self.assertIsNone(por_nome['Sem diagnóstico'].ultimo_diagnostico())
        self.assertContains(resposta, 'Bronze')
        self.assertContains(resposta, 'Ainda sem diagnóstico')

    def test_pilares_sao_buscados_uma_vez_por_diagnostico(self):
        estudio = Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        diagnostico = Diagnostico.objects.create(estudio=estudio, nota_e=8,
                                                 nota_s=5, nota_g=7)
        with CaptureQueriesContext(connection) as consultas:
            diagnostico.selo()
            diagnostico.pilares_ativos()
            diagnostico.notas_por_pilar()
        self.assertEqual(len(consultas), 1)
        self.assertEqual(diagnostico.selo(), 'Prata')

    def test_perfil_publico_tem_numero_de_consultas_travado(self):
        estudio = Estudio.objects.create(nome='Tinta Verde', cidade='Recife')
        Diagnostico.objects.create(estudio=estudio, nota_e=8, nota_s=5,
                                   nota_g=7)
        url = reverse('forum:estudio_perfil', args=[estudio.id])
        # Estúdio, diagnóstico, pilares, campanhas, checklist, aulas,
        # documentos e as 4 do Índice INKA (cálculos, estoque, aulas
        # disponíveis e campanha aberta). Diagnóstico e checklist são
        # buscados uma vez só, mesmo usados pelo perfil e pelo índice.
        with self.assertNumQueries(11):
            self.client.get(url)

    # Cache compartilhado entre os processos

    def test_cache_fica_no_banco(self):
        from django.conf import settings
        self.assertEqual(
            settings.CACHES['default']['BACKEND'],
            'django.core.cache.backends.db.DatabaseCache',
        )
        cache.set('teste-cache', 7, 60)
        self.assertEqual(cache.get('teste-cache'), 7)
        self.assertEqual(cache.incr('teste-cache'), 8)

    # requirements.txt

    def test_requirements_esta_em_utf8(self):
        caminho = Path(__file__).resolve().parent.parent / 'requirements.txt'
        conteudo = caminho.read_bytes()
        self.assertFalse(conteudo.startswith((b'\xff\xfe', b'\xfe\xff')))
        linhas = conteudo.decode('utf-8').split()
        self.assertIn('Django==6.1.1', linhas)
        self.assertIn('psycopg[binary]==3.3.9', linhas)

    # check --deploy com as variáveis do Render

    def rodar_check_deploy(self, **variaveis):
        ambiente = {
            nome: valor for nome, valor in os.environ.items()
            if nome not in ('DEBUG', 'DATABASE_URL', 'EMAIL_HOST')
        }
        ambiente.update({
            'RENDER': 'true',
            'SECRET_KEY': 'chave-de-teste-' + 'x' * 50,
            'PYTHONIOENCODING': 'utf-8',
        })
        ambiente.update(variaveis)
        raiz = Path(__file__).resolve().parent.parent
        return subprocess.run(
            [sys.executable, 'manage.py', 'check', '--deploy',
             '--fail-level', 'WARNING'],
            cwd=raiz, env=ambiente, capture_output=True, text=True,
            encoding='utf-8', timeout=120,
        )

    def test_check_deploy_passa_sem_smtp(self):
        resultado = self.rodar_check_deploy()
        self.assertEqual(resultado.returncode, 0,
                         resultado.stdout + resultado.stderr)

    def test_check_deploy_passa_com_smtp(self):
        resultado = self.rodar_check_deploy(EMAIL_HOST='smtp.example.com')
        self.assertEqual(resultado.returncode, 0,
                         resultado.stdout + resultado.stderr)


class PainelEquipeTest(TestCase):
    """Painel da equipe INKA: acesso, visão geral, estúdios e desativação."""

    MENSAGEM_SELO_INVALIDO = 'Selo não encontrado ou inválido!'

    def setUp(self):
        contas = get_user_model().objects
        self.admin = contas.create_user(
            username='admin', email='admin@inka.example', is_staff=True,
            is_superuser=True,
        )
        self.equipe = contas.create_user(
            username='equipe', email='equipe@inka.example', is_staff=True,
        )
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.dono = criar_dono(self.estudio)

    def urls_do_painel(self):
        return [
            reverse('forum:painel'),
            reverse('forum:painel_estudios'),
            reverse('forum:painel_estudio', args=[self.estudio.id]),
            reverse('forum:painel_estudio_situacao', args=[self.estudio.id]),
        ]

    def url_situacao(self, estudio=None):
        return reverse('forum:painel_estudio_situacao',
                       args=[(estudio or self.estudio).id])

    def envelhecer(self, estudio, dias=60):
        Estudio.objects.filter(id=estudio.id).update(
            criado_em=timezone.now() - timedelta(days=dias)
        )

    # Acesso

    def test_sem_login_vai_para_o_login(self):
        for url in self.urls_do_painel():
            resposta = self.client.get(url)
            self.assertRedirects(resposta,
                                 f'{reverse("forum:entrar")}?next={url}')

    def test_conta_de_estudio_recebe_404(self):
        self.client.force_login(self.dono)
        for url in self.urls_do_painel():
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_conta_da_equipe_recebe_200(self):
        for conta in (self.equipe, self.admin):
            self.client.force_login(conta)
            for url in self.urls_do_painel():
                self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_menu_mostra_o_painel_so_para_a_equipe(self):
        url_painel = reverse('forum:painel')
        self.client.force_login(self.dono)
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertNotContains(resposta, f'href="{url_painel}"')

        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse('forum:estudios'))
        self.assertContains(resposta, f'href="{url_painel}"')

    def test_equipe_entra_e_cai_no_painel(self):
        get_user_model().objects.create_user(
            username='ana@inka.example', email='ana@inka.example',
            password='Painel-Da-Equipe-2026', is_staff=True,
        )
        resposta = self.client.post(reverse('forum:entrar'), {
            'email': 'ana@inka.example', 'senha': 'Painel-Da-Equipe-2026',
        })
        self.assertRedirects(resposta, reverse('forum:painel'))

    def test_minha_area_leva_a_equipe_sem_estudio_ao_painel(self):
        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse('forum:minha_area'))
        self.assertRedirects(resposta, reverse('forum:painel'))

    # Desativar e reativar

    def test_desativar_exige_post_e_superusuario(self):
        self.client.force_login(self.admin)
        self.client.get(self.url_situacao())
        self.estudio.refresh_from_db()
        self.assertTrue(self.estudio.ativo)

        self.client.force_login(self.equipe)
        resposta = self.client.post(self.url_situacao(), follow=True)
        self.estudio.refresh_from_db()
        self.assertTrue(self.estudio.ativo)
        self.assertContains(resposta, 'Só administradores principais')
        self.assertFalse(RegistroEquipe.objects.exists())

    def test_superusuario_desativa_e_reativa_com_registro(self):
        self.client.force_login(self.admin)
        url_detalhe = reverse('forum:painel_estudio', args=[self.estudio.id])

        self.assertRedirects(self.client.post(self.url_situacao()),
                             url_detalhe)
        self.estudio.refresh_from_db()
        self.assertFalse(self.estudio.ativo)

        self.client.post(self.url_situacao())
        self.estudio.refresh_from_db()
        self.assertTrue(self.estudio.ativo)

        registros = list(RegistroEquipe.objects.order_by('id'))
        self.assertEqual([r.acao for r in registros],
                         ['Desativou o estúdio', 'Reativou o estúdio'])
        self.assertEqual(registros[0].usuario, self.admin)
        self.assertEqual(registros[0].nome_usuario, 'admin')
        self.assertEqual(registros[0].alvo,
                         f'Tinta Verde (#{self.estudio.id})')

    def test_estudio_desativado_some_do_publico(self):
        Diagnostico.objects.create(estudio=self.estudio, nota_e=9, nota_s=9,
                                   nota_g=9)
        self.estudio.ativo = False
        self.estudio.save()

        resposta = self.client.get(reverse('forum:estudios'))
        self.assertNotContains(resposta, 'Tinta Verde')

        # O perfil é o endereço do QR Code: responde como selo inválido.
        resposta = self.client.get(
            reverse('forum:estudio_perfil', args=[self.estudio.id])
        )
        self.assertEqual(resposta.status_code, 404)
        self.assertContains(resposta, self.MENSAGEM_SELO_INVALIDO,
                            status_code=404)
        self.assertNotContains(resposta, 'Ouro', status_code=404)

    def test_estudio_desativado_nao_aparece_entre_os_participantes(self):
        campanha = Campanha.objects.create(titulo='Cobertura', ong='ONG',
                                           descricao='Campanha.')
        ParticipacaoCampanha.objects.create(campanha=campanha,
                                            estudio=self.estudio)
        self.estudio.ativo = False
        self.estudio.save()
        resposta = self.client.get(reverse('forum:campanhas'))
        self.assertNotContains(resposta, 'Tinta Verde')

    def test_area_exclusiva_de_estudio_desativado_mostra_conta_suspensa(self):
        self.estudio.ativo = False
        self.estudio.save()
        self.client.force_login(self.dono)
        id_ = self.estudio.id
        for url in (reverse('forum:minha_area'),
                    reverse('forum:estudio_estoque', args=[id_]),
                    reverse('forum:estudio_qrcode', args=[id_]),
                    reverse('forum:estudio_evolucao', args=[id_])):
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 403, url)
            self.assertContains(resposta, 'Conta suspensa', status_code=403)
            self.assertContains(resposta, reverse('forum:fale_conosco'),
                                status_code=403)

        # Nada é gravado enquanto a conta está suspensa.
        resposta = self.client.post(
            reverse('forum:estudio_checklist', args=[id_]), {}
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(Checklist.objects.exists())

    def test_progresso_de_aula_de_estudio_desativado_responde_em_json(self):
        aula = Aula.objects.create(
            titulo='Libras', url_video='https://youtu.be/abcdefghijk',
            duracao_segundos=60,
        )
        self.estudio.ativo = False
        self.estudio.save()
        self.client.force_login(self.dono)
        resposta = self.client.post(
            reverse('forum:estudio_aula_progresso',
                    args=[self.estudio.id, aula.id]),
            {'segundos': '30'},
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertIn('suspensa', resposta.json()['erro'])

    # Visão geral

    def montar_plataforma(self):
        """Estúdios em situações diferentes, para conferir as contagens.

        Tinta Verde: novo, dois diagnósticos (vale o último, Prata).
        Bom Traço: antigo, Ouro, calculou resíduos agora.
        Sem Nada: antigo, nada registrado (parado).
        Baixa Nota: antigo, sem selo, checklist de 40 dias atrás (parado).
        Rotina: antigo, sem diagnóstico, checklist de 3 dias atrás.
        Suspenso: antigo, desativado (não conta como parado).
        """
        Diagnostico.objects.create(estudio=self.estudio, nota_e=9, nota_s=9,
                                   nota_g=9)
        diagnostico = Diagnostico.objects.create(estudio=self.estudio,
                                                 nota_e=8, nota_s=5, nota_g=7)
        # Garante a ordem pela data, como no site.
        Diagnostico.objects.filter(id=diagnostico.id).update(
            data=timezone.now() + timedelta(minutes=1)
        )

        bom = Estudio.objects.create(nome='Bom Traço', cidade='Olinda')
        Diagnostico.objects.create(estudio=bom, nota_e=9, nota_s=9, nota_g=9)
        CalculoResiduo.objects.create(
            estudio=bom, atendimentos=10, gramas_perfurocortante=120,
            gramas_contaminado=300, gramas_comum=80,
        )
        sem_nada = Estudio.objects.create(nome='Sem Nada', cidade='Recife')
        baixa = Estudio.objects.create(nome='Baixa Nota', cidade='Recife')
        Diagnostico.objects.create(estudio=baixa, nota_e=1, nota_s=1,
                                   nota_g=1)
        Checklist.objects.create(
            estudio=baixa, data=timezone.localdate() - timedelta(days=40),
            cumpridos=1, total_itens=9,
        )
        rotina = Estudio.objects.create(nome='Rotina', cidade='Recife')
        Checklist.objects.create(
            estudio=rotina, data=timezone.localdate() - timedelta(days=3),
            cumpridos=9, total_itens=9,
        )
        suspenso = Estudio.objects.create(nome='Suspenso', cidade='Recife',
                                          ativo=False)
        for estudio in (bom, sem_nada, baixa, rotina, suspenso):
            self.envelhecer(estudio)

        Contato.objects.create(nome='Ana', email='ana@example.com',
                               mensagem='Mensagem de teste para a equipe.',
                               data_envio=timezone.now())
        ConteudoDescarte.objects.create(
            titulo='Fora do ar', formato=ConteudoDescarte.VIDEO,
            url='https://example.com/v.mp4', disponivel=False,
        )
        return {'bom': bom, 'baixa': baixa, 'suspenso': suspenso}

    def test_numeros_da_visao_geral(self):
        self.montar_plataforma()
        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse('forum:painel'))
        panorama = resposta.context['panorama']

        self.assertEqual(panorama['estudios'], 6)
        self.assertEqual(panorama['estudios_ativos'], 5)
        self.assertEqual(panorama['novos_30_dias'], 1)
        self.assertEqual(panorama['com_diagnostico'], 3)
        selos = panorama['selos']
        self.assertEqual(
            {chave: selos[chave] for chave in
             ('ouro', 'prata', 'bronze', 'sem_selo', 'sem_diagnostico')},
            {'ouro': 1, 'prata': 1, 'bronze': 0, 'sem_selo': 1,
             'sem_diagnostico': 3},
        )
        # Média do último diagnóstico de cada um: (66,7 + 90 + 10) / 3.
        self.assertAlmostEqual(selos['indice_medio'], 55.56, places=2)
        self.assertEqual(panorama['checklists_7_dias'], 1)
        self.assertEqual(panorama['residuos_do_mes'], {
            'calculos': 1, 'perfurocortante': 120, 'contaminado': 300,
            'comum': 80,
        })
        self.assertEqual(panorama['contatos_sem_resposta'], 1)
        self.assertEqual(panorama['conteudos_indisponiveis'], 1)
        self.assertEqual([e.nome for e in panorama['parados']],
                         ['Baixa Nota', 'Sem Nada'])
        self.assertEqual(panorama['total_parados'], 2)
        self.assertContains(resposta, 'Estúdios parados (2)')

    def test_visao_geral_com_plataforma_vazia(self):
        Estudio.objects.all().delete()
        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse('forum:painel'))
        self.assertEqual(resposta.status_code, 200)
        self.assertIsNone(resposta.context['panorama']['selos']['indice_medio'])
        self.assertContains(resposta, 'Nenhum estúdio parado')

    # Lista de estúdios

    def nomes_da_lista(self, **filtros):
        resposta = self.client.get(reverse('forum:painel_estudios'), filtros)
        return [estudio.nome for estudio in resposta.context['pagina']]

    def test_lista_filtra_e_ordena(self):
        self.montar_plataforma()
        self.client.force_login(self.equipe)

        self.assertEqual(self.nomes_da_lista(selo='ouro'), ['Bom Traço'])
        self.assertEqual(self.nomes_da_lista(selo='prata'), ['Tinta Verde'])
        self.assertEqual(self.nomes_da_lista(selo='sem_diagnostico'),
                         ['Rotina', 'Sem Nada', 'Suspenso'])
        self.assertEqual(self.nomes_da_lista(situacao='desativados'),
                         ['Suspenso'])
        self.assertEqual(self.nomes_da_lista(cidade='olinda'), ['Bom Traço'])
        self.assertEqual(self.nomes_da_lista(busca='estudio'),
                         ['Tinta Verde'])   # pelo e-mail da conta
        self.assertEqual(self.nomes_da_lista(ordem='indice')[:3],
                         ['Bom Traço', 'Tinta Verde', 'Baixa Nota'])
        self.assertEqual(self.nomes_da_lista(ordem='recentes')[0],
                         'Tinta Verde')
        # Valores inválidos voltam ao padrão em vez de dar erro.
        self.assertEqual(len(self.nomes_da_lista(selo='diamante',
                                                 ordem='xyz')), 6)

    def test_lista_pagina_e_mantem_os_filtros(self):
        for numero in range(25):
            Estudio.objects.create(nome=f'Recife {numero:02d}',
                                   cidade='Recife')
        self.client.force_login(self.equipe)
        url = reverse('forum:painel_estudios')

        resposta = self.client.get(url, {'cidade': 'Recife'})
        self.assertEqual(resposta.context['pagina'].paginator.count, 26)
        self.assertEqual(len(resposta.context['pagina']), 20)
        self.assertContains(resposta, '?cidade=Recife&amp;pagina=2')
        # A tabela precisa aparecer no HTML, não só no contexto: um nome de
        # variável repetido no template já escondeu a lista inteira.
        self.assertContains(resposta, '>Recife 00</a>')
        self.assertContains(resposta, 'Página 1 de 2')

        resposta = self.client.get(url, {'cidade': 'Recife', 'pagina': '2'})
        self.assertEqual(len(resposta.context['pagina']), 6)

    def test_lista_nao_cresce_em_consultas_com_mais_estudios(self):
        self.client.force_login(self.equipe)
        url = reverse('forum:painel_estudios')
        self.client.get(url)   # aquece a sessão
        with CaptureQueriesContext(connection) as poucos:
            self.client.get(url)
        for numero in range(10):
            estudio = Estudio.objects.create(nome=f'E{numero}', cidade='X')
            Diagnostico.objects.create(estudio=estudio, nota_e=8, nota_s=8,
                                       nota_g=8)
        with CaptureQueriesContext(connection) as muitos:
            self.client.get(url)
        self.assertEqual(len(muitos), len(poucos))

    # Detalhe do estúdio

    def test_detalhe_mostra_historico_de_diagnosticos_e_diario(self):
        pratica = PraticaEstudio.objects.first()
        antigo = Diagnostico.objects.create(estudio=self.estudio, nota_e=9,
                                            nota_s=9, nota_g=9)
        Resposta.objects.create(diagnostico=antigo, pratica=pratica,
                                valor=Resposta.SIM)
        Diagnostico.objects.create(estudio=self.estudio, nota_e=8, nota_s=5,
                                   nota_g=7)
        ItemEstoque.objects.create(
            estudio=self.estudio, nome='Luva', tipo=ItemEstoque.MATERIAL,
            quantidade=0, fornecedor='EcoTattoo',
        )
        self.client.force_login(self.equipe)
        resposta = self.client.get(
            reverse('forum:painel_estudio', args=[self.estudio.id])
        )
        self.assertEqual(len(resposta.context['diagnosticos']), 2)
        self.assertContains(resposta, pratica.titulo)
        self.assertContains(resposta, 'Luva')
        self.assertContains(resposta, '(em falta)')
        self.assertContains(resposta, self.dono.email)
        self.assertContains(resposta, 'Estúdio cadastrado no INKA.')

    def test_detalhe_de_estudio_inexistente_responde_404(self):
        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse('forum:painel_estudio',
                                           args=[99999]))
        self.assertEqual(resposta.status_code, 404)


class PainelConteudoTest(TestCase):
    """Painel da equipe, segunda parte: contatos, conteúdo, moderação,
    registro de ações, relatório CSV e ajustes do /admin/."""

    def setUp(self):
        contas = get_user_model().objects
        self.admin = contas.create_user(
            username='admin', email='admin@inka.example', is_staff=True,
            is_superuser=True,
        )
        self.equipe = contas.create_user(
            username='equipe', email='equipe@inka.example', is_staff=True,
        )
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.dono = criar_dono(self.estudio)
        self.client.force_login(self.equipe)

    def ultimo_registro(self):
        return RegistroEquipe.objects.order_by('-id').first()

    # Acesso

    def test_paginas_novas_so_para_a_equipe(self):
        aula = Aula.objects.create(titulo='Libras', duracao_segundos=60,
                                   url_video='https://youtu.be/abcdefghijk')
        campanha = Campanha.objects.create(titulo='C', ong='O',
                                           descricao='D')
        urls = [
            reverse('forum:painel_contatos'),
            reverse('forum:painel_campanhas'),
            reverse('forum:painel_campanha_nova'),
            reverse('forum:painel_campanha_editar', args=[campanha.id]),
            reverse('forum:painel_aulas'),
            reverse('forum:painel_aula_nova'),
            reverse('forum:painel_aula_editar', args=[aula.id]),
            reverse('forum:painel_aula_remover', args=[aula.id]),
            reverse('forum:painel_descarte'),
            reverse('forum:painel_conteudo_novo'),
            reverse('forum:painel_empresa_nova'),
            reverse('forum:painel_checklist'),
            reverse('forum:painel_referencias'),
            reverse('forum:painel_moderacao'),
            reverse('forum:painel_registros'),
            reverse('forum:painel_relatorio_estudios'),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

        self.client.force_login(self.dono)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404, url)

        self.client.logout()
        for url in urls:
            self.assertRedirects(self.client.get(url),
                                 f'{reverse("forum:entrar")}?next={url}')

    def test_acoes_so_aceitam_post(self):
        contato = Contato.objects.create(
            nome='Ana', email='ana@example.com', mensagem='M' * 30,
            data_envio=timezone.now(),
        )
        campanha = Campanha.objects.create(titulo='C', ong='O',
                                           descricao='D')
        conteudo = ConteudoDescarte.objects.create(
            titulo='V', formato=ConteudoDescarte.VIDEO,
            url='https://example.com/v.mp4',
        )
        item = ItemChecklist.objects.first()
        urls = [
            reverse('forum:painel_contato_respondido', args=[contato.id]),
            reverse('forum:painel_campanha_situacao', args=[campanha.id]),
            reverse('forum:painel_conteudo_disponivel', args=[conteudo.id]),
            reverse('forum:painel_checklist_item', args=[item.id]),
            reverse('forum:painel_publicar', args=['aula', 1]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 405, url)
        self.assertFalse(RegistroEquipe.objects.exists())

    # Contatos

    def test_contatos_filtra_e_marca_como_respondido(self):
        pendente = Contato.objects.create(
            nome='Ana', email='ana@example.com', mensagem='M' * 30,
            assunto=Contato.ASSUNTO_PARCERIA, data_envio=timezone.now(),
        )
        Contato.objects.create(
            nome='Bia', email='bia@example.com', mensagem='M' * 30,
            respondido=True, data_envio=timezone.now(),
        )
        url = reverse('forum:painel_contatos')

        resposta = self.client.get(url)   # padrão: só os sem resposta
        self.assertEqual([c.nome for c in resposta.context['pagina']],
                         ['Ana'])
        self.assertContains(
            resposta,
            'mailto:ana@example.com?subject=Re%3A%20Proposta%20de%20parceria'
            '%20-%20INKA',
        )
        resposta = self.client.get(url, {'situacao': 'todos'})
        self.assertEqual(len(resposta.context['pagina']), 2)

        resposta = self.client.post(
            reverse('forum:painel_contato_respondido', args=[pendente.id]),
            {'situacao': 'todos', 'assunto': '', 'pagina': '1'},
        )
        self.assertRedirects(resposta, f'{url}?situacao=todos&pagina=1')
        pendente.refresh_from_db()
        self.assertTrue(pendente.respondido)
        self.assertEqual(self.ultimo_registro().acao,
                         'Marcou contato como respondido')

    # Campanhas

    def dados_campanha(self, **campos):
        dados = {'titulo': 'Cobertura de cicatrizes', 'ong': 'Instituto Luz',
                 'descricao': 'Tatuagens gratuitas.', 'cidade': 'Recife',
                 'email': '', 'site': '', 'encerra_em': '', 'ativa': 'on'}
        dados.update(campos)
        return dados

    def test_cadastrar_campanha_valida_e_publica(self):
        url = reverse('forum:painel_campanha_nova')
        resposta = self.client.post(url, self.dados_campanha(
            titulo='', email='nao-e-email', site='ftp://x', encerra_em='31/12'
        ))
        self.assertEqual(resposta.status_code, 200)
        for mensagem in ('Informe o título da campanha.',
                         'Informe um e-mail válido.',
                         'Informe um link válido',
                         'Informe uma data válida.'):
            self.assertContains(resposta, mensagem)
        self.assertFalse(Campanha.objects.exists())

        resposta = self.client.post(url, self.dados_campanha(
            encerra_em='2099-12-31'
        ))
        self.assertRedirects(resposta, reverse('forum:painel_campanhas'))
        campanha = Campanha.objects.get()
        self.assertEqual(campanha.encerra_em.isoformat(), '2099-12-31')
        self.assertEqual(self.ultimo_registro().acao, 'Cadastrou campanha')
        self.assertContains(self.client.get(reverse('forum:campanhas')),
                            'Cobertura de cicatrizes')

    def test_editar_e_encerrar_campanha(self):
        campanha = Campanha.objects.create(titulo='Antiga', ong='O',
                                           descricao='D')
        self.client.post(
            reverse('forum:painel_campanha_editar', args=[campanha.id]),
            self.dados_campanha(titulo='Nova', ativa=''),
        )
        campanha.refresh_from_db()
        self.assertEqual(campanha.titulo, 'Nova')
        self.assertFalse(campanha.ativa)

        self.client.post(
            reverse('forum:painel_campanha_situacao', args=[campanha.id])
        )
        campanha.refresh_from_db()
        self.assertTrue(campanha.ativa)
        self.assertEqual(self.ultimo_registro().acao, 'Reabriu campanha')

    # Aulas

    def dados_aula(self, **campos):
        dados = {'titulo': 'Acolhimento', 'descricao': '',
                 'url_video': 'https://youtu.be/abcdefghijk',
                 'minutos': '15', 'segundos': '0'}
        dados.update(campos)
        return dados

    def test_cadastrar_aula_da_plataforma(self):
        url = reverse('forum:painel_aula_nova')
        resposta = self.client.post(url, self.dados_aula(
            url_video='https://example.com/pagina', minutos='0', segundos='0'
        ))
        self.assertContains(resposta, Aula.MENSAGEM_URL_VIDEO)
        self.assertContains(resposta, 'Informe a duração do vídeo.')

        self.client.post(url, self.dados_aula())
        aula = Aula.objects.get()
        self.assertIsNone(aula.estudio)
        self.assertEqual(aula.duracao_segundos, 900)

        # Aparece para todos os estúdios.
        self.client.force_login(self.dono)
        resposta = self.client.get(
            reverse('forum:estudio_aulas', args=[self.estudio.id])
        )
        self.assertContains(resposta, 'Acolhimento')

    def test_painel_e_estudio_usam_a_mesma_validacao_de_aula(self):
        dados = self.dados_aula(titulo='', minutos='700')
        resposta = self.client.post(reverse('forum:painel_aula_nova'), dados)
        self.client.force_login(self.dono)
        do_estudio = self.client.post(
            reverse('forum:estudio_aula_nova', args=[self.estudio.id]), dados
        )
        self.assertEqual(resposta.context['erros'],
                         do_estudio.context['erros'])

    def test_aula_de_estudio_nao_e_editada_nem_removida_pelo_painel(self):
        aula = Aula.objects.create(titulo='Do estúdio', duracao_segundos=60,
                                   url_video='https://youtu.be/abcdefghijk',
                                   estudio=self.estudio)
        for nome in ('painel_aula_editar', 'painel_aula_remover'):
            url = reverse(f'forum:{nome}', args=[aula.id])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, self.dados_aula())
                             .status_code, 404)
        self.assertTrue(Aula.objects.filter(id=aula.id).exists())

    def test_editar_e_remover_aula_da_plataforma(self):
        aula = Aula.objects.create(titulo='Libras', duracao_segundos=125,
                                   url_video='https://youtu.be/abcdefghijk')
        url_editar = reverse('forum:painel_aula_editar', args=[aula.id])
        resposta = self.client.get(url_editar)
        self.assertEqual(resposta.context['dados']['minutos'], '2')
        self.assertEqual(resposta.context['dados']['segundos'], '5')

        self.client.post(url_editar, self.dados_aula(titulo='Libras II'))
        aula.refresh_from_db()
        self.assertEqual(aula.titulo, 'Libras II')

        url_remover = reverse('forum:painel_aula_remover', args=[aula.id])
        self.assertContains(self.client.get(url_remover), 'Libras II')
        self.assertRedirects(self.client.post(url_remover),
                             reverse('forum:painel_aulas'))
        self.assertFalse(Aula.objects.exists())
        self.assertEqual(self.ultimo_registro().acao, 'Removeu aula')

    # Descarte

    def test_cadastrar_conteudo_e_empresa_da_plataforma(self):
        self.client.post(reverse('forum:painel_conteudo_novo'), {
            'titulo': 'Guia', 'formato': ConteudoDescarte.SLIDES,
            'url': 'https://example.com/guia.pdf', 'descricao': '',
            'disponivel': 'on',
        })
        conteudo = ConteudoDescarte.objects.get()
        self.assertIsNone(conteudo.estudio)

        resposta = self.client.post(reverse('forum:painel_empresa_nova'), {
            'nome': 'Coleta', 'cidade': 'Recife', 'telefone': '81 9999-0000',
            'email': 'ruim', 'site': '', 'tipos_residuo': 'contaminado',
        })
        self.assertContains(resposta, 'Informe um e-mail válido.')
        self.assertFalse(EmpresaDescarte.objects.exists())

    def test_marcar_conteudo_de_estudio_fora_do_ar_pela_moderacao(self):
        conteudo = ConteudoDescarte.objects.create(
            titulo='Do estúdio', formato=ConteudoDescarte.VIDEO,
            url='https://example.com/v.mp4', estudio=self.estudio,
        )
        resposta = self.client.post(
            reverse('forum:painel_conteudo_disponivel', args=[conteudo.id]),
            {'voltar': 'moderacao'},
        )
        self.assertRedirects(resposta, reverse('forum:painel_moderacao'))
        conteudo.refresh_from_db()
        self.assertFalse(conteudo.disponivel)
        self.assertEqual(self.ultimo_registro().acao,
                         'Marcou conteúdo como indisponível')
        # Mas o painel não edita nem remove o conteúdo do estúdio.
        url = reverse('forum:painel_conteudo_editar', args=[conteudo.id])
        self.assertEqual(self.client.get(url).status_code, 404)

    # Checklist e referências

    def test_desativar_item_do_checklist(self):
        item = ItemChecklist.objects.first()
        url = reverse('forum:painel_checklist_item', args=[item.id])

        resposta = self.client.post(url, {'ordem': 'abc'}, follow=True)
        self.assertContains(resposta, 'Use uma ordem de 0 a 999.')

        # Sem "ativo": desativa. O follow mostra a mensagem de sucesso aqui,
        # para ela não aparecer na página do estúdio logo depois.
        self.client.post(url, {'ordem': '50'}, follow=True)
        item.refresh_from_db()
        self.assertEqual(item.ordem, 50)
        self.assertFalse(item.ativo)
        self.assertEqual(self.ultimo_registro().acao,
                         'Alterou item do checklist')

        self.client.force_login(self.dono)
        resposta = self.client.get(
            reverse('forum:estudio_evolucao', args=[self.estudio.id])
        )
        self.assertNotContains(resposta, item.texto)

    def test_referencias_mostram_praticas_e_materiais(self):
        resposta = self.client.get(reverse('forum:painel_referencias'))
        self.assertContains(resposta, PraticaEstudio.objects.first().titulo)
        self.assertContains(resposta, Material.objects.first().nome)
        self.assertContains(resposta, 'altera as notas e os selos')

    # Moderação

    def test_publicar_para_todos_cria_uma_copia(self):
        original = Aula.objects.create(
            titulo='Aula do estúdio', duracao_segundos=60,
            url_video='https://youtu.be/abcdefghijk', estudio=self.estudio,
        )
        url = reverse('forum:painel_publicar', args=['aula', original.id])
        self.assertRedirects(self.client.post(url),
                             reverse('forum:painel_moderacao'))

        copia = Aula.objects.get(estudio=None)
        self.assertEqual(copia.titulo, 'Aula do estúdio')
        self.assertTrue(Aula.objects.filter(id=original.id,
                                            estudio=self.estudio).exists())
        self.assertIn('Tinta Verde', self.ultimo_registro().alvo)

        resposta = self.client.post(url, follow=True)
        self.assertContains(resposta,
                            'Já existe um item igual publicado para todos.')
        self.assertEqual(Aula.objects.filter(estudio=None).count(), 1)

    def test_publicar_empresa_e_conteudo(self):
        empresa = EmpresaDescarte.objects.create(
            nome='Coleta', cidade='Recife', telefone='81',
            tipos_residuo='comum', estudio=self.estudio,
        )
        conteudo = ConteudoDescarte.objects.create(
            titulo='Vídeo', formato=ConteudoDescarte.VIDEO,
            url='https://example.com/v.mp4', estudio=self.estudio,
        )
        self.client.post(reverse('forum:painel_publicar',
                                 args=['empresa', empresa.id]))
        self.client.post(reverse('forum:painel_publicar',
                                 args=['conteudo', conteudo.id]))
        self.assertTrue(EmpresaDescarte.objects.filter(estudio=None).exists())
        self.assertTrue(ConteudoDescarte.objects.filter(estudio=None).exists())

    def test_publicar_tipo_invalido_ou_item_da_plataforma_responde_404(self):
        da_plataforma = Aula.objects.create(
            titulo='Já é de todos', duracao_segundos=60,
            url_video='https://youtu.be/abcdefghijk',
        )
        for args in (['outro', 1], ['aula', da_plataforma.id]):
            url = reverse('forum:painel_publicar', args=args)
            self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(Aula.objects.count(), 1)

    # Registro de ações

    def test_registro_lista_as_acoes(self):
        RegistroEquipe.registrar(self.admin, 'Desativou o estúdio',
                                 'Tinta Verde (#1)')
        resposta = self.client.get(reverse('forum:painel_registros'))
        self.assertContains(resposta, 'Desativou o estúdio')
        self.assertContains(resposta, 'admin')

    # Relatório CSV

    def test_relatorio_csv(self):
        Diagnostico.objects.create(estudio=self.estudio, nota_e=9, nota_s=9,
                                   nota_g=9)
        Diagnostico.objects.create(estudio=self.estudio, nota_e=8, nota_s=5,
                                   nota_g=7)
        Checklist.objects.create(estudio=self.estudio,
                                 data=timezone.localdate(), cumpridos=6,
                                 total_itens=9)
        CalculoResiduo.objects.create(
            estudio=self.estudio, atendimentos=10, gramas_perfurocortante=10,
            gramas_contaminado=20, gramas_comum=30,
        )
        aula = Aula.objects.create(titulo='A', duracao_segundos=60,
                                   url_video='https://youtu.be/abcdefghijk')
        ProgressoAula.objects.create(estudio=self.estudio, aula=aula,
                                     concluida=True)
        campanha = Campanha.objects.create(titulo='C', ong='O',
                                           descricao='D')
        ParticipacaoCampanha.objects.create(campanha=campanha,
                                            estudio=self.estudio)
        Estudio.objects.create(nome='São João Ink', cidade='Caruaru',
                               ativo=False)

        resposta = self.client.get(reverse('forum:painel_relatorio_estudios'))
        self.assertEqual(resposta['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('estudios-inka.csv', resposta['Content-Disposition'])

        texto = resposta.content.decode('utf-8')
        self.assertTrue(texto.startswith('\ufeff'))
        linhas = list(csv.reader(texto.lstrip('\ufeff').splitlines(),
                                 delimiter=';'))
        self.assertEqual(linhas[0][:6], ['Estúdio', 'Cidade', 'Cadastro',
                                         'Situação', 'Selo', 'Índice'])
        self.assertEqual(len(linhas), 3)   # cabeçalho + um por estúdio

        por_nome = {linha[0]: linha for linha in linhas[1:]}
        sao_joao = por_nome['São João Ink']
        self.assertEqual(sao_joao[3], 'Desativado')
        self.assertEqual(sao_joao[4], 'Sem diagnóstico')

        tinta = por_nome['Tinta Verde']
        self.assertEqual(tinta[4], 'Prata')          # vale o último
        self.assertEqual(tinta[5], '67')
        self.assertEqual(tinta[6:9], ['8,0', '5,0', '7,0'])
        self.assertEqual(tinta[11], '67')            # 6 de 9 no checklist
        self.assertEqual(tinta[13], '60')            # gramas do cálculo
        self.assertEqual(tinta[14:16], ['1', '1'])   # aulas e campanhas
        self.assertEqual(self.ultimo_registro().acao,
                         'Baixou o relatório de estúdios')

    def test_relatorio_csv_nao_deixa_texto_virar_formula(self):
        Estudio.objects.create(nome='=HYPERLINK("http://example.com")',
                               cidade='@SOMA(A1)')
        resposta = self.client.get(reverse('forum:painel_relatorio_estudios'))
        linhas = list(csv.reader(
            resposta.content.decode('utf-8').lstrip('\ufeff').splitlines(),
            delimiter=';',
        ))
        celulas = [linha[:2] for linha in linhas[1:]]
        self.assertIn(["'=HYPERLINK(\"http://example.com\")", "'@SOMA(A1)"],
                      celulas)
        self.assertIn(['Tinta Verde', 'Recife'], celulas)

    # /admin/ do Django

    def test_acoes_do_admin(self):
        self.client.force_login(self.admin)
        contato = Contato.objects.create(
            nome='Ana', email='ana@example.com', mensagem='M' * 30,
            data_envio=timezone.now(),
        )
        self.client.post(reverse('admin:forum_contato_changelist'), {
            'action': 'marcar_respondido', '_selected_action': [contato.id],
        })
        contato.refresh_from_db()
        self.assertTrue(contato.respondido)

        conteudo = ConteudoDescarte.objects.create(
            titulo='V', formato=ConteudoDescarte.VIDEO,
            url='https://example.com/v.mp4',
        )
        self.client.post(reverse('admin:forum_conteudodescarte_changelist'), {
            'action': 'marcar_indisponivel',
            '_selected_action': [conteudo.id],
        })
        conteudo.refresh_from_db()
        self.assertFalse(conteudo.disponivel)

    def test_admin_mostra_respostas_do_diagnostico(self):
        self.client.force_login(self.admin)
        diagnostico = Diagnostico.objects.create(estudio=self.estudio)
        pratica = PraticaEstudio.objects.first()
        Resposta.objects.create(diagnostico=diagnostico, pratica=pratica,
                                valor=Resposta.PARCIAL)
        resposta = self.client.get(reverse('admin:forum_diagnostico_change',
                                           args=[diagnostico.id]))
        self.assertContains(resposta, pratica.titulo)
        self.assertContains(resposta, 'Parcial')


class MinhaAreaTest(TestCase):
    """Fase 1: a Minha Área como tela inicial do estúdio (História 7)."""

    # Textos copiados de "histórias de usuário - fase 2.md".
    MENSAGEM_SEM_ESTUDIO = 'Esta conta ainda não está ligada a nenhum estúdio.'
    PENDENCIA_DIAGNOSTICO = (
        'Faça o diagnóstico ESG: é ele que dá a nota, o plano de ação e o '
        'selo do estúdio.'
    )
    TUDO_EM_DIA = 'Tudo em dia por aqui.'

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.dono = criar_dono(self.estudio)
        self.client.force_login(self.dono)
        self.url = reverse('forum:minha_area')
        self.hoje = timezone.localdate()

    def textos_das_pendencias(self):
        resposta = self.client.get(self.url)
        return [item['texto'] for item in resposta.context['pendencias']]

    def deixar_tudo_em_dia(self):
        Diagnostico.objects.create(estudio=self.estudio, nota_e=8, nota_s=8,
                                   nota_g=8)
        Checklist.objects.create(estudio=self.estudio, data=self.hoje,
                                 cumpridos=9, total_itens=9)
        CalculoResiduo.objects.create(estudio=self.estudio, atendimentos=10)

    def test_minha_area_abre_com_os_dados_do_estudio(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'forum/minha_area.html')
        self.assertContains(resposta, 'Olá, Tinta Verde')
        perfil = reverse('forum:estudio_perfil', args=[self.estudio.id])
        self.assertContains(resposta, f'data-copiar="http://testserver{perfil}"')
        for url in (perfil, reverse('forum:estudio_qrcode',
                                    args=[self.estudio.id]),
                    reverse('forum:estudio_documentos',
                            args=[self.estudio.id]),
                    reverse('forum:minha_area_dados')):
            self.assertContains(resposta, f'href="{url}"')

    def test_diagnostico_pendente_vem_primeiro_e_em_destaque(self):
        resposta = self.client.get(self.url)
        primeira = resposta.context['pendencias'][0]
        self.assertEqual(primeira['texto'], self.PENDENCIA_DIAGNOSTICO)
        self.assertTrue(primeira['destaque'])

        Diagnostico.objects.create(estudio=self.estudio, nota_e=8, nota_s=5,
                                   nota_g=7)
        self.assertNotIn(self.PENDENCIA_DIAGNOSTICO,
                         self.textos_das_pendencias())

    def test_sem_pendencias_mostra_tudo_em_dia(self):
        self.deixar_tudo_em_dia()
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.context['pendencias'], [])
        self.assertContains(resposta, self.TUDO_EM_DIA)

    def test_checklist_atrasado_aparece_e_some(self):
        self.deixar_tudo_em_dia()
        Checklist.objects.update(data=self.hoje - timedelta(days=7))
        self.assertIn('O último checklist foi há 7 dias.',
                      self.textos_das_pendencias())
        Checklist.objects.update(data=self.hoje - timedelta(days=6))
        self.assertEqual(self.textos_das_pendencias(), [])

    def test_metas_vencidas_ou_vencendo(self):
        self.deixar_tudo_em_dia()
        MetaEsg.objects.create(estudio=self.estudio,
                               indicador=MetaEsg.AULAS, alvo=5,
                               prazo=self.hoje - timedelta(days=1))
        # Ainda não alcançada: o estúdio não concluiu nenhuma aula.
        MetaEsg.objects.create(estudio=self.estudio,
                               indicador=MetaEsg.AULAS, alvo=9,
                               prazo=self.hoje + timedelta(days=7))
        MetaEsg.objects.create(estudio=self.estudio,
                               indicador=MetaEsg.CHECKLIST, alvo=100,
                               prazo=self.hoje + timedelta(days=30))
        textos = self.textos_das_pendencias()
        self.assertEqual(len(textos), 2)
        self.assertTrue(textos[0].startswith('Meta com prazo vencido'))
        self.assertTrue(textos[1].startswith('Meta vence em'))

    def test_meta_atingida_e_marcada_ao_abrir_a_minha_area(self):
        self.deixar_tudo_em_dia()
        meta = MetaEsg.objects.create(estudio=self.estudio,
                                      indicador=MetaEsg.CHECKLIST, alvo=80,
                                      prazo=self.hoje + timedelta(days=30))
        resposta = self.client.get(self.url)
        meta.refresh_from_db()
        self.assertIsNotNone(meta.atingida_em)
        self.assertContains(resposta,
                            'Meta atingida: Cumprir 80% do checklist.')
        self.assertEqual(resposta.context['metas_atingidas'], 1)

    def test_calculo_de_residuos_do_mes(self):
        self.deixar_tudo_em_dia()
        CalculoResiduo.objects.update(
            criado_em=timezone.now() - timedelta(days=40)
        )
        self.assertIn('Nenhum cálculo de resíduos neste mês.',
                      self.textos_das_pendencias())

    def test_aula_comecada_e_nao_concluida(self):
        self.deixar_tudo_em_dia()
        aula = Aula.objects.create(titulo='Libras', duracao_segundos=600,
                                   url_video='https://youtu.be/abcdefghijk')
        progresso = ProgressoAula.objects.create(
            estudio=self.estudio, aula=aula, segundos_assistidos=120
        )
        self.assertIn('Aula começada e não concluída: Libras.',
                      self.textos_das_pendencias())
        progresso.concluida = True
        progresso.save()
        self.assertEqual(self.textos_das_pendencias(), [])

    def test_documentos_e_estoque_entram_nas_pendencias(self):
        self.deixar_tudo_em_dia()
        DocumentoEstudio.objects.create(
            estudio=self.estudio, tipo=DocumentoEstudio.LICENCA_SANITARIA,
            emitido_em=self.hoje - timedelta(days=400),
            validade=self.hoje - timedelta(days=1),
        )
        ItemEstoque.objects.create(
            estudio=self.estudio, nome='Luva', tipo=ItemEstoque.MATERIAL,
            quantidade=2, quantidade_minima=10, fornecedor='EcoTattoo',
        )
        textos = self.textos_das_pendencias()
        self.assertTrue(any(t.startswith('Documento vencido em')
                            and t.endswith(': Licença sanitária.')
                            for t in textos))
        self.assertIn('1 item(ns) do estoque pedem atenção: Luva.', textos)

    def test_reavaliacao_disponivel_aparece(self):
        self.deixar_tudo_em_dia()
        Diagnostico.objects.update(data=timezone.now() - timedelta(days=91))
        self.assertTrue(any(t.startswith('Reavaliação disponível')
                            for t in self.textos_das_pendencias()))

    def test_nao_mostra_dados_de_outro_estudio(self):
        outro = Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        Diagnostico.objects.create(estudio=outro, nota_e=9, nota_s=9,
                                   nota_g=9)
        MetaEsg.objects.create(estudio=outro, indicador=MetaEsg.AULAS,
                               alvo=1, prazo=self.hoje - timedelta(days=1))
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.context['estudio'], self.estudio)
        self.assertIsNone(resposta.context['diagnostico'])
        self.assertNotContains(resposta, 'Agulha Viva')
        self.assertEqual(resposta.context['metas_em_andamento'], 0)

    def test_conta_comum_sem_estudio(self):
        conta = get_user_model().objects.create_user(username='sem@x.com')
        self.client.force_login(conta)
        resposta = self.client.get(self.url, follow=True)
        self.assertContains(resposta, self.MENSAGEM_SEM_ESTUDIO)

    def test_numero_de_consultas_nao_cresce_com_os_dados(self):
        self.deixar_tudo_em_dia()

        def acrescentar(quantidade, inicio):
            for numero in range(inicio, inicio + quantidade):
                ItemEstoque.objects.create(
                    estudio=self.estudio, nome=f'Item {numero}',
                    tipo=ItemEstoque.MATERIAL, quantidade=1,
                    quantidade_minima=3, fornecedor='F',
                )
                DocumentoEstudio.objects.create(
                    estudio=self.estudio, tipo=DocumentoEstudio.ALVARA,
                    emitido_em=self.hoje,
                    validade=self.hoje + timedelta(days=5),
                )
                MetaEsg.objects.create(
                    estudio=self.estudio, indicador=MetaEsg.AULAS,
                    alvo=50 + numero, prazo=self.hoje + timedelta(days=3),
                )
                aula = Aula.objects.create(
                    titulo=f'Aula {numero}', duracao_segundos=60,
                    url_video='https://youtu.be/abcdefghijk',
                )
                ProgressoAula.objects.create(estudio=self.estudio, aula=aula,
                                             segundos_assistidos=10)

        acrescentar(1, 0)
        self.client.get(self.url)
        with CaptureQueriesContext(connection) as poucos:
            self.client.get(self.url)
        acrescentar(5, 1)
        with CaptureQueriesContext(connection) as muitos:
            self.client.get(self.url)
        self.assertEqual(len(muitos), len(poucos))
        with self.assertNumQueries(27):
            self.client.get(self.url)

    # Navegação

    def test_modulos_voltam_para_a_minha_area(self):
        id_ = self.estudio.id
        for nome in ('estudio_evolucao', 'estudio_residuos', 'estudio_aulas',
                     'estudio_estoque', 'estudio_documentos'):
            resposta = self.client.get(reverse(f'forum:{nome}', args=[id_]))
            self.assertContains(resposta, 'Voltar para a Minha Área')
            self.assertContains(resposta, f'href="{self.url}"')

    def test_resultado_do_diagnostico_leva_a_minha_area(self):
        Diagnostico.objects.create(estudio=self.estudio, nota_e=8, nota_s=5,
                                   nota_g=7)
        resposta = self.client.get(
            reverse('forum:estudio_diagnostico', args=[self.estudio.id])
        )
        self.assertContains(resposta, 'Ir para a Minha Área')

    def test_perfil_avisa_o_dono_que_e_a_visao_do_cliente(self):
        url = reverse('forum:estudio_perfil', args=[self.estudio.id])
        aviso = 'Você está vendo seu perfil como os clientes veem.'
        self.assertContains(self.client.get(url), aviso)
        self.client.logout()
        self.assertNotContains(self.client.get(url), aviso)

    def test_menu_destaca_minha_area_na_area_exclusiva(self):
        resposta = self.client.get(
            reverse('forum:estudio_estoque', args=[self.estudio.id])
        )
        html = resposta.content.decode()
        trecho_minha_area = html[html.index(f'href="{self.url}"') - 80:
                                 html.index(f'href="{self.url}"')]
        self.assertIn('ativo', trecho_minha_area)
        url_estudios = reverse('forum:estudios')
        trecho_estudios = html[html.index(f'href="{url_estudios}"') - 140:
                               html.index(f'href="{url_estudios}"')]
        self.assertNotIn('"ativo"', trecho_estudios)


class ReavaliacaoTest(TestCase):
    """Fase 4: reavaliação ESG e selo dinâmico (História 9)."""

    MENSAGEM_JA_REALIZADO = (
        'Seu estúdio já realizou o diagnóstico inicial. '
        'Acompanhe sua evolução pelo painel!'
    )

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.client.force_login(criar_dono(self.estudio))
        self.url = reverse('forum:estudio_reavaliacao',
                           args=[self.estudio.id])
        self.url_diagnostico = reverse('forum:estudio_diagnostico',
                                       args=[self.estudio.id])
        self.praticas = list(PraticaEstudio.objects.all())

    def respostas(self, valor):
        return {f'pratica_{pratica.id}': str(valor)
                for pratica in self.praticas}

    def diagnostico_antigo(self, dias=90):
        diagnostico = Diagnostico.objects.create(
            estudio=self.estudio, nota_e=5, nota_s=5, nota_g=5
        )
        Diagnostico.objects.filter(id=diagnostico.id).update(
            data=timezone.now() - timedelta(days=dias)
        )
        return diagnostico

    def test_sem_diagnostico_inicial_vai_para_o_diagnostico(self):
        resposta = self.client.get(self.url, follow=True)
        self.assertRedirects(resposta, self.url_diagnostico)
        self.assertContains(resposta, 'Faça primeiro o diagnóstico inicial.')

    def test_antes_de_90_dias_informa_a_data(self):
        self.diagnostico_antigo(dias=10)
        data = (timezone.localdate() + timedelta(days=80)).strftime('%d/%m/%Y')
        resposta = self.client.get(self.url, follow=True)
        self.assertRedirects(resposta, reverse('forum:minha_area'))
        # Texto da História 9, cenário 2, com a data calculada.
        self.assertContains(
            resposta, f'A próxima reavaliação fica disponível em {data}.'
        )
        resposta = self.client.post(self.url, self.respostas(2))
        self.assertEqual(Diagnostico.objects.count(), 1)

    def test_reavaliacao_atualiza_o_selo_e_entra_no_diario(self):
        self.diagnostico_antigo()
        self.assertEqual(self.estudio.ultimo_diagnostico().selo(), '')

        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'Salvar reavaliação')
        resposta = self.client.post(self.url, self.respostas(2))
        self.assertRedirects(resposta, self.url_diagnostico)

        atual = self.estudio.ultimo_diagnostico()
        self.assertEqual(atual.tipo, Diagnostico.REAVALIACAO)
        self.assertEqual(atual.selo(), 'Ouro')
        self.assertEqual(atual.respostas.count(), len(self.praticas))

        perfil = self.client.get(reverse('forum:estudio_perfil',
                                         args=[self.estudio.id]))
        self.assertContains(perfil, 'Selo Estúdio Consciente Ouro')
        diario = self.client.get(reverse('forum:estudio_evolucao',
                                         args=[self.estudio.id]))
        self.assertContains(
            diario, 'Reavaliação ESG: índice 100 de 100 (+50 em relação à '
                    'anterior), selo Ouro.'
        )

    def test_reavaliacao_incompleta_nao_salva(self):
        self.diagnostico_antigo()
        dados = self.respostas(2)
        dados.pop(f'pratica_{self.praticas[0].id}')
        resposta = self.client.post(self.url, dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Faltou responder 1 prática(s).')
        self.assertEqual(Diagnostico.objects.count(), 1)

    def test_diagnostico_inicial_continua_unico(self):
        self.diagnostico_antigo()
        self.client.post(self.url, self.respostas(1))
        resposta = self.client.post(self.url_diagnostico, self.respostas(2))
        self.assertContains(resposta, self.MENSAGEM_JA_REALIZADO)
        self.assertEqual(Diagnostico.objects.count(), 2)
        self.assertEqual(
            Diagnostico.objects.filter(tipo=Diagnostico.INICIAL).count(), 1
        )

    def test_equipe_libera_a_reavaliacao_antes_do_prazo(self):
        self.diagnostico_antigo(dias=5)
        equipe = get_user_model().objects.create_user(username='equipe',
                                                      is_staff=True)
        dono = self.client.session['_auth_user_id']
        self.client.force_login(equipe)
        url = reverse('forum:painel_liberar_reavaliacao',
                      args=[self.estudio.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.estudio.refresh_from_db()
        self.assertTrue(self.estudio.reavaliacao_liberada)
        self.assertEqual(RegistroEquipe.objects.get().acao,
                         'Liberou reavaliação')

        self.client.force_login(get_user_model().objects.get(id=dono))
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.client.post(self.url, self.respostas(2))
        self.estudio.refresh_from_db()
        # Depois de usada, a liberação acaba: a próxima volta a ter prazo.
        self.assertFalse(self.estudio.reavaliacao_liberada)
        self.assertFalse(self.estudio.reavaliacao_disponivel())


class IndiceInkaTest(TestCase):
    """Fase 4: Índice INKA, separado do índice do diagnóstico."""

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.hoje = timezone.localdate()

    def componentes(self):
        resultado = indice_inka(self.estudio)
        return resultado, {c['chave']: c for c in resultado['componentes']}

    def test_pesos_somam_100(self):
        self.assertEqual(sum(PESOS_INDICE.values()), 100)

    def test_sem_dados_o_indice_e_zero(self):
        resultado, partes = self.componentes()
        self.assertEqual(resultado['total'], 0)
        self.assertTrue(all(parte['pontos'] == 0 for parte in partes.values()))
        # Texto da História 13, cenário 2.
        resposta = self.client.get(reverse('forum:estudio_perfil',
                                           args=[self.estudio.id]))
        self.assertContains(resposta, 'Índice INKA: 0/100')

    def test_tudo_no_maximo_da_100(self):
        Diagnostico.objects.create(estudio=self.estudio, nota_e=10,
                                   nota_s=10, nota_g=10)
        Checklist.objects.create(estudio=self.estudio, data=self.hoje,
                                 cumpridos=9, total_itens=9)
        CalculoResiduo.objects.create(estudio=self.estudio, atendimentos=10,
                                      gramas_comum=100)
        CalculoResiduo.objects.create(estudio=self.estudio, atendimentos=10,
                                      gramas_comum=80)
        ItemEstoque.objects.create(estudio=self.estudio, nome='Tinta vegana',
                                   tipo=ItemEstoque.MATERIAL, quantidade=1,
                                   fornecedor='F', origem_sustentavel=True)
        aula = Aula.objects.create(titulo='A', duracao_segundos=60,
                                   url_video='https://youtu.be/abcdefghijk')
        ProgressoAula.objects.create(estudio=self.estudio, aula=aula,
                                     concluida=True)
        campanha = Campanha.objects.create(titulo='C', ong='O', descricao='D')
        ParticipacaoCampanha.objects.create(campanha=campanha,
                                            estudio=self.estudio)
        resultado, _ = self.componentes()
        self.assertEqual(resultado['total'], 100)

    def test_checklist_antigo_nao_conta(self):
        Checklist.objects.create(estudio=self.estudio,
                                 data=self.hoje - timedelta(days=31),
                                 cumpridos=9, total_itens=9)
        _, partes = self.componentes()
        self.assertEqual(partes['checklist']['pontos'], 0)

    def test_residuos_primeiro_diminuiu_e_aumentou(self):
        CalculoResiduo.objects.create(estudio=self.estudio, atendimentos=1,
                                      gramas_comum=100)
        _, partes = self.componentes()
        self.assertEqual(partes['residuos']['pontos'], 5)     # 50% de 10
        CalculoResiduo.objects.create(estudio=self.estudio, atendimentos=1,
                                      gramas_comum=150)
        _, partes = self.componentes()
        self.assertEqual(partes['residuos']['pontos'], 0)

    def test_materiais_sustentaveis_e_campanha_encerrada(self):
        for sustentavel in (True, False):
            ItemEstoque.objects.create(
                estudio=self.estudio, nome=f'Item {sustentavel}',
                tipo=ItemEstoque.MATERIAL, quantidade=1, fornecedor='F',
                origem_sustentavel=sustentavel,
            )
        campanha = Campanha.objects.create(titulo='C', ong='O', descricao='D',
                                           ativa=False)
        ParticipacaoCampanha.objects.create(campanha=campanha,
                                            estudio=self.estudio)
        _, partes = self.componentes()
        self.assertEqual(partes['materiais']['pontos'], 5)     # 50% de 10
        self.assertEqual(partes['campanhas']['pontos'], 0)

    def test_selo_e_indice_do_diagnostico_nao_mudam(self):
        diagnostico = Diagnostico.objects.create(estudio=self.estudio,
                                                 nota_e=8, nota_s=5, nota_g=7)
        self.assertEqual(diagnostico.selo(), 'Prata')
        self.assertAlmostEqual(diagnostico.indice(), 66.67, places=2)
        resposta = self.client.get(reverse('forum:estudio_perfil',
                                           args=[self.estudio.id]))
        self.assertContains(resposta, '67 de 100')
        self.assertContains(resposta, 'Índice INKA: 33/100')


class DocumentoEstudioTest(TestCase):
    """Fase 4: documentos e licenças (História 10)."""

    # Texto copiado de "histórias de usuário - fase 2.md".
    MENSAGEM_VALIDADE = 'A validade não pode ser anterior à data de emissão!'

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.client.force_login(criar_dono(self.estudio))
        self.url_lista = reverse('forum:estudio_documentos',
                                 args=[self.estudio.id])
        self.url_novo = reverse('forum:estudio_documento_novo',
                                args=[self.estudio.id])
        self.hoje = timezone.localdate()

    def dados(self, **campos):
        dados = {
            'tipo': DocumentoEstudio.LICENCA_SANITARIA, 'descricao': '',
            'emitido_em': (self.hoje - timedelta(days=30)).isoformat(),
            'validade': (self.hoje + timedelta(days=300)).isoformat(),
            'link': 'https://drive.example.com/licenca',
        }
        dados.update(campos)
        return dados

    def test_cadastrar_e_aparecer_no_perfil_so_a_situacao(self):
        self.assertRedirects(self.client.post(self.url_novo, self.dados()),
                             self.url_lista)
        documento = DocumentoEstudio.objects.get()
        self.assertEqual(documento.situacao(), 'em_dia')

        perfil = self.client.get(reverse('forum:estudio_perfil',
                                         args=[self.estudio.id]))
        self.assertContains(perfil, 'Licença sanitária em dia')
        self.assertNotContains(perfil, 'drive.example.com')

        diario = self.client.get(reverse('forum:estudio_evolucao',
                                         args=[self.estudio.id]))
        self.assertContains(diario, 'Documento cadastrado: Licença sanitária')

    def test_validade_anterior_a_emissao(self):
        resposta = self.client.post(self.url_novo, self.dados(
            emitido_em=self.hoje.isoformat(),
            validade=(self.hoje - timedelta(days=1)).isoformat(),
        ))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, self.MENSAGEM_VALIDADE)
        self.assertFalse(DocumentoEstudio.objects.exists())

    def test_outros_erros_de_preenchimento(self):
        resposta = self.client.post(self.url_novo, self.dados(
            tipo=DocumentoEstudio.OUTRO, descricao='', emitido_em='',
            link='ftp://x',
        ))
        for mensagem in ('Descreva o documento.',
                         'Informe a data de emissão.',
                         'Informe um link válido'):
            self.assertContains(resposta, mensagem)

    def test_documento_vencido_nao_aparece_no_perfil(self):
        DocumentoEstudio.objects.create(
            estudio=self.estudio, tipo=DocumentoEstudio.AUTOCLAVE,
            emitido_em=self.hoje - timedelta(days=400),
            validade=self.hoje - timedelta(days=1),
        )
        perfil = self.client.get(reverse('forum:estudio_perfil',
                                         args=[self.estudio.id]))
        self.assertNotContains(perfil, 'Autoclave com manutenção em dia')
        lista = self.client.get(self.url_lista)
        self.assertContains(lista, 'Vencido')

    def test_editar_e_remover(self):
        documento = DocumentoEstudio.objects.create(
            estudio=self.estudio, tipo=DocumentoEstudio.ALVARA,
            emitido_em=self.hoje,
        )
        url_editar = reverse('forum:estudio_documento_editar',
                             args=[self.estudio.id, documento.id])
        self.client.post(url_editar, self.dados(tipo=DocumentoEstudio.ALVARA,
                                                validade=''))
        documento.refresh_from_db()
        self.assertIsNone(documento.validade)
        self.assertEqual(documento.situacao(), 'sem_validade')

        url_remover = reverse('forum:estudio_documento_remover',
                              args=[self.estudio.id, documento.id])
        self.assertContains(self.client.get(url_remover), 'Remover documento')
        self.client.post(url_remover)
        self.assertFalse(DocumentoEstudio.objects.exists())

    def test_documento_de_outro_estudio_responde_404(self):
        outro = Estudio.objects.create(nome='Agulha Viva', cidade='Olinda')
        documento = DocumentoEstudio.objects.create(
            estudio=outro, tipo=DocumentoEstudio.ALVARA, emitido_em=self.hoje,
        )
        for nome in ('estudio_documento_editar', 'estudio_documento_remover'):
            url = reverse(f'forum:{nome}', args=[self.estudio.id,
                                                 documento.id])
            self.assertEqual(self.client.get(url).status_code, 404)
        url = reverse('forum:estudio_documentos', args=[outro.id])
        self.assertEqual(self.client.get(url).status_code, 404)


class EstoqueAlertasTest(TestCase):
    """Fase 4: estoque com mínimo, validade e origem sustentável (História 11)."""

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.client.force_login(criar_dono(self.estudio))
        self.url_lista = reverse('forum:estudio_estoque',
                                 args=[self.estudio.id])
        self.url_novo = reverse('forum:estudio_estoque_novo',
                                args=[self.estudio.id])
        self.hoje = timezone.localdate()

    def dados(self, **campos):
        dados = {'nome': 'Luva de nitrilo', 'tipo': ItemEstoque.MATERIAL,
                 'quantidade': '3', 'fornecedor': 'EcoTattoo',
                 'quantidade_minima': '5',
                 'validade': (self.hoje + timedelta(days=10)).isoformat(),
                 'origem_sustentavel': 'on'}
        dados.update(campos)
        return dados

    def test_cadastrar_com_alertas_e_ver_no_estoque(self):
        self.client.post(self.url_novo, self.dados())
        item = ItemEstoque.objects.get()
        self.assertEqual(item.quantidade_minima, 5)
        self.assertTrue(item.origem_sustentavel)
        validade = (self.hoje + timedelta(days=10)).strftime('%d/%m/%Y')
        self.assertEqual(item.alertas(), ['Abaixo do mínimo (5)',
                                          f'Vence em {validade}'])

        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, 'Abaixo do mínimo (5)')
        self.assertContains(resposta, 'Origem sustentável')
        self.assertContains(resposta, 'ATENÇÃO')

    def test_item_vencido(self):
        item = ItemEstoque.objects.create(
            estudio=self.estudio, nome='Tinta', tipo=ItemEstoque.MATERIAL,
            quantidade=10, fornecedor='F',
            validade=self.hoje - timedelta(days=1),
        )
        self.assertEqual(item.situacao_validade(), 'vencido')
        self.assertContains(self.client.get(self.url_lista), 'Vencido em')

    def test_minimo_invalido_nao_salva(self):
        # Texto copiado de "histórias de usuário - fase 2.md".
        resposta = self.client.post(self.url_novo,
                                    self.dados(quantidade_minima='-2'))
        self.assertContains(resposta, 'Informe um número inteiro.')
        resposta = self.client.post(self.url_novo,
                                    self.dados(validade='31/12/2026'))
        self.assertContains(resposta, 'Informe uma data válida.')
        self.assertFalse(ItemEstoque.objects.exists())

    def test_campos_novos_sao_opcionais(self):
        self.client.post(self.url_novo, self.dados(
            quantidade_minima='', validade='', origem_sustentavel=''
        ))
        item = ItemEstoque.objects.get()
        self.assertEqual(item.quantidade_minima, 0)
        self.assertIsNone(item.validade)
        self.assertFalse(item.origem_sustentavel)
        self.assertEqual(item.alertas(), [])

    def test_editar_mantem_os_campos(self):
        self.client.post(self.url_novo, self.dados())
        item = ItemEstoque.objects.get()
        url = reverse('forum:estudio_estoque_editar',
                      args=[self.estudio.id, item.id])
        resposta = self.client.get(url)
        self.assertEqual(resposta.context['dados']['quantidade_minima'], '5')
        self.client.post(url, self.dados(quantidade_minima='1'))
        item.refresh_from_db()
        self.assertEqual(item.quantidade_minima, 1)
        self.assertFalse(item.abaixo_do_minimo())


class DadosEstudioTest(TestCase):
    """Fase 4: dados do estúdio e perfil mais completo (História 12)."""

    # Texto copiado de "histórias de usuário - fase 2.md".
    MENSAGEM_WHATSAPP = 'Informe o WhatsApp com DDD: 10 ou 11 números.'

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.client.force_login(criar_dono(self.estudio))
        self.url = reverse('forum:minha_area_dados')

    def dados(self, **campos):
        dados = {'nome': 'Tinta Verde Studio', 'cidade': 'Recife',
                 'bairro': 'Boa Viagem', 'descricao': 'Tatuagem autoral.',
                 'instagram': '@tintaverde', 'whatsapp': '(81) 99999-0000',
                 'site': 'https://tintaverde.example.com',
                 'acessibilidade': 'Rampa na entrada'}
        dados.update(campos)
        return dados

    def test_salvar_e_mostrar_no_perfil(self):
        self.assertRedirects(self.client.post(self.url, self.dados()),
                             reverse('forum:minha_area'))
        self.estudio.refresh_from_db()
        self.assertEqual(self.estudio.nome, 'Tinta Verde Studio')
        self.assertEqual(self.estudio.instagram, 'tintaverde')
        self.assertEqual(self.estudio.whatsapp, '81999990000')

        perfil = self.client.get(reverse('forum:estudio_perfil',
                                         args=[self.estudio.id]))
        self.assertContains(perfil, 'Boa Viagem, Recife')
        self.assertContains(perfil, 'Tatuagem autoral.')
        self.assertContains(perfil, 'href="https://wa.me/5581999990000"')
        self.assertContains(
            perfil, 'href="https://www.instagram.com/tintaverde/"'
        )
        self.assertContains(perfil, 'Acessibilidade: Rampa na entrada')

    def test_instagram_aceita_o_endereco_inteiro(self):
        self.client.post(self.url, self.dados(
            instagram='https://www.instagram.com/tinta.verde_/'
        ))
        self.estudio.refresh_from_db()
        self.assertEqual(self.estudio.instagram, 'tinta.verde_')

    def test_dados_invalidos_nao_salvam(self):
        resposta = self.client.post(self.url, self.dados(
            whatsapp='9999', instagram='tinta verde!', site='nao-e-link',
            nome='',
        ))
        self.assertContains(resposta, self.MENSAGEM_WHATSAPP)
        self.assertContains(resposta, 'Informe só o nome de usuário')
        self.assertContains(resposta, 'Informe um link válido')
        self.assertContains(resposta, 'Informe o nome do estúdio.')
        self.estudio.refresh_from_db()
        self.assertEqual(self.estudio.nome, 'Tinta Verde')

    def test_campos_opcionais_vazios(self):
        self.client.post(self.url, self.dados(
            bairro='', descricao='', instagram='', whatsapp='', site='',
            acessibilidade='',
        ))
        perfil = self.client.get(reverse('forum:estudio_perfil',
                                         args=[self.estudio.id]))
        self.assertNotContains(perfil, 'wa.me')
        self.assertNotContains(perfil, 'instagram.com')

    def test_exige_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url),
                             f'{reverse("forum:entrar")}?next={self.url}')


class FiltrosDaListaTest(TestCase):
    """Fase 4: lista pública com filtro por selo e ordem por índice."""

    def setUp(self):
        for nome, nota in (('Bronze Ink', 7.5), ('Ouro Ink', 9),
                           ('Sem Selo Ink', 2)):
            estudio = Estudio.objects.create(nome=nome, cidade='Recife')
            notas = {'nota_e': nota, 'nota_s': nota, 'nota_g': nota}
            if nome == 'Bronze Ink':
                notas = {'nota_e': 8, 'nota_s': 1, 'nota_g': 1}
            Diagnostico.objects.create(estudio=estudio, **notas)
        Estudio.objects.create(nome='Novo Ink', cidade='Recife')

    def nomes(self, **filtros):
        resposta = self.client.get(reverse('forum:estudios'), filtros)
        return [estudio.nome for estudio in resposta.context['estudios']]

    def test_filtra_por_selo(self):
        self.assertEqual(self.nomes(selo='ouro'), ['Ouro Ink'])
        self.assertEqual(self.nomes(selo='bronze'), ['Bronze Ink'])
        self.assertEqual(self.nomes(selo='sem_selo'), ['Sem Selo Ink'])
        self.assertEqual(len(self.nomes(selo='diamante')), 4)

    def test_ordena_por_indice(self):
        self.assertEqual(self.nomes(ordem='indice'),
                         ['Ouro Ink', 'Bronze Ink', 'Sem Selo Ink',
                          'Novo Ink'])
        self.assertEqual(self.nomes()[0], 'Bronze Ink')   # alfabética


class AulasCategoriaTest(TestCase):
    """Fase 4: categorias de aula e a meta que conta só inclusão."""

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.client.force_login(criar_dono(self.estudio))
        self.inclusao = Aula.objects.create(
            titulo='Libras', duracao_segundos=60,
            url_video='https://youtu.be/abcdefghijk',
        )
        self.bio = Aula.objects.create(
            titulo='Autoclave', duracao_segundos=60,
            url_video='https://youtu.be/abcdefghijk',
            categoria=Aula.BIOSSEGURANCA,
        )

    def test_aulas_agrupadas_por_categoria(self):
        resposta = self.client.get(reverse('forum:estudio_aulas',
                                           args=[self.estudio.id]))
        rotulos = [c['rotulo'] for c in resposta.context['categorias']]
        self.assertEqual(rotulos, ['Inclusão e acessibilidade',
                                   'Biossegurança'])
        self.assertContains(resposta, '<h4 class="aulas-categoria">'
                                      'Biossegurança</h4>', html=True)

    def test_meta_de_aulas_conta_so_inclusao(self):
        ProgressoAula.objects.create(estudio=self.estudio, aula=self.bio,
                                     concluida=True)
        self.assertEqual(
            MetaEsg.valor_do_indicador(self.estudio, MetaEsg.AULAS), 0
        )
        ProgressoAula.objects.create(estudio=self.estudio,
                                     aula=self.inclusao, concluida=True)
        self.assertEqual(
            MetaEsg.valor_do_indicador(self.estudio, MetaEsg.AULAS), 1
        )
        self.assertEqual(self.estudio.aulas_concluidas(), 2)

    def test_painel_cadastra_aula_com_categoria(self):
        equipe = get_user_model().objects.create_user(username='e',
                                                      is_staff=True)
        self.client.force_login(equipe)
        url = reverse('forum:painel_aula_nova')
        dados = {'titulo': 'Contratos', 'descricao': '',
                 'url_video': 'https://youtu.be/abcdefghijk',
                 'minutos': '5', 'segundos': '0', 'categoria': 'xyz'}
        resposta = self.client.post(url, dados)
        self.assertContains(resposta, 'Escolha uma das categorias da lista.')
        dados['categoria'] = Aula.GOVERNANCA
        self.client.post(url, dados)
        self.assertEqual(Aula.objects.get(titulo='Contratos').categoria,
                         Aula.GOVERNANCA)


class RecomendacoesCalculadoraTest(TestCase):
    """Fase 4: a calculadora destaca o resíduo que mais pesou."""

    def setUp(self):
        self.estudio = Estudio.objects.create(nome='Tinta Verde',
                                              cidade='Recife')
        self.client.force_login(criar_dono(self.estudio))
        self.url = reverse('forum:estudio_residuos', args=[self.estudio.id])

    def test_destaca_praticas_e_empresas_do_residuo_principal(self):
        CalculoResiduo.objects.create(
            estudio=self.estudio, atendimentos=10, gramas_perfurocortante=50,
            gramas_contaminado=300, gramas_comum=20,
        )
        EmpresaDescarte.objects.create(nome='Coleta Recife', cidade='recife',
                                       telefone='81',
                                       tipos_residuo='Contaminado, comum')
        EmpresaDescarte.objects.create(nome='Coleta Olinda', cidade='Olinda',
                                       telefone='81',
                                       tipos_residuo='contaminado')
        EmpresaDescarte.objects.create(nome='Só Agulhas', cidade='Recife',
                                       telefone='81',
                                       tipos_residuo='perfurocortante')

        resposta = self.client.get(self.url)
        self.assertEqual(resposta.context['tipo_principal'], 'Contaminado')
        recomendacoes = resposta.context['recomendacoes']
        self.assertEqual(len(recomendacoes), 4)
        self.assertEqual(recomendacoes[0].titulo, 'Redução de descartáveis')
        self.assertTrue(recomendacoes[0].destaque)
        self.assertFalse(any(p.destaque for p in recomendacoes[1:]))
        self.assertEqual([e.nome for e in
                          resposta.context['empresas_recomendadas']],
                         ['Coleta Recife'])
        self.assertContains(resposta, 'Para o seu resíduo principal')

    def test_sem_calculo_nao_destaca_nada(self):
        resposta = self.client.get(self.url)
        self.assertIsNone(resposta.context['tipo_principal'])
        self.assertFalse(any(p.destaque
                             for p in resposta.context['recomendacoes']))
