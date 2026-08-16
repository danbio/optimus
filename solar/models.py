from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models

from clientes.models import Cliente
from core.models import BaseModel


class ModuloFotovoltaico(BaseModel):
    fabricante = models.CharField(max_length=100, verbose_name="fabricante")
    modelo = models.CharField(max_length=100, verbose_name="modelo")
    potencia_wp = models.IntegerField(verbose_name="potência (Wp)")
    eficiencia = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="eficiência (%)")
    voc = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="tensão circuito aberto - Voc (V)")
    isc = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="corrente curto-circuito - Isc (A)")
    largura = models.IntegerField(verbose_name="largura (mm)")
    altura = models.IntegerField(verbose_name="altura (mm)")
    peso = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="peso (kg)")
    garantia_produto = models.IntegerField(verbose_name="garantia do produto (anos)")
    garantia_desempenho = models.IntegerField(verbose_name="garantia de desempenho (anos)")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "módulo fotovoltaico"
        verbose_name_plural = "módulos fotovoltaicos"
        ordering = ["fabricante", "modelo"]

    def __str__(self):
        return f"{self.fabricante} {self.modelo} ({self.potencia_wp}Wp)"

    @property
    def area_m2(self):
        return round((self.largura * self.altura) / 1_000_000, 2)


class Inversor(BaseModel):
    TIPO_STRING = "string"
    TIPO_MICRO = "micro"
    TIPO_HIBRIDO = "hibrido"
    TIPO_CHOICES = [
        (TIPO_STRING, "String"),
        (TIPO_MICRO, "Microinversor"),
        (TIPO_HIBRIDO, "Híbrido"),
    ]

    FASE_MONO = "monofasico"
    FASE_TRI = "trifasico"
    FASE_CHOICES = [
        (FASE_MONO, "Monofásico"),
        (FASE_TRI, "Trifásico"),
    ]

    fabricante = models.CharField(max_length=100, verbose_name="fabricante")
    modelo = models.CharField(max_length=100, verbose_name="modelo")
    potencia_kw = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="potência (kW)")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_STRING, verbose_name="tipo")
    fase = models.CharField(max_length=10, choices=FASE_CHOICES, default=FASE_MONO, verbose_name="fase")
    tensao_max_entrada = models.IntegerField(verbose_name="tensão máx. entrada (V)")
    quantidade_mppt = models.IntegerField(verbose_name="quantidade de MPPTs")
    garantia = models.IntegerField(verbose_name="garantia (anos)")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "inversor"
        verbose_name_plural = "inversores"
        ordering = ["fabricante", "potencia_kw"]

    def __str__(self):
        return f"{self.fabricante} {self.modelo} ({self.potencia_kw}kW)"


class EstruturaFixacao(BaseModel):
    TELHADO_CERAMICO = "ceramico"
    TELHADO_METALICO = "metalico"
    TELHADO_FIBROCIMENTO = "fibrocimento"
    LAJE = "laje"
    SOLO = "solo"
    TIPO_CHOICES = [
        (TELHADO_CERAMICO, "Telha Cerâmica"),
        (TELHADO_METALICO, "Telha Metálica"),
        (TELHADO_FIBROCIMENTO, "Telha Fibrocimento"),
        (LAJE, "Laje"),
        (SOLO, "Solo"),
    ]

    MATERIAL_ALUMINIO = "aluminio"
    MATERIAL_ACO = "aco_galvanizado"
    MATERIAL_CHOICES = [
        (MATERIAL_ALUMINIO, "Alumínio"),
        (MATERIAL_ACO, "Aço Galvanizado"),
    ]

    fabricante = models.CharField(max_length=100, verbose_name="fabricante")
    modelo = models.CharField(max_length=100, verbose_name="modelo")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="tipo de instalação")
    material = models.CharField(max_length=20, choices=MATERIAL_CHOICES, default=MATERIAL_ALUMINIO, verbose_name="material")
    descricao = models.TextField(blank=True, verbose_name="descrição")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "estrutura de fixação"
        verbose_name_plural = "estruturas de fixação"
        ordering = ["fabricante", "tipo"]

    def __str__(self):
        return f"{self.fabricante} {self.modelo} ({self.get_tipo_display()})"


