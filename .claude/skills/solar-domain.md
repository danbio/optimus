# Domínio Solar — ERP Optimus (Tocantins/BR)

> ⚠️ Esta skill reflete os models **reais** do app `solar`. Última revisão: 2026-08-16.

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
@property geracao_mensal_kwh   # potencia_real_kwp * hsp * 30 * fator_eficiencia (projeção técnica)
@property inversor_principal   # primeiro Inversor entre os itens (model não tem FK de inversor
                                # de referência como tem `modulo` — assume 1 inversor por proposta)
@property quantidade_inversores  # Sum(quantidade) dos itens que têm inversor
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

## 8. Análise financeira — compensação de GD (Lei 14.300/2022)

> **Implementado** em `solar/services.py`. Não reescrever a conta em outro
> lugar — a lógica é sutil e está verificada contra fatura real.

### ⚠️ O erro que essa seção existe para evitar

`economia = geração × tarifa` **está errado** e superestima a economia. Foi
exatamente assim que a primeira versão da feature saiu, e o usuário reprovou
olhando a fatura dele. A geração de um sistema de GD **não** vale tarifa
cheia, por três motivos independentes:

1. **Fio B** — a parcela da TUSD cobrada sobre a energia *compensada*, que
   sobe todo ano até 2028 (Lei 14.300, art. 27).
2. **Custo de disponibilidade** — mínimo de 30/50/100 kWh (mono/bi/tri) que
   o cliente paga mesmo gerando 100% do consumo (REN ANEEL 414/2010, art. 98).
3. **COSIP** (contribuição de iluminação pública) — nunca é compensada.

### Escala legal do Fio B

| Ano | % do Fio B cobrado sobre a energia compensada |
|-----|----|
| até 2022 | 0% |
| 2023 | 15% |
| 2024 | 30% |
| 2025 | 45% |
| **2026** | **60%** |
| 2027 | 75% |
| 2028 | 90% |
| 2029+ | ANEEL redefine (art. 28) — o código assume **100%**, hipótese conservadora |

> Quem pediu conexão antes de 07/01/2023 tem direito adquirido até 2045 e
> não paga Fio B. **Isso não é modelado**: o ERP gera propostas para
> instalações novas, que caem sempre na regra nova.

### As duas parcelas da geração têm valor diferente

Distinção que o vendedor informa por proposta (`autoconsumo_simultaneo_pct`):

| Parcela | Passa pela rede? | Vale quanto |
|---|---|---|
| **Autoconsumo simultâneo** — consumido no mesmo instante em que é gerado | não | **tarifa cheia** (escapa do Fio B) |
| **Excedente injetado** — vira crédito na distribuidora | sim | **tarifa de compensação** (menor) |

Faixas típicas de autoconsumo simultâneo: residencial 20–30%, comércio com
carga diurna 50–70%.

### Fórmula verificada

```python
tarifa_compensacao = tarifa_cheia − (tusd_fio_b × percentual_fio_b(ano))

autoconsumo   = min(geração × pct_simultâneo, consumo)
injetada      = geração − autoconsumo
consumo_rede  = consumo − autoconsumo
compensada    = min(injetada, max(0, consumo_rede − custo_disponibilidade))

economia = autoconsumo × tarifa_cheia + compensada × tarifa_compensacao
conta    = consumo_rede × tarifa_cheia − compensada × tarifa_compensacao + COSIP
```

### Âncora de verificação — fatura real Energisa TO

Fatura B1 residencial monofásico, ref. agosto/2026 (`RetornoGDContraFaturaRealTests`):

| Item da fatura | Quant. | Tarifa c/ tributos | Valor |
|---|---|---|---|
| Consumo em kWh | 547 | 1,385750 | 758,00 |
| Energia Atv Injetada GDI | 499 | **1,197480** | −597,54 |
| Contrib de Ilum Pub | — | — | +42,14 |
| Adic. Bandeira Amarela | — | — | +1,25 |
| Bônus Itaipu | — | — | −4,46 |
| **Total** | | | **199,39** |

A tarifa de compensação da fatura cai fora da fórmula:

```
1,385750 − (0,313783 × 0,60) = 1,197480   ← bate exatamente com a linha GDI
```

É daí que sai o padrão `Configuracao.tusd_fio_b_kwh = 0,313783`.

