from datetime import date, timedelta

from django.db import models

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

    numero = models.CharField(max_length=20, unique=True, editable=False, verbose_name="número")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="cliente")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_RASCUNHO, verbose_name="status")

    # Dimensionamento
    consumo_medio_kwh = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="consumo médio mensal (kWh)")
    hsp = models.DecimalField(max_digits=4, decimal_places=2, default=5.50, verbose_name="HSP — horas de sol pleno (h/dia)")
    fator_eficiencia = models.DecimalField(max_digits=4, decimal_places=2, default=0.75, verbose_name="fator de eficiência do sistema")
    potencia_kwp = models.DecimalField(max_digits=7, decimal_places=3, verbose_name="potência do sistema (kWp)")
    quantidade_modulos = models.IntegerField(verbose_name="quantidade de módulos")

    # Equipamentos
    modulo = models.ForeignKey(ModuloFotovoltaico, on_delete=models.PROTECT, verbose_name="módulo fotovoltaico")
    inversor = models.ForeignKey(Inversor, on_delete=models.PROTECT, verbose_name="inversor")
    estrutura = models.ForeignKey(EstruturaFixacao, on_delete=models.PROTECT, verbose_name="estrutura de fixação")

    # Financeiro
    valor_equipamentos = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="valor dos equipamentos (R$)")
    valor_instalacao = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="valor da instalação (R$)")

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
    def valor_total(self):
        return (self.valor_equipamentos or 0) + (self.valor_instalacao or 0)

    @property
    def potencia_real_kwp(self):
        return round(self.quantidade_modulos * self.modulo.potencia_wp / 1000, 3)

    @property
    def area_total_m2(self):
        return round(self.quantidade_modulos * self.modulo.area_m2, 2)

    def save(self, *args, **kwargs):
        if not self.numero:
            from datetime import date as _date

            mes = _date.today().strftime("%Y%m")
            ultimo = PropostaSolar.objects.filter(numero__startswith=f"SOL-{mes}").order_by("-numero").first()
            seq = (int(ultimo.numero.split("-")[-1]) + 1) if ultimo else 1
            self.numero = f"SOL-{mes}-{seq:04d}"
        super().save(*args, **kwargs)
