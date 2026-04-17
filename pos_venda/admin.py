from django.contrib import admin

from .models import Chamado, InteracaoChamado


class InteracaoInline(admin.TabularInline):
    model = InteracaoChamado
    extra = 0
    readonly_fields = ("criado_em",)


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "tipo", "status", "prioridade", "responsavel", "prazo", "criado_em")
    list_filter = ("status", "tipo", "prioridade")
    search_fields = ("numero", "assunto", "cliente__nome")
    readonly_fields = ("numero", "criado_em", "atualizado_em")
    inlines = [InteracaoInline]
