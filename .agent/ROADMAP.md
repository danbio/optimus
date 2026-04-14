# ROADMAP DE DESENVOLVIMENTO: ERP Optimus

> Documento de dívida técnica, gargalos e evolução sistêmica.
> Atualizado: 2026-04-14.

---

## Status em Andamento

| Item | Status | Bloqueia |
|------|--------|----------|
| Type Hints em views/services | 🔴 Pendente | Fase 2 (Async requer tipos corretos) |
| Async Views / Background Tasks | 🟡 Pendente | Nada, mas depende da Fase 1 |
| RBAC (grupos de permissão) | 🟠 Pendente | Implantação em produção |
| `pos_venda` (SLAs e chamados) | 🔲 Backlog | Pós-venda só após RBAC |
| PDF de propostas | 🔲 Backlog | Independente, pode ser feito a qualquer momento |

---

## Fase 1 — Conformidade com Strict Mode: Type Hints 🔴

**Prioridade:** Alta — bloqueia a adoção de async views (Fase 2).

**Problema:** Nenhuma view nem service tem assinaturas tipadas. O Strict Mode exige Type Hints completos.

**Onde aplicar:**
- `balcao/views.py` — todas as FBVs (ex: `finalizar_venda`, `adicionar_item`)
- `financeiro/views.py` — FBVs (`registrar_baixa`, `cancelar_lancamento`, `dashboard`)
- `financeiro/services.py` — todas as funções de service
- `solar/views.py` — FBVs e CBVs
- `ordens_servico/views.py` — FBVs

**Padrão mínimo exigido:**
```python
from django.http import HttpRequest, HttpResponse

def finalizar_venda(request: HttpRequest, pk: int) -> HttpResponse:
    ...
```

**Critério de conclusão:** `ruff check --select ANN` sem erros em todos os apps listados.

---

## Fase 2 — Async-First & Background Tasks 🟡

**Prioridade:** Média — impacto percebido somente com volume de dados crescente.
**Dependência:** Fase 1 concluída.

### Candidatos a Async View

| View | Motivo |
|------|--------|
| `financeiro.dashboard` | Múltiplos aggregates + loops Python em memória |
| `financeiro.LancamentoListView.get_context_data` | KPIs calculados a cada request |
| `balcao.VendaListView.get_context_data` | Aggregates de totais hoje/mês |

**Padrão Django 6.0+:**
```python
async def dashboard(request: HttpRequest) -> HttpResponse:
    total = await LancamentoFinanceiro.objects.aaggregate(s=Sum("valor_liquido"))
    ...
```

### Candidatos a Background Task (Django Tasks Framework nativo)

| Operação | Motivo |
|----------|--------|
| `criar_lancamento_de_venda_balcao` | Bloqueia a thread do PDV ao finalizar |
| Atualização de `status=vencido` em lote | Deve rodar periodicamente, não em cada request |

**⚠️ Atenção:** O backend de tasks do Django 6.x com SQLite tem limitações. Avaliar trade-offs antes de implementar em produção com SQLite.

---

## Fase 3 — Evolução de Features

### PDF de Propostas
- **O que:** Renderizar `proposta_detail.html` como PDF imprimível (A4, CSS `@media print`)
- **Como:** Adicionar `?print=1` na URL da detail view → renderiza template sem sidebar/topbar → CSS `@media print` formata para A4
- **Sem bibliotecas externas:** CSS puro + `window.print()` via link `<a onclick="window.print()">` é suficiente
- **Não depende de nenhuma fase anterior**

### `pos_venda` — SLAs e Chamados
- Estruturar models: `Chamado`, `HistoricoChamado`, `GarantiaInstalacao`
- Vinculado à `OrdemServico` de origem (rastreabilidade)
- SLA baseado na data de conclusão da OS de instalação

---

## Fase 4 — RBAC (Controle de Acesso) 🟠

**Prioridade:** Necessário antes de colocar em produção com múltiplos usuários.

**Grupos a criar:**
| Grupo | Permissões |
|-------|-----------|
| `admin` | Todos os módulos, incluindo cancelar lançamentos liquidados |
| `vendedor` | Criar propostas, fechar venda balcão. Sem acesso a financeiro |
| `tecnico` | Ler/atualizar OS atribuídas. Sem acesso a financeiro ou preços |
| `financeiro` | Financeiro completo. Apenas leitura em propostas |
| `gerente` | Tudo exceto configurações de sistema |

**Implementação:** `LoginRequiredMixin` + `PermissionRequiredMixin` nas CBVs, `@permission_required` nas FBVs.

---

## Gargalos de Performance Conhecidos

### N+1 Queries
- **`LancamentoListView`:** `total_pendente` e `total_vencido` fazem loop Python sobre QuerySet (sem `select_related` nas propriedades)
- **`VendaListView`:** KPIs recalculam aggregates a cada request de listagem

**Correção:** `select_related` + `prefetch_related` + mover KPIs para cache de sessão ou context processor otimizado.

### Migrações acumuladas em `solar`
- Há 8 migrações no app `solar`. Considerar squash quando o banco de produção estiver estável.
