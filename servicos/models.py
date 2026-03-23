from django.db import models

from core.models import BaseModel


class Servico(BaseModel):
    TIPO_CHOICES = [
        ("seguranca", "Segurança Eletrônica"),
        ("automacao", "Automação"),
        ("acesso", "Controle de Acesso"),
    ]

    nome = models.CharField(max_length=200, verbose_name="nome")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="tipo")
    descricao = models.TextField(blank=True, verbose_name="descrição")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "Serviço"
        verbose_name_plural = "Serviços"
        ordering = ["tipo", "nome"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.nome}"


class PropostaServico(BaseModel):
    STATUS_RASCUNHO = "rascunho"
    STATUS_ENVIADA = "enviada"
    STATUS_APROVADA = "aprovada"
    STATUS_CONCLUIDA = "concluida"
    STATUS_CANCELADA = "cancelada"
    STATUS_CHOICES = [
        (STATUS_RASCUNHO, "Rascunho"),
        (STATUS_ENVIADA, "Enviada"),
        (STATUS_APROVADA, "Aprovada"),
        (STATUS_CONCLUIDA, "Concluída"),
        (STATUS_CANCELADA, "Cancelada"),
    ]
    TIPO_CHOICES = [
        ("seguranca", "Segurança Eletrônica"),
        ("automacao", "Automação"),
        ("acesso", "Controle de Acesso"),
    ]

    numero = models.CharField(max_length=20, unique=True, editable=False, verbose_name="número")
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="propostas_servico",
        verbose_name="cliente",
    )
    tipo_servico = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="tipo de serviço")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho", verbose_name="status")
    validade = models.DateField(verbose_name="validade da proposta")
    observacoes = models.TextField(blank=True, verbose_name="observações")

    class Meta:
        verbose_name = "Proposta de Serviço"
        verbose_name_plural = "Propostas de Serviço"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.numero} — {self.cliente}"

    def save(self, *args, **kwargs):
        if not self.numero:
            from django.utils import timezone

            now = timezone.now()
            prefix = f"SRV-{now.strftime('%Y%m')}-"
            last = PropostaServico.objects.filter(numero__startswith=prefix).order_by("numero").last()
            if last:
                seq = int(last.numero.split("-")[-1]) + 1
            else:
                seq = 1
            self.numero = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)

    @property
    def total_servicos(self):
        return sum(i.valor for i in self.itens_servico.all())

    @property
    def total_produtos(self):
        return sum(i.quantidade * i.valor_unitario for i in self.itens_produto.all())

    @property
    def valor_total(self):
        return self.total_servicos + self.total_produtos


class ItemServico(models.Model):
    proposta = models.ForeignKey(
        PropostaServico,
        on_delete=models.CASCADE,
        related_name="itens_servico",
        verbose_name="proposta",
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        verbose_name="serviço",
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="valor (R$)")
    observacao = models.CharField(max_length=300, blank=True, verbose_name="observação")

    class Meta:
        verbose_name = "Item de Serviço"
        verbose_name_plural = "Itens de Serviço"

    def __str__(self):
        return f"{self.servico.nome} — R$ {self.valor}"


class ItemProduto(models.Model):
    proposta = models.ForeignKey(
        PropostaServico,
        on_delete=models.CASCADE,
        related_name="itens_produto",
        verbose_name="proposta",
    )
    produto = models.ForeignKey(
        "estoque.Produto",
        on_delete=models.PROTECT,
        verbose_name="produto",
    )
    quantidade = models.PositiveIntegerField(default=1, verbose_name="quantidade")
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="valor unitário (R$)")

    class Meta:
        verbose_name = "Item de Produto"
        verbose_name_plural = "Itens de Produto"

    @property
    def subtotal(self):
        return self.quantidade * self.valor_unitario

    def __str__(self):
        return f"{self.produto.descricao} x{self.quantidade}"
