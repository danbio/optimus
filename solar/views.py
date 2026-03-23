import math

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import PropostaSolarForm
from .models import ModuloFotovoltaico, PropostaSolar


class PropostaSolarListView(LoginRequiredMixin, ListView):
    model = PropostaSolar
    template_name = "solar/proposta_list.html"
    context_object_name = "propostas"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente", "modulo", "inversor")
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

    def get_success_url(self):
        return reverse_lazy("solar:detalhe", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        proposta = form.save(commit=False)
        proposta.potencia_kwp = _calcular_kwp(
            proposta.consumo_medio_kwh,
            proposta.hsp,
            proposta.fator_eficiencia,
        )
        proposta.quantidade_modulos = _calcular_quantidade_modulos(proposta.potencia_kwp, proposta.modulo)
        proposta.save()
        messages.success(self.request, f"Proposta {proposta.numero} criada com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova Proposta Solar"
        ctx["acao"] = "Criar proposta"
        return ctx


class PropostaSolarUpdateView(LoginRequiredMixin, UpdateView):
    model = PropostaSolar
    form_class = PropostaSolarForm
    template_name = "solar/proposta_form.html"

    def get_success_url(self):
        return reverse_lazy("solar:detalhe", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        proposta = form.save(commit=False)
        proposta.potencia_kwp = _calcular_kwp(
            proposta.consumo_medio_kwh,
            proposta.hsp,
            proposta.fator_eficiencia,
        )
        proposta.quantidade_modulos = _calcular_quantidade_modulos(proposta.potencia_kwp, proposta.modulo)
        proposta.save()
        messages.success(self.request, f"Proposta {proposta.numero} atualizada.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.numero}"
        ctx["acao"] = "Salvar alterações"
        return ctx


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


@login_required
def dimensionar(request):
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

    if kwp_necessario and modulo:
        qtd_sugerida = math.ceil(kwp_necessario * 1000 / modulo.potencia_wp)
        kwp_real = round(qtd_sugerida * modulo.potencia_wp / 1000, 3)
        area_m2 = round(qtd_sugerida * modulo.area_m2, 2)

    return render(
        request,
        "solar/_dimensionamento_preview.html",
        {
            "kwp_necessario": kwp_necessario,
            "qtd_sugerida": qtd_sugerida,
            "kwp_real": kwp_real,
            "area_m2": area_m2,
            "modulo": modulo,
        },
    )


# ── helpers ───────────────────────────────────────────────────────────────────


def _calcular_kwp(consumo_kwh, hsp, fator):
    try:
        return round(float(consumo_kwh) / (float(hsp) * 30 * float(fator)), 3)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


def _calcular_quantidade_modulos(kwp, modulo):
    try:
        return math.ceil(float(kwp) * 1000 / modulo.potencia_wp)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


# ── Transições de status ──────────────────────────────────────────────────────


@login_required
@require_POST
def enviar_proposta(request, pk):
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
def aprovar_proposta(request, pk):
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
def cancelar_proposta(request, pk):
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
def reabrir_proposta(request, pk):
    proposta = get_object_or_404(PropostaSolar, pk=pk)
    if proposta.status == PropostaSolar.STATUS_CANCELADA:
        proposta.status = PropostaSolar.STATUS_RASCUNHO
        proposta.save()
        messages.success(request, f"Proposta {proposta.numero} reaberta como Rascunho.")
    else:
        messages.error(request, "Apenas propostas canceladas podem ser reabertas.")
    return redirect("solar:detalhe", pk=pk)
