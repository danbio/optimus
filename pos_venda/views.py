from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import ChamadoForm, InteracaoForm
from .models import Chamado


class ChamadoListView(LoginRequiredMixin, ListView):
    model = Chamado
    template_name = "pos_venda/chamado_list.html"
    context_object_name = "chamados"
    paginate_by = 25

    def get_queryset(self):
        qs = Chamado.objects.select_related("cliente", "responsavel").order_by("-criado_em")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        tipo = self.request.GET.get("tipo", "")
        prioridade = self.request.GET.get("prioridade", "")

        if q:
            qs = qs.filter(Q(numero__icontains=q) | Q(assunto__icontains=q) | Q(cliente__nome__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if prioridade:
            qs = qs.filter(prioridade=prioridade)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        base = Chamado.objects.all()
        ctx["kpi_abertos"] = base.filter(status=Chamado.STATUS_ABERTO).count()
        ctx["kpi_em_atendimento"] = base.filter(status=Chamado.STATUS_ATENDIMENTO).count()
        ctx["kpi_vencidos"] = base.filter(
            prazo__lt=hoje,
            status__in=[Chamado.STATUS_ABERTO, Chamado.STATUS_ATENDIMENTO, Chamado.STATUS_AGUARDANDO],
        ).count()
        ctx["kpi_resolvidos_mes"] = base.filter(
            status__in=[Chamado.STATUS_RESOLVIDO, Chamado.STATUS_ENCERRADO],
            atualizado_em__month=hoje.month,
            atualizado_em__year=hoje.year,
        ).count()
        ctx["status_choices"] = Chamado.STATUS_CHOICES
        ctx["tipo_choices"] = Chamado.TIPO_CHOICES
        ctx["prioridade_choices"] = Chamado.PRIORIDADE_CHOICES
        ctx["filtros"] = self.request.GET
        return ctx


class ChamadoCreateView(LoginRequiredMixin, CreateView):
    model = Chamado
    form_class = ChamadoForm
    template_name = "pos_venda/chamado_form.html"

    def get_success_url(self):
        return reverse("pos_venda:detalhe", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Chamado"
        return ctx


class ChamadoUpdateView(LoginRequiredMixin, UpdateView):
    model = Chamado
    form_class = ChamadoForm
    template_name = "pos_venda/chamado_form.html"

    def get_success_url(self):
        return reverse("pos_venda:detalhe", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar Chamado {self.object.numero}"
        return ctx


class ChamadoDetailView(LoginRequiredMixin, DetailView):
    model = Chamado
    template_name = "pos_venda/chamado_detail.html"
    context_object_name = "chamado"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["interacoes"] = self.object.interacoes.select_related("autor").order_by("criado_em")
        ctx["form_interacao"] = InteracaoForm()
        ctx["status_choices"] = Chamado.STATUS_CHOICES
        return ctx


@login_required
@require_POST
def mudar_status(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    novo_status = request.POST.get("status")
    validos = [s for s, _ in Chamado.STATUS_CHOICES]
    if novo_status not in validos:
        messages.error(request, "Status inválido.")
        return redirect("pos_venda:detalhe", pk=pk)

    chamado.status = novo_status
    if novo_status in (Chamado.STATUS_RESOLVIDO, Chamado.STATUS_ENCERRADO):
        chamado.data_resolucao = timezone.now()
    else:
        chamado.data_resolucao = None
    chamado.save()
    messages.success(request, f"Chamado {chamado.numero} movido para «{chamado.get_status_display()}».")
    return redirect("pos_venda:detalhe", pk=pk)


@login_required
@require_POST
def adicionar_interacao(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    form = InteracaoForm(request.POST)
    if form.is_valid():
        interacao = form.save(commit=False)
        interacao.chamado = chamado
        interacao.autor = request.user
        interacao.save()
        # Muda status automaticamente se era aberto
        if chamado.status == Chamado.STATUS_ABERTO:
            chamado.status = Chamado.STATUS_ATENDIMENTO
            chamado.save()
        messages.success(request, "Interação registrada.")
    else:
        messages.error(request, "Erro ao registrar interação. Verifique os campos.")
    return redirect("pos_venda:detalhe", pk=pk)


@login_required
def historico_cliente(request, cliente_pk):
    from clientes.models import Cliente

    cliente = get_object_or_404(Cliente, pk=cliente_pk)
    chamados = Chamado.objects.filter(cliente=cliente).order_by("-criado_em")

    from ordens_servico.models import OrdemServico

    ordens = OrdemServico.objects.filter(cliente=cliente).order_by("-criado_em")

    from solar.models import PropostaSolar

    propostas_solar = PropostaSolar.objects.filter(cliente=cliente).order_by("-criado_em")

    from servicos.models import PropostaServico

    propostas_servico = PropostaServico.objects.filter(cliente=cliente).order_by("-criado_em")

    from balcao.models import Venda

    vendas = Venda.objects.filter(cliente=cliente).exclude(status="cancelada").order_by("-criado_em")

    return render(
        request,
        "pos_venda/historico_cliente.html",
        {
            "cliente": cliente,
            "chamados": chamados,
            "ordens": ordens,
            "propostas_solar": propostas_solar,
            "propostas_servico": propostas_servico,
            "vendas": vendas,
        },
    )
