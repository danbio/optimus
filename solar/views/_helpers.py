"""Helpers internos do app solar — usados por propostas, catálogo e preços."""

import math
from decimal import Decimal, InvalidOperation

from ..models import (
    EstruturaFixacao,
    Inversor,
    ModuloFotovoltaico,
    TaxaCartao,
)


def calcular_kwp(consumo_kwh: float, hsp: float, fator: float) -> float:
    """Calcula potência necessária do sistema em kWp."""
    try:
        return round(float(consumo_kwh) / (float(hsp) * 30 * float(fator)), 3)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


def calcular_quantidade_modulos(kwp: float, modulo: ModuloFotovoltaico) -> int:
    """Calcula quantidade de módulos necessários para atingir kWp."""
    try:
        return math.ceil(float(kwp) * 1000 / modulo.potencia_wp)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


def inversores_compativeis(potencia_kwp: Decimal | float, faixa_min_pct: Decimal, faixa_max_pct: Decimal) -> list[dict]:
    """Lista os inversores ativos com a relação CC:CA (potência do sistema
    dividida pela potência do inversor) em relação à potência dimensionada.

    A faixa aceitável (ex.: 80%–135%) vem de `Configuracao.atual()` — é o
    ponto de sobre/subdimensionamento que a Optimus tolera, não uma
    constante técnica fixa. Retorna todos os inversores ativos, marcados
    como compatível ou não, ordenados com os compatíveis primeiro e, dentro
    de cada grupo, pelos mais próximos de 100% (a relação "ideal").
    """
    try:
        kwp = Decimal(str(potencia_kwp))
    except (InvalidOperation, TypeError):
        return []
    if kwp <= 0:
        return []

    resultado = []
    for inversor in Inversor.objects.filter(ativo=True):
        if not inversor.potencia_kw or inversor.potencia_kw <= 0:
            continue
        ratio_pct = (kwp / inversor.potencia_kw) * 100
        compativel = faixa_min_pct <= ratio_pct <= faixa_max_pct
        resultado.append(
            {
                "inversor": inversor,
                "ratio_pct": round(ratio_pct, 1),
                "compativel": compativel,
            }
        )

    resultado.sort(key=lambda r: (not r["compativel"], abs(r["ratio_pct"] - 100)))
    return resultado


def calcular_parcela_cartao(valor_base: Decimal, bandeira: str) -> list[dict]:
    """Simula o parcelamento no cartão pra uma bandeira, no modelo "repassar
    ao portador": o cliente paga o acréscimo, a Optimus recebe `valor_base`
    cheio. Retorna crédito à vista (1x) e 2x a 21x, cada um com o valor
    total com acréscimo e o valor da parcela.

    Fórmula verificada contra a tabela oficial Intelbras (base R$750,00):
        valor_com_acrescimo = valor_base / (1 - percentual/100)
        valor_da_parcela = valor_com_acrescimo / parcelas
    NÃO é `valor_base * (1 + percentual/100)` — essa conta dá um valor
    menor e não bate com a planilha de referência.
    """
    if not valor_base or valor_base <= 0:
        return []

    taxas = TaxaCartao.objects.filter(
        forma=TaxaCartao.FORMA_CREDITO, bandeira=bandeira
    ).order_by("parcelas")

    resultado = []
    for taxa in taxas:
        fator = Decimal("1") - (taxa.percentual / Decimal("100"))
        if fator <= 0:
            continue  # taxa >= 100% não faz sentido matematicamente, ignora
        valor_com_acrescimo = valor_base / fator
        valor_parcela = valor_com_acrescimo / taxa.parcelas
        resultado.append(
            {
                "parcelas": taxa.parcelas,
                "percentual": taxa.percentual,
                "valor_total": valor_com_acrescimo.quantize(Decimal("0.01")),
                "valor_parcela": valor_parcela.quantize(Decimal("0.01")),
            }
        )
    return resultado


def campo_fk(equipamento: object) -> str:
    """Retorna o nome do campo FK no PrecoEquipamentoSolar para o tipo de equipamento."""
    if isinstance(equipamento, ModuloFotovoltaico):
        return "modulo"
    if isinstance(equipamento, Inversor):
        return "inversor"
    if isinstance(equipamento, EstruturaFixacao):
        return "estrutura"
    return "material"
