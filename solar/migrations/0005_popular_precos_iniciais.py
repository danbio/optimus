"""Data migration: popula PrecoEquipamentoSolar com valores zerados (placeholder)
para todos os equipamentos solares ativos já cadastrados.

O administrador deve preencher os valores reais pelo Django Admin após a migração.
"""

from datetime import date

from django.db import migrations


def popular_precos(apps, schema_editor):
    PrecoEquipamentoSolar = apps.get_model("solar", "PrecoEquipamentoSolar")
    ModuloFotovoltaico = apps.get_model("solar", "ModuloFotovoltaico")
    Inversor = apps.get_model("solar", "Inversor")
    EstruturaFixacao = apps.get_model("solar", "EstruturaFixacao")
    User = apps.get_model("auth", "User")

    hoje = date.today()
    admin_user = User.objects.filter(is_superuser=True).first()

    for modulo in ModuloFotovoltaico.objects.filter(ativo=True):
        PrecoEquipamentoSolar.objects.create(
            modulo=modulo,
            preco_custo=0,
            preco_venda=0,
            vigente_desde=hoje,
            vigente_ate=None,
            criado_por=admin_user,
        )

    for inversor in Inversor.objects.filter(ativo=True):
        PrecoEquipamentoSolar.objects.create(
            inversor=inversor,
            preco_custo=0,
            preco_venda=0,
            vigente_desde=hoje,
            vigente_ate=None,
            criado_por=admin_user,
        )

    for estrutura in EstruturaFixacao.objects.filter(ativo=True):
        PrecoEquipamentoSolar.objects.create(
            estrutura=estrutura,
            preco_custo=0,
            preco_venda=0,
            vigente_desde=hoje,
            vigente_ate=None,
            criado_por=admin_user,
        )


def desfazer_precos(apps, schema_editor):
    PrecoEquipamentoSolar = apps.get_model("solar", "PrecoEquipamentoSolar")
    PrecoEquipamentoSolar.objects.filter(preco_venda=0, preco_custo=0).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("solar", "0004_remove_propostasolar_valor_equipamentos_and_more"),
    ]

    operations = [
        migrations.RunPython(popular_precos, desfazer_precos),
    ]
