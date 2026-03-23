
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .forms import ItemVendaForm, VendaHeaderForm
from .models import ItemVenda, Venda


class VendaListView(LoginRequiredMixin, ListView):
    model = Venda
    template_name = "balcao/venda_list.html"
    context_object_name = "vendas"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente", "operador")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        data_de = self.request.GET.get("data_de", "")
        data_ate = self.request.GET.get("data_ate", "")

        if q:
            qs = qs.filter(Q(numero__icontains=q) | Q(cliente__nome__icontains=q) | Q(cliente_nome_avulso__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if data_de:
            qs = qs.filter(criado_em__date__gte=data_de)
        if data_ate:
            qs = qs.filter(criado_em__date__lte=data_ate)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()

        ctx["total_hoje"] = Venda.objects.filter(status=Venda.STATUS_FINALIZADA, criado_em__date=today).aggregate(s=Sum("total"))["s"] or 0

        ctx["total_mes"] = (
            Venda.objects.filter(
                status=Venda.STATUS_FINALIZADA,
                criado_em__date__gte=today.replace(day=1),
            ).aggregate(s=Sum("total"))["s"]
            or 0
        )

        ctx["rascunhos"] = Venda.objects.filter(status=Venda.STATUS_RASCUNHO).count()

        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_filtro"] = self.request.GET.get("status", "")
        ctx["data_de"] = self.request.GET.get("data_de", "")
        ctx["data_ate"] = self.request.GET.get("data_ate", "")
        ctx["status_choices"] = Venda.STATUS_CHOICES
        return ctx


@login_required
def nova_venda(request):
    """Cria uma venda em rascunho e redireciona para edição."""
    venda = Venda.objects.create()
    return redirect("balcao:editar", pk=venda.pk)


class VendaDetailView(LoginRequiredMixin, DetailView):
    model = Venda
    template_name = "balcao/venda_detail.html"
    context_object_name = "venda"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente", "operador").prefetch_related("itens__produto", "lancamentos")


@login_required
def editar_venda(request, pk):
    """Tela principal do carrinho — montagem e finalização."""
    venda = get_object_or_404(Venda, pk=pk)

    if venda.status != Venda.STATUS_RASCUNHO:
        return redirect("balcao:detalhe", pk=pk)

    if request.method == "POST":
        form = VendaHeaderForm(request.POST, instance=venda)
        if form.is_valid():
            form.save()
            venda.refresh_from_db()
            venda.recalcular_totais()
            messages.success(request, "Venda atualizada.")
        return redirect("balcao:editar", pk=pk)

    form = VendaHeaderForm(instance=venda)
    item_form = ItemVendaForm()
    return render(
        request,
        "balcao/venda_edit.html",
        {
            "venda": venda,
            "form": form,
            "item_form": item_form,
            "itens": venda.itens.select_related("produto").all(),
        },
    )


@login_required
@require_POST
def adicionar_item(request, pk):
    """Adiciona item à venda (POST, retorna partials HTMX)."""
    venda = get_object_or_404(Venda, pk=pk, status=Venda.STATUS_RASCUNHO)
    form = ItemVendaForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.venda = venda
        item.save()
        venda.recalcular_totais()
    itens = venda.itens.select_related("produto").all()
    venda.refresh_from_db()
    return render(request, "balcao/_carrinho.html", {"venda": venda, "itens": itens})


@login_required
@require_POST
def remover_item(request, pk, item_pk):
    """Remove item da venda (POST, retorna partials HTMX)."""
    venda = get_object_or_404(Venda, pk=pk, status=Venda.STATUS_RASCUNHO)
    item = get_object_or_404(ItemVenda, pk=item_pk, venda=venda)
    item.delete()
    venda.recalcular_totais()
    itens = venda.itens.select_related("produto").all()
    venda.refresh_from_db()
    return render(request, "balcao/_carrinho.html", {"venda": venda, "itens": itens})


@login_required
def buscar_produto(request):
    """Busca de produto para o carrinho (HTMX GET)."""
    q = request.GET.get("q", "").strip()
    from estoque.models import Produto

    if len(q) < 2:
        return HttpResponse("")

    filtro = Q(descricao__icontains=q, ativo=True)
    if q.replace(".", "").isdigit():
        filtro |= Q(codigo__icontains=q, ativo=True)

    produtos = Produto.objects.filter(filtro).values("pk", "codigo", "descricao", "pscf")[:15]
    return render(request, "balcao/_produto_resultados.html", {"produtos": produtos})


@login_required
def buscar_cliente(request):
    """Busca de cliente para o carrinho (HTMX GET)."""
    q = request.GET.get("q", "").strip()
    from clientes.models import Cliente

    if len(q) < 2:
        return HttpResponse("")

    clientes = Cliente.objects.filter(Q(nome__icontains=q) | Q(cpf_cnpj__icontains=q), ativo=True).values("pk", "nome", "cpf_cnpj")[:10]
    return render(request, "balcao/_cliente_resultados.html", {"clientes": clientes})


@login_required
@require_POST
def finalizar_venda(request, pk):
    """Finaliza a venda: valida, baixa estoque, gera lançamento financeiro."""
    venda = get_object_or_404(Venda, pk=pk, status=Venda.STATUS_RASCUNHO)

    if not venda.itens.exists():
        messages.error(request, "Adicione pelo menos um produto antes de finalizar.")
        return redirect("balcao:editar", pk=pk)

    if not venda.forma_pagamento:
        messages.error(request, "Selecione a forma de pagamento antes de finalizar.")
        return redirect("balcao:editar", pk=pk)

    with transaction.atomic():
        venda.recalcular_totais()
        venda.status = Venda.STATUS_FINALIZADA
        venda.operador = request.user
        venda.save()

        # Baixar estoque

        for item in venda.itens.select_related("produto").all():
            produto = item.produto
            if hasattr(produto, "quantidade_estoque"):
                produto.quantidade_estoque = max((produto.quantidade_estoque or 0) - float(item.quantidade), 0)
                produto.save(update_fields=["quantidade_estoque"])

        # Gerar lançamento financeiro
        from financeiro.services import criar_lancamento_de_venda_balcao

        criar_lancamento_de_venda_balcao(venda)

    messages.success(request, f"Venda {venda.numero} finalizada com sucesso!")
    return redirect("balcao:detalhe", pk=pk)


@login_required
@require_POST
def cancelar_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    if venda.status == Venda.STATUS_RASCUNHO:
        venda.status = Venda.STATUS_CANCELADA
        venda.save()
        messages.warning(request, f"Venda {venda.numero} cancelada.")
        return redirect("balcao:lista")
    messages.error(request, "Apenas rascunhos podem ser cancelados.")
    return redirect("balcao:detalhe", pk=pk)
