from django.contrib import admin

from .models import ItemVenda, Venda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    readonly_fields = ("subtotal",)


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nome_cliente_display", "total", "status", "criado_em")
    list_filter = ("status",)
    search_fields = ("numero", "cliente__nome", "cliente_nome_avulso")
    readonly_fields = ("numero",)
    inlines = [ItemVendaInline]
