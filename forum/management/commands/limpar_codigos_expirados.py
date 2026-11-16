from django.core.management.base import BaseCommand

from forum.redefinicao_senha import limpar_expirados


class Command(BaseCommand):
    help = ('Apaga os códigos e tokens de redefinição de senha vencidos ou '
            'já usados.')

    def handle(self, *args, **options):
        codigos, tokens = limpar_expirados()
        self.stdout.write(
            f'Apagados: {codigos} código(s) e {tokens} token(s).'
        )
