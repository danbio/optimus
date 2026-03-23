"""
Popula o banco com dados de referência do mercado solar brasileiro.
Uso: python manage.py seed_solar
"""

from django.core.management.base import BaseCommand
from solar.models import EstruturaFixacao, Inversor, ModuloFotovoltaico


MODULOS = [
    # Canadian Solar
    {
        "fabricante": "Canadian Solar",
        "modelo": "CS6R-435MS",
        "potencia_wp": 435,
        "eficiencia": 21.30,
        "voc": 49.90,
        "isc": 11.00,
        "largura": 1048,
        "altura": 2108,
        "peso": 22.50,
        "garantia_produto": 12,
        "garantia_desempenho": 25,
    },
    {
        "fabricante": "Canadian Solar",
        "modelo": "CS6R-550MS",
        "potencia_wp": 550,
        "eficiencia": 21.50,
        "voc": 53.50,
        "isc": 13.20,
        "largura": 1134,
        "altura": 2278,
        "peso": 28.00,
        "garantia_produto": 12,
        "garantia_desempenho": 25,
    },
    # BYD
    {
        "fabricante": "BYD",
        "modelo": "BYD435B10J",
        "potencia_wp": 435,
        "eficiencia": 21.20,
        "voc": 49.60,
        "isc": 10.98,
        "largura": 1048,
        "altura": 2094,
        "peso": 21.80,
        "garantia_produto": 12,
        "garantia_desempenho": 25,
    },
    {
        "fabricante": "BYD",
        "modelo": "BYD540B10J",
        "potencia_wp": 540,
        "eficiencia": 21.00,
        "voc": 52.40,
        "isc": 13.00,
        "largura": 1134,
        "altura": 2278,
        "peso": 27.90,
        "garantia_produto": 12,
        "garantia_desempenho": 25,
    },
    # JA Solar
    {
        "fabricante": "JA Solar",
        "modelo": "JAM72S30-550/MR",
        "potencia_wp": 550,
        "eficiencia": 21.30,
        "voc": 52.96,
        "isc": 13.23,
        "largura": 1134,
        "altura": 2278,
        "peso": 28.50,
        "garantia_produto": 12,
        "garantia_desempenho": 25,
    },
    {
        "fabricante": "JA Solar",
        "modelo": "JAM60S20-385/MR",
        "potencia_wp": 385,
        "eficiencia": 20.70,
        "voc": 45.50,
        "isc": 10.71,
        "largura": 1000,
        "altura": 1879,
        "peso": 19.50,
        "garantia_produto": 12,
        "garantia_desempenho": 25,
    },
    # Risen
    {
        "fabricante": "Risen",
        "modelo": "RSM110-8-540M",
        "potencia_wp": 540,
        "eficiencia": 20.90,
        "voc": 52.20,
        "isc": 13.20,
        "largura": 1134,
        "altura": 2278,
        "peso": 28.00,
        "garantia_produto": 12,
        "garantia_desempenho": 25,
    },
    # Trina Solar
    {
        "fabricante": "Trina Solar",
        "modelo": "TSM-440DE09R.08",
        "potencia_wp": 440,
        "eficiencia": 21.10,
        "voc": 49.80,
        "isc": 11.20,
        "largura": 1048,
        "altura": 2094,
        "peso": 22.00,
        "garantia_produto": 10,
        "garantia_desempenho": 25,
    },
]

INVERSORES = [
    # Growatt — líderes em market share no Brasil
    {
        "fabricante": "Growatt",
        "modelo": "MIN 3000TL-XH",
        "potencia_kw": 3.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 600,
        "quantidade_mppt": 2,
        "garantia": 5,
    },
    {
        "fabricante": "Growatt",
        "modelo": "MIN 5000TL-XH",
        "potencia_kw": 5.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 600,
        "quantidade_mppt": 2,
        "garantia": 5,
    },
    {
        "fabricante": "Growatt",
        "modelo": "MIN 6000TL-XH",
        "potencia_kw": 6.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 600,
        "quantidade_mppt": 2,
        "garantia": 5,
    },
    {
        "fabricante": "Growatt",
        "modelo": "MID 10KTL3-X",
        "potencia_kw": 10.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_TRI,
        "tensao_max_entrada": 1000,
        "quantidade_mppt": 3,
        "garantia": 5,
    },
    {
        "fabricante": "Growatt",
        "modelo": "MID 20KTL3-X",
        "potencia_kw": 20.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_TRI,
        "tensao_max_entrada": 1000,
        "quantidade_mppt": 4,
        "garantia": 5,
    },
    # WEG — fabricante brasileiro
    {
        "fabricante": "WEG",
        "modelo": "SIW300H M005",
        "potencia_kw": 5.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 600,
        "quantidade_mppt": 2,
        "garantia": 5,
    },
    {
        "fabricante": "WEG",
        "modelo": "SIW300H M010",
        "potencia_kw": 10.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_TRI,
        "tensao_max_entrada": 800,
        "quantidade_mppt": 3,
        "garantia": 5,
    },
    # Fronius
    {
        "fabricante": "Fronius",
        "modelo": "Primo 5.0-1",
        "potencia_kw": 5.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 600,
        "quantidade_mppt": 2,
        "garantia": 5,
    },
    {
        "fabricante": "Fronius",
        "modelo": "Symo 10.0-3",
        "potencia_kw": 10.00,
        "tipo": Inversor.TIPO_STRING,
        "fase": Inversor.FASE_TRI,
        "tensao_max_entrada": 800,
        "quantidade_mppt": 2,
        "garantia": 5,
    },
    # Hoymiles — microinversores
    {
        "fabricante": "Hoymiles",
        "modelo": "HM-600",
        "potencia_kw": 0.60,
        "tipo": Inversor.TIPO_MICRO,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 60,
        "quantidade_mppt": 2,
        "garantia": 10,
    },
    {
        "fabricante": "Hoymiles",
        "modelo": "HM-1500",
        "potencia_kw": 1.50,
        "tipo": Inversor.TIPO_MICRO,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 60,
        "quantidade_mppt": 4,
        "garantia": 10,
    },
    # Deye — híbridos em alta
    {
        "fabricante": "Deye",
        "modelo": "SUN-5K-SG03LP1-EU",
        "potencia_kw": 5.00,
        "tipo": Inversor.TIPO_HIBRIDO,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 500,
        "quantidade_mppt": 2,
        "garantia": 5,
    },
    {
        "fabricante": "Deye",
        "modelo": "SUN-8K-SG01LP1-EU",
        "potencia_kw": 8.00,
        "tipo": Inversor.TIPO_HIBRIDO,
        "fase": Inversor.FASE_MONO,
        "tensao_max_entrada": 500,
        "quantidade_mppt": 2,
        "garantia": 5,
    },
]

