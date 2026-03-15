# Domínio Solar — ERP Optimus (Tocantins/BR)

## Dados climáticos — Tocantins

| Parâmetro | Valor |
|-----------|-------|
| HSP média (Horas de Sol Pleno) | **5,2 h/dia** |
| Irradiação média | ~5,2 kWh/m²/dia |
| Perda do sistema (fator de eficiência) | 0,75 a 0,80 (típico) |

> Referência: CRESESB / Atlas Brasileiro de Energia Solar para região de Palmas/TO.

---

## Cálculo de dimensionamento (kWp)

```python
# Fórmula básica
# kWp = consumo_mensal_kwh / (HSP * dias_mes * fator_eficiencia)

HSP_TOCANTINS = 5.2          # horas de sol pleno
FATOR_EFICIENCIA = 0.77      # perdas típicas do sistema
DIAS_MES = 30

def calcular_kwp(consumo_mensal_kwh: float) -> float:
    """Retorna potência necessária do sistema em kWp."""
    return consumo_mensal_kwh / (HSP_TOCANTINS * DIAS_MES * FATOR_EFICIENCIA)


def calcular_paineis(kwp_total: float, potencia_painel_wp: int = 550) -> int:
    """Retorna número de painéis necessários (arredondado para cima)."""
    import math
    kwp_painel = potencia_painel_wp / 1000
    return math.ceil(kwp_total / kwp_painel)


def calcular_geracao_mensal(kwp_instalado: float) -> float:
    """Retorna estimativa de geração mensal em kWh."""
    return kwp_instalado * HSP_TOCANTINS * DIAS_MES * FATOR_EFICIENCIA
```

---

## Payback simples

```python
def calcular_payback(
    valor_sistema: float,
    economia_mensal_kwh: float,
    tarifa_kwh: float,
) -> float:
    """Retorna payback em anos."""
    economia_mensal_reais = economia_mensal_kwh * tarifa_kwh
    if economia_mensal_reais <= 0:
        return float("inf")
    return (valor_sistema / economia_mensal_reais) / 12
```

---

## Fluxo de uma proposta solar

```
1. Dimensionamento
   └── Entrada: consumo médio mensal (kWh), tarifa local (R$/kWh)
   └── Saída: kWp, número de painéis, geração estimada, payback

2. Proposta Comercial
   └── Itens: painéis, inversor, estrutura, cabeamento, mão de obra
   └── Aprovação pelo cliente → gera OS

3. Ordem de Serviço (instalação)
   └── Técnico responsável, data, checklist, fotos, assinatura cliente

4. Homologação ANEEL / Distribuidora
   └── Após instalação concluída
   └── Etapas: vistoria distribuidora → parecer de acesso → conexão à rede
   └── Prazo típico Energisa TO: 30–90 dias

5. Pós-venda
   └── Monitoramento, chamados de manutenção, garantia
```

---

## Campos esperados no model PropostaSolar

```python
# Referência de campos para solar/models.py
consumo_medio_kwh = models.DecimalField("consumo médio mensal (kWh)", max_digits=8, decimal_places=2)
kwp_calculado = models.DecimalField("potência calculada (kWp)", max_digits=6, decimal_places=2)
num_paineis = models.IntegerField("número de painéis")
potencia_painel_wp = models.IntegerField("potência do painel (Wp)", default=550)
geracao_estimada_kwh = models.DecimalField("geração estimada mensal (kWh)", max_digits=8, decimal_places=2)
valor_total = models.DecimalField("valor total (R$)", max_digits=10, decimal_places=2)
payback_anos = models.DecimalField("payback estimado (anos)", max_digits=4, decimal_places=1)
tarifa_kwh = models.DecimalField("tarifa kWh (R$)", max_digits=6, decimal_places=4)
```

---

## Observações regionais

- Distribuidora local: **Energisa Tocantins**
- Modalidade mais comum: **Geração na própria unidade** (microgeração < 75 kWp)
- Resolução normativa ANEEL vigente: **REN 1000/2021** (atualizar se mudar)
- ICMS sobre energia injetada: verificar legislação estadual TO vigente
