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

```python
from django.db import models


class NomeModel(models.Model):
    class Meta:
        verbose_name = "nome"
        verbose_name_plural = "nomes"
        ordering = ["-criado_em"]

    nome = models.CharField("nome", max_length=200)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    def __str__(self):
        return self.nome
```

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

## O que NÃO fazer

- Nunca `on_delete=models.CASCADE` sem comentário justificando
- Nunca `GenericForeignKey`
- Nunca duplicar dados de cliente — sempre ForeignKey para `clientes.Cliente`
- Nunca lista de tuplas para choices — usar `TextChoices`
