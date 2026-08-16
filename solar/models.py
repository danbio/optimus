from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models

from clientes.models import Cliente
from core.models import BaseModel

# Dias reais de cada mês (ano comum). A conta antiga usava 30 fixo, o que
# subestima a geração em ~1,4% no acumulado do ano.
DIAS_DO_MES = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
NOMES_DOS_MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")


class ModuloFotovoltaico(BaseModel):
    fabricante = models.CharField(max_length=100, verbose_name="fabricante")
    modelo = models.CharField(max_length=100, verbose_name="modelo")
    potencia_wp = models.IntegerField(
        # Mesma trava do inversor, na unidade oposta: módulo digitado em kW
        # (0 ou 1) ou em W errado por ordem de grandeza não passa.
        validators=[MinValueValidator(50), MaxValueValidator(2000)],
        verbose_name="potência (Wp)",
        help_text="Em Wp, não em kWp. Um módulo de 610 W se cadastra como 610.",
    )
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
    potencia_kw = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        # Trava o erro clássico de digitar em W: o SAJ 6K-R5 foi cadastrado
        # como 6000 em vez de 6, saiu "6.000,00kW" no PDF do cliente e
        # inutilizou a sugestão de inversor compatível por meses.
        validators=[MinValueValidator(Decimal("0.1")), MaxValueValidator(Decimal("500"))],
        verbose_name="potência (kW)",
        help_text="Em kW, não em W. Um inversor “6K” são 6 kW.",
    )
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


class Municipio(BaseModel):
    """Município com a irradiação solar do local.

    Mora no app `solar` porque existe para dimensionar sistema — os campos
    de HSP são o motivo dele. Se um dia outro app precisar de município
    genérico, aí sim vale promover para `core`.

    O HSP mensal é climatologia (média de longo prazo) da NASA POWER, então
    não expira: sincroniza uma vez e fica.
    """

    codigo_ibge = models.IntegerField(unique=True, verbose_name="código IBGE")
    nome = models.CharField(max_length=120, verbose_name="nome")
    uf = models.CharField(max_length=2, verbose_name="UF")

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="longitude")

    hsp_mensal = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="HSP por mês (kWh/m²/dia)",
        help_text='Climatologia NASA POWER, no formato {"1": 5.39, ..., "12": 5.46}.',
    )
    hsp_anual = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="HSP médio anual (h/dia)"
    )
    sincronizado_em = models.DateTimeField(null=True, blank=True, verbose_name="HSP sincronizado em")

    class Meta:
        verbose_name = "município"
        verbose_name_plural = "municípios"
        ordering = ["uf", "nome"]

    def __str__(self):
        return f"{self.nome}/{self.uf}"

    @property
    def tem_hsp(self) -> bool:
        return bool(self.hsp_anual and self.hsp_mensal)

    def hsp_do_mes(self, mes: int) -> Decimal | None:
        """HSP de um mês (1–12). O JSON volta do banco com chave string."""
        if not self.hsp_mensal:
            return None
        valor = self.hsp_mensal.get(str(mes), self.hsp_mensal.get(mes))
        return Decimal(str(valor)) if valor is not None else None


class Distribuidora(BaseModel):
    """Concessionária de distribuição de energia.

    O CNPJ é a chave usada para consultar as tarifas homologadas no portal
    de dados abertos da ANEEL (ver `sincronizar_tarifas_aneel`), por isso é
    obrigatório e único.
    """

    nome = models.CharField(max_length=120, verbose_name="nome")
    sigla = models.CharField(max_length=20, verbose_name="sigla ANEEL", help_text="Como aparece no campo SigNomeAgente da ANEEL. Ex.: ETO.")
    cnpj = models.CharField(max_length=14, unique=True, verbose_name="CNPJ (só dígitos)")
    uf = models.CharField(max_length=2, verbose_name="UF")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "distribuidora"
        verbose_name_plural = "distribuidoras"
        ordering = ["uf", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.uf})"


