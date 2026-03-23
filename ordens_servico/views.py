from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    AssinaturaForm,
    FotoOSForm,
    ItemChecklistFormSet,
    OrdemServicoForm,
    TecnicoForm,
)
from .models import ChecklistTemplate, FotoOS, OrdemServico, Tecnico

# ── Técnicos ──────────────────────────────────────────────────────────────────


class TecnicoListView(LoginRequiredMixin, ListView):
    model = Tecnico
    template_name = "ordens_servico/tecnico_list.html"
    context_object_name = "tecnicos"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        especialidade = self.request.GET.get("especialidade", "")
        ativo = self.request.GET.get("ativo", "")

        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(email__icontains=q))
        if especialidade:
            qs = qs.filter(especialidade=especialidade)
        if ativo == "1":
            qs = qs.filter(ativo=True)
        elif ativo == "0":
            qs = qs.filter(ativo=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["especialidade_filtro"] = self.request.GET.get("especialidade", "")
        ctx["ativo_filtro"] = self.request.GET.get("ativo", "")
        ctx["especialidade_choices"] = Tecnico.ESPECIALIDADE_CHOICES
        return ctx


class TecnicoCreateView(LoginRequiredMixin, CreateView):
    model = Tecnico
    form_class = TecnicoForm
    template_name = "ordens_servico/tecnico_form.html"
    success_url = reverse_lazy("ordens_servico:tecnicos")

    def form_valid(self, form):
        messages.success(self.request, f"Técnico '{form.instance.nome}' cadastrado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Técnico"
        ctx["acao"] = "Cadastrar técnico"
        return ctx


class TecnicoUpdateView(LoginRequiredMixin, UpdateView):
    model = Tecnico
    form_class = TecnicoForm
    template_name = "ordens_servico/tecnico_form.html"
    success_url = reverse_lazy("ordens_servico:tecnicos")

    def form_valid(self, form):
        messages.success(self.request, f"Técnico '{form.instance.nome}' atualizado.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome}"
        ctx["acao"] = "Salvar alterações"
        return ctx


class TecnicoDeleteView(LoginRequiredMixin, DeleteView):
    model = Tecnico
    template_name = "ordens_servico/tecnico_confirm_delete.html"
    success_url = reverse_lazy("ordens_servico:tecnicos")

    def form_valid(self, form):
        messages.success(self.request, f"Técnico '{self.object.nome}' removido.")
        return super().form_valid(form)


# ── Ordens de Serviço ────────────────────────────────────────────────────────


class OrdemServicoListView(LoginRequiredMixin, ListView):
    model = OrdemServico
    template_name = "ordens_servico/os_list.html"
    context_object_name = "ordens"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente", "tecnico")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        prioridade = self.request.GET.get("prioridade", "")
        tecnico = self.request.GET.get("tecnico", "")

        if q:
            qs = qs.filter(Q(numero__icontains=q) | Q(cliente__nome__icontains=q) | Q(cliente__cpf_cnpj__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if prioridade:
            qs = qs.filter(prioridade=prioridade)
        if tecnico:
            qs = qs.filter(tecnico_id=tecnico)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_filtro"] = self.request.GET.get("status", "")
        ctx["prioridade_filtro"] = self.request.GET.get("prioridade", "")
        ctx["tecnico_filtro"] = self.request.GET.get("tecnico", "")
        ctx["status_choices"] = OrdemServico.STATUS_CHOICES
        ctx["prioridade_choices"] = OrdemServico.PRIORIDADE_CHOICES
        ctx["tecnicos"] = Tecnico.objects.filter(ativo=True)
        return ctx


class OrdemServicoCreateView(LoginRequiredMixin, CreateView):
    model = OrdemServico
    form_class = OrdemServicoForm
    template_name = "ordens_servico/os_form.html"

    def get_success_url(self):
        return reverse("ordens_servico:detalhe", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill quando vem de uma proposta
        proposta_solar_pk = self.request.GET.get("proposta_solar")
        proposta_servico_pk = self.request.GET.get("proposta_servico")
        if proposta_solar_pk:
            from solar.models import PropostaSolar

            try:
                p = PropostaSolar.objects.select_related("modulo", "cliente").get(pk=proposta_solar_pk, status="aprovada")
                initial["proposta_solar"] = p.pk
                initial["cliente"] = p.cliente_id
                initial["descricao"] = (
                    f"Instalação Solar: {p.numero} — {p.potencia_real_kwp}kWp, {p.quantidade_modulos}x {p.modulo.fabricante} {p.modulo.modelo}"
                )
            except PropostaSolar.DoesNotExist:
                pass
        elif proposta_servico_pk:
            from servicos.models import PropostaServico

            try:
                p = PropostaServico.objects.prefetch_related("itens_servico__servico").get(pk=proposta_servico_pk, status="aprovada")
                initial["proposta_servico"] = p.pk
                initial["cliente"] = p.cliente_id
                nomes = [i.servico.nome for i in p.itens_servico.all()]
                tipo = p.get_tipo_servico_display()
                if nomes:
                    initial["descricao"] = f"Serviço ({tipo}): {', '.join(nomes)}"
                else:
                    initial["descricao"] = f"Serviço ({tipo}): {p.numero}"
            except PropostaServico.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset_checklist"] = ItemChecklistFormSet(self.request.POST, prefix="chk")
        else:
            ctx["formset_checklist"] = ItemChecklistFormSet(prefix="chk")
        ctx["titulo"] = "Nova Ordem de Serviço"
        ctx["acao"] = "Criar OS"
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset_checklist = ctx["formset_checklist"]

        if formset_checklist.is_valid():
            os_obj = form.save()
            self.object = os_obj

            # Carregar itens do checklist template se nenhum item manual foi adicionado
            itens_manuais = [f for f in formset_checklist if f.cleaned_data and f.cleaned_data.get("descricao") and not f.cleaned_data.get("DELETE")]
            if not itens_manuais:
                self._carregar_checklist_templates(os_obj)

            formset_checklist.instance = os_obj
            formset_checklist.save()
            messages.success(self.request, f"OS {os_obj.numero} criada com sucesso.")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def _carregar_checklist_templates(self, os_obj):
        """Carrega itens do ChecklistTemplate baseado na origem da OS."""
        tipos = ["geral"]
        if os_obj.proposta_solar_id:
            tipos.append("solar")
        elif os_obj.proposta_servico_id:
            from servicos.models import PropostaServico

            try:
                prop = PropostaServico.objects.get(pk=os_obj.proposta_servico_id)
                tipos.append(prop.tipo_servico)
            except PropostaServico.DoesNotExist:
                pass

        templates = ChecklistTemplate.objects.filter(tipo__in=tipos, ativo=True)
        from .models import ItemChecklist

        for tmpl in templates:
            ItemChecklist.objects.create(
                ordem_servico=os_obj,
                descricao=tmpl.descricao,
                ordem=tmpl.ordem,
            )


class OrdemServicoUpdateView(LoginRequiredMixin, UpdateView):
    model = OrdemServico
    form_class = OrdemServicoForm
    template_name = "ordens_servico/os_form.html"

    def get_success_url(self):
        return reverse("ordens_servico:detalhe", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset_checklist"] = ItemChecklistFormSet(self.request.POST, instance=self.object, prefix="chk")
        else:
            ctx["formset_checklist"] = ItemChecklistFormSet(instance=self.object, prefix="chk")
        ctx["titulo"] = f"Editar — {self.object.numero}"
        ctx["acao"] = "Salvar alterações"
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset_checklist = ctx["formset_checklist"]

        if formset_checklist.is_valid():
            os_obj = form.save()
            self.object = os_obj
            formset_checklist.instance = os_obj
            formset_checklist.save()
            messages.success(self.request, f"OS {os_obj.numero} atualizada.")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class OrdemServicoDetailView(LoginRequiredMixin, DetailView):
    model = OrdemServico
    template_name = "ordens_servico/os_detail.html"
    context_object_name = "os_obj"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente", "tecnico", "proposta_solar", "proposta_servico").prefetch_related("itens_checklist", "fotos")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["foto_form"] = FotoOSForm()
        ctx["assinatura_form"] = AssinaturaForm()
        return ctx


class OrdemServicoDeleteView(LoginRequiredMixin, DeleteView):
    model = OrdemServico
    template_name = "ordens_servico/os_confirm_delete.html"
    success_url = reverse_lazy("ordens_servico:lista")

    def get_queryset(self):
        # Só permite excluir OS com status "aberta"
        return super().get_queryset().filter(status=OrdemServico.STATUS_ABERTA)

    def form_valid(self, form):
        messages.success(self.request, f"OS {self.object.numero} removida.")
        return super().form_valid(form)


# ── Transições de Estado ─────────────────────────────────────────────────────


@login_required
@require_POST
def agendar_os(request, pk):
    os_obj = get_object_or_404(OrdemServico, pk=pk)
    if os_obj.status == OrdemServico.STATUS_ABERTA:
        data = request.POST.get("data_agendamento")
        if data:
            os_obj.data_agendamento = data
            os_obj.status = OrdemServico.STATUS_AGENDADA
            os_obj.save()
            messages.success(request, f"OS {os_obj.numero} agendada com sucesso.")
        else:
            messages.error(request, "Informe a data de agendamento.")
    return redirect("ordens_servico:detalhe", pk=pk)


@login_required
@require_POST
def iniciar_os(request, pk):
    os_obj = get_object_or_404(OrdemServico, pk=pk)
    if os_obj.status == OrdemServico.STATUS_AGENDADA:
        os_obj.status = OrdemServico.STATUS_EM_EXECUCAO
        os_obj.data_inicio_execucao = timezone.now()
        os_obj.save()
        messages.success(request, f"OS {os_obj.numero} em execução.")
    return redirect("ordens_servico:detalhe", pk=pk)


@login_required
@require_POST
def concluir_os(request, pk):
    os_obj = get_object_or_404(OrdemServico, pk=pk)
    if os_obj.status == OrdemServico.STATUS_EM_EXECUCAO:
        form = AssinaturaForm(request.POST)
        if form.is_valid():
            # Verificar se todos os itens do checklist estão concluídos
            pendentes = os_obj.itens_checklist.filter(concluido=False).count()
            if pendentes > 0:
                messages.error(
                    request,
                    f"Existem {pendentes} item(ns) pendente(s) no checklist. Conclua todos antes de finalizar a OS.",
                )
                return redirect("ordens_servico:detalhe", pk=pk)

            os_obj.status = OrdemServico.STATUS_CONCLUIDA
            os_obj.data_conclusao = timezone.now()
            os_obj.assinatura_nome = form.cleaned_data["assinatura_nome"]
            os_obj.assinatura_confirmada = True
            os_obj.assinatura_data = timezone.now()
            os_obj.save()

            # Atualizar proposta vinculada para "concluída"
            if os_obj.proposta_solar:
                os_obj.proposta_solar.status = "concluida"
                os_obj.proposta_solar.save()
            elif os_obj.proposta_servico:
                os_obj.proposta_servico.status = "concluida"
                os_obj.proposta_servico.save()

            messages.success(request, f"OS {os_obj.numero} concluída com sucesso.")
        else:
            messages.error(request, "Preencha o nome e confirme a assinatura para concluir.")
    return redirect("ordens_servico:detalhe", pk=pk)


@login_required
@require_POST
def faturar_os(request, pk):
    os_obj = get_object_or_404(OrdemServico, pk=pk)
    if os_obj.status == OrdemServico.STATUS_CONCLUIDA:
        os_obj.status = OrdemServico.STATUS_FATURADA
        os_obj.save()
        from financeiro.services import criar_lancamento_de_ordem_servico

        criar_lancamento_de_ordem_servico(os_obj)
        messages.success(request, f"OS {os_obj.numero} faturada! Lançamento financeiro gerado.")
    else:
        messages.error(request, "Apenas OS concluídas podem ser faturadas.")
    return redirect("ordens_servico:detalhe", pk=pk)


@login_required
@require_POST
def suspender_os(request, pk):
    os_obj = get_object_or_404(OrdemServico, pk=pk)
    if os_obj.status == OrdemServico.STATUS_EM_EXECUCAO:
        motivo = request.POST.get("motivo", "").strip()
        os_obj.status = OrdemServico.STATUS_SUSPENSA
        if motivo:
            os_obj.observacoes = f"{os_obj.observacoes}\n[Suspensa] {motivo}".strip()
        os_obj.save()
        messages.warning(request, f"OS {os_obj.numero} suspensa.")
    return redirect("ordens_servico:detalhe", pk=pk)


@login_required
@require_POST
def reagendar_os(request, pk):
    os_obj = get_object_or_404(OrdemServico, pk=pk)
    if os_obj.status in (OrdemServico.STATUS_AGENDADA, OrdemServico.STATUS_SUSPENSA):
        data = request.POST.get("data_agendamento")
        if data:
            os_obj.data_agendamento = data
            os_obj.status = OrdemServico.STATUS_AGENDADA
            os_obj.save()
            messages.success(request, f"OS {os_obj.numero} reagendada.")
        else:
            messages.error(request, "Informe a nova data de agendamento.")
    return redirect("ordens_servico:detalhe", pk=pk)


# ── Fotos ────────────────────────────────────────────────────────────────────


@login_required
@require_POST
def adicionar_foto(request, pk):
    os_obj = get_object_or_404(OrdemServico, pk=pk)
    form = FotoOSForm(request.POST, request.FILES)
    if form.is_valid():
        foto = form.save(commit=False)
        foto.ordem_servico = os_obj
        foto.save()
        messages.success(request, "Foto adicionada com sucesso.")
    else:
        messages.error(request, "Erro ao enviar foto. Verifique o arquivo.")
    return redirect("ordens_servico:detalhe", pk=pk)


@login_required
@require_POST
def remover_foto(request, pk, foto_pk):
    os_obj = get_object_or_404(OrdemServico, pk=pk)
    foto = get_object_or_404(FotoOS, pk=foto_pk, ordem_servico=os_obj)
    foto.foto.delete(save=False)
    foto.delete()
    messages.success(request, "Foto removida.")
    return redirect("ordens_servico:detalhe", pk=pk)


# ── HTMX ─────────────────────────────────────────────────────────────────────


@login_required
@require_POST
def toggle_checklist_item(request, pk, item_pk):
    """Alterna o estado concluído de um item do checklist (usado via HTMX)."""
    from .models import ItemChecklist

    os_obj = get_object_or_404(OrdemServico, pk=pk)
    item = get_object_or_404(ItemChecklist, pk=item_pk, ordem_servico=os_obj)
    if os_obj.status not in (OrdemServico.STATUS_CONCLUIDA, OrdemServico.STATUS_FATURADA):
        item.concluido = not item.concluido
        item.save()
    return render(request, "ordens_servico/_checklist_item_row.html", {"item": item, "os_obj": os_obj})


@login_required
def carregar_checklist_template(request):
    """Retorna itens do checklist template como JSON baseado no tipo."""
    tipo = request.GET.get("tipo", "")
    tipos = ["geral"]
    if tipo:
        tipos.append(tipo)

    templates = ChecklistTemplate.objects.filter(tipo__in=tipos, ativo=True).values("descricao", "ordem")
    data = [{"descricao": t["descricao"], "ordem": t["ordem"]} for t in templates]
    return JsonResponse(data, safe=False)
