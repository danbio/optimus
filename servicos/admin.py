from django.contrib import admin

from .models import ItemProduto, ItemServico, PropostaServico, Servico


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "ativo"]
    list_filter = ["tipo", "ativo"]
    search_fields = ["nome", "descricao"]


class ItemServicoInline(admin.TabularInline):
    model = ItemServico
    extra = 0
    fields = ["servico", "valor", "observacao"]


class ItemProdutoInline(admin.TabularInline):
    model = ItemProduto
    extra = 0
    fields = ["produto", "quantidade", "valor_unitario"]


@admin.register(PropostaServico)
class PropostaServicoAdmin(admin.ModelAdmin):
    list_display = ["numero", "cliente", "tipo_servico", "status", "validade", "criado_em"]
    list_filter = ["tipo_servico", "status"]
    search_fields = ["numero", "cliente__nome"]
    readonly_fields = ["numero", "criado_em", "atualizado_em"]
    inlines = [ItemServicoInline, ItemProdutoInline]
