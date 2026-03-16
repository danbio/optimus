from decimal import Decimal

from django.db import models

from core.models import BaseModel


class Produto(BaseModel):
    PRECO_REF_CHOICES = [
        ("", "—"),
        ("PSD", "PSD"),
        ("PP", "PP"),
        ("S/Controle de Venda", "S/Controle de Venda"),
    ]

    # Identificação
    codigo = models.IntegerField(unique=True, verbose_name="código")
    descricao = models.CharField(max_length=300, verbose_name="descrição")
    bu = models.CharField(max_length=60, blank=True, verbose_name="BU")
    segmento = models.CharField(max_length=100, blank=True, verbose_name="segmento")
    familia = models.CharField(max_length=100, blank=True, verbose_name="família")

    # Fiscal
    ncm = models.CharField(max_length=20, blank=True, verbose_name="NCM")
    ean = models.CharField(max_length=30, blank=True, verbose_name="EAN")
    ipi = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"), verbose_name="IPI (%)")
    icms = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"), verbose_name="ICMS (%)")

    # Preços
    psd = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"), verbose_name="PSD — Preço de Custo")
    pscf = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"), verbose_name="PSCF — Preço de Venda")
    preco_referencia = models.CharField(max_length=30, blank=True, choices=PRECO_REF_CHOICES, verbose_name="controle de venda")
    qtd_multipla = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1"), verbose_name="qtd. múltipla")

    # Outros
    observacoes = models.TextField(blank=True, verbose_name="observações")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        ordering = ["descricao"]

    def __str__(self):
        return f"{self.codigo} — {self.descricao}"

    @property
    def margem(self):
        if self.pscf and self.pscf > 0:
            return round(float((self.pscf - self.psd) / self.pscf * 100), 1)
        return None
