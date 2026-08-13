# Domínio Solar — ERP Optimus (Tocantins/BR)

> ⚠️ Esta skill reflete os models **reais** do app `solar`. Última revisão: 2026-08-13.

---

## 1. Dados climáticos — Tocantins

| Parâmetro                     | Valor               |
| ----------------------------- | ------------------- |
| HSP padrão (default no model) | **5,50 h/dia**      |
| Irradiação média              | ~5,2–5,5 kWh/m²/dia |
| Fator de eficiência padrão    | 0,75 (configurável) |

> Referência: CRESESB / Atlas Brasileiro de Energia Solar, Palmas/TO.
> **Atenção:** O model usa `hsp=5.50` como default — não usar 5,2 de fontes externas.

---

## 2. Models reais do app `solar`

### `ModuloFotovoltaico` (herda `BaseModel`)

```python
fabricante          # CharField(100)
modelo              # CharField(100)
potencia_wp         # IntegerField
eficiencia          # DecimalField(5,2) — %
voc                 # DecimalField(6,2) — tensão circuito aberto (V)
isc                 # DecimalField(6,2) — corrente curto-circuito (A)
largura             # IntegerField — mm
altura              # IntegerField — mm
peso                # DecimalField(5,2) — kg
garantia_produto    # IntegerField — anos
garantia_desempenho # IntegerField — anos
ativo               # BooleanField (default=True)

# Property:
@property area_m2   # (largura * altura) / 1_000_000
```

---

### `Inversor` (herda `BaseModel`)

```python
fabricante         # CharField(100)
modelo             # CharField(100)
potencia_kw        # DecimalField(6,2)
tipo               # string | micro | hibrido
fase               # monofasico | trifasico
tensao_max_entrada # IntegerField — V
quantidade_mppt    # IntegerField
garantia           # IntegerField — anos
ativo              # BooleanField
```

---

### 2.1 Sugestão automática de inversor compatível

`solar/views/_helpers.py::inversores_compativeis(potencia_kwp, faixa_min_pct, faixa_max_pct)`

Regra: relação CC:CA — `potência do sistema (kWp) ÷ potência do inversor
(kW) × 100`. A faixa aceita **não é constante no código** — vem de
`Configuracao.atual()` (`inversor_sobrecarga_minima_pct` /
`_maxima_pct`, padrão 80%–135%, editável em `/configuracoes/`, só
Administrador). Retorna todos os inversores `ativo=True`, marcados
`compativel: bool`, ordenados com os compatíveis primeiro e, dentro de
cada grupo, pelos mais próximos de 100%.

Não valida fase (mono/trifásico) nem string sizing (Voc em série vs.
`tensao_max_entrada`) — o model `Cliente` não tem campo de fase, e o
sistema não modela configuração de string. Só a relação de potência.

```python
from decimal import Decimal
from configuracoes.models import Configuracao
from solar.views._helpers import inversores_compativeis

config = Configuracao.atual()
resultado = inversores_compativeis(
    Decimal("6.0"), config.inversor_sobrecarga_minima_pct, config.inversor_sobrecarga_maxima_pct
)
# [{"inversor": <Inversor>, "ratio_pct": Decimal("120.0"), "compativel": True}, ...]
```

---

### `EstruturaFixacao` (herda `BaseModel`)

```python
fabricante  # CharField(100)
modelo      # CharField(100)
tipo        # ceramico | metalico | fibrocimento | laje | solo
material    # aluminio | aco_galvanizado
descricao   # TextField (blank)
ativo       # BooleanField
```

---

### `MateriaisEletricos` (herda `BaseModel`)

```python
fabricante  # CharField(100)
modelo      # CharField(100) — referência
categoria   # cabo | disjuntor | eletroduto | dps | outros
unidade     # m (metro) | pc (peça)
descricao   # TextField (blank)
ativo       # BooleanField
```

---

### `PrecoEquipamentoSolar` (herda `BaseModel`)

Tabela de preços com vigência. Exatamente **um** dos quatro FKs deve estar preenchido.