> Reproduzir a fatura **ao centavo não é possível**: a distribuidora arredonda
> linha a linha e a tarifa impressa já é arredondada. O teste usa tolerância de
> 2 centavos — forçar igualdade exata seria ajustar o cálculo a artefato de
> arredondamento, não à regra de negócio.

### Parâmetros e onde ficam

| Parâmetro | Onde | Padrão |
|---|---|---|
| `tarifa_kwh` | por proposta | — (sem ela, nada é calculado) |
| `tipo_ligacao` | por proposta | monofásico |
| `autoconsumo_simultaneo_pct` | por proposta | 25% |
| `tusd_fio_b_kwh` | `Configuracao` (regional) | 0,313783 |
| `cosip_mensal` | `Configuracao` (regional) | 42,14 |
| reajuste tarifário | constante em `services.py` | 7% a.a. |
| degradação do módulo | constante em `services.py` | 0,5% a.a. |

### Ainda não implementado

- **TIR** — exigiria `numpy-financial` (fora do `requirements.txt`) ou
  bissecção manual. Payback simples cobre a necessidade comercial hoje.
- **Financiamento bancário** — lógica própria (ver §10), fora de escopo por
  decisão do usuário.
- **Direito adquirido pré-2023** — ver acima.

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

## 11.1 Resumo de fechamento (copiar/colar) — implementado (2026-08-13)

Card em `proposta_detail.html` ("Resumo para fechamento"), textarea somente-
leitura pré-preenchida a partir das properties do model + botão "Copiar"
(`navigator.clipboard.writeText`, com fallback `execCommand('copy')` pra
contexto HTTP sem clipboard API — comum em rede local sem HTTPS). Não é uma
view/endpoint novo, é só o template de `proposta_detail.html` — sem lib
externa, sem JS de terceiro.

