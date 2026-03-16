from django.contrib import admin

from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao", "bu", "segmento", "psd", "pscf", "ativo")
    list_filter = ("bu", "segmento", "ativo")
    search_fields = ("codigo", "descricao", "ean", "ncm")
    list_per_page = 50