```python
modulo      # FK → ModuloFotovoltaico (nullable, CASCADE)
inversor    # FK → Inversor (nullable, CASCADE)
estrutura   # FK → EstruturaFixacao (nullable, CASCADE)
material    # FK → MateriaisEletricos (nullable, CASCADE)

preco_custo   # DecimalField(10,2)
preco_venda   # DecimalField(10,2)
vigente_desde # DateField
vigente_ate   # DateField (null = ainda vigente)
criado_por    # FK → auth.User (PROTECT, editable=False)
```

**Constraint no banco:** `preco_solar_apenas_um_tipo` — exatamente um FK preenchido.

**Método de classe crítico:**

```python
PrecoEquipamentoSolar.get_preco_vigente(equipamento, data)
# Retorna o registro de preço vigente para o equipamento na data.
# Sempre usar ao criar ItemPropostaSolar — nunca capturar preço manualmente.
```

**Comportamento no Admin:** ao cadastrar novo preço, o Admin fecha automaticamente o anterior (`vigente_ate = hoje - 1 dia`).

---

### `ItemPropostaSolar`

Item com **snapshot imutável** do preço na data de criação. Nunca atualizar preços em itens já gravados.

```python
proposta    # FK → PropostaSolar (CASCADE, related_name="itens")

# Exatamente um dos quatro FKs deve estar preenchido (constraint no banco):
modulo      # FK → ModuloFotovoltaico (PROTECT, nullable)
inversor    # FK → Inversor (PROTECT, nullable)
estrutura   # FK → EstruturaFixacao (PROTECT, nullable)
material    # FK → MateriaisEletricos (PROTECT, nullable)

quantidade              # IntegerField (default=1)
preco_venda_snapshot    # DecimalField(10,2) — imutável após criação
preco_custo_snapshot    # DecimalField(10,2) — imutável após criação
data_referencia_preco   # DateField — data em que o preço foi capturado

# Property:
@property subtotal  # preco_venda_snapshot * quantidade
```

---

### `PropostaSolar` (herda `BaseModel`)

```python
# Identificação
numero    # auto-gerado "SOL-YYYYMM-0001" (único, imutável — gerado em save())
cliente   # FK → clientes.Cliente (PROTECT)
status    # rascunho | enviada | aprovada | concluida | cancelada

# Dimensionamento (todos configuráveis por proposta)
consumo_medio_kwh  # DecimalField(8,2) — kWh/mês
hsp                # DecimalField(4,2) — default=5.50
fator_eficiencia   # DecimalField(4,2) — default=0.75
potencia_kwp       # DecimalField(7,3) — calculado em form_valid()
quantidade_modulos # IntegerField — default=0, readonly no form
modulo             # FK → ModuloFotovoltaico (SET_NULL, nullable) — ref. dimensionamento

# Financeiro
valor_instalacao   # DecimalField(10,2) — default=0 (mão de obra + outros)
validade           # DateField — default: hoje + 30 dias
observacoes        # TextField (blank)

# Properties:
@property valor_equipamentos   # Sum(preco_venda_snapshot * quantidade) de todos os itens
@property valor_total          # valor_equipamentos + valor_instalacao
@property potencia_real_kwp    # quantidade_modulos * modulo.potencia_wp / 1000
@property area_total_m2        # quantidade_modulos * modulo.area_m2
```

---

## 3. Helpers — `solar/views/_helpers.py`

```python
from solar.views._helpers import calcular_kwp, calcular_quantidade_modulos, campo_fk

def calcular_kwp(consumo_kwh: float, hsp: float, fator: float) -> float:
    """Potência necessária em kWp. Resultado arredondado para 3 casas."""
    return round(consumo_kwh / (hsp * 30 * fator), 3)

def calcular_quantidade_modulos(kwp: float, modulo: ModuloFotovoltaico) -> int:
    """Módulos necessários — arredonda para cima (math.ceil)."""
    return math.ceil(kwp * 1000 / modulo.potencia_wp)

def campo_fk(equipamento: object) -> str:
    """Nome do campo FK em PrecoEquipamentoSolar para o tipo do equipamento."""
    # Retorna: "modulo" | "inversor" | "estrutura" | "material"
```

