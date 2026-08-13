"""Views de propostas solares — CRUD, dimensionamento HTMX e transições de status."""

import math
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import (
    ItemPropostaSolarForm,
    ItemPropostaSolarFormSet,
    PropostaSolarForm,
)
from ..models import (
    EstruturaFixacao,
    Inversor,
    MateriaisEletricos,
    ModuloFotovoltaico,
    PrecoEquipamentoSolar,
    PropostaSolar,
)
from ._helpers import calcular_kwp, inversores_compativeis

# ── CRUD de Propostas ─────────────────────────────────────────────────────────


class PropostaSolarListView(LoginRequiredMixin, ListView):
    model = PropostaSolar
    template_name = "solar/proposta_list.html"
    context_object_name = "propostas"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente", "modulo")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")

        if q:
            qs = qs.filter(Q(numero__icontains=q) | Q(cliente__nome__icontains=q) | Q(cliente__cpf_cnpj__icontains=q))
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_filtro"] = self.request.GET.get("status", "")
        ctx["status_choices"] = PropostaSolar.STATUS_CHOICES
        return ctx


class PropostaSolarCreateView(LoginRequiredMixin, CreateView):
    model = PropostaSolar
    form_class = PropostaSolarForm
    template_name = "solar/proposta_form.html"

    def get_success_url(self) -> str:
        return reverse_lazy("solar:detalhe", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs) -> dict:
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = ItemPropostaSolarFormSet(self.request.POST)
        else:
            ctx["formset"] = ItemPropostaSolarFormSet()
        ctx["titulo"] = "Nova Proposta Solar"
        ctx["acao"] = "Criar proposta"
        return ctx

    def form_valid(self, form: PropostaSolarForm) -> HttpResponse:
        context = self.get_context_data()
        formset = context["formset"]

        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        proposta = form.save(commit=False)
        proposta.potencia_kwp = calcular_kwp(
            proposta.consumo_medio_kwh,
            proposta.hsp,
            proposta.fator_eficiencia,
        )

        formset.instance = proposta
        hoje = date.today()
        instances = formset.save(commit=False)

        modulo_item = next((item for item in instances if item.modulo), None)
        if modulo_item:
            proposta.modulo = modulo_item.modulo
            proposta.quantidade_modulos = sum(item.quantidade for item in instances if item.modulo)

        proposta.save()
        self.object = proposta

        for obj in formset.deleted_objects:
            obj.delete()

        for item in instances:
            equip = item.modulo or item.inversor or item.estrutura or item.material
            preco = PrecoEquipamentoSolar.get_preco_vigente(equip, hoje) if equip else None
            item.preco_venda_snapshot = preco.preco_venda if preco else 0
            item.preco_custo_snapshot = preco.preco_custo if preco else 0
            item.data_referencia_preco = hoje
            item.save()

        messages.success(self.request, f"Proposta {proposta.numero} criada com sucesso.")
        return HttpResponseRedirect(self.get_success_url())


class PropostaSolarUpdateView(LoginRequiredMixin, UpdateView):
    model = PropostaSolar
    form_class = PropostaSolarForm
    template_name = "solar/proposta_form.html"

    def get_success_url(self) -> str:
        return reverse_lazy("solar:detalhe", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs) -> dict:
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = ItemPropostaSolarFormSet(self.request.POST, instance=self.object)
        else:
            ctx["formset"] = ItemPropostaSolarFormSet(instance=self.object)
        ctx["titulo"] = f"Editar — {self.object.numero}"
        ctx["acao"] = "Salvar alterações"
        return ctx

    def form_valid(self, form: PropostaSolarForm) -> HttpResponse:
        context = self.get_context_data()
        formset = context["formset"]

        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        proposta = form.save(commit=False)
        proposta.potencia_kwp = calcular_kwp(
            proposta.consumo_medio_kwh,
            proposta.hsp,
            proposta.fator_eficiencia,
        )

        formset.instance = proposta
        hoje = date.today()
        instances = formset.save(commit=False)

        modulo_item = next((item for item in instances if item.modulo), None)
        if modulo_item:
            proposta.modulo = modulo_item.modulo
            proposta.quantidade_modulos = sum(item.quantidade for item in instances if item.modulo)
        elif not proposta.modulo_id:
            proposta.modulo = PropostaSolar.objects.filter(pk=proposta.pk).values_list("modulo", flat=True).first()

        proposta.save()
        self.object = proposta

        for obj in formset.deleted_objects:
            obj.delete()

        for item in instances:
            if not item.pk:
                equip = item.modulo or item.inversor or item.estrutura or item.material
                preco = PrecoEquipamentoSolar.get_preco_vigente(equip, hoje) if equip else None
                item.preco_venda_snapshot = preco.preco_venda if preco else 0
                item.preco_custo_snapshot = preco.preco_custo if preco else 0
                item.data_referencia_preco = hoje
            item.save()

        messages.success(self.request, f"Proposta {proposta.numero} atualizada.")
        return HttpResponseRedirect(self.get_success_url())


