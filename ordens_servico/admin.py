from django.contrib import admin

from .models import ChecklistTemplate, FotoOS, ItemChecklist, OrdemServico, Tecnico


@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    list_display = ["nome", "especialidade", "telefone", "ativo"]
    list_filter = ["especialidade", "ativo"]
    search_fields = ["nome", "email"]


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "ordem", "ativo"]
    list_filter = ["tipo", "ativo"]
    search_fields = ["descricao"]
    ordering = ["tipo", "ordem"]


class ItemChecklistInline(admin.TabularInline):
    model = ItemChecklist
    extra = 0
    fields = ["descricao", "concluido", "observacao", "ordem"]


class FotoOSInline(admin.TabularInline):
    model = FotoOS
    extra = 0
    fields = ["foto", "legenda"]
    readonly_fields = ["enviada_em"]


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ["numero", "cliente", "tecnico", "status", "prioridade", "criado_em"]
    list_filter = ["status", "prioridade"]
    search_fields = ["numero", "cliente__nome"]
    readonly_fields = ["numero", "criado_em", "atualizado_em"]
    inlines = [ItemChecklistInline, FotoOSInline]
