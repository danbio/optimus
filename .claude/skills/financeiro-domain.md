# Domínio Financeiro — ERP Optimus

## Visão geral

O app `financeiro` é referenciado por **todos** os outros apps via ForeignKey.
Toda venda (solar, serviços, balcão) gera parcelas. O fluxo de caixa agrega recebimentos por período.

---

## Choices padrão

```python
from django.db import models


class FormasPagamento(models.TextChoices):
    DINHEIRO = "DINHEIRO", "Dinheiro"
    PIX = "PIX", "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO", "Cartão de Crédito"
    CARTAO_DEBITO = "CARTAO_DEBITO", "Cartão de Débito"
    BOLETO = "BOLETO", "Boleto Bancário"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferência Bancária"
    CHEQUE = "CHEQUE", "Cheque"


class StatusParcela(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    PAGO = "PAGO", "Pago"
    VENCIDO = "VENCIDO", "Vencido"
    CANCELADO = "CANCELADO", "Cancelado"
```

---

## Model Parcela

```python
class Parcela(models.Model):
    class Meta:
        verbose_name = "parcela"
        verbose_name_plural = "parcelas"
        ordering = ["data_vencimento"]

    # Vínculo com a origem (apenas um dos dois será preenchido)
    proposta_solar = models.ForeignKey(
        "solar.PropostaSolar",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="proposta solar",
        related_name="parcelas",
    )
    proposta_servico = models.ForeignKey(
        "servicos.PropostaServico",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="proposta de serviço",
        related_name="parcelas",
    )
    venda_balcao = models.ForeignKey(
        "balcao.VendaBalcao",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="venda balcão",
        related_name="parcelas",
    )

    numero = models.PositiveSmallIntegerField("número da parcela", default=1)
    total_parcelas = models.PositiveSmallIntegerField("total de parcelas", default=1)
    valor = models.DecimalField("valor (R$)", max_digits=10, decimal_places=2)
    data_vencimento = models.DateField("data de vencimento")
    data_pagamento = models.DateField("data de pagamento", null=True, blank=True)
    forma_pagamento = models.CharField(
        "forma de pagamento",
        max_length=20,
        choices=FormasPagamento.choices,
        default=FormasPagamento.PIX,
    )
    status = models.CharField(
        "status",
        max_length=10,
        choices=StatusParcela.choices,
        default=StatusParcela.PENDENTE,
    )
    observacoes = models.TextField("observações", blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    def __str__(self):
        return f"Parcela {self.numero}/{self.total_parcelas} — R$ {self.valor}"

    @property
    def esta_vencido(self) -> bool:
        from datetime import date
        return self.status == StatusParcela.PENDENTE and self.data_vencimento < date.today()
```

---

## Gerar parcelas em loop

```python
from datetime import date
from dateutil.relativedelta import relativedelta  # pip install python-dateutil


def gerar_parcelas(proposta, valor_total: float, num_parcelas: int, forma_pagamento: str, data_primeira: date):
    """Cria N parcelas mensais a partir de data_primeira."""
    valor_parcela = round(valor_total / num_parcelas, 2)

    for i in range(num_parcelas):
        Parcela.objects.create(
            proposta_solar=proposta if hasattr(proposta, 'kwp_calculado') else None,
            proposta_servico=proposta if not hasattr(proposta, 'kwp_calculado') else None,
            numero=i + 1,
            total_parcelas=num_parcelas,
            valor=valor_parcela,
            data_vencimento=data_primeira + relativedelta(months=i),
            forma_pagamento=forma_pagamento,
            status=StatusParcela.PENDENTE,
        )
```

---

## Fluxo de caixa — agregação por período

```python
from django.db.models import Sum
from django.db.models.functions import TruncMonth


def fluxo_caixa_mensal(ano: int):
    """Retorna recebimentos agrupados por mês para um ano."""
    return (
        Parcela.objects
        .filter(status=StatusParcela.PAGO, data_pagamento__year=ano)
        .annotate(mes=TruncMonth("data_pagamento"))
        .values("mes")
        .annotate(total=Sum("valor"))
        .order_by("mes")
    )
```

---

## Registrar pagamento

```python
def registrar_pagamento(parcela: Parcela, data_pagamento, forma_pagamento: str):
    from datetime import date
    parcela.status = StatusParcela.PAGO
    parcela.data_pagamento = data_pagamento or date.today()
    parcela.forma_pagamento = forma_pagamento
    parcela.save()
```

---

## Regras de negócio

- **Nunca usar GenericForeignKey** — FK nullable explícita por tipo de origem
- Apenas **um** dos campos de FK deve ser preenchido por parcela (solar, serviço ou balcão)
- `on_delete=PROTECT` em todas as FK — não deletar proposta se houver parcelas
- Status `VENCIDO` pode ser calculado via `property` ou via task periódica (`update_vencidos()`)
- Valor total deve ser consistente: soma das parcelas = valor da proposta
