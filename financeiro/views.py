import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import BaixaForm, LancamentoForm
from .models import LancamentoFinanceiro, ParcelaLancamento


class LancamentoListView(LoginRequiredMixin, ListView):
    model = LancamentoFinanceiro
    template_name = "financeiro/lancamento_list.html"
    context_object_name = "lancamentos"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        forma = self.request.GET.get("forma", "")
        origem = self.request.GET.get("origem", "")
        data_de = self.request.GET.get("data_de", "")
        data_ate = self.request.GET.get("data_ate", "")

        if q:
            qs = qs.filter(Q(numero__icontains=q) | Q(descricao__icontains=q) | Q(cliente__nome__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if forma:
            qs = qs.filter(forma_pagamento=forma)
        if origem == "balcao":
            qs = qs.filter(venda_balcao__isnull=False)
        elif origem == "solar":
            qs = qs.filter(proposta_solar__isnull=False)
        elif origem == "servico":
            qs = qs.filter(proposta_servico__isnull=False)
        elif origem == "os":
            qs = qs.filter(ordem_servico__isnull=False)
        elif origem == "manual":
            qs = qs.filter(
                venda_balcao__isnull=True,
                proposta_solar__isnull=True,
                proposta_servico__isnull=True,
                ordem_servico__isnull=True,
            )
        if data_de:
            qs = qs.filter(data_vencimento__gte=data_de)
        if data_ate:
            qs = qs.filter(data_vencimento__lte=data_ate)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()

        # KPIs sobre o queryset filtrado
        qs = self.get_queryset()
        ctx["total_recebido"] = qs.aggregate(s=Sum("valor_recebido"))["s"] or 0
        ctx["total_liquido"] = qs.aggregate(s=Sum("valor_liquido"))["s"] or 0
        ctx["total_pendente"] = sum(lan.saldo_aberto for lan in qs.filter(status__in=["pendente", "parcial"]))
        ctx["total_vencido"] = sum(lan.saldo_aberto for lan in qs.filter(status__in=["pendente", "parcial"]) if lan.data_vencimento < today)

        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_filtro"] = self.request.GET.get("status", "")
        ctx["forma_filtro"] = self.request.GET.get("forma", "")
        ctx["origem_filtro"] = self.request.GET.get("origem", "")
        ctx["data_de"] = self.request.GET.get("data_de", "")
        ctx["data_ate"] = self.request.GET.get("data_ate", "")
        ctx["status_choices"] = LancamentoFinanceiro.STATUS_CHOICES
        ctx["forma_choices"] = LancamentoFinanceiro.FORMA_CHOICES
        ctx["today"] = today
        return ctx


class LancamentoDetailView(LoginRequiredMixin, DetailView):
    model = LancamentoFinanceiro
    template_name = "financeiro/lancamento_detail.html"
    context_object_name = "lan"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("cliente", "venda_balcao", "proposta_solar", "proposta_servico", "ordem_servico")
            .prefetch_related("parcelas", "baixas__registrado_por")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["baixa_form"] = BaixaForm(lancamento=self.object)
        ctx["today"] = timezone.localdate()
        return ctx


class LancamentoCreateView(LoginRequiredMixin, CreateView):
    model = LancamentoFinanceiro
    form_class = LancamentoForm
    template_name = "financeiro/lancamento_form.html"

    def get_success_url(self):
        return reverse("financeiro:detalhe", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        lan = form.save()
        self.object = lan
        # Criar parcelas
        num = lan.num_parcelas or 1
        from .services import _criar_parcelas

        _criar_parcelas(lan, num, lan.data_vencimento)
        messages.success(self.request, f"Lançamento {lan.numero} criado com sucesso.")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Lançamento Manual"
        ctx["acao"] = "Criar lançamento"
        return ctx


class LancamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = LancamentoFinanceiro
    form_class = LancamentoForm
    template_name = "financeiro/lancamento_form.html"

    def get_queryset(self):
        return super().get_queryset().filter(status__in=["pendente", "parcial"])

    def get_success_url(self):
        return reverse("financeiro:detalhe", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        lan = form.save()
        messages.success(self.request, f"Lançamento {lan.numero} atualizado.")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.numero}"
        ctx["acao"] = "Salvar alterações"
        return ctx


@login_required
@require_POST
def cancelar_lancamento(request, pk):
    lan = get_object_or_404(LancamentoFinanceiro, pk=pk)
    if lan.status not in (LancamentoFinanceiro.STATUS_LIQUIDADO, LancamentoFinanceiro.STATUS_CANCELADO):
        lan.status = LancamentoFinanceiro.STATUS_CANCELADO
        lan.save()
        lan.parcelas.filter(status="pendente").update(status="cancelado")
        messages.warning(request, f"Lançamento {lan.numero} cancelado.")
    else:
        messages.error(request, "Este lançamento não pode ser cancelado.")
    return redirect("financeiro:detalhe", pk=pk)


@login_required
@require_POST
def registrar_baixa(request, pk):
    lan = get_object_or_404(LancamentoFinanceiro, pk=pk)
    form = BaixaForm(request.POST, lancamento=lan)

    if lan.status in (LancamentoFinanceiro.STATUS_LIQUIDADO, LancamentoFinanceiro.STATUS_CANCELADO):
        messages.error(request, "Este lançamento já está liquidado ou cancelado.")
        return redirect("financeiro:detalhe", pk=pk)

    if form.is_valid():
        with transaction.atomic():
            baixa = form.save(commit=False)
            baixa.lancamento = lan
            baixa.registrado_por = request.user
            baixa.save()

            # Atualizar parcela se informada
            parcela = form.cleaned_data.get("parcela")
            if parcela:
                parcela.valor_pago = (parcela.valor_pago or 0) + baixa.valor
                parcela.data_pagamento = baixa.data_pagamento
                if parcela.valor_pago >= parcela.valor:
                    parcela.status = ParcelaLancamento.STATUS_PAGO
                parcela.save()

            # Recalcular valor_recebido e status do lançamento
            total_recebido = lan.baixas.aggregate(s=Sum("valor"))["s"] or 0
            lan.valor_recebido = total_recebido
            if lan.valor_recebido >= lan.valor_liquido:
                lan.status = LancamentoFinanceiro.STATUS_LIQUIDADO
                lan.data_liquidacao = timezone.localdate()
            elif lan.valor_recebido > 0:
                lan.status = LancamentoFinanceiro.STATUS_PARCIAL
            lan.save()

        messages.success(request, f"Baixa de R$ {baixa.valor} registrada com sucesso.")
    else:
        for erros in form.errors.values():
            for e in erros:
                messages.error(request, e)

    return redirect("financeiro:detalhe", pk=pk)


@login_required
def form_baixa_htmx(request, pk):
    """Retorna o formulário de baixa como partial HTML (HTMX GET)."""
    lan = get_object_or_404(LancamentoFinanceiro, pk=pk)
    form = BaixaForm(lancamento=lan)
    return render(request, "financeiro/_form_baixa.html", {"form": form, "lan": lan})


@login_required
def dashboard(request):
    today = timezone.localdate()
    primeiro_mes = today.replace(day=1)

    periodo = request.GET.get("periodo", "mes")
    if periodo == "mes":
        data_de = primeiro_mes
        data_ate = today
    elif periodo == "trimestre":
        mes_inicio = ((today.month - 1) // 3) * 3 + 1
        data_de = today.replace(month=mes_inicio, day=1)
        data_ate = today
    elif periodo == "ano":
        data_de = today.replace(month=1, day=1)
        data_ate = today
    else:  # personalizado
        try:
            data_de = datetime.date.fromisoformat(request.GET.get("data_de", str(primeiro_mes)))
            data_ate = datetime.date.fromisoformat(request.GET.get("data_ate", str(today)))
        except ValueError:
            data_de = primeiro_mes
            data_ate = today

    qs = LancamentoFinanceiro.objects.filter(
        data_vencimento__gte=data_de,
        data_vencimento__lte=data_ate,
    ).select_related("cliente")

    total_liquido = qs.aggregate(s=Sum("valor_liquido"))["s"] or 0
    total_recebido = qs.aggregate(s=Sum("valor_recebido"))["s"] or 0

    pendentes = qs.filter(status__in=["pendente", "parcial"])
    total_pendente = sum(lan.saldo_aberto for lan in pendentes)
    total_vencido = sum(lan.saldo_aberto for lan in pendentes if lan.data_vencimento < today)

    inadimplencia_pct = round(total_vencido / total_liquido * 100, 1) if total_liquido > 0 else 0

    # Vencimentos próximos (7 dias)
    proximos = (
        LancamentoFinanceiro.objects.filter(
            status__in=["pendente", "parcial"],
            data_vencimento__gte=today,
            data_vencimento__lte=today + datetime.timedelta(days=7),
        )
        .select_related("cliente")
        .order_by("data_vencimento")
    )

    # Em atraso
    atrasados = (
        LancamentoFinanceiro.objects.filter(
            status__in=["pendente", "parcial"],
            data_vencimento__lt=today,
        )
        .select_related("cliente")
        .order_by("data_vencimento")
    )

    # Recebido por forma de pagamento
    formas = {}
    for lan in qs.filter(status__in=["parcial", "liquidado"]):
        forma = lan.get_forma_pagamento_display() or "Não informado"
        formas[forma] = formas.get(forma, 0) + float(lan.valor_recebido)
    formas_sorted = sorted(formas.items(), key=lambda x: x[1], reverse=True)
    max_forma = max((v for _, v in formas_sorted), default=1)

    return render(
        request,
        "financeiro/dashboard.html",
        {
            "periodo": periodo,
            "data_de": data_de,
            "data_ate": data_ate,
            "total_liquido": total_liquido,
            "total_recebido": total_recebido,
            "total_pendente": total_pendente,
            "total_vencido": total_vencido,
            "inadimplencia_pct": inadimplencia_pct,
            "proximos": proximos,
            "atrasados": atrasados,
            "formas_sorted": formas_sorted,
            "max_forma": max_forma,
            "today": today,
        },
    )