class PropostaSolarDetailView(LoginRequiredMixin, DetailView):
    model = PropostaSolar
    template_name = "solar/proposta_detail.html"
    context_object_name = "proposta"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente").prefetch_related("ordens_servico__tecnico")


class PropostaSolarDeleteView(LoginRequiredMixin, DeleteView):
    model = PropostaSolar
    template_name = "solar/proposta_confirm_delete.html"
    success_url = reverse_lazy("solar:lista")

    def form_valid(self, form):
        messages.success(self.request, f"Proposta {self.object.numero} removida.")
        return super().form_valid(form)


# ── Dimensionamento HTMX ─────────────────────────────────────────────────────


@login_required
def dimensionar(request: HttpRequest) -> HttpResponse:
    """Endpoint HTMX — retorna preview do dimensionamento em tempo real."""
    try:
        consumo = float(request.GET.get("consumo_medio_kwh") or 0)
        hsp = float(request.GET.get("hsp") or 5.5)
        fator = float(request.GET.get("fator_eficiencia") or 0.75)
        modulo_id = request.GET.get("modulo")
    except (ValueError, TypeError):
        return HttpResponse("")

    if consumo <= 0:
        return HttpResponse("")

    modulo = None
    if modulo_id:
        modulo = ModuloFotovoltaico.objects.filter(pk=modulo_id, ativo=True).first()

    kwp_necessario = round(consumo / (hsp * 30 * fator), 3) if hsp > 0 and fator > 0 else None
    qtd_sugerida = None
    kwp_real = None
    area_m2 = None
    inversores = []

    if kwp_necessario and modulo:
        qtd_sugerida = math.ceil(kwp_necessario * 1000 / modulo.potencia_wp)
        kwp_real = round(qtd_sugerida * modulo.potencia_wp / 1000, 3)
        area_m2 = round(qtd_sugerida * modulo.area_m2, 2)

        from configuracoes.models import Configuracao

        config = Configuracao.atual()
        inversores = inversores_compativeis(
            kwp_real,
            config.inversor_sobrecarga_minima_pct,
            config.inversor_sobrecarga_maxima_pct,
        )

    return render(
        request,
        "solar/_dimensionamento_preview.html",
        {
            "kwp_necessario": kwp_necessario,
            "qtd_sugerida": qtd_sugerida,
            "kwp_real": kwp_real,
            "area_m2": area_m2,
            "modulo": modulo,
            "inversores": inversores,
        },
    )


@login_required
def adicionar_item_solar(request: HttpRequest) -> HttpResponse:
    """Endpoint HTMX para adicionar uma linha ao formset.

    Sem parâmetros: linha vazia (botão "Adicionar Item"). Com `modulo`,
    `inversor`, `estrutura` ou `material` (+ opcionalmente `quantidade`):
    linha pré-preenchida — usado pelos botões "Usar este dimensionamento" e
    "Usar este inversor" no preview, pra não obrigar o vendedor a calcular a
    sugestão e depois digitá-la de novo na tabela.
    """
    index = request.GET.get("index", "0")
    initial = {}
    for campo in ("modulo", "inversor", "estrutura", "material"):
        valor = request.GET.get(campo)
        if valor:
            initial[campo] = valor
    quantidade = request.GET.get("quantidade")
    if quantidade:
        initial["quantidade"] = quantidade
    form = ItemPropostaSolarForm(prefix=f"itens-{index}", initial=initial or None)
    return render(
        request,
        "solar/_item_proposta_row.html",
        {"item_form": form, "index": index},
    )