ESTRUTURAS = [
    # Romagnole — maior fabricante nacional
    {
        "fabricante": "Romagnole",
        "modelo": "Kit Telha Colonial",
        "tipo": EstruturaFixacao.TELHADO_CERAMICO,
        "material": EstruturaFixacao.MATERIAL_ALUMINIO,
        "descricao": "Kit para telha colonial (portuguesa), perfis de alumínio anodizado, trilhos e grampos universais.",
    },
    {
        "fabricante": "Romagnole",
        "modelo": "Kit Telha Metálica Trapezoidal",
        "tipo": EstruturaFixacao.TELHADO_METALICO,
        "material": EstruturaFixacao.MATERIAL_ALUMINIO,
        "descricao": "Kit para telha metálica trapezoidal, fixação direta no perfil da telha sem perfuração.",
    },
    {
        "fabricante": "Romagnole",
        "modelo": "Kit Fibrocimento",
        "tipo": EstruturaFixacao.TELHADO_FIBROCIMENTO,
        "material": EstruturaFixacao.MATERIAL_ALUMINIO,
        "descricao": "Kit para telha de fibrocimento (Brasilit, Eternit), ganchos com vedação EPDM.",
    },
    {
        "fabricante": "Romagnole",
        "modelo": "Kit Laje",
        "tipo": EstruturaFixacao.LAJE,
        "material": EstruturaFixacao.MATERIAL_ALUMINIO,
        "descricao": "Estrutura em alumínio para laje plana, inclinação ajustável de 10° a 30°.",
    },
    # Yamada
    {
        "fabricante": "Yamada",
        "modelo": "YM-TC",
        "tipo": EstruturaFixacao.TELHADO_CERAMICO,
        "material": EstruturaFixacao.MATERIAL_ALUMINIO,
        "descricao": "Suporte alumínio 6063-T5 para telha cerâmica, gancho com parafuso inox A4.",
    },
    {
        "fabricante": "Yamada",
        "modelo": "YM-TM",
        "tipo": EstruturaFixacao.TELHADO_METALICO,
        "material": EstruturaFixacao.MATERIAL_ALUMINIO,
        "descricao": "Suporte alumínio para telha metálica tipo sanduíche e trapezoidal.",
    },
    # Estrutura Solo (aço galvanizado)
    {
        "fabricante": "Exmetal",
        "modelo": "EX-SOLO-30",
        "tipo": EstruturaFixacao.SOLO,
        "material": EstruturaFixacao.MATERIAL_ACO,
        "descricao": "Estrutura de solo em aço galvanizado, inclinação fixa 30°, para sistemas de grande porte.",
    },
    {
        "fabricante": "Exmetal",
        "modelo": "EX-SOLO-ADJ",
        "tipo": EstruturaFixacao.SOLO,
        "material": EstruturaFixacao.MATERIAL_ACO,
        "descricao": "Estrutura de solo em aço galvanizado com inclinação ajustável de 15° a 45°.",
    },
]


class Command(BaseCommand):
    help = "Popula o banco com módulos, inversores e estruturas de fixação de referência."

    def handle(self, *args, **options):
        self._seed_modulos()
        self._seed_inversores()
        self._seed_estruturas()
        self.stdout.write(self.style.SUCCESS("Dados solares carregados com sucesso."))

    def _seed_modulos(self):
        criados = 0
        for dados in MODULOS:
            _, novo = ModuloFotovoltaico.objects.get_or_create(
                fabricante=dados["fabricante"],
                modelo=dados["modelo"],
                defaults=dados,
            )
            if novo:
                criados += 1
        self.stdout.write(f"  Módulos: {criados} criados, {len(MODULOS) - criados} já existiam.")

    def _seed_inversores(self):
        criados = 0
        for dados in INVERSORES:
            _, novo = Inversor.objects.get_or_create(
                fabricante=dados["fabricante"],
                modelo=dados["modelo"],
                defaults=dados,
            )
            if novo:
                criados += 1
        self.stdout.write(f"  Inversores: {criados} criados, {len(INVERSORES) - criados} já existiam.")

    def _seed_estruturas(self):
        criados = 0
        for dados in ESTRUTURAS:
            _, novo = EstruturaFixacao.objects.get_or_create(
                fabricante=dados["fabricante"],
                modelo=dados["modelo"],
                defaults=dados,
            )
            if novo:
                criados += 1
        self.stdout.write(f"  Estruturas: {criados} criadas, {len(ESTRUTURAS) - criados} já existiam.")
