from django.contrib import admin

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
    SecaoConteudo,
    Tecnologia,
)


@admin.register(SecaoConteudo)
class SecaoConteudoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'pagina', 'ordem']
    list_filter = ['pagina']
    search_fields = ['titulo', 'texto']


@admin.register(MembroEquipe)
class MembroEquipeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', 'curso', 'ordem', 'ativo']
    list_filter = ['ativo', 'curso']
    search_fields = ['nome', 'email']


@admin.register(Pilar)
class PilarAdmin(admin.ModelAdmin):
    list_display = ['sigla', 'nome', 'ordem']


@admin.register(ItemLista)
class ItemListaAdmin(admin.ModelAdmin):
    list_display = ['texto', 'categoria', 'ordem']
    list_filter = ['categoria']


@admin.register(Tecnologia)
class TecnologiaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ordem']


@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', 'empresa', 'assunto', 'data_envio',
                    'respondido']
    list_filter = ['assunto', 'respondido', 'data_envio']
    search_fields = ['nome', 'email', 'empresa', 'mensagem']
    date_hierarchy = 'data_envio'


@admin.register(PraticaEstudio)
class PraticaEstudioAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'pilar', 'ordem']
    list_filter = ['pilar']
    search_fields = ['titulo', 'descricao']


@admin.register(Estudio)
class EstudioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cidade', 'usuario', 'criado_em']
    search_fields = ['nome', 'cidade', 'usuario__email']


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ['estudio', 'data', 'nota_e', 'nota_s', 'nota_g']
    list_filter = ['estudio']


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'gramas_por_atendimento']
    list_filter = ['tipo']


@admin.register(CalculoResiduo)
class CalculoResiduoAdmin(admin.ModelAdmin):
    list_display = ['estudio', 'criado_em', 'atendimentos',
                    'gramas_perfurocortante', 'gramas_contaminado',
                    'gramas_comum']
    list_filter = ['estudio']


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'quantidade', 'fornecedor', 'estudio']
    list_filter = ['tipo', 'estudio']
    search_fields = ['nome', 'fornecedor']


@admin.register(ConteudoDescarte)
class ConteudoDescarteAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'formato', 'disponivel', 'estudio']
    list_filter = ['formato', 'disponivel', 'estudio']
    list_editable = ['disponivel']
    search_fields = ['titulo', 'descricao']


@admin.register(EmpresaDescarte)
class EmpresaDescarteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cidade', 'telefone', 'email', 'estudio']
    list_filter = ['cidade', 'estudio']
    search_fields = ['nome', 'cidade', 'tipos_residuo']


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'duracao', 'estudio', 'ordem']
    list_filter = ['estudio']
    search_fields = ['titulo', 'descricao']

    @admin.display(description='Duração')
    def duracao(self, aula):
        return aula.duracao_formatada()


@admin.register(ProgressoAula)
class ProgressoAulaAdmin(admin.ModelAdmin):
    list_display = ['estudio', 'aula', 'segundos_assistidos', 'concluida']
    list_filter = ['concluida', 'aula', 'estudio']
