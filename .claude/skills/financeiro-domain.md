# Domínio Financeiro — ERP Optimus

> ⚠️ Esta skill reflete os models e services **reais** do app `financeiro`. Última revisão: 2026-08-16.

## Visão Geral

O app `financeiro` é o **hub central de receitas**. Toda operação que gera faturamento (solar, serviços, balcão, OS) cria um `LancamentoFinanceiro` via service dedicado. Nunca crie lançamentos diretamente — use os services.

### ⚠️ Modelo de negócio real: venda direta, sem estoque de gerador

Confirmado pelo usuário em 2026-08-16, depois de o financeiro somar como
receita um dinheiro que a empresa nunca recebe. **O cliente compra o
equipamento solar direto do fornecedor** (Intelbras, Belenus) — a Optimus
faz a interface (dimensiona, escolhe equipamento, monta a proposta), mas
**não tem margem sobre o equipamento e nunca fatura esse valor**. É assim
que a venda de gerador fica isenta do ICMS que incidiria se a Optimus
mantivesse estoque próprio (prática comum no mercado solar brasileiro).

O caixa real da Optimus vem só de **instalação e manutenção**.

Por isso `LancamentoFinanceiro.tipo` distingue:

```python
TIPO_RECEITA  # dinheiro que a Optimus fatura e recebe de verdade (padrão)
TIPO_REPASSE  # cliente paga direto ao fornecedor — só rastreio, não é receita
```

`criar_lancamento_de_proposta_solar` cria o lançamento de equipamento como
`TIPO_REPASSE` — existe pra lembrar de cobrar o cliente e pra dar
visibilidade do tamanho real do negócio, mas **o dashboard exclui repasse
dos KPIs de faturamento** (`total_liquido`, `total_recebido`,
`total_pendente`, `inadimplência`). Somar repasse ali infla a receita real
pelo preço do equipamento inteiro — foi exatamente o bug que motivou essa
distinção.

O PDF da proposta continua mostrando o **valor combinado** (equipamento +
instalação) como "Valor do Investimento" — isso é o que o cliente vai
gastar no total, e é uma decisão deliberada do usuário manter assim mesmo
sabendo que são duas notas fiscais/pagamentos diferentes por trás.

---

## Models (estrutura real)

### `LancamentoFinanceiro` (herda `BaseModel`)

```python
# Campos principais
numero          # auto-gerado: "LAN-YYYYMM-0001" (único, imutável)
descricao       # ex: "Proposta Solar SOL-202604-0001"
status          # pendente | parcial | liquidado | cancelado
valor_bruto     # DecimalField
desconto        # DecimalField (default=0)
valor_liquido   # calculado em save(): valor_bruto - desconto
valor_recebido  # acumulado das BaixaFinanceira
data_emissao    # auto_now_add
data_vencimento # DateField
data_liquidacao # preenchido quando status → liquidado
forma_pagamento # dinheiro|pix|cartao_debito|cartao_credito|boleto|crediario|transferencia
num_parcelas    # PositiveIntegerField (default=1)

# FK de cliente (obrigatória — nunca null)
cliente  # FK → clientes.Cliente

# FKs de origem (apenas UMA pode estar preenchida — constraint no banco)
venda_balcao     # FK → balcao.Venda (nullable)
proposta_solar   # FK → solar.PropostaSolar (nullable)
proposta_servico # FK → servicos.PropostaServico (nullable)
ordem_servico    # FK → ordens_servico.OrdemServico (nullable)
```

**Properties úteis:**
```python
lan.esta_vencido  # bool — True se pendente/parcial e data_vencimento < hoje
lan.saldo_aberto  # Decimal — valor_liquido - valor_recebido
lan.origem_display  # tuple ("Balcão", "verde") — para badge no template
lan.origem_url    # tuple ("balcao:detalhe", pk) — para link de volta à origem
```

---

### `ParcelaLancamento`

```python
lancamento      # FK → LancamentoFinanceiro (CASCADE)
numero_parcela  # PositiveIntegerField
valor           # DecimalField
data_vencimento # DateField
data_pagamento  # DateField (null ao criar)
valor_pago      # DecimalField (default=0)
status          # pendente | pago | cancelado
observacao      # CharField
```