@login_required
def calcular_total_equipamentos(request: HttpRequest) -> HttpResponse:
    """Endpoint HTMX — calcula total de equipamentos a partir do formset."""
    hoje = date.today()
    total = Decimal("0")

    try:
        total_forms = int(request.GET.get("itens-TOTAL_FORMS") or 0)
    except (ValueError, TypeError):
        total_forms = 0

    for i in range(total_forms):
        try:
            quantidade = int(request.GET.get(f"itens-{i}-quantidade") or 0)
        except (ValueError, TypeError):
            quantidade = 0
        if quantidade <= 0:
            continue

        equip = None
        for campo, modelo in [
            ("modulo", ModuloFotovoltaico),
            ("inversor", Inversor),
            ("estrutura", EstruturaFixacao),
            ("material", MateriaisEletricos),
        ]:
            pk = request.GET.get(f"itens-{i}-{campo}")
            if pk:
                try:
                    equip = modelo.objects.get(pk=int(pk))
                except (modelo.DoesNotExist, ValueError):
                    pass
                break

        if equip:
            preco = PrecoEquipamentoSolar.get_preco_vigente(equip, hoje)
            if preco:
                total += preco.preco_venda * quantidade

    return HttpResponse(f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))


# ── Transições de status ─────────────────────────────────────────────────────


@login_required
@require_POST
def enviar_proposta(request: HttpRequest, pk: int) -> HttpResponse:
    proposta = get_object_or_404(PropostaSolar, pk=pk)
    if proposta.status == PropostaSolar.STATUS_RASCUNHO:
        proposta.status = PropostaSolar.STATUS_ENVIADA
        proposta.save()
        messages.success(request, f"Proposta {proposta.numero} enviada ao cliente.")
    else:
        messages.error(request, "Apenas propostas em Rascunho podem ser enviadas.")
    return redirect("solar:detalhe", pk=pk)


@login_required
@require_POST
def aprovar_proposta(request: HttpRequest, pk: int) -> HttpResponse:
    proposta = get_object_or_404(PropostaSolar, pk=pk)
    if proposta.status == PropostaSolar.STATUS_ENVIADA:
        proposta.status = PropostaSolar.STATUS_APROVADA
        proposta.save()
        from financeiro.services import criar_lancamento_de_proposta_solar

        criar_lancamento_de_proposta_solar(proposta)
        messages.success(request, f"Proposta {proposta.numero} aprovada! Lançamento financeiro gerado.")
    else:
        messages.error(request, "Apenas propostas Enviadas podem ser aprovadas.")
    return redirect("solar:detalhe", pk=pk)


@login_required
@require_POST
def cancelar_proposta(request: HttpRequest, pk: int) -> HttpResponse:
    proposta = get_object_or_404(PropostaSolar, pk=pk)
    if proposta.status not in (PropostaSolar.STATUS_CONCLUIDA, PropostaSolar.STATUS_CANCELADA):
        proposta.status = PropostaSolar.STATUS_CANCELADA
        proposta.save()
        messages.warning(request, f"Proposta {proposta.numero} cancelada.")
    else:
        messages.error(request, "Esta proposta não pode ser cancelada.")
    return redirect("solar:detalhe", pk=pk)


@login_required
@require_POST
def reabrir_proposta(request: HttpRequest, pk: int) -> HttpResponse:
    proposta = get_object_or_404(PropostaSolar, pk=pk)
    if proposta.status == PropostaSolar.STATUS_CANCELADA:
        proposta.status = PropostaSolar.STATUS_RASCUNHO
        proposta.save()
        messages.success(request, f"Proposta {proposta.numero} reaberta como Rascunho.")
    else:
        messages.error(request, "Apenas propostas canceladas podem ser reabertas.")
    return redirect("solar:detalhe", pk=pk)
