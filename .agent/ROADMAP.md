# ROADMAP DE DESENVOLVIMENTO: ERP Optimus

> Documento de dívida técnica, gargalos e evolução sistêmica.
> Atualizado: 2026-04-15.

---

## Status em Andamento

| Item | Status | Bloqueia |
|------|--------|----------|
| Type Hints em views/services | 🔴 ~3% cobertura (24/725 funções) | Fase 2 (Async requer tipos corretos) |
| Testes em apps sem cobertura | 🔴 0 testes em clientes, servicos, financeiro, pos_venda | Refatoração segura |
| Quebrar views >300 linhas | 🟡 solar feito, faltam ordens_servico, financeiro, estoque, servicos | Edição confiável por agentes |
| Inline styles nos templates | 🟡 ~1190 ocorrências | Consistência de patches |
| Async Views / Background Tasks | 🟡 Pendente | Nada, mas depende da Fase 1 |
| RBAC (grupos de permissão) | ✅ Feito (2026-08-09) | — (era o bloqueador de produção) |
| Hardening de produção (HTTPS/HSTS/cookies) | ✅ Feito (2026-08-09) | — |
| PostgreSQL via DATABASE_URL | ✅ Feito (2026-08-09) | — |
| Backup do banco (`backup_db`) | ✅ Feito (2026-08-09) | — (falta agendar execução em produção) |
| Mojibake em 24 produtos do estoque | 🔴 Pendente | Nada, mas os nomes aparecem errados na tela |
| `Inversor.potencia_kw = 6000.00` no SAJ 6K-R5 | 🔴 **Pendente — aparece no PDF do cliente** | Deveria ser `6.00` (o "6K" do modelo é 6 kW). Sai como "6.000,00kW" na proposta impressa. Não é bug de código, é dado errado no cadastro — mas a sugestão de inversor compatível (relação CC:CA) também usa esse campo |
| Hospedagem com suporte a Python | 🔴 Pendente | **Implantação em produção** |
| PDF de propostas | ✅ Feito (2026-08-13) | `@media print` + `window.print()`, sem lib externa — ver skill solar-domain §12 |
| Sugestão automática de inversor compatível | ✅ Feito (2026-08-13) | Relação CC:CA, faixa configurável em `/configuracoes/` — ver skill solar-domain §2.1 |
| Resumo de fechamento (copiar/colar p/ WhatsApp) | ✅ Feito (2026-08-13) | Card em `proposta_detail.html` — geração, equipamento, valor à vista. Ainda sem financiamento/cartão |
| **Composição de preço incompleta nas propostas** | 🔴 **Pendente — afeta proposta que vai pro cliente** | Faltam estrutura de fixação, cabos e conectores nos itens. O valor total sai **subestimado**, e como o payback divide o investimento pela economia, ele sai **otimista demais** (ex.: SOL-202608-0006 fechou em 1 ano e 1 mês). O cálculo de retorno está certo; o que entra nele é que não. |
| Tabela de preços desatualizada | 🔴 Pendente | `PrecoEquipamentoSolar` com preços vencidos — mesma consequência do item acima |
| Alimentar preços automaticamente (API de fornecedor / scraping) | 🟡 Planejado | Intenção do usuário (2026-08-16) para resolver os dois itens acima de vez, em vez de digitação manual. Ainda sem fornecedor/método definido |
| Payback / economia conforme Lei 14.300 | ✅ Feito (2026-08-16) | Motor em `solar/services.py`, verificado contra fatura real da Energisa TO. Fio B gradual, custo de disponibilidade, COSIP e autoconsumo simultâneo — ver skill solar-domain §8 |
| Formatação de moeda `R$ 1.234.567,89` | ✅ Feito (2026-08-16) | `USE_THOUSAND_SEPARATOR=True` — vale para o app inteiro. **Cuidado:** localiza todo número no template, inclusive anos e coordenadas de SVG (ver AGENTS.md) |
| Financiamento / parcelamento no cartão | ✅ Feito (2026-08-15) | Modelo `TaxaCartao` + admin + seed com tabela real Intelbras (87 linhas) + resumo de fechamento com bandeira/entrada via HTMX — ver skill solar-domain §13. Financiamento bancário segue fora de escopo (lógica própria) |

