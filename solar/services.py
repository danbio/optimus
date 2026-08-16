"""Cálculo de retorno financeiro de sistemas de geração distribuída (GD).

Implementa as regras reais de compensação da Lei 14.300/2022 — não a conta
ingênua `geração × tarifa`, que superestima a economia porque ignora tudo
que a GD **não** compensa. Ver `.claude/skills/solar-domain.md` §8.

Verificado contra uma fatura real da Energisa Tocantins (B1 residencial
monofásico, agosto/2026) — ver `RetornoGDContraFaturaRealTests`.
"""

from decimal import ROUND_HALF_UP, Decimal

# Percentual da TUSD Fio B cobrado sobre a energia compensada, por ano
# (Lei 14.300/2022, art. 27). Antes de 2023 não havia cobrança; a partir de
# 2029 a metodologia será redefinida pela ANEEL (art. 28) — até lá assumimos
# cobrança integral, que é a hipótese conservadora para uma proposta.
FIO_B_PERCENTUAL_POR_ANO = {
    2023: Decimal("0.15"),
    2024: Decimal("0.30"),
    2025: Decimal("0.45"),
    2026: Decimal("0.60"),
    2027: Decimal("0.75"),
    2028: Decimal("0.90"),
}

# Consumo mínimo faturado independentemente da geração (REN ANEEL 414/2010,
# art. 98). O cliente com solar nunca zera a conta por causa disso.
CUSTO_DISPONIBILIDADE_KWH = {
    "monofasico": 30,
    "bifasico": 50,
    "trifasico": 100,
}

# Reajuste tarifário anual — média histórica ANEEL. Decisão do usuário:
# constante, não parâmetro por proposta (ver DIARIO 2026-08-15).
REAJUSTE_TARIFARIO_ANUAL = Decimal("0.07")


def aplicar_tributos(
    tarifa_base: Decimal,
    icms_pct: Decimal,
    pis_cofins_pct: Decimal,
) -> Decimal:
    """Converte a tarifa publicada pela ANEEL (sem tributos) na tarifa que
    aparece na fatura do cliente.

    ICMS e PIS/COFINS incidem "por dentro": cada um divide a base pelo seu
    complemento, em cascata.

        tarifa_com_tributos = base / (1 − PIS/COFINS) / (1 − ICMS)

    Verificado contra duas faturas reais da Energisa TO, erro de 0,0005%:
        0,930220 / 0,9075 / 0,80 = 1,281295  (fatura: 1,281290)
        1,006060 / 0,9075 / 0,80 = 1,385758  (fatura: 1,385750)
    """
    fator_pis_cofins = Decimal("1") - (pis_cofins_pct / Decimal("100"))
    fator_icms = Decimal("1") - (icms_pct / Decimal("100"))
    if fator_pis_cofins <= 0 or fator_icms <= 0:
        return tarifa_base
    return tarifa_base / fator_pis_cofins / fator_icms

# Perda de eficiência dos módulos por ano. 0,5%/ano é o patamar coberto pela
# garantia de desempenho de 25 anos dos fabricantes do catálogo.
DEGRADACAO_ANUAL_MODULO = Decimal("0.005")

ANOS_PROJECAO_PADRAO = 25

_CENTAVO = Decimal("0.01")


def percentual_fio_b(ano: int) -> Decimal:
    """Fração da TUSD Fio B cobrada sobre a energia compensada no ano.

    Retorna 0 antes de 2023 e 1 (integral) de 2029 em diante.
    """
    if ano < 2023:
        return Decimal("0")
    if ano >= 2029:
        return Decimal("1")
    return FIO_B_PERCENTUAL_POR_ANO[ano]


