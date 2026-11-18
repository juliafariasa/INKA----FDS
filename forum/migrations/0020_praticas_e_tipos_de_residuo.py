from django.db import migrations

# Práticas do pilar Ambiental que reduzem cada tipo de resíduo. A calculadora
# mostra essas primeiro quando o tipo é o que mais pesou no cálculo.
LIGACOES = {
    'Descarte de perfurocortantes': 'perfurocortante',
    'Redução de descartáveis': 'contaminado, comum',
    'Origem das tintas e insumos': 'comum',
}


def ligar(apps, schema_editor):
    PraticaEstudio = apps.get_model('forum', 'PraticaEstudio')
    for titulo, tipos in LIGACOES.items():
        PraticaEstudio.objects.filter(titulo=titulo).update(
            tipos_residuo=tipos
        )


def desligar(apps, schema_editor):
    PraticaEstudio = apps.get_model('forum', 'PraticaEstudio')
    PraticaEstudio.objects.filter(titulo__in=LIGACOES).update(
        tipos_residuo=''
    )


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0019_ideias_do_quadro'),
    ]

    operations = [
        migrations.RunPython(ligar, desligar),
    ]
