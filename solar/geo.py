"""Dados geográficos e de irradiação solar, de APIs públicas.

Duas fontes, ambas gratuitas e sem chave:

- **IBGE** (`servicodados.ibge.gov.br`) — lista de municípios e malha
  geográfica, de onde tiramos o centroide de cada um.
- **NASA POWER** (`power.larc.nasa.gov`) — climatologia de irradiação
  solar por coordenada.

⚠️ **HSP e irradiação diária são o mesmo número.** O parâmetro
`ALLSKY_SFC_SW_DWN` vem em kWh/m²/dia; como a irradiância de referência é
1 kW/m², dividir um pelo outro dá horas — daí "horas de sol pleno". Não é
conversão, é a mesma grandeza em outra leitura.

Validação: para Gurupi/TO a NASA devolve 5,51 kWh/m²/dia de média anual,
contra o padrão histórico de 5,50 que o ERP já usava (CRESESB).
"""

import gzip
import json
import urllib.request
from decimal import Decimal

IBGE_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades"
IBGE_MALHAS = "https://servicodados.ibge.gov.br/api/v3/malhas"
NASA_POWER = "https://power.larc.nasa.gov/api/temporal/climatology/point"

TIMEOUT_PADRAO = 180

# A NASA devolve os meses por sigla em inglês, nesta ordem.
_MESES_NASA = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


class ErroGeo(RuntimeError):
    """Falha ao consultar IBGE ou NASA POWER."""


def _get_json(url: str) -> dict | list:
    """GET + parse de JSON, tolerante a gzip.

    O IBGE às vezes devolve o corpo comprimido **mesmo pedindo
    `Accept-Encoding: identity`** e sem marcar `Content-Encoding`, o que faz
    o parser quebrar no byte 0x8b. Por isso a checagem é pelo número mágico
    do gzip, não pelo cabeçalho.
    """
    requisicao = urllib.request.Request(url, headers={"User-Agent": "optimus-erp"})
    try:
        with urllib.request.urlopen(requisicao, timeout=TIMEOUT_PADRAO) as resposta:
            corpo = resposta.read()
        if corpo[:2] == b"\x1f\x8b":
            corpo = gzip.decompress(corpo)
        return json.loads(corpo.decode("utf-8"))
    except Exception as erro:  # noqa: BLE001 — rede: qualquer falha vira ErroGeo
        raise ErroGeo(f"falha ao consultar {url}: {erro}") from erro


def listar_municipios(uf: str) -> list[dict]:
    """Municípios de uma UF: código IBGE e nome. Uma requisição."""
    dados = _get_json(f"{IBGE_LOCALIDADES}/estados/{uf.upper()}/municipios")
    return [{"codigo_ibge": int(m["id"]), "nome": m["nome"]} for m in dados]


def centroides(uf: str) -> dict[int, tuple[Decimal, Decimal]]:
    """Centroide aproximado de cada município da UF. Uma requisição.

    O centroide é a média dos vértices do polígono — não é o centro
    geométrico exato, mas a NASA POWER trabalha em células de 1° (~111 km)
    para dados solares, então a diferença não muda o resultado. Para Gurupi
    a média cai a ~25 km do centro urbano e devolve a mesma irradiação.
    """
    url = f"{IBGE_MALHAS}/estados/{uf.upper()}?formato=application/vnd.geo+json&intrarregiao=municipio"
    colecao = _get_json(url)

    resultado: dict[int, tuple[Decimal, Decimal]] = {}
    for feature in colecao.get("features", []):
        codigo = feature.get("properties", {}).get("codarea")
        if not codigo:
            continue
        pontos = list(_pontos(feature["geometry"]["coordinates"]))
        if not pontos:
            continue
        longitude = sum(p[0] for p in pontos) / len(pontos)
        latitude = sum(p[1] for p in pontos) / len(pontos)
        resultado[int(codigo)] = (
            Decimal(str(round(latitude, 6))),
            Decimal(str(round(longitude, 6))),
        )
    return resultado


def _pontos(coordenadas):
    """Achata a estrutura aninhada de um Polygon/MultiPolygon em pares."""
    if coordenadas and isinstance(coordenadas[0], (int, float)):
        yield coordenadas
        return
    for item in coordenadas:
        yield from _pontos(item)


def hsp_mensal(latitude: Decimal, longitude: Decimal) -> dict:
    """Irradiação média diária por mês (= HSP), da climatologia NASA POWER.

    Devolve `{"mensal": {1: Decimal, ..., 12: Decimal}, "anual": Decimal}`.
    A climatologia é uma média de longo prazo — não muda de ano para ano,
    então o resultado pode ser cacheado indefinidamente.
    """
    url = (
        f"{NASA_POWER}?parameters=ALLSKY_SFC_SW_DWN&community=RE"
        f"&latitude={latitude}&longitude={longitude}&format=JSON"
    )
    dados = _get_json(url)

    try:
        valores = dados["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    except (KeyError, TypeError) as erro:
        raise ErroGeo(f"resposta inesperada da NASA POWER: {dados!r}") from erro

    mensal = {}
    for indice, sigla in enumerate(_MESES_NASA, start=1):
        bruto = valores.get(sigla)
        if bruto is None:
            raise ErroGeo(f"NASA POWER não devolveu o mês {sigla}")
        mensal[indice] = Decimal(str(round(float(bruto), 2)))

    anual = valores.get("ANN")
    if anual is None:
        anual = sum(mensal.values()) / Decimal("12")
    else:
        anual = Decimal(str(round(float(anual), 2)))

    return {"mensal": mensal, "anual": anual}
