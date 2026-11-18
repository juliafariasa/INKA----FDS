from django.contrib import admin

from .models import (
    Aula,
    CalculoResiduo,
    Campanha,
    Checklist,
    Contato,
    ConteudoDescarte,
    Diagnostico,
    EmpresaDescarte,
    Estudio,
    ItemChecklist,
    ItemEstoque,
    ItemLista,
    Material,
    MembroEquipe,
    MetaEsg,
    ParticipacaoCampanha,
    Pilar,
    PraticaEstudio,
    ProgressoAula,
    RegistroEquipe,
    Resposta,
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
    actions = ['marcar_respondido']

    @admin.action(description='Marcar como respondido')
    def marcar_respondido(self, request, queryset):
        total = queryset.update(respondido=True)
        self.message_user(request,
                          f'{total} contato(s) marcado(s) como respondido.')


@admin.register(PraticaEstudio)
class PraticaEstudioAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'pilar', 'ordem']
    list_filter = ['pilar']
    search_fields = ['titulo', 'descricao']


@admin.register(Estudio)
class EstudioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cidade', 'usuario', 'ativo', 'criado_em']
    list_filter = ['ativo']
    list_select_related = ['usuario']
    search_fields = ['nome', 'cidade', 'usuario__email']
    autocomplete_fields = ['usuario']


class RespostaInline(admin.TabularInline):
    """Respostas do diagnóstico, só para leitura.

    Mudar uma resposta aqui não recalcularia as notas, e a nota ficaria
    diferente das respostas.
    """

    model = Resposta
    fields = ['pratica', 'valor']
    readonly_fields = ['pratica', 'valor']
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ['estudio', 'data', 'nota_e', 'nota_s', 'nota_g']
    list_filter = ['estudio']
    list_select_related = ['estudio']
    autocomplete_fields = ['estudio']
    inlines = [RespostaInline]


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
    list_select_related = ['estudio']
    autocomplete_fields = ['estudio']


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'quantidade', 'fornecedor', 'estudio']
    list_filter = ['tipo', 'estudio']
    search_fields = ['nome', 'fornecedor']
    list_select_related = ['estudio']
    autocomplete_fields = ['estudio']


@admin.register(ConteudoDescarte)
class ConteudoDescarteAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'formato', 'disponivel', 'estudio']
    list_filter = ['formato', 'disponivel', 'estudio']
    list_editable = ['disponivel']
    list_select_related = ['estudio']
    search_fields = ['titulo', 'descricao']
    autocomplete_fields = ['estudio']
    actions = ['marcar_indisponivel']

    @admin.action(description='Marcar como indisponível')
    def marcar_indisponivel(self, request, queryset):
        total = queryset.update(disponivel=False)
        self.message_user(
            request, f'{total} conteúdo(s) marcado(s) como indisponível.'
        )


@admin.register(EmpresaDescarte)
class EmpresaDescarteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cidade', 'telefone', 'email', 'estudio']
    list_filter = ['cidade', 'estudio']
    search_fields = ['nome', 'cidade', 'tipos_residuo']
    list_select_related = ['estudio']
    autocomplete_fields = ['estudio']


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'duracao', 'estudio', 'ordem']
    list_filter = ['estudio']
    search_fields = ['titulo', 'descricao']
    list_select_related = ['estudio']
    autocomplete_fields = ['estudio']

    @admin.display(description='Duração')
    def duracao(self, aula):
        return aula.duracao_formatada()


@admin.register(ProgressoAula)
class ProgressoAulaAdmin(admin.ModelAdmin):
    list_display = ['estudio', 'aula', 'segundos_assistidos', 'concluida']
    list_filter = ['concluida', 'aula', 'estudio']
    list_select_related = ['estudio', 'aula']
    autocomplete_fields = ['estudio']


@admin.register(ItemChecklist)
class ItemChecklistAdmin(admin.ModelAdmin):
    list_display = ['texto', 'categoria', 'ordem', 'ativo']
    list_filter = ['categoria', 'ativo']
    search_fields = ['texto']


@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ['estudio', 'data', 'cumpridos', 'total_itens']
    list_filter = ['estudio']
    list_select_related = ['estudio']
    autocomplete_fields = ['estudio']


@admin.register(MetaEsg)
class MetaEsgAdmin(admin.ModelAdmin):
    list_display = ['estudio', 'indicador', 'alvo', 'prazo', 'atingida_em']
    list_filter = ['indicador', 'estudio']
    list_select_related = ['estudio']
    autocomplete_fields = ['estudio']


class ParticipacaoCampanhaInline(admin.TabularInline):
    model = ParticipacaoCampanha
    extra = 0
    autocomplete_fields = ['estudio']


@admin.register(Campanha)
class CampanhaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'ong', 'cidade', 'encerra_em', 'ativa']
    list_filter = ['ativa', 'cidade']
    search_fields = ['titulo', 'ong', 'descricao']
    inlines = [ParticipacaoCampanhaInline]


@admin.register(RegistroEquipe)
class RegistroEquipeAdmin(admin.ModelAdmin):
    """Só leitura: o registro é a memória do que a equipe fez."""

    list_display = ['criado_em', 'nome_usuario', 'acao', 'alvo']
    list_filter = ['acao']
    search_fields = ['nome_usuario', 'acao', 'alvo']
    readonly_fields = ['usuario', 'nome_usuario', 'acao', 'alvo', 'criado_em']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