class TarifaDistribuidora(BaseModel):
    """Espelho local das tarifas homologadas pela ANEEL.

    ⚠️ Os valores são gravados **em R$/MWh e SEM tributos**, exatamente como
    a ANEEL publica. Quem converte para R$/kWh com tributos é
    `solar/services.py` — o gross-up está verificado contra fatura real da
    Energisa TO com erro de 0,0005%.

    Cada linha vale para uma vigência (a ANEEL reajusta uma vez por ano).
    """

    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.CASCADE, related_name="tarifas", verbose_name="distribuidora")
    subgrupo = models.CharField(max_length=10, default="B1", verbose_name="subgrupo tarifário")
    modalidade = models.CharField(max_length=40, default="Convencional", verbose_name="modalidade")
    subclasse = models.CharField(max_length=80, default="Residencial", verbose_name="subclasse")

    vigencia_inicio = models.DateField(verbose_name="início da vigência")
    vigencia_fim = models.DateField(null=True, blank=True, verbose_name="fim da vigência")

    vlr_tusd = models.DecimalField(max_digits=12, decimal_places=6, verbose_name="TUSD (R$/MWh)")
    vlr_te = models.DecimalField(max_digits=12, decimal_places=6, verbose_name="TE (R$/MWh)")
    vlr_tusd_fio_b = models.DecimalField(max_digits=12, decimal_places=6, default=0, verbose_name="TUSD Fio B (R$/MWh)")

    sincronizado_em = models.DateTimeField(null=True, blank=True, verbose_name="sincronizado em")

    class Meta:
        verbose_name = "tarifa da distribuidora"
        verbose_name_plural = "tarifas das distribuidoras"
        ordering = ["distribuidora", "-vigencia_inicio", "subclasse"]
        constraints = [
            models.UniqueConstraint(
                fields=["distribuidora", "subgrupo", "modalidade", "subclasse", "vigencia_inicio"],
                name="tarifa_aneel_unica_por_vigencia",
            )
        ]

    def __str__(self):
        return f"{self.distribuidora.sigla} {self.subgrupo} {self.subclasse} — {self.vigencia_inicio:%d/%m/%Y}"

    @property
    def tarifa_base_kwh(self) -> Decimal:
        """TUSD + TE convertidos para R$/kWh, ainda sem tributos.

        É o valor que a fatura da Energisa imprime na coluna "Tarifa Unit".
        """
        return (self.vlr_tusd + self.vlr_te) / Decimal("1000")

    @property
    def fio_b_kwh(self) -> Decimal:
        """TUSD Fio B em R$/kWh, sem tributos. É a base do "Ajuste GDII"."""
        return self.vlr_tusd_fio_b / Decimal("1000")

    @classmethod
    def vigente(cls, distribuidora, data, subclasse="Residencial", subgrupo="B1"):
        """Tarifa válida numa data. Vigência aberta (`vigencia_fim` nulo)
        conta como ainda vigente."""
        return (
            cls.objects.filter(
                distribuidora=distribuidora,
                subgrupo=subgrupo,
                subclasse=subclasse,
                vigencia_inicio__lte=data,
            )
            .filter(models.Q(vigencia_fim__gte=data) | models.Q(vigencia_fim__isnull=True))
            .order_by("-vigencia_inicio")
            .first()
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

    distribuidora = models.ForeignKey(
        Distribuidora,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="distribuidora do cliente",
        help_text="Define a tarifa homologada e o Fio B usados na análise de retorno, direto da ANEEL.",
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="município da instalação",
        help_text=(
            "Onde o gerador vai ser instalado — nem sempre é onde o cliente "
            "mora. Define o HSP e a curva de geração mês a mês."
        ),
    )

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
    def pendencias(self):
        """O que falta na proposta para ela ser confiável.

        Existe porque o sistema aceitava em silêncio uma proposta só com
        módulo e inversor. Faltando estrutura e material elétrico, o valor
        total sai subestimado — e como o payback divide o investimento pela
        economia, ele sai **otimista demais**, que é o pior tipo de erro
        para mostrar a um cliente.

        Retorna lista de mensagens; vazia quer dizer proposta completa.
        """
        itens = list(self.itens.all())
        avisos = []

        if not any(item.modulo_id for item in itens):
            avisos.append("Nenhum módulo fotovoltaico na lista de equipamentos.")
        if not any(item.inversor_id for item in itens):
            avisos.append("Nenhum inversor na lista de equipamentos.")
        if not any(item.estrutura_id for item in itens):
            avisos.append("Falta a estrutura de fixação — o valor total está subestimado.")
        if not any(item.material_id for item in itens):
            avisos.append("Faltam materiais elétricos (cabos, conectores, DPS, disjuntores).")

        if not self.valor_instalacao:
            avisos.append("Mão de obra de instalação está zerada.")

        if any(item.preco_venda_snapshot <= 0 for item in itens):
            avisos.append("Há item com preço zerado — confira se o equipamento tem preço vigente.")

        if not self.tarifa_kwh and not self.distribuidora_id:
            avisos.append("Sem distribuidora nem tarifa: o PDF sai sem a análise de retorno.")

        return avisos

    @property
    def geracao_mensal_serie(self):
        """Geração projetada mês a mês, em kWh.

        Só existe quando a proposta tem município com HSP sincronizado —
        é o HSP daquele mês, no local da instalação, com os dias reais do
        mês (não 30 fixo). Retorna None sem esses dados, e aí o resto do
        sistema cai na média anual.
        """
        if not self.municipio_id or not self.potencia_real_kwp:
            return None
        municipio = self.municipio
        if not municipio.tem_hsp:
            return None

        potencia = Decimal(str(self.potencia_real_kwp))
        fator = Decimal(str(self.fator_eficiencia))

        serie = []
        for mes in range(1, 13):
            hsp = municipio.hsp_do_mes(mes)
            if hsp is None:
                return None
            dias = Decimal(DIAS_DO_MES[mes - 1])
            serie.append(
                {
                    "mes": mes,
                    "nome": NOMES_DOS_MESES[mes - 1],
                    "hsp": hsp,
                    "kwh": (potencia * hsp * dias * fator).quantize(Decimal("1")),
                }
            )
        return serie

    @property
    def geracao_anual_kwh(self):
        serie = self.geracao_mensal_serie
        if serie:
            return sum(item["kwh"] for item in serie)
        return Decimal(str(self.geracao_mensal_kwh)) * 12

    @property
    def geracao_mensal_kwh(self):
        """Projeção técnica de geração mensal média, em kWh.

        Com município sincronizado usa a média real dos 12 meses (HSP de
        cada mês × dias daquele mês); sem ele, cai na conta antiga
        kWp × HSP × 30 × fator. Não é promessa financeira, é a conversão da
        potência dimensionada em energia esperada."""
        if not self.potencia_real_kwp:
            return 0

        serie = self.geracao_mensal_serie
        if serie:
            return int(sum(item["kwh"] for item in serie) / 12)

        return round(float(self.potencia_real_kwp) * float(self.hsp) * 30 * float(self.fator_eficiencia))

    @property
    def tarifas_aplicaveis(self):
        """Tarifas de consumo e injeção (com tributos) e o Fio B base.

        Prioriza a tarifa homologada da distribuidora do cliente, espelhada
        da ANEEL (`TarifaDistribuidora`). Se a proposta não tem distribuidora
        ou não há tarifa sincronizada para a data, cai para `tarifa_kwh`
        digitada da fatura — nesse caso o Fio B fica zerado, porque não dá
        pra separar a parcela sem a tarifa-base da ANEEL.

        Retorna None quando não há nenhuma das duas: sem dado real, a
        análise de retorno inteira some da proposta.
        """
        from configuracoes.models import Configuracao

        from .services import aplicar_tributos

        config = Configuracao.atual()
        referencia = self.criado_em.date() if self.criado_em else date.today()

        tarifa = None
        if self.distribuidora_id:
            tarifa = TarifaDistribuidora.vigente(self.distribuidora, referencia)

        if tarifa:
            base = tarifa.tarifa_base_kwh
            return {
                "consumo": aplicar_tributos(base, config.icms_pct, config.pis_cofins_pct),
                "injecao": aplicar_tributos(base, config.icms_efetivo_injecao_pct, config.pis_cofins_pct),
                "fio_b": tarifa.fio_b_kwh,
                "origem": "aneel",
                "vigencia": tarifa.vigencia_inicio,
            }

        if self.tarifa_kwh and self.tarifa_kwh > 0:
            # Sem a decomposição da ANEEL, o melhor que dá pra fazer é
            # reconstruir a tarifa de injeção pelo mesmo gross-up reduzido.
            base_estimada = self.tarifa_kwh * (Decimal("1") - config.pis_cofins_pct / 100) * (Decimal("1") - config.icms_pct / 100)
            return {
                "consumo": self.tarifa_kwh,
                "injecao": aplicar_tributos(base_estimada, config.icms_efetivo_injecao_pct, config.pis_cofins_pct),
                "fio_b": Decimal("0"),
                "origem": "manual",
                "vigencia": None,
            }

        return None

    @property
    def retorno_financeiro(self):
        """Projeção de retorno pelas regras reais de GD da Lei 14.300/2022.

        Modela a fatura linha a linha: consumo, crédito da injeção (com ICMS
        reduzido), Ajuste do Fio B e COSIP. Sem tarifa — nem da ANEEL nem
        digitada — retorna None em vez de inventar número. Ver
        `solar/services.py` e a skill solar-domain §8."""
        from configuracoes.models import Configuracao

        from .services import projetar_retorno

        tarifas = self.tarifas_aplicaveis
        if not tarifas:
            return None

        config = Configuracao.atual()
        resultado = projetar_retorno(
            valor_investimento=self.valor_total,
            geracao_mensal_kwh=Decimal(str(self.geracao_mensal_kwh or 0)),
            consumo_mensal_kwh=self.consumo_medio_kwh,
            tarifa_consumo_kwh=tarifas["consumo"],
            tarifa_injecao_kwh=tarifas["injecao"],
            fio_b_kwh=tarifas["fio_b"],
            tipo_ligacao=self.tipo_ligacao,
            cosip_mensal=config.cosip_mensal,
            autoconsumo_simultaneo_pct=self.autoconsumo_simultaneo_pct,
            ano_base=(self.criado_em.year if self.criado_em else date.today().year),
        )
        if resultado:
            resultado["origem_tarifa"] = tarifas["origem"]
            resultado["vigencia_tarifa"] = tarifas["vigencia"]
            resultado["tarifa_consumo_kwh"] = tarifas["consumo"]
        return resultado

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
