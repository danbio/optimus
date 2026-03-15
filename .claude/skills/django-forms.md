# Padrão: Formulários Django (ModelForm) — ERP Optimus

## Regras obrigatórias

- Sempre usar `ModelForm` — nunca `Form` puro para dados de model
- Aplicar `form-control` via `__init__` (padrão do projeto) — nunca via dict `widgets` por campo
- Campos de data/hora precisam de `type="date"` ou `type="datetime-local"` via override no `__init__`
- Upload de arquivo exige `enctype="multipart/form-data"` no template
- Validação customizada via `clean_<campo>()` ou `clean()`
- `autocomplete="off"` em todos os campos (já incluso no padrão abaixo)

---

## ModelForm padrão — obrigatório em todo form do projeto

```python
from django import forms
from .models import NomeModel


class NomeModelForm(forms.ModelForm):
    class Meta:
        model = NomeModel
        fields = ["nome", "tipo", "data", "valor", "observacoes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        # Campos de data precisam de type explícito
        if "data" in self.fields:
            self.fields["data"].widget.attrs["type"] = "date"
        if "data_hora" in self.fields:
            self.fields["data_hora"].widget.attrs["type"] = "datetime-local"
```

---

## Campos especiais — overrides no `__init__`

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Aplicar form-control em todos
    for field in self.fields.values():
        field.widget.attrs["class"] = "form-control"
        field.widget.attrs["autocomplete"] = "off"

    # Data
    self.fields["data_vencimento"].widget.attrs["type"] = "date"

    # Data + hora
    self.fields["data_execucao"].widget.attrs["type"] = "datetime-local"

    # Decimal — mostrar 2 casas
    self.fields["valor"].widget.attrs["step"] = "0.01"

    # Placeholder informativo
    self.fields["cpf_cnpj"].widget.attrs["placeholder"] = "Somente números"
    self.fields["cep"].widget.attrs["placeholder"] = "00000000"
    self.fields["celular"].widget.attrs["placeholder"] = "(63) 90000-0000"

    # Textarea — controlar linhas
    self.fields["observacoes"].widget.attrs["rows"] = "3"

    # Campo opcional (mesmo que obrigatório no model)
    self.fields["telefone"].required = False

    # Help text
    self.fields["cpf_cnpj"].help_text = "Somente dígitos, sem pontuação"
```

---

## Upload de arquivo (ImageField / FileField)

```python
# forms.py — FileInput não herda form-control automaticamente do __init__
# Adicionar manualmente se necessário:
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    for field in self.fields.values():
        field.widget.attrs["class"] = "form-control"
        field.widget.attrs["autocomplete"] = "off"
    # FileInput precisa apenas de form-control (já aplicado acima)
```

```html
<!-- template: obrigatório enctype quando há upload -->
<form method="post" enctype="multipart/form-data" novalidate>
    {% csrf_token %}
    ...
</form>
```

---

## Filtrar queryset de FK no formulário

```python
class PropostaForm(forms.ModelForm):
    class Meta:
        model = Proposta
        fields = ["cliente", "descricao", "valor"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        # Filtrar FK — apenas clientes ativos
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True).order_by("nome")
        self.fields["cliente"].empty_label = "Selecione um cliente..."
```

---

## Validação customizada

```python
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "cpf_cnpj", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        self.fields["cpf_cnpj"].widget.attrs["placeholder"] = "Somente números"

    def clean_cpf_cnpj(self):
        valor = self.cleaned_data.get("cpf_cnpj", "")
        apenas_digitos = "".join(filter(str.isdigit, valor))
        if len(apenas_digitos) not in (11, 14):
            raise forms.ValidationError("CPF deve ter 11 dígitos ou CNPJ 14 dígitos.")
        return apenas_digitos

    def clean(self):
        # Validação cruzada entre campos
        cleaned = super().clean()
        return cleaned
```

---

## O que NÃO fazer

- Nunca usar `fields = "__all__"` em produção — listar explicitamente
- Nunca definir classes via dict `widgets` na `Meta` — usar `__init__`
- Nunca usar `form-select` ou `form-check-input` (classes Bootstrap) — usar `form-control`
- Nunca omitir `enctype="multipart/form-data"` quando há upload
- Nunca usar `DateField` sem `type="date"` no widget — o input padrão é texto puro
- Nunca validar CPF/CNPJ só no frontend — sempre validar no `clean_`