def tarifa_compensacao(tarifa_injecao_ct: Decimal, fio_b_base: Decimal, ano: int) -> Decimal:
    """Quanto cada kWh injetado efetivamente abate da conta.

    Duas coisas distintas reduzem o valor do kWh injetado, e confundi-las
    já custou um erro de 29% nesta base de código:

    1. **Tributo** — o crédito da injeção recebe ICMS menor que o consumo,
       então `tarifa_injecao_ct` já nasce abaixo da tarifa de consumo. Isso
       vale para **todo** consumidor de GD, inclusive os antigos (GD1).
    2. **Fio B** (Lei 14.300/2022) — cobrança à parte, isenta de tributo,
       que só atinge quem entrou na regra nova (GDII). Na fatura é a linha
       "Ajuste GDII - TRF Reduzida".

    A diferença entre as linhas "Consumo" e "Energia Atv Injetada" da fatura
    é o item 1, **não** o Fio B — a fatura de um GD1, que não paga Fio B
    nenhum, tem exatamente a mesma diferença.
    """
    return tarifa_injecao_ct - (fio_b_base * percentual_fio_b(ano))


def custo_disponibilidade_kwh(tipo_ligacao: str) -> int:
    return CUSTO_DISPONIBILIDADE_KWH.get(tipo_ligacao, 30)


def formatar_prazo(anos: Decimal | None) -> str:
    """Formata um prazo em anos como "3 anos e 2 meses".

    Payback em decimal ("1,1 anos") não diz nada a um cliente — ele pensa
    em meses. Arredonda para o mês mais próximo.
    """
    if anos is None:
        return "—"

    total_meses = int((anos * 12).to_integral_value(rounding=ROUND_HALF_UP))
    if total_meses <= 0:
        return "menos de 1 mês"

    quantidade_anos, meses = divmod(total_meses, 12)
    partes = []
    if quantidade_anos:
        partes.append(f"{quantidade_anos} ano" if quantidade_anos == 1 else f"{quantidade_anos} anos")
    if meses:
        partes.append(f"{meses} mês" if meses == 1 else f"{meses} meses")
    return " e ".join(partes)