class MateriaisEletricos(BaseModel):
    CATEGORIA_CABO = "cabo"
    CATEGORIA_DISJUNTOR = "disjuntor"
    CATEGORIA_ELETRODUTO = "eletroduto"
    CATEGORIA_DPS = "dps"
    CATEGORIA_OUTROS = "outros"
    CATEGORIA_CHOICES = [
        (CATEGORIA_CABO, "Cabo"),
        (CATEGORIA_DISJUNTOR, "Disjuntor"),
        (CATEGORIA_ELETRODUTO, "Eletroduto"),
        (CATEGORIA_DPS, "DPS / Protetor de Surto"),
        (CATEGORIA_OUTROS, "Outros"),
    ]

    UNIDADE_METRO = "m"
    UNIDADE_PECA = "pc"
    UNIDADE_CHOICES = [
        (UNIDADE_METRO, "Metro (m)"),
        (UNIDADE_PECA, "Peça (pc)"),
    ]

    fabricante = models.CharField(max_length=100, verbose_name="fabricante")
    modelo = models.CharField(max_length=100, verbose_name="modelo / referência")
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default=CATEGORIA_OUTROS,
        verbose_name="categoria",
    )
    unidade = models.CharField(
        max_length=5,
        choices=UNIDADE_CHOICES,
        default=UNIDADE_PECA,
        verbose_name="unidade de medida",
    )
    descricao = models.TextField(blank=True, verbose_name="descrição / especificação")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "material elétrico"
        verbose_name_plural = "materiais elétricos"
        ordering = ["categoria", "fabricante", "modelo"]

    def __str__(self):
        return f"{self.get_categoria_display()} — {self.fabricante} {self.modelo}"


class PrecoEquipamentoSolar(BaseModel):
    """Tabela de preços com vigência para os equipamentos solares.

    Exatamente um dos quatro FKs de equipamento/material deve estar preenchido.
    Ao cadastrar um novo preço, o anterior (vigente_ate=null) é fechado automaticamente
    pelo Admin (PrecoEquipamentoSolarAdmin.save_model).
    """

    modulo = models.ForeignKey(
        ModuloFotovoltaico,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="módulo",
    )
    inversor = models.ForeignKey(
        Inversor,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="inversor",
    )
    estrutura = models.ForeignKey(
        EstruturaFixacao,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="estrutura",
    )
    material = models.ForeignKey(
        MateriaisEletricos,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="material elétrico",
    )

    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="preço de custo (R$)")
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="preço de venda (R$)")
    vigente_desde = models.DateField(verbose_name="vigente desde")
    vigente_ate = models.DateField(null=True, blank=True, verbose_name="vigente até")

    criado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        editable=False,
        verbose_name="criado por",
    )

    class Meta:
        verbose_name = "preço de equipamento solar"
        verbose_name_plural = "preços de equipamentos solares"
        ordering = ["-vigente_desde"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(modulo__isnull=False, inversor__isnull=True, estrutura__isnull=True, material__isnull=True)
                    | models.Q(modulo__isnull=True, inversor__isnull=False, estrutura__isnull=True, material__isnull=True)
                    | models.Q(modulo__isnull=True, inversor__isnull=True, estrutura__isnull=False, material__isnull=True)
                    | models.Q(modulo__isnull=True, inversor__isnull=True, estrutura__isnull=True, material__isnull=False)
                ),
                name="preco_solar_apenas_um_tipo",
            )
        ]

    def __str__(self):
        equip = self.modulo or self.inversor or self.estrutura or self.material
        return f"{equip} — R$ {self.preco_venda} (desde {self.vigente_desde})"

    def clean(self):
        preenchidos = sum(
            [
                bool(self.modulo_id),
                bool(self.inversor_id),
                bool(self.estrutura_id),
                bool(self.material_id),
            ]
        )
        if preenchidos != 1:
            raise ValidationError("Informe exatamente um equipamento ou material.")

    @classmethod
    def get_preco_vigente(cls, equipamento, data):
        """Retorna o registro de preço vigente para um equipamento/material em uma data."""
        if isinstance(equipamento, ModuloFotovoltaico):
            qs = cls.objects.filter(modulo=equipamento)
        elif isinstance(equipamento, Inversor):
            qs = cls.objects.filter(inversor=equipamento)
        elif isinstance(equipamento, EstruturaFixacao):
            qs = cls.objects.filter(estrutura=equipamento)
        elif isinstance(equipamento, MateriaisEletricos):
            qs = cls.objects.filter(material=equipamento)
        else:
            return None
        return (
            qs.filter(vigente_desde__lte=data).filter(models.Q(vigente_ate__isnull=True) | models.Q(vigente_ate__gte=data)).order_by("-vigente_desde").first()
        )


