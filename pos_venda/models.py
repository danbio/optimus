from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from core.models import BaseModel


class Chamado(BaseModel):
    TIPO_CHOICES = [
        ("suporte", "Suporte Técnico"),
        ("garantia", "Garantia"),
        ("reclamacao", "Reclamação"),
        ("manutencao", "Manutenção"),
        ("outro", "Outro"),
    ]

    STATUS_ABERTO = "aberto"
    STATUS_ATENDIMENTO = "em_atendimento"
    STATUS_AGUARDANDO = "aguardando_cliente"
    STATUS_RESOLVIDO = "resolvido"
    STATUS_ENCERRADO = "encerrado"
    STATUS_CHOICES = [
        (STATUS_ABERTO, "Aberto"),
        (STATUS_ATENDIMENTO, "Em Atendimento"),
        (STATUS_AGUARDANDO, "Aguardando Cliente"),
        (STATUS_RESOLVIDO, "Resolvido"),
        (STATUS_ENCERRADO, "Encerrado"),
    ]

    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("normal", "Normal"),
        ("alta", "Alta"),
        ("urgente", "Urgente"),
    ]

    numero = models.CharField(max_length=20, unique=True, editable=False, verbose_name="número")
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="chamados",
        verbose_name="cliente",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="tipo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ABERTO, verbose_name="status")
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default="normal", verbose_name="prioridade")
    assunto = models.CharField(max_length=300, verbose_name="assunto")
    descricao = models.TextField(blank=True, verbose_name="descrição")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados_responsavel",
        verbose_name="responsável",
    )
    prazo = models.DateField(null=True, blank=True, verbose_name="prazo de resolução")
    data_resolucao = models.DateTimeField(null=True, blank=True, verbose_name="data de resolução")

    # Origens — FKs nullable para rastrear de onde veio o chamado
    ordem_servico = models.ForeignKey(
        "ordens_servico.OrdemServico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados",
        verbose_name="OS de origem",
    )
    proposta_solar = models.ForeignKey(
        "solar.PropostaSolar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados",
        verbose_name="proposta solar de origem",
    )
    proposta_servico = models.ForeignKey(
        "servicos.PropostaServico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados",
        verbose_name="proposta de serviço de origem",
    )
    venda_balcao = models.ForeignKey(
        "balcao.Venda",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados",
        verbose_name="venda de origem",
    )

    class Meta:
        verbose_name = "chamado"
        verbose_name_plural = "chamados"
        ordering = ["-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~(models.Q(ordem_servico__isnull=False) & models.Q(proposta_solar__isnull=False))
                    & ~(models.Q(ordem_servico__isnull=False) & models.Q(proposta_servico__isnull=False))
                    & ~(models.Q(ordem_servico__isnull=False) & models.Q(venda_balcao__isnull=False))
                    & ~(models.Q(proposta_solar__isnull=False) & models.Q(proposta_servico__isnull=False))
                    & ~(models.Q(proposta_solar__isnull=False) & models.Q(venda_balcao__isnull=False))
                    & ~(models.Q(proposta_servico__isnull=False) & models.Q(venda_balcao__isnull=False))
                ),
                name="pos_venda_apenas_uma_origem",
            )
        ]

    def __str__(self):
        return f"{self.numero} — {self.assunto}"

    def clean(self):
        super().clean()
        origens = [self.ordem_servico_id, self.proposta_solar_id, self.proposta_servico_id, self.venda_balcao_id]
        if sum(bool(origem) for origem in origens) > 1:
            raise ValidationError("Um chamado pode ter no máximo uma origem vinculada.")

        if self.ordem_servico_id and self.cliente_id:
            from ordens_servico.models import OrdemServico

            cliente_origem_id = OrdemServico.objects.filter(pk=self.ordem_servico_id).values_list("cliente_id", flat=True).first()
            if cliente_origem_id and cliente_origem_id != self.cliente_id:
                raise ValidationError({"cliente": "O cliente deve ser o mesmo da OS vinculada."})
        if self.proposta_solar_id and self.cliente_id:
            from solar.models import PropostaSolar

            cliente_origem_id = PropostaSolar.objects.filter(pk=self.proposta_solar_id).values_list("cliente_id", flat=True).first()
            if cliente_origem_id and cliente_origem_id != self.cliente_id:
                raise ValidationError({"cliente": "O cliente deve ser o mesmo da proposta solar vinculada."})
        if self.proposta_servico_id and self.cliente_id:
            from servicos.models import PropostaServico

            cliente_origem_id = PropostaServico.objects.filter(pk=self.proposta_servico_id).values_list("cliente_id", flat=True).first()
            if cliente_origem_id and cliente_origem_id != self.cliente_id:
                raise ValidationError({"cliente": "O cliente deve ser o mesmo da proposta de serviço vinculada."})
        if self.venda_balcao_id:
            from balcao.models import Venda

            cliente_origem_id = Venda.objects.filter(pk=self.venda_balcao_id).values_list("cliente_id", flat=True).first()
            if not cliente_origem_id:
                raise ValidationError({"venda_balcao": "Venda avulsa sem cliente não pode ser vinculada ao chamado."})
            if self.cliente_id and cliente_origem_id != self.cliente_id:
                raise ValidationError({"cliente": "O cliente deve ser o mesmo da venda de balcão vinculada."})

    def _gerar_numero(self):
        mes = timezone.now().strftime("%Y%m")
        prefix = f"CHM-{mes}-"
        ultimo = Chamado.objects.filter(numero__startswith=prefix).order_by("numero").last()
        seq = (int(ultimo.numero.split("-")[-1]) + 1) if ultimo else 1
        return f"{prefix}{seq:04d}"

    def save(self, *args, **kwargs):
        self.clean()
        if self.numero:
            return super().save(*args, **kwargs)

        for _ in range(5):
            self.numero = self._gerar_numero()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.numero = ""
        raise IntegrityError("Falha ao gerar número único para chamado após múltiplas tentativas.")

    @property
    def esta_vencido(self):
        if self.prazo and self.status not in (self.STATUS_RESOLVIDO, self.STATUS_ENCERRADO):
            return self.prazo < timezone.localdate()
        return False

    @property
    def origem_display(self):
        if self.ordem_servico_id:
            return ("OS", self.ordem_servico)
        if self.proposta_solar_id:
            return ("Solar", self.proposta_solar)
        if self.proposta_servico_id:
            return ("Serviço", self.proposta_servico)
        if self.venda_balcao_id:
            return ("Balcão", self.venda_balcao)
        return None


class InteracaoChamado(models.Model):
    TIPO_CHOICES = [
        ("comentario", "Comentário interno"),
        ("ligacao", "Ligação"),
        ("email", "E-mail"),
        ("visita", "Visita técnica"),
        ("resolucao", "Resolução"),
    ]

    chamado = models.ForeignKey(
        Chamado,
        on_delete=models.CASCADE,
        related_name="interacoes",
        verbose_name="chamado",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="comentario", verbose_name="tipo")
    texto = models.TextField(verbose_name="descrição")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="autor",
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="registrado em")

    class Meta:
        verbose_name = "interação"
        verbose_name_plural = "interações"
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.chamado.numero}"
