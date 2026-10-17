from django.db import migrations

MATERIAIS = [
    ('Cartuchos e agulhas', 'perfurocortante', 12),
    ('Lâminas de barbear descartáveis', 'perfurocortante', 5),
    ('Luvas de nitrilo', 'contaminado', 24),
    ('Papel toalha com sangue e tinta', 'contaminado', 30),
    ('Filme plástico e barreiras de proteção', 'contaminado', 15),
    ('Batoques de tinta', 'contaminado', 5),
    ('Capas de máquina e de cabo', 'contaminado', 8),
    ('Embalagens de insumos', 'comum', 20),
    ('Copos e utensílios descartáveis', 'comum', 10),
    ('Papel de decalque', 'comum', 5),
]


def carregar(apps, schema_editor):
    Material = apps.get_model('forum', 'Material')

    for nome, tipo, gramas in MATERIAIS:
        Material.objects.create(
            nome=nome, tipo=tipo, gramas_por_atendimento=gramas
        )


def remover(apps, schema_editor):
    apps.get_model('forum', 'Material').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0007_material_calculoresiduo'),
    ]

    operations = [
        migrations.RunPython(carregar, remover),
    ]
