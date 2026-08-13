"""Helpers internos do app solar — usados por propostas, catálogo e preços."""

import math
from decimal import Decimal, InvalidOperation

from ..models import (
    EstruturaFixacao,
    Inversor,
    ModuloFotovoltaico,
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


def campo_fk(equipamento: object) -> str:
    """Retorna o nome do campo FK no PrecoEquipamentoSolar para o tipo de equipamento."""
    if isinstance(equipamento, ModuloFotovoltaico):
        return "modulo"
    if isinstance(equipamento, Inversor):
        return "inversor"
    if isinstance(equipamento, EstruturaFixacao):
        return "estrutura"
    return "material"