class TaxaCartao(BaseModel):
    """Tabela de acréscimo do cartão por bandeira/parcela (fonte: tabela
    oficial Intelbras — "Simulador de Acréscimo ao Portador"). Usada pra
    calcular quanto o cliente paga se optar por parcelar no cartão, no
    modelo "repassar ao portador" (a Optimus recebe o valor cheio, o
    acréscimo vai todo pro cliente).

    Fórmula (ver solar/views/_helpers.py::calcular_parcela_cartao):
        valor_com_acrescimo = valor_base / (1 - percentual/100)
        valor_da_parcela = valor_com_acrescimo / parcelas

    NÃO é `valor_base × (1 + percentual)` — essa conta dá um resultado
    ligeiramente menor e propositalmente NÃO é a usada aqui; verificado
    contra a planilha oficial (base R$750, débito 1,29% → R$759,80, que só
    bate dividindo pelo complemento).
    """

    FORMA_DEBITO = "debito"
    FORMA_CREDITO = "credito"
    FORMA_PIX = "pix"
    FORMA_CHOICES = [
        (FORMA_DEBITO, "Débito"),
        (FORMA_CREDITO, "Crédito"),
        (FORMA_PIX, "PIX"),
    ]

    BANDEIRA_VISA_MASTER = "visa_master"
    BANDEIRA_AMEX = "amex"
    BANDEIRA_ELO = "elo"
    BANDEIRA_HIPER = "hiper"
    BANDEIRA_CHOICES = [
        (BANDEIRA_VISA_MASTER, "Visa ou Master"),
        (BANDEIRA_AMEX, "Amex"),
        (BANDEIRA_ELO, "Elo"),
        (BANDEIRA_HIPER, "Hiper"),
    ]

    forma = models.CharField(max_length=10, choices=FORMA_CHOICES, verbose_name="forma")
    bandeira = models.CharField(max_length=15, choices=BANDEIRA_CHOICES, verbose_name="bandeira")
    parcelas = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="parcelas",
        help_text="1 para débito/PIX/crédito à vista; 2 a 21 para crédito parcelado.",
    )
    percentual = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="acréscimo (%)")

    class Meta:
        verbose_name = "taxa de cartão"
        verbose_name_plural = "taxas de cartão"
        ordering = ["bandeira", "forma", "parcelas"]
        constraints = [
            models.UniqueConstraint(fields=["forma", "bandeira", "parcelas"], name="taxa_cartao_unica_por_combinacao")
        ]

    def __str__(self):
        rotulo_parcela = f"{self.parcelas}x" if self.forma == self.FORMA_CREDITO and self.parcelas > 1 else self.get_forma_display()
        return f"{self.get_bandeira_display()} — {rotulo_parcela} — {self.percentual}%"