> **Hospedagem:** o plano atual (Hostinger Business Web Hosting) **não roda
> Django** — a própria Hostinger documenta que Python exige acesso root,
> disponível só no VPS. Publicar exige VPS ou uma plataforma gerenciada de
> Python. A landing (`optimus-landing`, PHP estático) continua onde está.

---

## Fase 0 — Infraestrutura para Agentes (NOVA)

**Prioridade:** Crítica — melhora diretamente a qualidade das edições dos agentes de IA.

### Já concluído:
- [x] `AGENTS.md` unificado na raiz
- [x] `scripts/check.ps1` (lint + testes + migrations + deploy check)
- [x] Quebra do `solar/views.py` em subpacote (`propostas.py`, `catalogo.py`, `precos.py`)
- [x] Atualização de SSOT (pos_venda está implementado, não pendente)

### Pendente:
- [ ] Quebrar `ordens_servico/views.py` (497 linhas)
- [ ] Quebrar `estoque/views.py` (346 linhas)
- [ ] Quebrar `servicos/views.py` (305 linhas)
- [ ] Quebrar `financeiro/views.py` (305 linhas)
- [ ] Limpar worktree (commit organizado das 125+ entradas pendentes)
- [ ] Migrar DIARIO.md para formato compacto (TL;DR + últimas 5 sessões)

---

## Fase 1 — Conformidade: Type Hints + Testes 🔴

**Prioridade:** Alta — bloqueia a adoção de async views (Fase 2) e refatoração segura.

### Type Hints

**Onde aplicar (por prioridade de edição dos agentes):**
- `solar/views/propostas.py` — ✅ já tipado na quebra
- `solar/views/catalogo.py` — parcialmente tipado
- `solar/views/precos.py` — ✅ já tipado na quebra
- `financeiro/views.py` — FBVs e services
- `financeiro/services.py` — todas as funções
- `ordens_servico/views.py` — FBVs
- `balcao/views.py` — FBVs
- `pos_venda/views.py` — FBVs

**Padrão mínimo exigido:**
```python
from django.http import HttpRequest, HttpResponse

def finalizar_venda(request: HttpRequest, pk: int) -> HttpResponse:
    ...
```

**Critério de conclusão:** `ruff check --select ANN` sem erros em todos os apps.

### Testes

**Apps sem nenhum teste (prioridade):**
- `clientes` — testar CRUD, validação CPF/CNPJ
- `servicos` — testar CRUD de propostas, transições de status
- `financeiro` — testar lançamentos, parcelas, baixas, services
- `pos_venda` — testar chamados, interações, mudança de status

**Critério de conclusão:** cada app com pelo menos 1 TestCase cobrindo happy path do CRUD.

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

**⚠️ Atenção:** O backend de tasks do Django 6.x com SQLite tem limitações.

---

## Fase 3 — Evolução de Features

### PDF de Propostas
- CSS `@media print` + `window.print()` — sem bibliotecas externas
- Não depende de nenhuma fase anterior

### `pos_venda` — Evolução
- ✅ CRUD de chamados implementado
- ✅ Interações e histórico do cliente implementados
- Pendente: SLAs, garantias, relatórios

---

## Fase 4 — RBAC (Controle de Acesso) 🟠

**Prioridade:** Necessário antes de produção com múltiplos usuários.

| Grupo | Permissões |
|-------|-----------|
| `admin` | Todos os módulos |
| `vendedor` | Criar propostas, venda balcão. Sem financeiro |
| `tecnico` | Ler/atualizar OS atribuídas. Sem financeiro/preços |
| `financeiro` | Financeiro completo. Leitura em propostas |
| `gerente` | Tudo exceto configurações de sistema |

**Implementação:** `LoginRequiredMixin` + `PermissionRequiredMixin` nas CBVs.

---

## Gargalos de Performance Conhecidos

### N+1 Queries
- **`LancamentoListView`:** KPIs fazem loop Python sobre QuerySet
- **`VendaListView`:** Aggregates recalculados a cada request

**Correção:** `select_related` + `prefetch_related` + cache de sessão.

### Migrações acumuladas em `solar`
- 10 migrações. Considerar squash quando banco estiver estável.