---

## 4. Endpoints HTMX — formulário de proposta

O form de criação/edição usa três endpoints HTMX para interatividade em tempo real:

```bash
GET /solar/dimensionar/
  → Parâmetros: consumo_medio_kwh, hsp, fator_eficiencia, modulo (pk)
  → Retorna: solar/_dimensionamento_preview.html
  → Mostra: kWp necessário, qtd sugerida, kWp real, área m², e a lista de
    inversores ativos compatíveis com o kWp real (ver seção 2.1 abaixo)

GET /solar/adicionar-item/?index=N
  → Retorna: solar/_item_proposta_row.html (linha do formset)
  → Sem parâmetros: linha vazia — botão "+ Adicionar item"
  → Com modulo=pk / inversor=pk / estrutura=pk / material=pk (+ quantidade
    opcional): linha pré-preenchida — botões "Usar este dimensionamento" e
    "Usar este inversor" no preview do dimensionamento

GET /solar/calcular-total/?itens-TOTAL_FORMS=N&itens-0-modulo=pk&itens-0-quantidade=2...
  → Retorna: texto puro "R$ 12.345,67"
  → Recalcula total dos equipamentos ao vivo sem salvar
```

**Prefixo do formset:** `itens` (ex.: `itens-0-modulo`, `itens-1-inversor`).

**Fluxo no `form_valid()`:**

```python
# 1. Calcula kWp
proposta.potencia_kwp = calcular_kwp(consumo, hsp, fator)

# 2. Identifica módulo-base e quantidade
proposta.modulo = primeiro item do formset que seja ModuloFotovoltaico
proposta.quantidade_modulos = sum(item.quantidade for item in instances if item.modulo)

# 3. Captura snapshot de preço para cada item novo
preco = PrecoEquipamentoSolar.get_preco_vigente(equip, hoje)
item.preco_venda_snapshot = preco.preco_venda if preco else 0
item.data_referencia_preco = hoje

# Itens existentes (pk preenchido) NÃO têm o snapshot atualizado — imutabilidade
```

---

## 5. Status e transições

```bash
rascunho ──► enviada ──► aprovada ──► concluida
    │            │           │
    │            │           └──► (faturada via OS: status não existe em PropostaSolar)
    │            │
    └────────────┴──────────────────────────────► cancelada
                                                      │
                                                   reabrir
                                                      │
                                                  rascunho
```

**Transições e efeitos colaterais:**

| Transição              | View                       | Efeito                                               |
| ---------------------- | -------------------------- | ---------------------------------------------------- |
| `rascunho → enviada`   | `enviar_proposta` (POST)   | Nenhum                                               |
| `enviada → aprovada`   | `aprovar_proposta` (POST)  | Chama `criar_lancamento_de_proposta_solar(proposta)` |
| `qualquer → cancelada` | `cancelar_proposta` (POST) | Bloqueado se `concluida` ou já `cancelada`           |
| `cancelada → rascunho` | `reabrir_proposta` (POST)  | Nenhum                                               |

---

## 6. Integrações com outros apps

### Financeiro

```python
# Chamado APENAS em aprovar_proposta(), status == "enviada"
from financeiro.services import criar_lancamento_de_proposta_solar
criar_lancamento_de_proposta_solar(proposta)

# Guard de duplicata embutido no service — seguro chamar mais de uma vez
# Usa proposta.valor_total como valor_bruto do LancamentoFinanceiro
```

### Ordens de Serviço

```python
# OrdemServico tem FK nullable proposta_solar → PropostaSolar
# Constraint XOR: proposta_solar e proposta_servico nunca simultaneamente preenchidos
# clean() valida que os.cliente == proposta.cliente

# Queryset padrão na DetailView da proposta:
proposta.ordens_servico.select_related("tecnico")

# Quando a OS é faturada, status da PropostaSolar NÃO muda automaticamente —
# status "concluida" da proposta é gerenciado separadamente.
```

