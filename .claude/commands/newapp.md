Scaffolda um novo app Django para o Optimus ERP.

Nome do app: $ARGUMENTS

Execute os seguintes passos em ordem:

1. Criar o app:
   `python manage.py startapp $ARGUMENTS`

2. Criar o diretório de templates dentro do app:
   `$ARGUMENTS/templates/$ARGUMENTS/`

3. Criar `$ARGUMENTS/urls.py` com o conteúdo:
   ```python
   from django.urls import path

   app_name = "$ARGUMENTS"

   urlpatterns = []
   ```

4. Registrar em INSTALLED_APPS no `config/settings.py`:
   `"$ARGUMENTS",`

5. Incluir no `config/urls.py` principal:
   `path("$ARGUMENTS/", include("$ARGUMENTS.urls", namespace="$ARGUMENTS")),`

6. Criar `$ARGUMENTS/forms.py` com stub inicial:
   ```python
   from django import forms

   # from .models import NomeModel
   #
   # class NomeModelForm(forms.ModelForm):
   #     class Meta:
   #         model = NomeModel
   #         fields = "__all__"
   #         widgets = {
   #             "nome": forms.TextInput(attrs={"class": "form-control"}),
   #         }
   ```

7. Substituir o conteúdo de `$ARGUMENTS/admin.py` por:
   ```python
   from django.contrib import admin

   # from .models import NomeModel
   #
   # @admin.register(NomeModel)
   # class NomeModelAdmin(admin.ModelAdmin):
   #     list_display = ["__str__", "criado_em"]
   #     search_fields = ["nome"]
   #     list_filter = []
   ```

Convenções obrigatórias:
- Nomes de campos e verbose_name em português
- `__str__` definido em todo model
- CBVs (CreateView, UpdateView, DeleteView, ListView, DetailView) para CRUD
- Formulários Django — nunca HTML puro

Ao final, mostre um resumo dos arquivos criados/modificados e o próximo passo sugerido.
