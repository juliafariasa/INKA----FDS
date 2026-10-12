from django.db import migrations

CAMPOS_POR_MODEL = {
    'SecaoConteudo': ['titulo', 'texto'],
    'ItemLista': ['texto'],
    'Pilar': ['descricao'],
    'Tecnologia': ['descricao'],
    'PraticaEstudio': ['titulo', 'descricao'],
}


def trocar_nome(apps, antigo, novo):
    for nome_model, campos in CAMPOS_POR_MODEL.items():
        for objeto in apps.get_model('forum', nome_model).objects.all():
            alterado = False
            for campo in campos:
                valor = getattr(objeto, campo)
                if antigo in valor:
                    setattr(objeto, campo, valor.replace(antigo, novo))
                    alterado = True
            if alterado:
                objeto.save()


def renomear(apps, schema_editor):
    trocar_nome(apps, 'ESGRise', 'INKA')


def desfazer(apps, schema_editor):
    trocar_nome(apps, 'INKA', 'ESGRise')


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0004_conteudo_estudios'),
    ]

    operations = [
        migrations.RunPython(renomear, desfazer),
    ]
