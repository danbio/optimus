# Padrão: Models Django — ERP Optimus

## Regras obrigatórias

- Todos os `verbose_name` e `verbose_name_plural` em **português**
- `on_delete=models.PROTECT` como padrão — nunca CASCADE sem justificativa explícita
- Choices definidas via `models.TextChoices` (nunca lista de tuplas avulsas)
- `auto_now_add=True` para criação, `auto_now=True` para atualização
- `__str__` obrigatório em todo model
- `class Meta` com `verbose_name`, `verbose_name_plural` e `ordering` padrão

---

## Template base de model

**Obrigatório:** todos os models herdam de `BaseModel` — nunca de `models.Model` diretamente.

```python
from core.models import BaseModel


class NomeModel(BaseModel):
    class Meta:
        verbose_name = "nome"
        verbose_name_plural = "nomes"
        ordering = ["-criado_em"]

    nome = models.CharField("nome", max_length=200)

    def __str__(self):
        return self.nome
```

`BaseModel` (`core/models.py`) já fornece `criado_em` e `atualizado_em` — não redeclarar.

---

## Choices com TextChoices

```python
class TipoCliente(models.TextChoices):
    PESSOA_FISICA = "PF", "Pessoa Física"
    PESSOA_JURIDICA = "PJ", "Pessoa Jurídica"

tipo = models.CharField(
    "tipo",
    max_length=2,
    choices=TipoCliente.choices,
    default=TipoCliente.PESSOA_FISICA,
)
```

---

## ForeignKey padrão

```python
cliente = models.ForeignKey(
    "clientes.Cliente",
    on_delete=models.PROTECT,
    verbose_name="cliente",
    related_name="pedidos",
)
```

---

## Campos comuns por contexto

| Uso | Campo |
|-----|-------|
| Valor monetário | `models.DecimalField("valor", max_digits=10, decimal_places=2)` |
| Porcentagem | `models.DecimalField("desconto", max_digits=5, decimal_places=2, default=0)` |
| Foto / documento | `models.ImageField("foto", upload_to="fotos/%Y/%m/", blank=True)` |
| Texto longo | `models.TextField("observações", blank=True)` |
| Booleano | `models.BooleanField("ativo", default=True)` |
| Data execução | `models.DateTimeField("data de execução")` |

---

## Número auto-gerado — padrão do projeto

Todos os apps com documentos (proposta, OS, venda, chamado) usam este padrão:

```python
# Prefixos por app: SOL- | SRV- | OS- | BAL- | LAN- | CHM-
def _gerar_numero(self):
    mes = timezone.now().strftime("%Y%m")
    prefix = f"SOL-{mes}-"
    ultimo = PropostaSolar.objects.filter(numero__startswith=prefix).order_by("numero").last()
    seq = (int(ultimo.numero.split("-")[-1]) + 1) if ultimo else 1
    return f"{prefix}{seq:04d}"

def save(self, *args, **kwargs):
    if self.numero:
        return super().save(*args, **kwargs)
    for _ in range(5):
        self.numero = self._gerar_numero()
        try:
            with transaction.atomic():
                return super().save(*args, **kwargs)
        except IntegrityError:
            self.numero = ""
    raise IntegrityError("Falha ao gerar número único após múltiplas tentativas.")
```

---

## CheckConstraint XOR — padrão do projeto

Usado quando exatamente um (ou no máximo um) FK deve estar preenchido:

```python
from django.db.models import Q

class Meta:
    constraints = [
        models.CheckConstraint(
            condition=(
                ~(Q(proposta_solar__isnull=False) & Q(proposta_servico__isnull=False))
            ),
            name="meumodel_apenas_uma_origem",
        )
    ]
```

Acompanhar sempre com validação em `clean()`:

```python
def clean(self):
    origens = [self.proposta_solar_id, self.proposta_servico_id]
    if sum(bool(o) for o in origens) > 1:
        raise ValidationError("Apenas uma origem permitida.")
```

---

## O que NÃO fazer

- Nunca herdar de `models.Model` — sempre de `BaseModel`
- Nunca `on_delete=models.CASCADE` sem comentário justificando
- Nunca `GenericForeignKey`
- Nunca duplicar dados de cliente — sempre ForeignKey para `clientes.Cliente`
- Nunca lista de tuplas para choices — usar `TextChoices`