def grafico_economia_anual(
    retorno: dict,
    largura: float = 680.0,
    altura: float = 170.0,
) -> dict | None:
    """Monta a geometria de um gráfico de barras da economia ano a ano.

    Devolve caminhos SVG prontos em vez de deixar o template fazer conta —
    o motor de template do Django não faz aritmética, e o PDF é gerado por
    `window.print()` sem nenhuma biblioteca de gráfico (ver skill
    solar-domain §12).

    Série única (economia anual), então não há legenda: o título da seção
    já diz o que a barra representa. O ano do payback vira uma linha
    tracejada — marcar por cor exigiria uma segunda tonalidade, e o
    verde-claro da marca reprova em contraste (1,91:1) sobre branco.

    ⚠️ Todo número que vai virar atributo de SVG sai daqui **como string**.
    O projeto roda com `USE_THOUSAND_SEPARATOR=True` (moeda em pt-BR), e o
    template localiza qualquer número que receba: `680.0` viraria `680,0` e
    o ano `2026` viraria `2.026`, quebrando o `viewBox` e os rótulos. Só
    `economia_ano` continua Decimal, porque esse *deve* ser localizado.
    """
    fluxo = retorno.get("fluxo_anual") if retorno else None
    if not fluxo:
        return None

    maximo = max(float(f["economia_ano"]) for f in fluxo)
    if maximo <= 0:
        return None

    total = len(fluxo)
    espacamento = 2.0  # respiro de 2px entre barras, como manda a spec de marcas
    passo = largura / total
    largura_barra = max(passo - espacamento, 1.0)

    margem_topo = 22.0  # espaço para o rótulo do marcador de payback
    margem_base = 18.0  # espaço para os rótulos de ano

    barras = []
    for indice, ponto in enumerate(fluxo):
        altura_barra = (float(ponto["economia_ano"]) / maximo) * altura
        x = indice * passo
        y = altura - altura_barra
        # Só arredonda a ponta enquanto couber — barra baixa com raio grande
        # vira um desenho torto.
        raio = min(4.0, largura_barra / 2, altura_barra / 2) if altura_barra > 0 else 0.0
        direita = x + largura_barra
        # Rótulo da primeira e da última barra encosta na borda do viewBox se
        # for centralizado — ancora no canto pra não sair cortado.
        if indice == 0:
            ancora, rotulo_x = "start", 0.0
        elif indice == total - 1:
            ancora, rotulo_x = "end", largura
        else:
            ancora, rotulo_x = "middle", x + largura_barra / 2

        barras.append(
            {
                "ano": str(ponto["ano"]),
                "economia_ano": ponto["economia_ano"],
                "ancora": ancora,
                "rotulo_x": f"{rotulo_x:.2f}",
                "centro_x": f"{x + largura_barra / 2:.2f}",
                "path": (
                    f"M{x:.2f},{altura:.2f} "
                    f"L{x:.2f},{y + raio:.2f} "
                    f"Q{x:.2f},{y:.2f} {x + raio:.2f},{y:.2f} "
                    f"L{direita - raio:.2f},{y:.2f} "
                    f"Q{direita:.2f},{y:.2f} {direita:.2f},{y + raio:.2f} "
                    f"L{direita:.2f},{altura:.2f} Z"
                ),
                # Rótulo direto só nas pontas: 25 números no gráfico viram ruído.
                "rotulo_valor": indice in (0, total - 1),
                "rotulo_ano": indice % 5 == 0 or indice == total - 1,
                "rotulo_valor_y": f"{y - 6:.2f}",
            }
        )

    payback = retorno.get("payback_anos")
    payback_x = float(payback) * passo if payback is not None else None
    # Marcador perto da borda direita joga o texto pra fora; nesse caso o
    # rótulo vai pra esquerda da linha tracejada.
    if payback_x is not None and payback_x > largura * 0.75:
        payback_ancora, payback_rotulo_x = "end", payback_x - 4
    else:
        payback_ancora, payback_rotulo_x = "start", payback_x + 4 if payback_x is not None else 0.0

    return {
        "view_box": f"0 {-margem_topo:.0f} {largura:.0f} {altura + margem_topo + margem_base:.0f}",
        "largura": f"{largura:.0f}",
        "base_y": f"{altura:.0f}",
        "ano_y": f"{altura + 14:.0f}",
        "marcador_topo_y": f"{-margem_topo + 6:.0f}",
        "marcador_linha_y": f"{-margem_topo + 8:.0f}",
        "barras": barras,
        "payback_x": f"{payback_x:.2f}" if payback_x is not None else None,
        "payback_rotulo_x": f"{payback_rotulo_x:.2f}" if payback_x is not None else None,
        "payback_ancora": payback_ancora,
        "payback_anos": payback,
    }


def grafico_geracao_mensal(
    serie: list[dict] | None,
    largura: float = 680.0,
    altura: float = 150.0,
) -> dict | None:
    """Geometria do gráfico de geração mês a mês.

    Mesmo padrão de `grafico_economia_anual`: caminhos SVG prontos, números
    já como string (o template localizaria e quebraria o SVG — ver
    AGENTS.md). Todo mês leva rótulo, porque são só 12 barras e o valor de
    cada mês é justamente o que interessa mostrar.
    """
    if not serie:
        return None

    valores = [float(item["kwh"]) for item in serie]
    maximo = max(valores)
    if maximo <= 0:
        return None

    total = len(serie)
    espacamento = 4.0
    passo = largura / total
    largura_barra = max(passo - espacamento, 1.0)
    media = sum(valores) / total

    barras = []
    for indice, item in enumerate(serie):
        altura_barra = (float(item["kwh"]) / maximo) * altura
        x = indice * passo
        y = altura - altura_barra
        raio = min(4.0, largura_barra / 2, altura_barra / 2) if altura_barra > 0 else 0.0
        direita = x + largura_barra
        barras.append(
            {
                "mes": item["nome"],
                "kwh": item["kwh"],
                "hsp": item["hsp"],
                "centro_x": f"{x + largura_barra / 2:.2f}",
                "rotulo_y": f"{y - 6:.2f}",
                "path": (
                    f"M{x:.2f},{altura:.2f} "
                    f"L{x:.2f},{y + raio:.2f} "
                    f"Q{x:.2f},{y:.2f} {x + raio:.2f},{y:.2f} "
                    f"L{direita - raio:.2f},{y:.2f} "
                    f"Q{direita:.2f},{y:.2f} {direita:.2f},{y + raio:.2f} "
                    f"L{direita:.2f},{altura:.2f} Z"
                ),
            }
        )

    margem_topo = 16.0
    margem_base = 18.0
    y_media = altura - (media / maximo) * altura

    return {
        "view_box": f"0 {-margem_topo:.0f} {largura:.0f} {altura + margem_topo + margem_base:.0f}",
        "largura": f"{largura:.0f}",
        "base_y": f"{altura:.0f}",
        "mes_y": f"{altura + 13:.0f}",
        "media_y": f"{y_media:.2f}",
        "media_rotulo_y": f"{y_media - 4:.2f}",
        "media_kwh": int(round(media)),
        "barras": barras,
    }