class ItemPropostaSolar(models.Model):
    """Item de uma proposta solar com snapshot imutável do preço na data de criação."""

    proposta = models.ForeignKey(
        "PropostaSolar",
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="proposta",
    )
    modulo = models.ForeignKey(
        ModuloFotovoltaico,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name="módulo",
    )
    inversor = models.ForeignKey(
        Inversor,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name="inversor",
    )
    estrutura = models.ForeignKey(
        EstruturaFixacao,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name="estrutura",
    )
    material = models.ForeignKey(
        MateriaisEletricos,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name="material elétrico",
    )
    quantidade = models.IntegerField(default=1, verbose_name="quantidade")

    # Snapshot imutável: registra exatamente o preço vigente no momento da criação da proposta
    preco_venda_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="preço de venda (snapshot)",
    )
    preco_custo_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="preço de custo (snapshot)",
    )
    data_referencia_preco = models.DateField(verbose_name="data de referência do preço")

    class Meta:
        verbose_name = "item da proposta solar"
        verbose_name_plural = "itens da proposta solar"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(modulo__isnull=False, inversor__isnull=True, estrutura__isnull=True, material__isnull=True)
                    | models.Q(modulo__isnull=True, inversor__isnull=False, estrutura__isnull=True, material__isnull=True)
                    | models.Q(modulo__isnull=True, inversor__isnull=True, estrutura__isnull=False, material__isnull=True)
                    | models.Q(modulo__isnull=True, inversor__isnull=True, estrutura__isnull=True, material__isnull=False)
                ),
                name="item_proposta_solar_apenas_um_tipo",
            )
        ]

    def __str__(self):
        equip = self.modulo or self.inversor or self.estrutura or self.material
        return f"{equip} × {self.quantidade}"

    @property
    def subtotal(self):
        return self.preco_venda_snapshot * self.quantidade


def _validade_padrao():
    return date.today() + timedelta(days=30)


