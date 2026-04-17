import math

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    EstruturaFixacaoForm,
    InversorForm,
    ItemPropostaSolarFormSet,  # Novo FormSet
    MateriaisEletricosForm,
    ModuloFotovoltaicoForm,
    PrecoEquipamentoSolarForm,
    PropostaSolarForm,
)
from .models import (
    EstruturaFixacao,
    Inversor,
    MateriaisEletricos,
    ModuloFotovoltaico,
    PrecoEquipamentoSolar,
    PropostaSolar,
)


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

        from datetime import date

        proposta = form.save(commit=False)
        proposta.potencia_kwp = _calcular_kwp(
            proposta.consumo_medio_kwh,
            proposta.hsp,
            proposta.fator_eficiencia,
        )

        # Deriva modulo e quantidade_modulos do formset antes de salvar
        formset.instance = proposta
        hoje = date.today()
        instances = formset.save(commit=False)

        modulo_item = next((item for item in instances if item.modulo), None)
        if modulo_item:
            proposta.modulo = modulo_item.modulo
            proposta.quantidade_modulos = sum(item.quantidade for item in instances if item.modulo)

        proposta.save()
        self.object = proposta

        # Trata exclusões do formset
        for obj in formset.deleted_objects:
            obj.delete()

        # Salva novos itens com snapshot de preço
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

        from datetime import date

        proposta = form.save(commit=False)
        proposta.potencia_kwp = _calcular_kwp(
            proposta.consumo_medio_kwh,
            proposta.hsp,
            proposta.fator_eficiencia,
        )

        # Deriva modulo e quantidade_modulos do formset antes de salvar
        formset.instance = proposta
        hoje = date.today()
        instances = formset.save(commit=False)

        modulo_item = next((item for item in instances if item.modulo), None)
        if modulo_item:
            proposta.modulo = modulo_item.modulo
            proposta.quantidade_modulos = sum(item.quantidade for item in instances if item.modulo)
        elif not proposta.modulo_id:
            # Proposta existente sem módulo no formset: manter valor anterior do banco
            proposta.modulo = PropostaSolar.objects.filter(pk=proposta.pk).values_list("modulo", flat=True).first()

        proposta.save()
        self.object = proposta

        # Trata exclusões
        for obj in formset.deleted_objects:
            obj.delete()

        # Atualiza/Cria itens com snapshot de preço
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


@login_required
def dimensionar(request):
    """Endpoint HTMX — retorna preview do dimensionamento em tempo real e sugere kit automático."""
    import math

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


@login_required
def adicionar_item_solar(request: HttpRequest) -> HttpResponse:
    """Endpoint HTMX para adicionar uma linha vazia ao formset."""
    from .forms import ItemPropostaSolarForm

    index = request.GET.get("index", "0")
    form = ItemPropostaSolarForm(
        prefix=f"itens-{index}",
    )
    return render(
        request,
        "solar/_item_proposta_row.html",
        {
            "item_form": form,
            "index": index,
        },
    )


# ── helpers ───────────────────────────────────────────────────────────────────


def _calcular_kwp(consumo_kwh, hsp, fator):
    try:
        return round(float(consumo_kwh) / (float(hsp) * 30 * float(fator)), 3)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@login_required
def calcular_total_equipamentos(request):
    """Endpoint HTMX — recebe itens do formset via GET e retorna o total de equipamentos."""
    from datetime import date
    from decimal import Decimal

    hoje = date.today()
    total = Decimal("0")

    # Lê quantas linhas o formset tem
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


# ---------------------------------------------------------------------------
# Catálogo — Módulos Fotovoltaicos
# ---------------------------------------------------------------------------


