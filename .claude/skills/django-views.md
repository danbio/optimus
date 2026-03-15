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

## HTMX — busca parcial sem reload

```python
# View retorna fragmento HTML quando requisição é HTMX
def buscar_cliente(request):
    q = request.GET.get("q", "")
    clientes = Cliente.objects.filter(nome__icontains=q)[:10]
    if request.htmx:
        return render(request, "clientes/_lista_parcial.html", {"clientes": clientes})
    return render(request, "clientes/buscar.html", {"clientes": clientes})
```

```html
<!-- Template com HTMX -->
<input type="text" name="q"
       hx-get="{% url 'clientes:buscar' %}"
       hx-target="#resultado"
       hx-trigger="keyup changed delay:300ms">
<div id="resultado"></div>
```
