"""Helpers internos do app solar — usados por propostas, catálogo e preços."""

import math

from ..models import (
    EstruturaFixacao,
    Inversor,
    MateriaisEletricos,
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


def campo_fk(equipamento: object) -> str:
    """Retorna o nome do campo FK no PrecoEquipamentoSolar para o tipo de equipamento."""
    if isinstance(equipamento, ModuloFotovoltaico):
        return "modulo"
    if isinstance(equipamento, Inversor):
        return "inversor"
    if isinstance(equipamento, EstruturaFixacao):
        return "estrutura"
    return "material"
