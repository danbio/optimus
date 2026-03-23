from django.contrib import admin
from .models import EstruturaFixacao, Inversor, ModuloFotovoltaico


@admin.register(ModuloFotovoltaico)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ["fabricante", "modelo", "potencia_wp", "eficiencia", "garantia_produto", "ativo"]
    list_filter = ["fabricante", "ativo"]
    search_fields = ["fabricante", "modelo"]


@admin.register(Inversor)
class InversorAdmin(admin.ModelAdmin):
    list_display = ["fabricante", "modelo", "potencia_kw", "tipo", "fase", "garantia", "ativo"]
    list_filter = ["fabricante", "tipo", "fase", "ativo"]
    search_fields = ["fabricante", "modelo"]


@admin.register(EstruturaFixacao)
class EstruturaAdmin(admin.ModelAdmin):
    list_display = ["fabricante", "modelo", "tipo", "material", "ativo"]
    list_filter = ["tipo", "material", "ativo"]
    search_fields = ["fabricante", "modelo"]
