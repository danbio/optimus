from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class Venda(BaseModel):
    STATUS_RASCUNHO = "rascunho"
    STATUS_FINALIZADA = "finalizada"
    STATUS_CANCELADA = "cancelada"
    STATUS_CHOICES = [
        (STATUS_RASCUNHO, "Rascunho"),
        (STATUS_FINALIZADA, "Finalizada"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    FORMA_CHOICES = [
        ("dinheiro", "Dinheiro"),
        ("pix", "PIX"),
        ("cartao_debito", "Cartão Débito"),
        ("cartao_credito", "Cartão Crédito"),
        ("boleto", "Boleto"),
        ("crediario", "Crediário"),
    ]

    numero = models.CharField(max_length=20, unique=True, editable=False, verbose_name="número")
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vendas_balcao",
        verbose_name="cliente",
    )
    cliente_nome_avulso = models.CharField(max_length=100, blank=True, verbose_name="nome (avulso)")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_RASCUNHO, verbose_name="status")
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vendas_balcao",
        verbose_name="operador",
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="subtotal (R$)")
    desconto_reais = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="desconto (R$)")
    desconto_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="desconto (%)")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="total (R$)")

    forma_pagamento = models.CharField(max_length=20, choices=FORMA_CHOICES, blank=True, verbose_name="forma de pagamento")
    num_parcelas = models.PositiveIntegerField(default=1, verbose_name="nº de parcelas")
    observacoes = models.TextField(blank=True, verbose_name="observações")

    class Meta:
        verbose_name = "venda"
        verbose_name_plural = "vendas"
        ordering = ["-criado_em"]

    def __str__(self):
        nome = self.cliente.nome if self.cliente else (self.cliente_nome_avulso or "Avulso")
        return f"{self.numero} — {nome}"

    def save(self, *args, **kwargs):
        if not self.numero:
            mes = timezone.now().strftime("%Y%m")
            prefix = f"BAL-{mes}-"
            ultimo = Venda.objects.filter(numero__startswith=prefix).order_by("numero").last()
            seq = (int(ultimo.numero.split("-")[-1]) + 1) if ultimo else 1
            self.numero = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)

    def recalcular_totais(self):
        self.subtotal = sum(item.subtotal for item in self.itens.all())
        if self.desconto_pct > 0:
            self.desconto_reais = round(self.subtotal * self.desconto_pct / 100, 2)
        self.total = max(self.subtotal - self.desconto_reais, 0)
        self.save(update_fields=["subtotal", "desconto_reais", "desconto_pct", "total"])

    @property
    def nome_cliente_display(self):
        if self.cliente:
            return self.cliente.nome
        return self.cliente_nome_avulso or "Avulso"


class ItemVenda(models.Model):
    venda = models.ForeignKey(
        Venda,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="venda",
    )
    produto = models.ForeignKey(
        "estoque.Produto",
        on_delete=models.PROTECT,
        verbose_name="produto",
    )
    quantidade = models.DecimalField(max_digits=8, decimal_places=2, default=1, verbose_name="quantidade")
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="valor unitário (R$)")
    desconto_item = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="desconto (R$)")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="subtotal (R$)")

    class Meta:
        verbose_name = "item de venda"
        verbose_name_plural = "itens de venda"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantidade}x {self.produto.descricao} — R$ {self.subtotal}"

    def save(self, *args, **kwargs):
        self.subtotal = max(self.quantidade * self.valor_unitario - self.desconto_item, 0)
        super().save(*args, **kwargs)
