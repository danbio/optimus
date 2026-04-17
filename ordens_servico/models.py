from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from core.models import BaseModel


class Tecnico(BaseModel):
    ESPECIALIDADE_CHOICES = [
        ("solar", "Energia Solar"),
        ("seguranca", "Segurança Eletrônica"),
        ("automacao", "Automação"),
        ("acesso", "Controle de Acesso"),
        ("geral", "Geral"),
    ]

    nome = models.CharField(max_length=200, verbose_name="nome")
    telefone = models.CharField(max_length=20, blank=True, verbose_name="telefone")
    email = models.EmailField(blank=True, verbose_name="e-mail")
    especialidade = models.CharField(
        max_length=20,
        choices=ESPECIALIDADE_CHOICES,
        default="geral",
        verbose_name="especialidade",
    )
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "técnico"
        verbose_name_plural = "técnicos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class OrdemServico(BaseModel):
    STATUS_ABERTA = "aberta"
    STATUS_AGENDADA = "agendada"
    STATUS_EM_EXECUCAO = "em_execucao"
    STATUS_CONCLUIDA = "concluida"
    STATUS_FATURADA = "faturada"
    STATUS_SUSPENSA = "suspensa"
    STATUS_CHOICES = [
        (STATUS_ABERTA, "Aberta"),
        (STATUS_AGENDADA, "Agendada"),
        (STATUS_EM_EXECUCAO, "Em Execução"),
        (STATUS_CONCLUIDA, "Concluída"),
        (STATUS_FATURADA, "Faturada"),
        (STATUS_SUSPENSA, "Suspensa"),
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
        related_name="ordens_servico",
        verbose_name="cliente",
    )
    proposta_solar = models.ForeignKey(
        "solar.PropostaSolar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_servico",
        verbose_name="proposta solar",
    )
    proposta_servico = models.ForeignKey(
        "servicos.PropostaServico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_servico",
        verbose_name="proposta de serviço",
    )
    tecnico = models.ForeignKey(
        Tecnico,
        on_delete=models.PROTECT,
        related_name="ordens_servico",
        verbose_name="técnico responsável",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ABERTA,
        verbose_name="status",
    )
    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default="normal",
        verbose_name="prioridade",
    )
    descricao = models.TextField(blank=True, verbose_name="descrição do serviço")

    # Datas de acompanhamento
    data_agendamento = models.DateTimeField(null=True, blank=True, verbose_name="data do agendamento")
    data_inicio_execucao = models.DateTimeField(null=True, blank=True, verbose_name="início da execução")
    data_conclusao = models.DateTimeField(null=True, blank=True, verbose_name="data de conclusão")

    # Assinatura do cliente
    assinatura_nome = models.CharField(max_length=200, blank=True, verbose_name="nome de quem assinou")
    assinatura_confirmada = models.BooleanField(default=False, verbose_name="cliente confirmou a conclusão")
    assinatura_data = models.DateTimeField(null=True, blank=True, verbose_name="data da assinatura")

    observacoes = models.TextField(blank=True, verbose_name="observações")

    class Meta:
        verbose_name = "ordem de serviço"
        verbose_name_plural = "ordens de serviço"
        ordering = ["-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=~(models.Q(proposta_solar__isnull=False) & models.Q(proposta_servico__isnull=False)),
                name="os_apenas_uma_proposta_origem",
            )
        ]

    def __str__(self):
        return f"{self.numero} — {self.cliente.nome}"

    def clean(self):
        super().clean()

        if self.proposta_solar_id and self.proposta_servico_id:
            raise ValidationError("Uma OS não pode estar vinculada a Proposta Solar e Proposta de Serviço ao mesmo tempo.")

        if self.proposta_solar_id and self.cliente_id:
            from solar.models import PropostaSolar

            cliente_proposta_id = PropostaSolar.objects.filter(pk=self.proposta_solar_id).values_list("cliente_id", flat=True).first()
            if cliente_proposta_id and cliente_proposta_id != self.cliente_id:
                raise ValidationError({"cliente": "O cliente da OS deve ser o mesmo da Proposta Solar vinculada."})

        if self.proposta_servico_id and self.cliente_id:
            from servicos.models import PropostaServico

            cliente_proposta_id = PropostaServico.objects.filter(pk=self.proposta_servico_id).values_list("cliente_id", flat=True).first()
            if cliente_proposta_id and cliente_proposta_id != self.cliente_id:
                raise ValidationError({"cliente": "O cliente da OS deve ser o mesmo da Proposta de Serviço vinculada."})

    def _gerar_numero(self):
        now = timezone.now()
        prefix = f"OS-{now.strftime('%Y%m')}-"
        last = OrdemServico.objects.filter(numero__startswith=prefix).order_by("numero").last()
        seq = (int(last.numero.split("-")[-1]) + 1) if last else 1
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
        raise IntegrityError("Falha ao gerar número único para Ordem de Serviço após múltiplas tentativas.")

    @property
    def tipo_origem(self):
        if self.proposta_solar_id:
            return "Solar"
        elif self.proposta_servico_id:
            return "Serviço"
        return "Avulsa"

    @property
    def checklist_total(self):
        return self.itens_checklist.count()

    @property
    def checklist_concluidos(self):
        return self.itens_checklist.filter(concluido=True).count()

    @property
    def checklist_percentual(self):
        total = self.checklist_total
        if total == 0:
            return 0
        return int(self.checklist_concluidos / total * 100)


class ChecklistTemplate(BaseModel):
    TIPO_CHOICES = [
        ("solar", "Energia Solar"),
        ("seguranca", "Segurança Eletrônica"),
        ("automacao", "Automação"),
        ("acesso", "Controle de Acesso"),
        ("geral", "Geral"),
    ]

    descricao = models.CharField(max_length=300, verbose_name="descrição do item")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="tipo de serviço")
    ordem = models.PositiveIntegerField(default=0, verbose_name="ordem")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "item de checklist (template)"
        verbose_name_plural = "itens de checklist (templates)"
        ordering = ["tipo", "ordem", "descricao"]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.descricao}"


class ItemChecklist(models.Model):
    ordem_servico = models.ForeignKey(
        OrdemServico,
        on_delete=models.CASCADE,
        related_name="itens_checklist",
        verbose_name="ordem de serviço",
    )
    descricao = models.CharField(max_length=300, verbose_name="descrição")
    concluido = models.BooleanField(default=False, verbose_name="concluído")
    observacao = models.TextField(blank=True, verbose_name="observação")
    ordem = models.PositiveIntegerField(default=0, verbose_name="ordem")

    class Meta:
        verbose_name = "item de checklist"
        verbose_name_plural = "itens de checklist"
        ordering = ["ordem", "pk"]

    def __str__(self):
        status = "✓" if self.concluido else "○"
        return f"{status} {self.descricao}"


class FotoOS(models.Model):
    ordem_servico = models.ForeignKey(
        OrdemServico,
        on_delete=models.CASCADE,
        related_name="fotos",
        verbose_name="ordem de serviço",
    )
    foto = models.ImageField(upload_to="ordens_servico/fotos/%Y/%m/", verbose_name="foto")
    legenda = models.CharField(max_length=200, blank=True, verbose_name="legenda")
    enviada_em = models.DateTimeField(auto_now_add=True, verbose_name="enviada em")

    class Meta:
        verbose_name = "foto da OS"
        verbose_name_plural = "fotos da OS"
        ordering = ["-enviada_em"]

    def __str__(self):
        return f"Foto {self.pk} — {self.ordem_servico.numero}"
