"""Views de catálogo solar — CRUD de módulos, inversores, estruturas e materiais."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..forms import (
    EstruturaFixacaoForm,
    InversorForm,
    MateriaisEletricosForm,
    ModuloFotovoltaicoForm,
)
from ..models import (
    EstruturaFixacao,
    Inversor,
    MateriaisEletricos,
    ModuloFotovoltaico,
    PrecoEquipamentoSolar,
)


# ── Módulos Fotovoltaicos ─────────────────────────────────────────────────────


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


# ── Inversores ────────────────────────────────────────────────────────────────


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


# ── Estruturas de Fixação ─────────────────────────────────────────────────────


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


# ── Materiais Elétricos ───────────────────────────────────────────────────────


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