class PropostaSolar(BaseModel):
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

    LIGACAO_MONOFASICO = "monofasico"
    LIGACAO_BIFASICO = "bifasico"
    LIGACAO_TRIFASICO = "trifasico"

    numero = models.CharField(max_length=20, unique=True, editable=False, verbose_name="número")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="cliente")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_RASCUNHO, verbose_name="status")

    # Dimensionamento
    consumo_medio_kwh = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="consumo médio mensal (kWh)")
    hsp = models.DecimalField(max_digits=4, decimal_places=2, default=5.50, verbose_name="HSP — horas de sol pleno (h/dia)")
    fator_eficiencia = models.DecimalField(max_digits=4, decimal_places=2, default=0.75, verbose_name="fator de eficiência do sistema")
    potencia_kwp = models.DecimalField(max_digits=7, decimal_places=3, verbose_name="potência do sistema (kWp)")
    quantidade_modulos = models.IntegerField(verbose_name="quantidade de módulos", default=0)

    # Equipamento Base de Dimensionamento (Referência)
    modulo = models.ForeignKey(ModuloFotovoltaico, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="módulo fotovoltaico")

    # Financeiro
    valor_instalacao = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="valor da instalação (R$)")
    tarifa_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="tarifa de energia do cliente (R$/kWh)",
        help_text=(
            "Com tributos, como aparece na fatura na linha “Consumo em kWh”. "
            "Opcional — sem ela o PDF não mostra a análise de retorno."
        ),
    )
    autoconsumo_simultaneo_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("25.00"),
        verbose_name="autoconsumo simultâneo (%)",
        help_text=(
            "Quanto da geração o cliente consome no mesmo instante em que é "
            "produzida (não passa pela rede, logo não sofre Fio B e economiza "
            "a tarifa cheia). Residencial costuma ficar em 20–30%; comércio "
            "com carga diurna chega a 50–70%."
        ),
    )
    tipo_ligacao = models.CharField(
        max_length=12,
        choices=[
            (LIGACAO_MONOFASICO, "Monofásico (mínimo 30 kWh)"),
            (LIGACAO_BIFASICO, "Bifásico (mínimo 50 kWh)"),
            (LIGACAO_TRIFASICO, "Trifásico (mínimo 100 kWh)"),
        ],
        default=LIGACAO_MONOFASICO,
        verbose_name="tipo de ligação",
        help_text="Define o custo de disponibilidade — o mínimo que o cliente paga mesmo gerando toda a energia.",
    )

    # Proposta
    validade = models.DateField(default=_validade_padrao, verbose_name="validade da proposta")
    observacoes = models.TextField(blank=True, verbose_name="observações")

    class Meta:
        verbose_name = "proposta solar"
        verbose_name_plural = "propostas solares"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.numero} — {self.cliente.nome}"

    @property
    def valor_equipamentos(self):
        """Soma de preco_venda_snapshot × quantidade de todos os itens da proposta."""
        from django.db.models import DecimalField as Dec
        from django.db.models import F, Sum

        total = self.itens.aggregate(
            total=Sum(
                F("preco_venda_snapshot") * F("quantidade"),
                output_field=Dec(max_digits=12, decimal_places=2),
            )
        )["total"]
        return total or Decimal("0.00")

    @property
    def valor_total(self):
        return (self.valor_equipamentos or 0) + (self.valor_instalacao or 0)

    @property
    def potencia_real_kwp(self):
        if not self.modulo:
            return 0
        return round(self.quantidade_modulos * self.modulo.potencia_wp / 1000, 3)

    @property
    def area_total_m2(self):
        if not self.modulo:
            return 0
        return round(self.quantidade_modulos * self.modulo.area_m2, 2)

    @property
    def geracao_mensal_kwh(self):
        """Projeção técnica de geração (kWp × HSP × 30 dias × fator de
        eficiência) — não é uma promessa financeira, é só a conversão da
        potência dimensionada em energia esperada. Usada no PDF e no resumo
        de fechamento (ver proposta_detail.html)."""
        if not self.potencia_real_kwp:
            return 0
        return round(float(self.potencia_real_kwp) * float(self.hsp) * 30 * float(self.fator_eficiencia))

    @property
    def retorno_financeiro(self):
        """Projeção de retorno pelas regras reais de GD da Lei 14.300/2022 —
        Fio B gradual sobre a energia compensada, custo de disponibilidade e
        COSIP não compensados. Só calcula quando o vendedor informa a tarifa
        do cliente (`tarifa_kwh`); sem isso retorna None, não inventa número.
        Ver `solar/services.py` e a skill solar-domain §8."""
        from configuracoes.models import Configuracao

        from .services import projetar_retorno

        config = Configuracao.atual()
        return projetar_retorno(
            valor_investimento=self.valor_total,
            geracao_mensal_kwh=Decimal(str(self.geracao_mensal_kwh or 0)),
            consumo_mensal_kwh=self.consumo_medio_kwh,
            tarifa_kwh=self.tarifa_kwh,
            tusd_fio_b_kwh=config.tusd_fio_b_kwh,
            tipo_ligacao=self.tipo_ligacao,
            cosip_mensal=config.cosip_mensal,
            autoconsumo_simultaneo_pct=self.autoconsumo_simultaneo_pct,
            ano_base=(self.criado_em.year if self.criado_em else date.today().year),
        )

    @property
    def inversor_principal(self):
        """Primeiro inversor entre os itens da proposta. Simplificação: o
        modelo não rastreia um FK de "inversor de referência" como faz com
        `modulo` — a grande maioria das propostas tem só um inversor, então
        isso cobre o caso comum. Se um dia existir proposta com múltiplos
        modelos de inversor, isto mostra só o primeiro."""
        item = self.itens.filter(inversor__isnull=False).select_related("inversor").first()
        return item.inversor if item else None

    @property
    def quantidade_inversores(self):
        from django.db.models import Sum

        total = self.itens.filter(inversor__isnull=False).aggregate(total=Sum("quantidade"))["total"]
        return total or 0

    def _gerar_numero(self):
        mes = date.today().strftime("%Y%m")
        ultimo = PropostaSolar.objects.filter(numero__startswith=f"SOL-{mes}").order_by("-numero").first()
        seq = (int(ultimo.numero.split("-")[-1]) + 1) if ultimo else 1
        return f"SOL-{mes}-{seq:04d}"

    def save(self, *args, **kwargs):
        if self.numero:
            return super().save(*args, **kwargs)

        for _ in range(5):
            self.numero = self._gerar_numero()
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                self.numero = ""
        raise IntegrityError("Falha ao gerar número único para proposta solar após múltiplas tentativas.")