**Constraint:** `unique_together = [("lancamento", "numero_parcela")]`

---

### `BaixaFinanceira`

```python
lancamento      # FK → LancamentoFinanceiro (CASCADE)
parcela         # FK → ParcelaLancamento (SET_NULL, nullable)
valor           # DecimalField — valor efetivamente recebido
forma_pagamento # mesmas choices de LancamentoFinanceiro
data_pagamento  # DateField
registrado_por  # FK → AUTH_USER_MODEL (PROTECT)
criado_em       # DateTimeField auto
observacao      # CharField
```

> `BaixaFinanceira` é **imutável depois de criada** — registros de auditoria. Para corrigir, cancele o lançamento.

---

## Services (única forma de criar lançamentos)

Arquivo: `financeiro/services.py`

```python
# Importar e chamar — nunca instanciar LancamentoFinanceiro diretamente
from financeiro.services import (
    criar_lancamento_de_proposta_solar,    # solar/views.py → aprovar_proposta
    criar_lancamento_de_proposta_servico,  # servicos/views.py → aprovar_proposta
    criar_lancamento_de_ordem_servico,     # ordens_servico/views.py → faturar_os
    criar_lancamento_de_venda_balcao,      # balcao/views.py → finalizar_venda
)
```

**Todos os services incluem:**
- Guard de duplicata (`if LancamentoFinanceiro.objects.filter(...).exists(): return None`)
- Criação automática das `ParcelaLancamento` via `_criar_parcelas()`
- Baixa automática para pagamentos à vista (balcão: dinheiro, pix, débito)

---

## Fluxo de Status

```
                  registrar_baixa (parcial)
pendente ────────────────────────────────► parcial
    │                                         │
    │         valor_recebido >= valor_liquido │
    └─────────────────────────────────────────┴──► liquidado
    
pendente / parcial ──► cancelar_lancamento ──► cancelado
```

---

## Regras de Negócio Críticas

0. **`tipo` distingue receita de repasse** — ver seção acima. Todo KPI de faturamento/dashboard deve filtrar `tipo=TIPO_RECEITA`; listagens e detalhe podem mostrar os dois, com o repasse claramente rotulado.
1. **UMA origem por lançamento** — constraint no banco (`CheckConstraint`) e validação em `clean()`. Violar isso lança `ValidationError`.
2. **Cliente obrigatório** — sem FK de cliente, o lançamento não é criado (vendas avulsas sem cliente vinculado ficam sem lançamento).
3. **Não deletar origens que têm lançamento** — FKs usam `SET_NULL`, não `CASCADE` (o lançamento sobrevive se a proposta for alterada).
4. **Baixas são imutáveis** — nunca edite `BaixaFinanceira`. O `valor_recebido` do lançamento é recalculado via `Sum("baixas__valor")`.
5. **Status `vencido` não persiste no banco** — é calculado em runtime via `@property esta_vencido`.

---

## Queryset Padrão para Listagens

```python
# Sempre usar select_related para evitar N+1
LancamentoFinanceiro.objects.select_related(
    "cliente", "venda_balcao", "proposta_solar", "proposta_servico", "ordem_servico"
).prefetch_related("parcelas", "baixas__registrado_por")
```

---

## Dashboard — Aggregates Usados

```python
from django.db.models import Sum
from django.utils import timezone

today = timezone.localdate()
qs = LancamentoFinanceiro.objects.filter(data_vencimento__gte=data_de, data_vencimento__lte=data_ate)

total_liquido   = qs.aggregate(s=Sum("valor_liquido"))["s"] or 0
total_recebido  = qs.aggregate(s=Sum("valor_recebido"))["s"] or 0
# total_pendente e total_vencido: calculados via Python (saldo_aberto é property, não campo)
pendentes = qs.filter(status__in=["pendente", "parcial"])
total_pendente = sum(lan.saldo_aberto for lan in pendentes)
total_vencido  = sum(lan.saldo_aberto for lan in pendentes if lan.data_vencimento < today)
```
