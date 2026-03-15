from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "cpf_cnpj", "cidade", "estado", "ativo")
    list_filter = ("tipo", "ativo", "estado")
    search_fields = ("nome", "cpf_cnpj", "email")
    readonly_fields = ("tipo", "criado_em", "atualizado_em")
