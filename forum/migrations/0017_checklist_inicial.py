from django.db import migrations

# Práticas de rotina do checklist (higiene, segurança e gestão de resíduos).
# A equipe pode editar a lista pelo admin.
ITENS = [
    ('higiene', 'Bancada e maca limpas e desinfetadas a cada atendimento'),
    ('higiene', 'Barreiras de proteção trocadas a cada cliente'),
    ('higiene', 'Mãos higienizadas e luvas novas antes de cada procedimento'),
    ('seguranca', 'Agulhas e cartuchos de uso único, abertos na frente do cliente'),
    ('seguranca', 'Autoclave com teste e manutenção em dia'),
    ('seguranca', 'Licença sanitária válida e à vista na recepção'),
    ('residuos', 'Perfurocortantes descartados na caixa coletora rígida'),
    ('residuos', 'Resíduos contaminados separados em saco branco leitoso'),
    ('residuos', 'Coleta feita por empresa especializada, com comprovante guardado'),
]


def carregar(apps, schema_editor):
    ItemChecklist = apps.get_model('forum', 'ItemChecklist')

    for ordem, (categoria, texto) in enumerate(ITENS, start=1):
        ItemChecklist.objects.create(
            categoria=categoria, texto=texto, ordem=ordem
        )


def remover(apps, schema_editor):
    apps.get_model('forum', 'ItemChecklist').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0016_evolucao_e_campanhas'),
    ]

    operations = [
        migrations.RunPython(carregar, remover),
    ]
