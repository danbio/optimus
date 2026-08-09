# Padrão: Views Django (CBV) — ERP Optimus

## Regras obrigatórias

- Preferir CBV para todo CRUD (ListView, CreateView, UpdateView, DeleteView, DetailView)
- `select_related` obrigatório em ListView quando há ForeignKey no template
- `messages.success` após criação/edição/exclusão
- `login_required` em todas as views (mixin ou decorator)
- `app_name` definido no `urls.py` de cada app
- `{% url 'app_name:nome_url' %}` — nunca URL hardcoded

---

## ListView padrão

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import NomeModel


class NomeModelListView(LoginRequiredMixin, ListView):
    model = NomeModel
    template_name = "nome_app/nomemodel_list.html"
    context_object_name = "itens"
    paginate_by = 20

    def get_queryset(self):
        return NomeModel.objects.select_related("cliente").order_by("-criado_em")
```

---

## CreateView padrão

```python
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView

from .forms import NomeModelForm
from .models import NomeModel


class NomeModelCreateView(LoginRequiredMixin, CreateView):
    model = NomeModel
    form_class = NomeModelForm
    template_name = "nome_app/nomemodel_form.html"
    success_url = reverse_lazy("nome_app:lista")

    def form_valid(self, form):
        messages.success(self.request, "Registro criado com sucesso.")
        return super().form_valid(form)
```

---

## UpdateView padrão

```python
from django.views.generic.edit import UpdateView

class NomeModelUpdateView(LoginRequiredMixin, UpdateView):
    model = NomeModel
    form_class = NomeModelForm
    template_name = "nome_app/nomemodel_form.html"
    success_url = reverse_lazy("nome_app:lista")

    def form_valid(self, form):
        messages.success(self.request, "Registro atualizado com sucesso.")
        return super().form_valid(form)
```

---

## urls.py padrão por app

```python
from django.urls import path

from . import views

app_name = "nome_app"

urlpatterns = [
    path("", views.NomeModelListView.as_view(), name="lista"),
    path("novo/", views.NomeModelCreateView.as_view(), name="criar"),
    path("<int:pk>/editar/", views.NomeModelUpdateView.as_view(), name="editar"),
    path("<int:pk>/", views.NomeModelDetailView.as_view(), name="detalhe"),
]
```

---

## Inclusão no urls.py principal (config/urls.py)

```python
from django.urls import include, path

urlpatterns = [
    path("nome-app/", include("nome_app.urls", namespace="nome_app")),
]
```

---

## FBV com ação de status — padrão do projeto

Transições de status (aprovar, cancelar, faturar) usam FBV com `@login_required` + `@require_POST`:

```python
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import MeuModel


@login_required
@require_POST
def aprovar(request: HttpRequest, pk: int) -> HttpResponse:
    obj = get_object_or_404(MeuModel, pk=pk)
    if obj.status == MeuModel.STATUS_ENVIADA:
        obj.status = MeuModel.STATUS_APROVADA
        obj.save()
        messages.success(request, f"{obj} aprovado.")
    else:
        messages.error(request, "Status inválido para esta ação.")
    return redirect("app:detalhe", pk=pk)
```

---

## HTMX — endpoint de fragmento HTML

`django-htmx` **não está instalado**. Não usar `request.htmx`. Os endpoints HTMX são FBVs simples que retornam `render()` diretamente:

```python
@login_required
def buscar_cliente(request: HttpRequest) -> HttpResponse:
    q = request.GET.get("q", "").strip()
    clientes = Cliente.objects.filter(nome__icontains=q, ativo=True)[:10] if q else []
    return render(request, "clientes/_busca_resultado.html", {"clientes": clientes})
```

```html
<input type="text" name="q"
       hx-get="{% url 'clientes:buscar' %}"
       hx-target="#resultado"
       hx-trigger="keyup changed delay:300ms">
<div id="resultado"></div>
```

---

## DeleteView padrão

```python
from django.views.generic import DeleteView

class NomeModelDeleteView(LoginRequiredMixin, DeleteView):
    model = NomeModel
    template_name = "nome_app/nomemodel_confirm_delete.html"
    success_url = reverse_lazy("nome_app:lista")

    def form_valid(self, form):
        messages.success(self.request, f"{self.object} removido.")
        return super().form_valid(form)
```

---

## Subpacote de views (apps com >300 linhas)

Quando `views.py` ultrapassar 300 linhas, quebrar em subpacote:

```
app/
└── views/
    ├── __init__.py   # re-exporta tudo: from .propostas import *
    ├── propostas.py
    └── acoes.py      # FBVs de transição de status
```

---

## Type hints — obrigatório (ROADMAP Fase 1)

```python
from django.http import HttpRequest, HttpResponse

def minha_view(request: HttpRequest, pk: int) -> HttpResponse:
    ...
```
