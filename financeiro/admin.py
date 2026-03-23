from django.contrib import admin

from .models import BaixaFinanceira, LancamentoFinanceiro, ParcelaLancamento


class ParcelaInline(admin.TabularInline):
    model = ParcelaLancamento
    extra = 0
    readonly_fields = ("numero_parcela", "valor", "data_vencimento")


class BaixaInline(admin.TabularInline):
    model = BaixaFinanceira
    extra = 0
    readonly_fields = ("valor", "forma_pagamento", "data_pagamento", "registrado_por", "criado_em")


@admin.register(LancamentoFinanceiro)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "descricao", "valor_liquido", "status", "data_vencimento")
    list_filter = ("status", "forma_pagamento")
    search_fields = ("numero", "descricao", "cliente__nome")
    inlines = [ParcelaInline, BaixaInline]
    readonly_fields = ("numero", "data_emissao", "valor_liquido")