---

## 7. Queryset padrão

```python
from solar.models import PropostaSolar

PropostaSolar.objects.select_related("cliente", "modulo").prefetch_related(
    "itens__modulo", "itens__inversor", "itens__estrutura", "itens__material",
    "ordens_servico__tecnico",
)
```

---

## 8. Análise financeira — fórmulas de referência

### Payback simples

```python
def calcular_payback_anos(valor_sistema: float, economia_mensal_kwh: float, tarifa_kwh: float) -> float:
    """Payback simples em anos."""
    economia_mes = economia_mensal_kwh * tarifa_kwh
    if economia_mes <= 0:
        return float("inf")
    return (valor_sistema / economia_mes) / 12
```

### Economia acumulada em N anos (com reajuste tarifário)

```python
def economia_acumulada(
    economia_mensal_inicial: float,
    reajuste_anual: float = 0.07,   # ~7%/ano histórico ANEEL
    anos: int = 25,
) -> float:
    """Economia total ao longo da vida útil do sistema."""
    total = 0.0
    economia_ano = economia_mensal_inicial * 12
    for _ in range(anos):
        total += economia_ano
        economia_ano *= (1 + reajuste_anual)
    return total
```

### TIR estimada (simplificada)

```python
import numpy_financial as npf  # pip install numpy-financial

def calcular_tir(valor_sistema: float, economia_mensal: float, meses: int = 300) -> float:
    """TIR mensal. Multiplicar por 12 para TIR anual."""
    fluxos = [-valor_sistema] + [economia_mensal] * meses
    tir_mensal = npf.irr(fluxos)
    return (1 + tir_mensal) ** 12 - 1  # TIR anual
```

> `numpy-financial` não está no `requirements.txt`. Adicionar antes de usar.
> Alternativa sem dependência: usar método iterativo de bissecção.

---

## 9. Bandeiras tarifárias — impacto no payback

A economia mensal varia conforme a bandeira vigente. Usar no simulador de payback:

| Bandeira    | Adicional (R$/kWh) | Cenário            |
| ----------- | ------------------ | ------------------ |
| Verde       | R$ 0,00            | Conservador (base) |
| Amarela     | R$ 0,01874         | Moderado           |
| Vermelha I  | R$ 0,04463         | Pessimista         |
| Vermelha II | R$ 0,07877         | Pessimista extremo |

> Valores ANEEL 2024/2025 — verificar em `aneel.gov.br/bandeiras-tarifarias` antes de usar em proposta.

```python
ADICIONAL_BANDEIRA = {
    "verde": Decimal("0.00000"),
    "amarela": Decimal("0.01874"),
    "vermelha_1": Decimal("0.04463"),
    "vermelha_2": Decimal("0.07877"),
}

def tarifa_com_bandeira(tarifa_base: Decimal, bandeira: str) -> Decimal:
    return tarifa_base + ADICIONAL_BANDEIRA.get(bandeira, Decimal("0"))
```

---

## 10. Simulação de financiamento solar

Linhas de crédito comuns no mercado (2025):

| Linha                        | Taxa típica      | Prazo máximo |
| ---------------------------- | ---------------- | ------------ |
| BNDES Finem (via banco)      | TJLP + 1–3% a.a. | 120 meses    |
| BB Crédito Solar             | ~1,5–2,0% a.m.   | 60 meses     |
| Sicoob/Sicredi Rural Solar   | ~1,0–1,5% a.m.   | 84 meses     |
| Financiamento direto empresa | negociável       | 24–48 meses  |

```python
def calcular_parcela_price(
    valor_financiado: float,
    taxa_mensal: float,     # ex.: 0.015 para 1,5% a.m.
    meses: int,
) -> float:
    """Sistema Price (parcelas fixas)."""
    if taxa_mensal == 0:
        return valor_financiado / meses
    return valor_financiado * (taxa_mensal * (1 + taxa_mensal) ** meses) / ((1 + taxa_mensal) ** meses - 1)
```