def projetar_retorno(
    *,
    valor_investimento: Decimal,
    geracao_mensal_kwh: Decimal,
    consumo_mensal_kwh: Decimal,
    tarifa_consumo_kwh: Decimal,
    tarifa_injecao_kwh: Decimal,
    fio_b_kwh: Decimal,
    tipo_ligacao: str,
    cosip_mensal: Decimal,
    ano_base: int,
    autoconsumo_simultaneo_pct: Decimal = Decimal("0"),
    anos: int = ANOS_PROJECAO_PADRAO,
) -> dict | None:
    """Projeta a economia ano a ano de um sistema de GD.

    Retorna None quando falta dado essencial (tarifa ou geração) — nunca
    inventa número para preencher a proposta.

    A geração se divide em duas parcelas com valor econômico **diferente**:

    - **Autoconsumo simultâneo**: consumido no mesmo instante em que é
      gerado, nunca passa pelo medidor de injeção. Não sofre Fio B nem
      qualquer regra de compensação — economiza a tarifa cheia.
    - **Excedente injetado**: vai para a rede e volta como crédito, já
      descontado do Fio B da Lei 14.300 — economiza a tarifa de
      compensação, que é menor.

    A conta modelada é linha a linha a mesma da fatura:

        conta = consumo_da_rede × tarifa_consumo        ("Consumo em kWh")
              − compensada      × tarifa_injecao        ("Energia Atv Injetada")
              + compensada      × ajuste_fio_b          ("Ajuste GDII", só GDII)
              + COSIP                                   ("Contrib de Ilum Pub")

    O custo de disponibilidade (30/50/100 kWh conforme a ligação) entra como
    **piso da conta de energia**, não como teto da compensação — é assim que
    a fatura real se comporta.

    `tarifa_consumo_kwh` e `tarifa_injecao_kwh` já vêm **com tributos**;
    `fio_b_kwh` vem **sem tributos** e a 100% — o percentual do ano é
    aplicado aqui dentro, ano a ano.
    """
    if not tarifa_consumo_kwh or tarifa_consumo_kwh <= 0:
        return None
    if not geracao_mensal_kwh or geracao_mensal_kwh <= 0:
        return None
    if not consumo_mensal_kwh or consumo_mensal_kwh <= 0:
        return None

    tarifa_injecao_kwh = tarifa_injecao_kwh or tarifa_consumo_kwh
    fio_b_kwh = fio_b_kwh or Decimal("0")
    cosip_mensal = cosip_mensal or Decimal("0")
    minimo_kwh = Decimal(custo_disponibilidade_kwh(tipo_ligacao))
    fracao_simultanea = (autoconsumo_simultaneo_pct or Decimal("0")) / Decimal("100")

    fluxo: list[dict] = []
    acumulado = Decimal("0")
    payback_anos: Decimal | None = None

    for indice in range(anos):
        ano_calendario = ano_base + indice
        correcao = (Decimal("1") + REAJUSTE_TARIFARIO_ANUAL) ** indice
        degradacao = (Decimal("1") - DEGRADACAO_ANUAL_MODULO) ** indice

        tarifa_ano = tarifa_consumo_kwh * correcao
        tarifa_injecao_ano = tarifa_injecao_kwh * correcao
        fio_b_ano = fio_b_kwh * correcao
        tarifa_comp = tarifa_compensacao(tarifa_injecao_ano, fio_b_ano, ano_calendario)

        geracao_ano = geracao_mensal_kwh * degradacao

        # Parcela consumida na hora: não pode passar do consumo total.
        autoconsumo = min(geracao_ano * fracao_simultanea, consumo_mensal_kwh)
        injetada = geracao_ano - autoconsumo

        # O excedente só abate o que ainda vem da rede. Gerar além disso
        # vira crédito (válido 60 meses), que esta projeção não conta como
        # economia.
        consumo_rede = consumo_mensal_kwh - autoconsumo
        compensada = min(injetada, consumo_rede)

        # Conta de energia montada linha a linha, como na fatura.
        ajuste = fio_b_ano * percentual_fio_b(ano_calendario)
        valor_energia = (
            consumo_rede * tarifa_ano
            - compensada * tarifa_injecao_ano
            + compensada * ajuste
        )

        # Custo de disponibilidade é **piso da conta**, não teto da
        # compensação: a fatura real compensa o consumo inteiro e só depois
        # garante o mínimo. Modelar como teto subestimava a economia em um
        # mês inteiro de mínimo.
        valor_energia = max(valor_energia, minimo_kwh * tarifa_ano)

        economia_mes = (consumo_mensal_kwh * tarifa_ano) - valor_energia
        economia_ano = (economia_mes * 12).quantize(_CENTAVO)

        anterior = acumulado
        acumulado += economia_ano

        if payback_anos is None and acumulado >= valor_investimento:
            # Interpola dentro do ano para não arredondar o payback para cima.
            falta = valor_investimento - anterior
            fracao = (falta / economia_ano) if economia_ano > 0 else Decimal("0")
            # Precisão de 3 casas: 0,1 ano seria uma granularidade de ~1,2
            # mês, grossa demais pra formatar "X anos e Y meses".
            payback_anos = (Decimal(indice) + fracao).quantize(Decimal("0.001"))

        fluxo.append(
            {
                "indice": indice,
                "ano": ano_calendario,
                "percentual_fio_b": percentual_fio_b(ano_calendario) * 100,
                "geracao_mensal_kwh": geracao_ano.quantize(_CENTAVO),
                "autoconsumo_mensal_kwh": autoconsumo.quantize(_CENTAVO),
                "compensada_mensal_kwh": compensada.quantize(_CENTAVO),
                "tarifa_compensacao": tarifa_comp.quantize(Decimal("0.000001")),
                "economia_mensal": economia_mes.quantize(_CENTAVO),
                "economia_ano": economia_ano,
                "acumulado": acumulado.quantize(_CENTAVO),
            }
        )

    primeiro = fluxo[0]
    conta_atual = (consumo_mensal_kwh * tarifa_consumo_kwh + cosip_mensal).quantize(_CENTAVO)
    conta_estimada = (conta_atual - primeiro["economia_mensal"]).quantize(_CENTAVO)

    return {
        "economia_mensal": primeiro["economia_mensal"],
        "conta_atual": conta_atual,
        "conta_estimada": conta_estimada,
        "payback_anos": payback_anos,
        "payback_texto": formatar_prazo(payback_anos),
        "economia_total": acumulado.quantize(_CENTAVO),
        "autoconsumo_mensal_kwh": primeiro["autoconsumo_mensal_kwh"],
        "compensada_mensal_kwh": primeiro["compensada_mensal_kwh"],
        "custo_disponibilidade_kwh": int(minimo_kwh),
        "percentual_fio_b_atual": percentual_fio_b(ano_base) * 100,
        "fluxo_anual": fluxo,
        "anos": anos,
    }
