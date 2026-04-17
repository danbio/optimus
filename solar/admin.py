from datetime import date

from django.contrib import admin

from .models import EstruturaFixacao, Inversor, MateriaisEletricos, ModuloFotovoltaico, PrecoEquipamentoSolar


@admin.register(MateriaisEletricos)
class MateriaisEletricosAdmin(admin.ModelAdmin):
    list_display = ["fabricante", "modelo", "categoria", "unidade", "ativo"]
    list_filter = ["categoria", "ativo"]
    search_fields = ["fabricante", "modelo"]


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


@admin.register(PrecoEquipamentoSolar)
class PrecoEquipamentoSolarAdmin(admin.ModelAdmin):
    list_display = ["__str__", "preco_custo", "preco_venda", "vigente_desde", "vigente_ate", "criado_por"]
    list_filter = ["vigente_ate"]
    ordering = ["-vigente_desde"]

    def get_readonly_fields(self, request, obj=None):
        # Registros históricos (vigente_ate preenchido) são totalmente readonly — não se edita histórico
        if obj and obj.vigente_ate is not None:
            return [f.name for f in self.model._meta.fields]
        return ["vigente_ate", "criado_por", "criado_em", "atualizado_em"]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criado_por = request.user
            # Fecha automaticamente o preço vigente anterior do mesmo equipamento
            filtro = {}
            if obj.modulo_id:
                filtro["modulo"] = obj.modulo
            elif obj.inversor_id:
                filtro["inversor"] = obj.inversor
            elif obj.estrutura_id:
                filtro["estrutura"] = obj.estrutura
            elif obj.material_id:
                filtro["material"] = obj.material
            PrecoEquipamentoSolar.objects.filter(vigente_ate__isnull=True, **filtro).update(vigente_ate=date.today())
        super().save_model(request, obj, form, change)

    def has_module_perms(self, request):
        return request.user.is_staff