> Campos sugeridos no `PropostaSolar` quando implementado:
> `financiamento_ativo`, `valor_financiado`, `taxa_mensal`, `prazo_meses`, `parcela_estimada`

---

## 11. Homologação ANEEL — rastreamento

Etapas do processo junto à distribuidora (Energisa Tocantins):

```bash
1. Solicitação de acesso        → protocolo na distribuidora
2. Vistoria técnica             → inspeção na instalação (após OS concluída)
3. Parecer de acesso            → aprovação ou exigências técnicas
4. Adequações (se houver)       → cliente corrige eventuais pendências
5. Troca do medidor bidirecional → distribuidora instala medidor net metering
6. Conexão à rede               → sistema habilitado para injetar energia
```

**Prazos Energisa TO (estimados):**

- Microgeração (< 75 kWp): 30–90 dias corridos após solicitação completa
- Minigeração (75 kWp – 5 MW): 60–120 dias

**Campos sugeridos em `OrdemServico` (ou model dedicado `HomologacaoSolar`):**

```python
# Adicionais à OS quando implementado
data_solicitacao_acesso   # DateField — quando foi protocolado
numero_protocolo          # CharField — número da distribuidora
status_homologacao        # solicitada | vistoria_agendada | parecer_recebido | adequacoes | concluida
data_conclusao_homologacao # DateField (null até concluída)
observacoes_homologacao   # TextField
```

**Resolução normativa vigente:** REN 1000/2021 (ANEEL). Verificar se houve atualização antes de gerar documentos oficiais.

---

## 12. PDF de proposta — abordagem planejada

Conforme ROADMAP (Fase 3), a abordagem é **CSS `@media print` + `window.print()`** sem bibliotecas externas.

**Padrão a seguir quando implementado:**

```html
<!-- solar/templates/solar/proposta_print.html -->
{% extends "base_print.html" %}
<!-- base_print.html: sem topbar/sidebar, só conteúdo -->
```

```css
/* static/css/print.css */
@media print {
    .topbar, .sidebar, .btn-acao { display: none; }
    .proposta-pdf { page-break-inside: avoid; }
    @page { size: A4; margin: 2cm; }
}
```

**Estrutura sugerida do PDF:**

1. Cabeçalho: logo empresa, dados do cliente, número/data da proposta
2. Sumário técnico: kWp, módulos, inversor, área, geração estimada
3. Tabela de equipamentos: modelo, qtd, preço unitário, subtotal
4. Análise financeira: investimento total, economia mensal, payback, economia em 25 anos
5. Validade e condições gerais
6. Espaço para assinatura

---

## 13. Google Maps Solar API — dimensionamento geográfico

> Fase 3 — requer integração externa. Não implementado.

A [Google Solar API](https://developers.google.com/maps/documentation/solar) retorna:

- Área de telhado disponível (m²)
- Irradiação solar anual por segmento de telhado
- Sombreamento por estruturas próximas
- kWh/kWp estimado para o endereço exato

**Fluxo de integração sugerido:**

```bash
1. Cliente informa endereço no cadastro (já existe em clientes.Cliente)
2. Geocodificação: endereço → lat/lng (Google Geocoding API)
3. Consulta Solar API: lat/lng → dados solares do imóvel
4. Preencher hsp e consumo_medio_kwh automaticamente na proposta
```

**Custo (2025):** ~US$ 0,005 por buildingInsights request. Monitorar billing.

> Implementar apenas quando houver chave de API configurada em `.env` (`GOOGLE_MAPS_API_KEY`).

---

## 14. Observações regionais

- Distribuidora local: **Energisa Tocantins**
- Modalidade mais comum: **Geração na própria unidade** (microgeração ≤ 75 kWp)
- Modalidade crescente: **Autoconsumo remoto** e **UPAC** (≤ 1 MW por ponto)
- ICMS sobre energia injetada: verificar legislação estadual TO vigente (isenção parcial em alguns estados)
- DAS/MEI: instaladores autônomos precisam emitir nota fiscal; verificar regime tributário do cliente
