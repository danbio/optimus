# Domínio Clientes — ERP Optimus

## Visão geral

`clientes` é um app **core** — referenciado via ForeignKey por todos os outros apps.
Nunca duplicar dados de cliente em outros apps. Sempre referenciar `clientes.Cliente`.

---

## Choices

```python
from django.db import models


class TipoCliente(models.TextChoices):
    PESSOA_FISICA = "PF", "Pessoa Física"
    PESSOA_JURIDICA = "PJ", "Pessoa Jurídica"
```

---

## Model Cliente

```python
class Cliente(models.Model):
    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nome"]

    tipo = models.CharField(
        "tipo",
        max_length=2,
        choices=TipoCliente.choices,
        default=TipoCliente.PESSOA_FISICA,
    )
    nome = models.CharField("nome / razão social", max_length=200)
    cpf_cnpj = models.CharField("CPF / CNPJ", max_length=14, unique=True)

    # Contato
    email = models.EmailField("e-mail", blank=True)
    telefone = models.CharField("telefone", max_length=15, blank=True)
    celular = models.CharField("celular", max_length=15, blank=True)

    # Endereço
    cep = models.CharField("CEP", max_length=8, blank=True)
    logradouro = models.CharField("logradouro", max_length=200, blank=True)
    numero = models.CharField("número", max_length=10, blank=True)
    complemento = models.CharField("complemento", max_length=100, blank=True)
    bairro = models.CharField("bairro", max_length=100, blank=True)
    cidade = models.CharField("cidade", max_length=100, blank=True)
    estado = models.CharField("estado (UF)", max_length=2, blank=True)

    ativo = models.BooleanField("ativo", default=True)
    observacoes = models.TextField("observações", blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    def __str__(self):
        return f"{self.nome} ({self.cpf_cnpj})"

    @property
    def is_pf(self) -> bool:
        return self.tipo == TipoCliente.PESSOA_FISICA

    @property
    def is_pj(self) -> bool:
        return self.tipo == TipoCliente.PESSOA_JURIDICA
```

---

## Validação CPF / CNPJ no formulário

```python
# clientes/forms.py
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo", "nome", "cpf_cnpj", "email", "telefone", "celular",
            "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "estado",
            "ativo", "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        # Placeholders específicos
        self.fields["cpf_cnpj"].widget.attrs["placeholder"] = "Somente números"
        self.fields["telefone"].widget.attrs["placeholder"] = "(63) 3000-0000"
        self.fields["celular"].widget.attrs["placeholder"] = "(63) 90000-0000"
        self.fields["cep"].widget.attrs["placeholder"] = "00000000"
        self.fields["estado"].widget.attrs["placeholder"] = "TO"
        self.fields["observacoes"].widget.attrs["rows"] = "2"
        # Campos opcionais
        self.fields["telefone"].required = False
        self.fields["complemento"].required = False

    def clean_cpf_cnpj(self):
        valor = self.cleaned_data.get("cpf_cnpj", "")
        apenas_digitos = "".join(filter(str.isdigit, valor))
        if len(apenas_digitos) == 11:
            return apenas_digitos  # CPF
        elif len(apenas_digitos) == 14:
            return apenas_digitos  # CNPJ
        raise forms.ValidationError("Informe um CPF válido (11 dígitos) ou CNPJ válido (14 dígitos).")
```

---

## Busca HTMX de cliente (padrão usado em outras apps)

```python
# clientes/views.py — view de busca parcial
from django.shortcuts import render
from .models import Cliente

def buscar_cliente(request):
    q = request.GET.get("q", "").strip()
    clientes = Cliente.objects.filter(nome__icontains=q, ativo=True)[:10] if q else []
    return render(request, "clientes/_busca_resultado.html", {"clientes": clientes})
```

```html
<!-- template com HTMX -->
<input type="text"
       class="form-control"
       placeholder="Buscar cliente pelo nome..."
       hx-get="{% url 'clientes:buscar' %}"
       hx-target="#resultado-cliente"
       hx-trigger="keyup changed delay:300ms"
       name="q">
<div id="resultado-cliente"></div>
```

```html
<!-- clientes/templates/clientes/_busca_resultado.html -->
{% for cliente in clientes %}
<div style="padding: 8px 12px; border-bottom: 1px solid var(--fundo-alt); cursor: pointer"
     onclick="selecionarCliente({{ cliente.pk }}, '{{ cliente.nome }}')">
    <strong>{{ cliente.nome }}</strong>
    <span style="color: var(--texto-corpo); font-size: 0.875rem"> — {{ cliente.get_tipo_display }} | {{ cliente.celular }}</span>
</div>
{% empty %}
<div style="padding: 8px 12px; color: var(--texto-corpo)">Nenhum cliente encontrado.</div>
{% endfor %}
```

---

## Como outros apps referenciam clientes

```python
# Em qualquer model de outro app:
cliente = models.ForeignKey(
    "clientes.Cliente",
    on_delete=models.PROTECT,
    verbose_name="cliente",
    related_name="propostas_solar",  # nome descritivo e único por app
)
```

---

## Admin

```python
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "cpf_cnpj", "celular", "cidade", "ativo"]
    list_filter = ["tipo", "ativo", "estado"]
    search_fields = ["nome", "cpf_cnpj", "email", "celular"]
    list_editable = ["ativo"]
```

---

## Regras

- `cpf_cnpj` armazenado **sem formatação** (somente dígitos) — formatar apenas na exibição
- `unique=True` em `cpf_cnpj` — nunca dois registros com o mesmo documento
- `on_delete=PROTECT` em todas as FK que apontam para Cliente — não deletar cliente com histórico
- Endereço completo é importante para OS (ordens de serviço de instalação solar)
