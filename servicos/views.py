import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from estoque.models import Produto

from .forms import (
    ItemProdutoFormSet,
    ItemServicoFormSet,
    PropostaServicoForm,
    ServicoForm,
)
from .models import PropostaServico, Servico

# ── Catálogo de Serviços ───────────────────────────────────────────────────────


class ServicoListView(LoginRequiredMixin, ListView):
    model = Servico
    template_name = "servicos/servico_list.html"
    context_object_name = "servicos"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "")
        ativo = self.request.GET.get("ativo", "")

        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
        if tipo:
            qs = qs.filter(tipo=tipo)
        if ativo == "1":
            qs = qs.filter(ativo=True)
        elif ativo == "0":
            qs = qs.filter(ativo=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo_filtro"] = self.request.GET.get("tipo", "")
        ctx["ativo_filtro"] = self.request.GET.get("ativo", "")
        ctx["tipo_choices"] = Servico.TIPO_CHOICES
        return ctx


class ServicoCreateView(LoginRequiredMixin, CreateView):
    model = Servico
    form_class = ServicoForm
    template_name = "servicos/servico_form.html"
    success_url = reverse_lazy("servicos:catalogo")

    def form_valid(self, form):
        messages.success(self.request, f"Serviço '{form.instance.nome}' cadastrado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Serviço"
        ctx["acao"] = "Cadastrar serviço"
        return ctx


class ServicoUpdateView(LoginRequiredMixin, UpdateView):
    model = Servico
    form_class = ServicoForm
    template_name = "servicos/servico_form.html"
    success_url = reverse_lazy("servicos:catalogo")

    def form_valid(self, form):
        messages.success(self.request, f"Serviço '{form.instance.nome}' atualizado.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome}"
        ctx["acao"] = "Salvar alterações"
        return ctx


class ServicoDeleteView(LoginRequiredMixin, DeleteView):
    model = Servico
    template_name = "servicos/servico_confirm_delete.html"
    success_url = reverse_lazy("servicos:catalogo")

    def form_valid(self, form):
        messages.success(self.request, f"Serviço '{self.object.nome}' removido.")
        return super().form_valid(form)


# ── Propostas de Serviço ──────────────────────────────────────────────────────


class PropostaListView(LoginRequiredMixin, ListView):
    model = PropostaServico
    template_name = "servicos/proposta_list.html"
    context_object_name = "propostas"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente")
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "")
        status = self.request.GET.get("status", "")

        if q:
            qs = qs.filter(Q(numero__icontains=q) | Q(cliente__nome__icontains=q) | Q(cliente__cpf_cnpj__icontains=q))
        if tipo:
            qs = qs.filter(tipo_servico=tipo)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo_filtro"] = self.request.GET.get("tipo", "")
        ctx["status_filtro"] = self.request.GET.get("status", "")
        ctx["tipo_choices"] = PropostaServico.TIPO_CHOICES
        ctx["status_choices"] = PropostaServico.STATUS_CHOICES
        return ctx


class PropostaCreateView(LoginRequiredMixin, CreateView):
    model = PropostaServico
    form_class = PropostaServicoForm
    template_name = "servicos/proposta_form.html"

    def get_success_url(self):
        return reverse_lazy("servicos:detalhe", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        initial["validade"] = datetime.date.today() + datetime.timedelta(days=30)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset_servicos"] = ItemServicoFormSet(self.request.POST, prefix="srv")
            ctx["formset_produtos"] = ItemProdutoFormSet(self.request.POST, prefix="prod")
        else:
            ctx["formset_servicos"] = ItemServicoFormSet(prefix="srv")
            ctx["formset_produtos"] = ItemProdutoFormSet(prefix="prod")
        ctx["titulo"] = "Nova Proposta de Serviço"
        ctx["acao"] = "Criar proposta"
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset_servicos = ctx["formset_servicos"]
        formset_produtos = ctx["formset_produtos"]

        if formset_servicos.is_valid() and formset_produtos.is_valid():
            proposta = form.save()
            formset_servicos.instance = proposta
            formset_servicos.save()
            formset_produtos.instance = proposta
            formset_produtos.save()
            messages.success(self.request, f"Proposta {proposta.numero} criada com sucesso.")
            self.object = proposta
            return super().form_valid(form)
        else:
            return self.form_invalid(form)


class PropostaUpdateView(LoginRequiredMixin, UpdateView):
    model = PropostaServico
    form_class = PropostaServicoForm
    template_name = "servicos/proposta_form.html"

    def get_success_url(self):
        return reverse_lazy("servicos:detalhe", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset_servicos"] = ItemServicoFormSet(self.request.POST, instance=self.object, prefix="srv")
            ctx["formset_produtos"] = ItemProdutoFormSet(self.request.POST, instance=self.object, prefix="prod")
        else:
            ctx["formset_servicos"] = ItemServicoFormSet(instance=self.object, prefix="srv")
            ctx["formset_produtos"] = ItemProdutoFormSet(instance=self.object, prefix="prod")
        ctx["titulo"] = f"Editar — {self.object.numero}"
        ctx["acao"] = "Salvar alterações"
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset_servicos = ctx["formset_servicos"]
        formset_produtos = ctx["formset_produtos"]

        if formset_servicos.is_valid() and formset_produtos.is_valid():
            proposta = form.save()
            formset_servicos.instance = proposta
            formset_servicos.save()
            formset_produtos.instance = proposta
            formset_produtos.save()
            messages.success(self.request, f"Proposta {proposta.numero} atualizada.")
            self.object = proposta
            return super().form_valid(form)
        else:
            return self.form_invalid(form)


class PropostaDetailView(LoginRequiredMixin, DetailView):
    model = PropostaServico
    template_name = "servicos/proposta_detail.html"
    context_object_name = "proposta"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente").prefetch_related("itens_servico__servico", "itens_produto__produto", "ordens_servico__tecnico")


class PropostaDeleteView(LoginRequiredMixin, DeleteView):
    model = PropostaServico
    template_name = "servicos/proposta_confirm_delete.html"
    success_url = reverse_lazy("servicos:lista")

    def form_valid(self, form):
        messages.success(self.request, f"Proposta {self.object.numero} removida.")
        return super().form_valid(form)


# ── Transições de status ──────────────────────────────────────────────────────


@login_required
@require_POST
def enviar_proposta(request, pk):
    proposta = get_object_or_404(PropostaServico, pk=pk)
    if proposta.status == PropostaServico.STATUS_RASCUNHO:
        proposta.status = PropostaServico.STATUS_ENVIADA
        proposta.save()
        messages.success(request, f"Proposta {proposta.numero} enviada ao cliente.")
    else:
        messages.error(request, "Apenas propostas em Rascunho podem ser enviadas.")
    return redirect("servicos:detalhe", pk=pk)


@login_required
@require_POST
def aprovar_proposta(request, pk):
    proposta = get_object_or_404(PropostaServico, pk=pk)
    if proposta.status == PropostaServico.STATUS_ENVIADA:
        proposta.status = PropostaServico.STATUS_APROVADA
        proposta.save()
        messages.success(request, f"Proposta {proposta.numero} aprovada!")
    else:
        messages.error(request, "Apenas propostas Enviadas podem ser aprovadas.")
    return redirect("servicos:detalhe", pk=pk)


@login_required
@require_POST
def cancelar_proposta(request, pk):
    proposta = get_object_or_404(PropostaServico, pk=pk)
    if proposta.status not in (PropostaServico.STATUS_CONCLUIDA, PropostaServico.STATUS_CANCELADA):
        proposta.status = PropostaServico.STATUS_CANCELADA
        proposta.save()
        messages.warning(request, f"Proposta {proposta.numero} cancelada.")
    else:
        messages.error(request, "Esta proposta não pode ser cancelada.")
    return redirect("servicos:detalhe", pk=pk)


@login_required
@require_POST
def reabrir_proposta(request, pk):
    proposta = get_object_or_404(PropostaServico, pk=pk)
    if proposta.status == PropostaServico.STATUS_CANCELADA:
        proposta.status = PropostaServico.STATUS_RASCUNHO
        proposta.save()
        messages.success(request, f"Proposta {proposta.numero} reaberta como Rascunho.")
    else:
        messages.error(request, "Apenas propostas canceladas podem ser reabertas.")
    return redirect("servicos:detalhe", pk=pk)


# ── API ───────────────────────────────────────────────────────────────────────


@login_required
def buscar_produtos(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    filtro = Q(descricao__icontains=q, ativo=True)
    if q.isdigit():
        filtro |= Q(codigo=int(q), ativo=True)
    qs = Produto.objects.filter(filtro).values("pk", "codigo", "descricao", "pscf")[:20]
    data = [{"pk": p["pk"], "codigo": p["codigo"], "descricao": p["descricao"], "pscf": float(p["pscf"])} for p in qs]
    return JsonResponse(data, safe=False)