Motivação: o usuário monta esse texto manualmente hoje pra fechar venda por
WhatsApp com cliente que não vai ler um PDF de 10 páginas ("talvez meu
melhor instrumento de fechamento"). Desde 2026-08-15 o card também inclui
parcelamento no cartão — ver §11.2. Financiamento bancário segue fora do
card (lógica de cálculo própria, fora de escopo — ver §10).

## 11.2 Financiamento / parcelamento no cartão — implementado (2026-08-15)

Model novo `TaxaCartao` (herda `BaseModel`) em `solar/models.py`, guardando
a tabela real de taxas por forma de pagamento (débito/crédito), bandeira e
quantidade de parcelas — dados oficiais Intelbras fornecidos pelo usuário
(não os 3 adquirentes da planilha de comparação, que tinha bugs visíveis e
foi propositalmente excluída):

```python
class TaxaCartao(BaseModel):
    forma       # "debito" | "credito"
    bandeira    # "visa_master" | "amex" | "elo" | "hiper"
    parcelas    # IntegerField — 1 a 21
    percentual  # DecimalField(5,2) — taxa da adquirente, ex. 3.49 = 3,49%
    ativo       # BooleanField (default=True)
```

Gerenciado via **Django Admin** (`/admin/solar/taxacartao/`,
`list_editable = ["percentual"]` — mesmo padrão de
`PrecoEquipamentoSolarAdmin`), não uma tela própria do app. Seed inicial
(87 linhas reais) via `python manage.py seed_taxas_cartao`
(`solar/management/commands/seed_taxas_cartao.py`, idempotente via
`update_or_create`).

**Fórmula de cálculo** — `solar/views/_helpers.py::calcular_parcela_cartao`:

```python
def calcular_parcela_cartao(valor_base: Decimal, bandeira: str) -> list[dict]:
    """Valor da parcela = valor_base / (1 - percentual/100), NÃO valor_base * (1 + percentual)."""
    # Retorna [{"parcelas": int, "valor_parcela": Decimal}, ...] ordenado 1x→21x
```

⚠️ **A fórmula NÃO é `valor * (1 + taxa)`** — essa foi a primeira hipótese
levantada e estava **errada**; só foi corrigida depois de buscar a planilha
real do usuário e verificar contra 4 pontos de referência reais (1x, 2x,
21x Visa/Master + Amex). Ver teste de regressão
`CalcularParcelaCartaoTests.test_formula_nao_e_multiplicar_pela_taxa`.

**Entrada = valor da mão de obra** (`proposta.valor_instalacao`), tratado
como um detalhe interno de composição de preço — o texto do resumo nunca
expõe esse valor como "entrada" isoladamente sem contexto; é sempre
"Entrada de R$ X + parcelamento do restante" (com entrada) ou "Parcelamento
de 100% no cartão" (sem entrada). Toggle "Com entrada" / "100% no cartão"
no card, junto com o seletor de bandeira — ambos via HTMX
(`hx-get` para `solar:resumo_fechamento`, `hx-target="#resumo-fechamento-card"`),
recalculando ao vivo sem reload. View: `solar/views/propostas.py::resumo_fechamento`,
reaproveitando o helper `_contexto_resumo_fechamento` também usado pela
`PropostaSolarDetailView` (evita duplicar a lógica entre a página cheia e o
parcial HTMX).

Tabela mostrada no resumo: **completa, 2x a 21x** (decisão do usuário —
não abreviada), conforme a bandeira e o toggle selecionados.

**Fora de escopo (deliberado):** financiamento bancário tem lógica própria
diferente (não é taxa de adquirente de cartão) — não modelado aqui, ver §10.

## 12. PDF de proposta — implementado (2026-08-13)

`GET /solar/<pk>/imprimir/` — `solar/views/propostas.py::proposta_print`. CSS
`@media print` + `window.print()` do navegador ("Salvar como PDF" nativo),
sem biblioteca externa, exatamente como planejado.

```html
<!-- solar/templates/solar/proposta_print.html -->
{% extends "base_print.html" %}
<!-- templates/base_print.html: sem topbar/sidebar/htmx, só o conteúdo.
     Carrega intelbras.css (reaproveita cores/.tabela) + static/css/print.css
     (layout A4, .doc-cabecalho, .doc-secao, .doc-grid, .doc-assinaturas). -->
```

Botão "Imprimir / PDF" em `proposta_detail.html` abre em nova aba
(`target="_blank"`). Acesso: mesmo nível do resto do app `solar`
(Administrador + Vendedor via RBAC) — não é restrito.

**Estrutura implementada:**

1. Cabeçalho: nome/CNPJ/endereço da Optimus (hardcoded no template — não é
   parâmetro de `Configuracao`; é dado de registro da empresa, não regra de
   negócio), número/data/validade da proposta
2. Dados do cliente (`endereco_resumido`, `telefone_principal` — properties
   já existentes em `clientes.Cliente`)
3. Sumário técnico: kWp real, módulos, área, **geração mensal estimada**
   (kWp × HSP × 30 × fator_eficiencia — calculada na view)
4. Tabela de equipamentos: item, especificação (com garantia inline pra
   módulo/inversor), qtd, preço unitário, subtotal
5. Investimento: equipamentos + instalação = total
6. Validade e condições gerais + espaço para assinatura

**Análise de retorno (desde 2026-08-16):** três seções a mais quando a
proposta tem `tarifa_kwh` preenchida — "Retorno do investimento" (conta
atual × conta estimada, economia, payback, acumulado), "Economia projetada
ano a ano" (gráfico) e "Como esta conta foi feita" (memória de cálculo com
o Fio B explícito). **Sem `tarifa_kwh` as três somem** — a regra segue
valendo: nunca estimar economia sem dado real do cliente. Ver §8.

**Gráfico de barras** — `solar/services.py::grafico_economia_anual` devolve
`path` de SVG já montado. Série única em `#00a335` (verde da marca, aprovado
nos checks de contraste); sem legenda, porque o título da seção já nomeia a
série; rótulo direto só na primeira e na última barra; payback marcado por
linha tracejada, não por cor — o verde-claro da marca reprova em contraste
(1,91:1 sobre branco).

> ⚠️ **Todo número que vira atributo de SVG sai de `services.py` como
> string.** O projeto roda com `USE_THOUSAND_SEPARATOR=True`, então o
> template localizaria: `680.0` → `680,0` no `viewBox` e o ano `2026` →
> `2.026` no rótulo, quebrando o gráfico. Só valores em R$ continuam
> `Decimal`, porque esses *devem* ser localizados. Travado por
> `test_svg_nao_sofre_localizacao_de_numero`.

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
