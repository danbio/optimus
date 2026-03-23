from django.conf import settings
from django.db import models

from core.models import BaseModel


class LancamentoFinanceiro(BaseModel):
    STATUS_PENDENTE = "pendente"
    STATUS_PARCIAL = "parcial"
    STATUS_LIQUIDADO = "liquidado"
    STATUS_CANCELADO = "cancelado"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_PARCIAL, "Parcial"),
        (STATUS_LIQUIDADO, "Liquidado"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    FORMA_DINHEIRO = "dinheiro"
    FORMA_PIX = "pix"
    FORMA_DEBITO = "cartao_debito"
    FORMA_CREDITO = "cartao_credito"
    FORMA_BOLETO = "boleto"
    FORMA_CREDIARIO = "crediario"
    FORMA_TRANSFERENCIA = "transferencia"
    FORMA_CHOICES = [
        (FORMA_DINHEIRO, "Dinheiro"),
        (FORMA_PIX, "PIX"),
        (FORMA_DEBITO, "Cartão Débito"),
        (FORMA_CREDITO, "Cartão Crédito"),
        (FORMA_BOLETO, "Boleto"),
        (FORMA_CREDIARIO, "Crediário"),
        (FORMA_TRANSFERENCIA, "Transferência Bancária"),
    ]

    numero = models.CharField(max_length=20, unique=True, editable=False, verbose_name="número")
    descricao = models.CharField(max_length=300, verbose_name="descrição")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDENTE, verbose_name="status")

    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="valor bruto (R$)")
    desconto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="desconto (R$)")
    valor_liquido = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="valor líquido (R$)")
    valor_recebido = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="valor recebido (R$)")

    data_emissao = models.DateField(auto_now_add=True, verbose_name="data de emissão")
    data_vencimento = models.DateField(verbose_name="data de vencimento")
    data_liquidacao = models.DateField(null=True, blank=True, verbose_name="data de liquidação")

    forma_pagamento = models.CharField(max_length=20, choices=FORMA_CHOICES, blank=True, verbose_name="forma de pagamento")
    num_parcelas = models.PositiveIntegerField(default=1, verbose_name="nº de parcelas")

    # Origens — FKs nullable, sem GenericForeignKey
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="lancamentos",
        verbose_name="cliente",
    )
    venda_balcao = models.ForeignKey(
        "balcao.Venda",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos",
        verbose_name="venda balcão",
    )
    proposta_solar = models.ForeignKey(
        "solar.PropostaSolar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos",
        verbose_name="proposta solar",
    )
    proposta_servico = models.ForeignKey(
        "servicos.PropostaServico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos",
        verbose_name="proposta de serviço",
    )
    ordem_servico = models.ForeignKey(
        "ordens_servico.OrdemServico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos",
        verbose_name="ordem de serviço",
    )

    observacoes = models.TextField(blank=True, verbose_name="observações")

    class Meta:
        verbose_name = "lançamento financeiro"
        verbose_name_plural = "lançamentos financeiros"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.numero} — {self.cliente.nome} — R$ {self.valor_liquido}"

    def save(self, *args, **kwargs):
        self.valor_liquido = self.valor_bruto - self.desconto
        if not self.numero:
            from django.utils import timezone

            mes = timezone.now().strftime("%Y%m")
            prefix = f"LAN-{mes}-"
            ultimo = LancamentoFinanceiro.objects.filter(numero__startswith=prefix).order_by("numero").last()
            seq = (int(ultimo.numero.split("-")[-1]) + 1) if ultimo else 1
            self.numero = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)

    @property
    def esta_vencido(self):
        from django.utils import timezone

        if self.status in (self.STATUS_LIQUIDADO, self.STATUS_CANCELADO):
            return False
        return self.data_vencimento < timezone.localdate()

    @property
    def saldo_aberto(self):
        return self.valor_liquido - self.valor_recebido

    @property
    def origem_display(self):
        if self.venda_balcao_id:
            return ("Balcão", "verde")
        if self.proposta_solar_id:
            return ("Solar", "laranja")
        if self.proposta_servico_id:
            return ("Serviço", "azul")
        if self.ordem_servico_id:
            return ("OS", "roxo")
        return ("Manual", "cinza")

    @property
    def origem_url(self):
        if self.venda_balcao_id:
            return ("balcao:detalhe", self.venda_balcao_id)
        if self.proposta_solar_id:
            return ("solar:detalhe", self.proposta_solar_id)
        if self.proposta_servico_id:
            return ("servicos:detalhe", self.proposta_servico_id)
        if self.ordem_servico_id:
            return ("ordens_servico:detalhe", self.ordem_servico_id)
        return None


class ParcelaLancamento(models.Model):
    STATUS_PENDENTE = "pendente"
    STATUS_PAGO = "pago"
    STATUS_CANCELADO = "cancelado"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_PAGO, "Pago"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    lancamento = models.ForeignKey(
        LancamentoFinanceiro,
        on_delete=models.CASCADE,
        related_name="parcelas",
        verbose_name="lançamento",
    )
    numero_parcela = models.PositiveIntegerField(verbose_name="nº da parcela")
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="valor (R$)")
    data_vencimento = models.DateField(verbose_name="vencimento")
    data_pagamento = models.DateField(null=True, blank=True, verbose_name="data de pagamento")
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="valor pago (R$)")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDENTE, verbose_name="status")
    observacao = models.CharField(max_length=300, blank=True, verbose_name="observação")

    class Meta:
        verbose_name = "parcela"
        verbose_name_plural = "parcelas"
        ordering = ["numero_parcela"]
        unique_together = [("lancamento", "numero_parcela")]

    def __str__(self):
        return f"Parcela {self.numero_parcela}/{self.lancamento.num_parcelas} — {self.lancamento.numero}"

    @property
    def esta_vencida(self):
        from django.utils import timezone

        if self.status != self.STATUS_PENDENTE:
            return False
        return self.data_vencimento < timezone.localdate()


class BaixaFinanceira(models.Model):
    lancamento = models.ForeignKey(
        LancamentoFinanceiro,
        on_delete=models.CASCADE,
        related_name="baixas",
        verbose_name="lançamento",
    )
    parcela = models.ForeignKey(
        ParcelaLancamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="baixas",
        verbose_name="parcela",
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="valor recebido (R$)")
    forma_pagamento = models.CharField(
        max_length=20,
        choices=LancamentoFinanceiro.FORMA_CHOICES,
        verbose_name="forma de pagamento",
    )
    data_pagamento = models.DateField(verbose_name="data do pagamento")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="registrado por",
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="registrado em")
    observacao = models.CharField(max_length=300, blank=True, verbose_name="observação")

    class Meta:
        verbose_name = "baixa financeira"
        verbose_name_plural = "baixas financeiras"
        ordering = ["-data_pagamento"]

    def __str__(self):
        return f"Baixa R$ {self.valor} em {self.data_pagamento} — {self.lancamento.numero}"
