# Domínio Ordens de Serviço — ERP Optimus

> ⚠️ Esta skill reflete os models **reais** do app `ordens_servico`. Última revisão: 2026-04-14.

## Visão Geral

O app `ordens_servico` registra a execução física dos serviços vendidos. Uma OS pode ser originada por uma `PropostaSolar` ou uma `PropostaServico` — nunca os dois ao mesmo tempo (constraint XOR no banco).

---

## Models (estrutura real)

### `Tecnico` (herda `BaseModel`)

```python
nome          # CharField(200)
telefone      # CharField (blank)
email         # EmailField (blank)
especialidade # solar | seguranca | automacao | acesso | geral
ativo         # BooleanField (default=True)
```

---

### `OrdemServico` (herda `BaseModel`)

```python
# Identificação
numero   # auto-gerado "OS-YYYYMM-0001" (único, imutável — gerado em save())
cliente  # FK → clientes.Cliente (PROTECT)
tecnico  # FK → Tecnico (PROTECT)
status   # aberta | agendada | em_execucao | concluida | faturada | suspensa
prioridade  # baixa | normal | alta | urgente

# Origens (XOR — apenas uma pode estar preenchida)
proposta_solar   # FK → solar.PropostaSolar (SET_NULL, nullable)
proposta_servico # FK → servicos.PropostaServico (SET_NULL, nullable)

# Datas de ciclo de vida
data_agendamento       # DateTimeField (nullable)
data_inicio_execucao   # DateTimeField (nullable)
data_conclusao         # DateTimeField (nullable)

# Assinatura do cliente (confirmação de conclusão)
assinatura_nome        # CharField (nome de quem assinou)
assinatura_confirmada  # BooleanField
assinatura_data        # DateTimeField (nullable)

descricao    # TextField (descrição do serviço)
observacoes  # TextField
```

**Constraint no banco:**
```python
# Nunca proposta_solar E proposta_servico ao mesmo tempo
CheckConstraint(~(Q(proposta_solar__isnull=False) & Q(proposta_servico__isnull=False)))
```

**Properties úteis:**
```python
os.tipo_origem          # "Solar" | "Serviço" | "Avulsa"
os.checklist_total      # int — total de itens
os.checklist_concluidos # int — itens marcados como concluídos
os.checklist_percentual # int — % de conclusão (0-100)
```

---

### `ChecklistTemplate` (herda `BaseModel`)

Template de itens que são copiados para a OS ao criar:

```python
descricao  # CharField(300) — ex: "Verificar torque dos parafusos"
tipo       # solar | seguranca | automacao | acesso | geral
ordem      # PositiveIntegerField
ativo      # BooleanField
```

---

### `ItemChecklist`

Itens efetivos de uma OS específica (cópia dos templates + personalizados):

```python
ordem_servico  # FK → OrdemServico (CASCADE, related_name="itens_checklist")
descricao      # CharField(300)
concluido      # BooleanField (default=False)
observacao     # TextField
ordem          # PositiveIntegerField
```

---

### `FotoOS`

```python
ordem_servico  # FK → OrdemServico (CASCADE, related_name="fotos")
foto           # ImageField (upload_to="ordens_servico/fotos/%Y/%m/")
legenda        # CharField(200, blank)
enviada_em     # DateTimeField (auto_now_add)
```

> `MEDIA_ROOT` deve estar configurado. Usa `PIL`/`Pillow` para validação de imagens.

---

## Fluxo de Status

```
aberta ──► agendada ──► em_execucao ──► concluida ──► faturada
    │                                       │
    └───────────────────────────────────────┴──► suspensa
```

**Transição `concluida → faturada`:**
- Acionada pela view `faturar_os` (POST, `ordens_servico:<int:pk>/faturar/`)
- Chama `financeiro.services.criar_lancamento_de_ordem_servico(os_obj)`
- Só disponível quando `status == "concluida"`

---

## Regras de Negócio Críticas

1. **XOR de origens** — constraint no banco + `clean()` impedem `proposta_solar` e `proposta_servico` ao mesmo tempo.
2. **Cliente consistente** — `clean()` valida que o cliente da OS é o mesmo da proposta vinculada.
3. **Número imutável** — gerado em `save()` com retry (até 5x) para evitar colisão de concorrência.
4. **Assinatura não é autenticação** — é apenas um campo de confirmação textual. Não implementar OAuth/biometria.
5. **Fotos exigem `Pillow`** — já está em `requirements.txt`.

---

## Queryset Padrão

```python
from ordens_servico.models import OrdemServico

OrdemServico.objects.select_related(
    "cliente", "tecnico", "proposta_solar", "proposta_servico"
).prefetch_related(
    "itens_checklist", "fotos", "lancamentos"
)
```

---

## Integração com Financeiro

A única forma de gerar lançamento a partir de uma OS é via:

```python
from financeiro.services import criar_lancamento_de_ordem_servico
criar_lancamento_de_ordem_servico(os_obj)  # chamado apenas quando status == "concluida"
```

O lançamento usa o `valor_total` da proposta de origem (solar ou serviço). Se for OS avulsa sem proposta, `valor=0` e deve ser editado manualmente no módulo financeiro.
