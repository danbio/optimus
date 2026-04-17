"""Views de gerenciamento de preços de equipamentos solares."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from ..forms import PrecoEquipamentoSolarForm
from ..models import (
    EstruturaFixacao,
    Inversor,
    MateriaisEletricos,
    ModuloFotovoltaico,
    PrecoEquipamentoSolar,
)
from ._helpers import campo_fk


def _gerenciar_preco(request: HttpRequest, equipamento: object, lista_url: str, tipo_label: str) -> HttpResponse:
    """View genérica de histórico + cadastro de novo preço para um equipamento."""
    historico = PrecoEquipamentoSolar.objects.filter(**{campo_fk(equipamento): equipamento}).order_by("-vigente_desde")
    preco_vigente = PrecoEquipamentoSolar.get_preco_vigente(equipamento, date.today())

    if request.method == "POST":
        form = PrecoEquipamentoSolarForm(request.POST)
        if form.is_valid():
            novo = form.save(commit=False)
            PrecoEquipamentoSolar.objects.filter(
                vigente_ate__isnull=True,
                **{campo_fk(equipamento): equipamento},
            ).update(vigente_ate=date.today())
            setattr(novo, campo_fk(equipamento), equipamento)
            novo.criado_por = request.user
            novo.save()
            messages.success(request, "Preço cadastrado com sucesso.")
            return redirect(lista_url)
    else:
        form = PrecoEquipamentoSolarForm()

    return render(
        request,
        "solar/preco_gerenciar.html",
        {
            "equipamento": equipamento,
            "tipo_label": tipo_label,
            "historico": historico,
            "preco_vigente": preco_vigente,
            "form": form,
            "voltar_url": lista_url,
        },
    )


@login_required
def modulo_precos(request: HttpRequest, pk: int) -> HttpResponse:
    equipamento = get_object_or_404(ModuloFotovoltaico, pk=pk)
    return _gerenciar_preco(request, equipamento, reverse_lazy("solar:modulos"), "Módulo Fotovoltaico")


@login_required
def inversor_precos(request: HttpRequest, pk: int) -> HttpResponse:
    equipamento = get_object_or_404(Inversor, pk=pk)
    return _gerenciar_preco(request, equipamento, reverse_lazy("solar:inversores"), "Inversor")


@login_required
def estrutura_precos(request: HttpRequest, pk: int) -> HttpResponse:
    equipamento = get_object_or_404(EstruturaFixacao, pk=pk)
    return _gerenciar_preco(request, equipamento, reverse_lazy("solar:estruturas"), "Estrutura de Fixação")


@login_required
def material_precos(request: HttpRequest, pk: int) -> HttpResponse:
    equipamento = get_object_or_404(MateriaisEletricos, pk=pk)
    return _gerenciar_preco(request, equipamento, reverse_lazy("solar:materiais"), "Material Elétrico")
