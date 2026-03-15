Gera CRUD completo para um model dentro de um app Django existente no ERP Optimus.

Uso: /scaffold <app> <NomeModel>
Exemplo: /scaffold clientes Cliente

$ARGUMENTS contém: "<app> <NomeModel>" — extraia os dois valores.

Execute os seguintes passos em ordem:

---

### 1. Model (`<app>/models.py`)

Adicionar o model seguindo o padrão de `django-models` skill:
- `verbose_name` e `verbose_name_plural` em português
- `on_delete=models.PROTECT` em todas as FK
- Choices via `TextChoices`
- `auto_now_add` e `auto_now` para timestamps
- `__str__` obrigatório
- `class Meta` com `verbose_name`, `verbose_name_plural`, `ordering`

Perguntar ao usuário quais campos o model deve ter antes de gerar, se não foram especificados.

---

### 2. Formulário (`<app>/forms.py`)

Criar `<NomeModel>Form(forms.ModelForm)` usando o padrão obrigatório do projeto:

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    for field in self.fields.values():
        field.widget.attrs["class"] = "form-control"
        field.widget.attrs["autocomplete"] = "off"
    # Campos de data precisam de type explícito:
    # self.fields["data"].widget.attrs["type"] = "date"
    # self.fields["data_hora"].widget.attrs["type"] = "datetime-local"
```

Ver `django-forms` skill para todos os overrides especiais (data, decimal, placeholders, FK filter).

---

### 3. Views (`<app>/views.py`)

Criar 5 views CBV seguindo o padrão de `django-views` skill:
- `<NomeModel>ListView` — com `select_related`, `paginate_by=20`
- `<NomeModel>CreateView` — com `messages.success`
- `<NomeModel>UpdateView` — com `messages.success`
- `<NomeModel>DeleteView` — com `messages.success`
- `<NomeModel>DetailView`

Todas com `LoginRequiredMixin`.

---

### 4. URLs (`<app>/urls.py`)

Adicionar 5 padrões:
```python
path("", <NomeModel>ListView.as_view(), name="lista"),
path("novo/", <NomeModel>CreateView.as_view(), name="criar"),
path("<int:pk>/", <NomeModel>DetailView.as_view(), name="detalhe"),
path("<int:pk>/editar/", <NomeModel>UpdateView.as_view(), name="editar"),
path("<int:pk>/excluir/", <NomeModel>DeleteView.as_view(), name="excluir"),
```

---

### 5. Admin (`<app>/admin.py`)

Registrar com:
```python
@admin.register(<NomeModel>)
class <NomeModel>Admin(admin.ModelAdmin):
    list_display = ["__str__", "criado_em"]
    search_fields = ["nome"]
    list_filter = []
```

---

### 6. Templates (`<app>/templates/<app>/`)

Criar 4 arquivos usando os padrões de `bs5-components` skill:

- `<nomemodel>_list.html` — tabela responsiva com paginação, botão "Novo", ações por linha
- `<nomemodel>_form.html` — formulário com csrf_token, botões Salvar/Cancelar
- `<nomemodel>_detail.html` — card com campos em dl/dt/dd, botões Editar/Voltar
- `<nomemodel>_confirm_delete.html` — confirmação de exclusão com botões Confirmar/Cancelar

---

### 7. Finalização

Ao concluir:
- Mostrar resumo de todos os arquivos criados/modificados
- Lembrar: rode `/migrate` se o model é novo
- Lembrar: acesse `/admin` para verificar o registro no Django admin