class ModuloListView(LoginRequiredMixin, ListView):
    model = ModuloFotovoltaico
    template_name = "solar/modulo_list.html"
    context_object_name = "modulos"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(fabricante__icontains=q) | Q(modelo__icontains=q))
        ativo = self.request.GET.get("ativo", "1")
        if ativo == "0":
            qs = qs.filter(ativo=False)
        else:
            qs = qs.filter(ativo=True)
        return qs

    def get_context_data(self, **kwargs):
        from datetime import date

        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["ativo_filtro"] = self.request.GET.get("ativo", "1")
        hoje = date.today()
        ctx["modulos_precos"] = [(m, PrecoEquipamentoSolar.get_preco_vigente(m, hoje)) for m in ctx["modulos"]]
        return ctx


class ModuloCreateView(LoginRequiredMixin, CreateView):
    model = ModuloFotovoltaico
    form_class = ModuloFotovoltaicoForm
    template_name = "solar/modulo_form.html"
    success_url = reverse_lazy("solar:modulos")

    def form_valid(self, form):
        messages.success(self.request, f"Módulo «{form.instance}» cadastrado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Módulo Fotovoltaico"
        ctx["acao"] = "Cadastrar módulo"
        return ctx


class ModuloUpdateView(LoginRequiredMixin, UpdateView):
    model = ModuloFotovoltaico
    form_class = ModuloFotovoltaicoForm
    template_name = "solar/modulo_form.html"
    success_url = reverse_lazy("solar:modulos")

    def form_valid(self, form):
        messages.success(self.request, f"Módulo «{form.instance}» atualizado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object}"
        ctx["acao"] = "Salvar alterações"
        return ctx


class ModuloDeleteView(LoginRequiredMixin, DeleteView):
    model = ModuloFotovoltaico
    template_name = "solar/equipamento_confirm_delete.html"
    success_url = reverse_lazy("solar:modulos")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo"] = "módulo fotovoltaico"
        ctx["voltar_url"] = reverse_lazy("solar:modulos")
        return ctx

    def form_valid(self, form):
        from django.db.models import ProtectedError

        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Não é possível excluir: este módulo possui preços ou itens de proposta vinculados.")
            return redirect("solar:modulos")


# ---------------------------------------------------------------------------
# Catálogo — Inversores
# ---------------------------------------------------------------------------


class InversorListView(LoginRequiredMixin, ListView):
    model = Inversor
    template_name = "solar/inversor_list.html"
    context_object_name = "inversores"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(fabricante__icontains=q) | Q(modelo__icontains=q))
        tipo = self.request.GET.get("tipo", "")
        if tipo:
            qs = qs.filter(tipo=tipo)
        ativo = self.request.GET.get("ativo", "1")
        if ativo == "0":
            qs = qs.filter(ativo=False)
        else:
            qs = qs.filter(ativo=True)
        return qs

    def get_context_data(self, **kwargs):
        from datetime import date

        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo_filtro"] = self.request.GET.get("tipo", "")
        ctx["ativo_filtro"] = self.request.GET.get("ativo", "1")
        ctx["tipo_choices"] = Inversor.TIPO_CHOICES
        hoje = date.today()
        ctx["inversores_precos"] = [(i, PrecoEquipamentoSolar.get_preco_vigente(i, hoje)) for i in ctx["inversores"]]
        return ctx


class InversorCreateView(LoginRequiredMixin, CreateView):
    model = Inversor
    form_class = InversorForm
    template_name = "solar/inversor_form.html"
    success_url = reverse_lazy("solar:inversores")

    def form_valid(self, form):
        messages.success(self.request, f"Inversor «{form.instance}» cadastrado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Inversor"
        ctx["acao"] = "Cadastrar inversor"
        return ctx


class InversorUpdateView(LoginRequiredMixin, UpdateView):
    model = Inversor
    form_class = InversorForm
    template_name = "solar/inversor_form.html"
    success_url = reverse_lazy("solar:inversores")

    def form_valid(self, form):
        messages.success(self.request, f"Inversor «{form.instance}» atualizado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object}"
        ctx["acao"] = "Salvar alterações"
        return ctx


class InversorDeleteView(LoginRequiredMixin, DeleteView):
    model = Inversor
    template_name = "solar/equipamento_confirm_delete.html"
    success_url = reverse_lazy("solar:inversores")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo"] = "inversor"
        ctx["voltar_url"] = reverse_lazy("solar:inversores")
        return ctx

    def form_valid(self, form):
        from django.db.models import ProtectedError

        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Não é possível excluir: este inversor possui preços ou itens de proposta vinculados.")
            return redirect("solar:inversores")


# ---------------------------------------------------------------------------
# Catálogo — Estruturas de Fixação
# ---------------------------------------------------------------------------


class EstruturaListView(LoginRequiredMixin, ListView):
    model = EstruturaFixacao
    template_name = "solar/estrutura_list.html"
    context_object_name = "estruturas"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(fabricante__icontains=q) | Q(modelo__icontains=q))
        tipo = self.request.GET.get("tipo", "")
        if tipo:
            qs = qs.filter(tipo=tipo)
        ativo = self.request.GET.get("ativo", "1")
        if ativo == "0":
            qs = qs.filter(ativo=False)
        else:
            qs = qs.filter(ativo=True)
        return qs

    def get_context_data(self, **kwargs):
        from datetime import date

        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo_filtro"] = self.request.GET.get("tipo", "")
        ctx["ativo_filtro"] = self.request.GET.get("ativo", "1")
        ctx["tipo_choices"] = EstruturaFixacao.TIPO_CHOICES
        hoje = date.today()
        ctx["estruturas_precos"] = [(e, PrecoEquipamentoSolar.get_preco_vigente(e, hoje)) for e in ctx["estruturas"]]
        return ctx


class EstruturaCreateView(LoginRequiredMixin, CreateView):
    model = EstruturaFixacao
    form_class = EstruturaFixacaoForm
    template_name = "solar/estrutura_form.html"
    success_url = reverse_lazy("solar:estruturas")

    def form_valid(self, form):
        messages.success(self.request, f"Estrutura «{form.instance}» cadastrada com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova Estrutura de Fixação"
        ctx["acao"] = "Cadastrar estrutura"
        return ctx


class EstruturaUpdateView(LoginRequiredMixin, UpdateView):
    model = EstruturaFixacao
    form_class = EstruturaFixacaoForm
    template_name = "solar/estrutura_form.html"
    success_url = reverse_lazy("solar:estruturas")

    def form_valid(self, form):
        messages.success(self.request, f"Estrutura «{form.instance}» atualizada com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object}"
        ctx["acao"] = "Salvar alterações"
        return ctx


class EstruturaDeleteView(LoginRequiredMixin, DeleteView):
    model = EstruturaFixacao
    template_name = "solar/equipamento_confirm_delete.html"
    success_url = reverse_lazy("solar:estruturas")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo"] = "estrutura de fixação"
        ctx["voltar_url"] = reverse_lazy("solar:estruturas")
        return ctx

    def form_valid(self, form):
        from django.db.models import ProtectedError

        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Não é possível excluir: esta estrutura possui preços ou itens de proposta vinculados.")
            return redirect("solar:estruturas")


# ---------------------------------------------------------------------------
# Catálogo — Materiais Elétricos
# ---------------------------------------------------------------------------


class MateriaisListView(LoginRequiredMixin, ListView):
    model = MateriaisEletricos
    template_name = "solar/material_list.html"
    context_object_name = "materiais"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(fabricante__icontains=q) | Q(modelo__icontains=q) | Q(descricao__icontains=q))
        categoria = self.request.GET.get("categoria", "")
        if categoria:
            qs = qs.filter(categoria=categoria)
        ativo = self.request.GET.get("ativo", "1")
        if ativo == "0":
            qs = qs.filter(ativo=False)
        else:
            qs = qs.filter(ativo=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["categoria_filtro"] = self.request.GET.get("categoria", "")
        ctx["ativo_filtro"] = self.request.GET.get("ativo", "1")
        ctx["categoria_choices"] = MateriaisEletricos.CATEGORIA_CHOICES
        from datetime import date

        hoje = date.today()
        ctx["materiais_precos"] = [(m, PrecoEquipamentoSolar.get_preco_vigente(m, hoje)) for m in ctx["materiais"]]
        return ctx


class MateriaisCreateView(LoginRequiredMixin, CreateView):
    model = MateriaisEletricos
    form_class = MateriaisEletricosForm
    template_name = "solar/material_form.html"
    success_url = reverse_lazy("solar:materiais")

    def form_valid(self, form):
        messages.success(self.request, f"Material «{form.instance}» cadastrado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Material Elétrico"
        ctx["acao"] = "Cadastrar material"
        return ctx


class MateriaisUpdateView(LoginRequiredMixin, UpdateView):
    model = MateriaisEletricos
    form_class = MateriaisEletricosForm
    template_name = "solar/material_form.html"
    success_url = reverse_lazy("solar:materiais")

    def form_valid(self, form):
        messages.success(self.request, f"Material «{form.instance}» atualizado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object}"
        ctx["acao"] = "Salvar alterações"
        return ctx


class MateriaisDeleteView(LoginRequiredMixin, DeleteView):
    model = MateriaisEletricos
    template_name = "solar/equipamento_confirm_delete.html"
    success_url = reverse_lazy("solar:materiais")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo"] = "material elétrico"
        ctx["voltar_url"] = reverse_lazy("solar:materiais")
        return ctx

    def form_valid(self, form):
        from django.db.models import ProtectedError

        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Não é possível excluir: este material possui preços vinculados.")
            return redirect("solar:materiais")


# ---------------------------------------------------------------------------
# Gerenciamento de preços por equipamento
# ---------------------------------------------------------------------------


def _gerenciar_preco(request, equipamento, lista_url, tipo_label):
    """View genérica de histórico + cadastro de novo preço para um equipamento."""
    from datetime import date

    historico = PrecoEquipamentoSolar.objects.filter(**{_campo_fk(equipamento): equipamento}).order_by("-vigente_desde")

    preco_vigente = PrecoEquipamentoSolar.get_preco_vigente(equipamento, date.today())

    if request.method == "POST":
        form = PrecoEquipamentoSolarForm(request.POST)
        if form.is_valid():
            novo = form.save(commit=False)
            # Fecha o preço vigente anterior
            PrecoEquipamentoSolar.objects.filter(
                vigente_ate__isnull=True,
                **{_campo_fk(equipamento): equipamento},
            ).update(vigente_ate=date.today())
            # Associa ao equipamento correto
            setattr(novo, _campo_fk(equipamento), equipamento)
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


def _campo_fk(equipamento):
    if isinstance(equipamento, ModuloFotovoltaico):
        return "modulo"
    if isinstance(equipamento, Inversor):
        return "inversor"
    if isinstance(equipamento, EstruturaFixacao):
        return "estrutura"
    return "material"


@login_required
def modulo_precos(request, pk):
    equipamento = get_object_or_404(ModuloFotovoltaico, pk=pk)
    return _gerenciar_preco(request, equipamento, reverse_lazy("solar:modulos"), "Módulo Fotovoltaico")


@login_required
def inversor_precos(request, pk):
    equipamento = get_object_or_404(Inversor, pk=pk)
    return _gerenciar_preco(request, equipamento, reverse_lazy("solar:inversores"), "Inversor")


@login_required
def estrutura_precos(request, pk):
    equipamento = get_object_or_404(EstruturaFixacao, pk=pk)
    return _gerenciar_preco(request, equipamento, reverse_lazy("solar:estruturas"), "Estrutura de Fixação")


@login_required
def material_precos(request, pk):
    equipamento = get_object_or_404(MateriaisEletricos, pk=pk)
    return _gerenciar_preco(request, equipamento, reverse_lazy("solar:materiais"), "Material Elétrico")
