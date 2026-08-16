"""Cliente do portal de dados abertos da ANEEL (CKAN).

API pública, sem chave e sem cadastro. Só faz leitura.

O dataset relevante é `componentes-tarifarias`, que publica a tarifa
**decomposta por componente** — é lá que está o `TUSD_FioB` separado, que o
dataset consolidado de tarifas não traz. Os valores saem em **R$/MWh e sem
tributos**; quem faz o gross-up é `solar/services.py::aplicar_tributos`.

Validado contra fatura real da Energisa TO: TUSD 683,43 + TE 322,63 =
1006,06 R$/MWh, exatamente a coluna "Tarifa Unit" da fatura de agosto/2026.
"""

import json
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation

BASE_URL = "https://dadosabertos.aneel.gov.br/api/3/action"
DATASET_COMPONENTES = "componentes-tarifarias"
TIMEOUT_PADRAO = 120

# Componentes que interessam para a análise de GD. O resto da decomposição
# (encargos, PROINFA, CDE...) já está embutido no total.
COMPONENTE_TUSD = "TUSD"
COMPONENTE_TE = "TE"
COMPONENTE_FIO_B = "TUSD_FioB"


class ErroANEEL(RuntimeError):
    """Falha ao consultar o portal de dados abertos."""


def _get(acao: str, **params) -> dict:
    url = f"{BASE_URL}/{acao}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_PADRAO) as resposta:
            corpo = json.load(resposta)
    except Exception as erro:  # noqa: BLE001 — rede: qualquer falha vira ErroANEEL
        raise ErroANEEL(f"falha ao consultar {acao}: {erro}") from erro

    if not corpo.get("success"):
        raise ErroANEEL(f"resposta sem sucesso em {acao}: {corpo!r}")
    return corpo["result"]


def resource_id_do_ano(ano: int) -> str:
    """Descobre o resource_id do CSV de um ano.

    Resolvido em tempo de execução em vez de fixado no código: a ANEEL cria
    um recurso novo a cada ano, com UUID novo.
    """
    pacote = _get("package_show", id=DATASET_COMPONENTES)
    alvo = f"componentes-tarifarias-{ano}.csv"
    for recurso in pacote.get("resources", []):
        if recurso.get("name") == alvo:
            return recurso["id"]
    raise ErroANEEL(f"a ANEEL não publica {alvo}")


def _decimal(valor: str) -> Decimal | None:
    """A ANEEL usa vírgula decimal e às vezes devolve string vazia."""
    if valor is None:
        return None
    texto = str(valor).strip().replace(".", "").replace(",", ".")
    if not texto:
        return None
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def buscar_componentes(
    resource_id: str,
    cnpj: str,
    subgrupo: str = "B1",
    modalidade: str = "Convencional",
    limite: int = 10000,
) -> list[dict]:
    """Baixa os componentes tarifários de uma distribuidora.

    Filtra por CNPJ (não pela sigla): a sigla varia de grafia entre anos, o
    CNPJ não.
    """
    filtros = {
        "NumCPFCNPJ": cnpj,
        "DscSubGrupoTarifario": subgrupo,
        "DscModalidadeTarifaria": modalidade,
    }
    resultado = _get(
        "datastore_search",
        resource_id=resource_id,
        filters=json.dumps(filtros),
        limit=limite,
    )
    return resultado.get("records", [])


def consolidar_tarifas(registros: list[dict]) -> dict[tuple, dict]:
    """Agrupa os componentes soltos em uma tarifa por vigência/subclasse.

    A ANEEL devolve uma linha por componente (TUSD, TE, TUSD_FioB, dezenas
    de encargos...). Aqui viram um dicionário por (vigência, subclasse) com
    só os três que a análise de GD usa.

    Considera apenas `DscBaseTarifaria == "Tarifa de Aplicação"` — é a
    tarifa efetivamente cobrada, e é ela que bate com a fatura. "Base
    Econômica" e "CVA" são outras visões do mesmo período.
    """
    consolidado: dict[tuple, dict] = {}

    for registro in registros:
        base = (registro.get("DscBaseTarifaria") or "").strip()
        if not base.lower().startswith("tarifa de aplica"):
            continue

        componente = (registro.get("DscComponenteTarifario") or "").strip()
        if componente not in (COMPONENTE_TUSD, COMPONENTE_TE, COMPONENTE_FIO_B):
            continue

        valor = _decimal(registro.get("VlrComponenteTarifario"))
        if valor is None:
            continue

        inicio = (registro.get("DatInicioVigencia") or "")[:10]
        fim = (registro.get("DatFimVigencia") or "")[:10]
        subclasse = (registro.get("DscSubClasseConsumidor") or "").strip()
        if not inicio or not subclasse:
            continue

        chave = (inicio, subclasse)
        linha = consolidado.setdefault(
            chave,
            {
                "vigencia_inicio": inicio,
                "vigencia_fim": fim or None,
                "subclasse": subclasse,
                "subgrupo": (registro.get("DscSubGrupoTarifario") or "B1").strip(),
                "modalidade": (registro.get("DscModalidadeTarifaria") or "Convencional").strip(),
            },
        )
        if componente == COMPONENTE_TUSD:
            linha["vlr_tusd"] = valor
        elif componente == COMPONENTE_TE:
            linha["vlr_te"] = valor
        else:
            linha["vlr_tusd_fio_b"] = valor

    # Sem TUSD ou TE a linha não serve pra calcular tarifa nenhuma.
    return {
        chave: linha
        for chave, linha in consolidado.items()
        if "vlr_tusd" in linha and "vlr_te" in linha
    }
