import json
import urllib.request

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ClienteForm
from .models import Cliente


class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "clientes/cliente_list.html"
    context_object_name = "clientes"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "")
        ativo = self.request.GET.get("ativo", "1")

        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(cpf_cnpj__icontains=q) | Q(email__icontains=q) | Q(cidade__icontains=q))
        if tipo in ("PF", "PJ"):
            qs = qs.filter(tipo=tipo)
        qs = qs.filter(ativo=(ativo != "0"))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo_filtro"] = self.request.GET.get("tipo", "")
        ctx["ativo_filtro"] = self.request.GET.get("ativo", "1")
        ctx["total_ativos"] = Cliente.objects.filter(ativo=True).count()
        ctx["total_inativos"] = Cliente.objects.filter(ativo=False).count()
        return ctx


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/cliente_form.html"

    def get_success_url(self):
        return reverse_lazy("clientes:detalhe", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Cliente «{form.instance.nome}» cadastrado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Cliente"
        ctx["acao"] = "Cadastrar"
        return ctx


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/cliente_form.html"

    def get_success_url(self):
        return reverse_lazy("clientes:detalhe", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Cliente «{form.instance.nome}» atualizado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome}"
        ctx["acao"] = "Salvar alterações"
        return ctx


class ClienteDetailView(LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = "clientes/cliente_detail.html"
    context_object_name = "cliente"


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Cliente
    template_name = "clientes/cliente_confirm_delete.html"
    success_url = reverse_lazy("clientes:lista")

    def form_valid(self, form):
        messages.success(self.request, f"Cliente «{self.object.nome}» removido com sucesso.")
        return super().form_valid(form)


@login_required
def buscar_cnpj(request):
    cnpj = re_digits(request.GET.get("cnpj", ""))
    if len(cnpj) != 14:
        return JsonResponse({"erro": "CNPJ inválido"}, status=400)
    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
        req = urllib.request.Request(url, headers={"User-Agent": "ERP-Optimus/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        return JsonResponse(
            {
                "razao_social": data.get("razao_social", ""),
                "nome_fantasia": data.get("nome_fantasia", ""),
                "telefone": re_digits(data.get("ddd_telefone_1", "")),
                "email": (data.get("email") or "").strip().lower(),
                "cep": re_digits(data.get("cep", "")),
                "logradouro": data.get("logradouro", ""),
                "numero": data.get("numero", ""),
                "complemento": data.get("complemento", ""),
                "bairro": data.get("bairro", ""),
                "cidade": data.get("municipio", ""),
                "estado": data.get("uf", ""),
            }
        )
    except Exception:
        return JsonResponse({"erro": "Falha ao consultar o CNPJ. Preencha os dados manualmente."}, status=503)


@login_required
def buscar_cep(request):
    cep = re_digits(request.GET.get("cep", ""))
    if len(cep) != 8:
        return JsonResponse({"erro": "CEP inválido"}, status=400)
    try:
        url = f"https://viacep.com.br/ws/{cep}/json/"
        req = urllib.request.Request(url, headers={"User-Agent": "ERP-Optimus/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
        if data.get("erro"):
            return JsonResponse({"erro": "CEP não encontrado"}, status=404)
        return JsonResponse(
            {
                "logradouro": data.get("logradouro", ""),
                "bairro": data.get("bairro", ""),
                "cidade": data.get("localidade", ""),
                "estado": data.get("uf", ""),
            }
        )
    except Exception:
        return JsonResponse({"erro": "Falha ao consultar o CEP. Preencha o endereço manualmente."}, status=503)


def re_digits(value: str) -> str:
    import re

    return re.sub(r"\D", "", value)
