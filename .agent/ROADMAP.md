# ROADMAP — ERP Optimus

> **Atualizado:** 2026-08-16
>
> **Como ler:** as seções estão em ordem de prioridade real, não por
> categoria técnica. A pergunta que organiza tudo é *"o que impede a
> ferramenta de ser usada com um cliente de verdade?"* — não *"o que está
> tecnicamente imperfeito?"*.
>
> **Decisão de contexto (2026-08-16):** produção **não tem pressa**. A
> empresa opera há anos sem ferramenta própria; algumas semanas a mais não
> mudam nada. Por isso tudo que só importa no deploy foi rebaixado, e o que
> afeta o número que vai ao cliente subiu.

---

## 🎯 Próximo passo

Se você abrir este arquivo sem saber por onde continuar, é por aqui:

1. ~~Corrigir `Inversor.potencia_kw` do SAJ 6K-R5~~ ✅ feito em 2026-08-16
   (e o model agora rejeita potência em W, para não repetir).
2. ~~Aviso de proposta incompleta~~ ✅ feito em 2026-08-16 — card na tela de
   detalhe lista o que falta antes de virar PDF.
3. ~~Financeiro contava repasse ao fornecedor como receita~~ ✅ feito em
   2026-08-16 — ver seção 1.
4. **Popular o catálogo** — 👉 **é aqui que estamos.** Trabalho de dado, seu:
   cadastrar estruturas de fixação, cabos, conectores, DPS e disjuntores em
   `/solar/estruturas/` e `/solar/materiais/`, com preço em
   `/solar/precos/`. Enquanto isso não existe, toda proposta sai
   subestimada — e o aviso do item 2 vai continuar aparecendo.

---

## 1. Impede usar com cliente real

O que faz a proposta sair com número errado. **Maior prioridade.**

| Item | Situação |
|---|---|
| ~~**Financeiro somava repasse ao fornecedor como receita da Optimus**~~ | ✅ Corrigido (2026-08-16). Modelo de negócio real: o cliente compra o equipamento **direto do fornecedor** (Intelbras, Belenus), sem margem da Optimus — é assim que a venda de gerador fica isenta do ICMS que incidiria sobre estoque próprio. A Optimus só fatura instalação e manutenção. O sistema estava lançando o valor do equipamento como se fosse receita, inflando o dashboard de faturamento pelo preço do gerador inteiro. `LancamentoFinanceiro.tipo` agora distingue `receita` de `repasse` — o repasse continua rastreado (lembrete de cobrar o cliente, tamanho real do negócio), mas fica fora dos KPIs de faturamento. Ver skill financeiro-domain |
| **Catálogo praticamente vazio** | 1 módulo, 1 inversor, 1 estrutura, 2 materiais elétricos. Todos têm preço vigente — o problema **não é preço faltando, é item inexistente**. Sem estrutura de fixação, cabos e conectores cadastrados, nenhuma proposta consegue ficar completa |
| **Composição de preço incompleta** | Consequência do item acima: o valor total sai **subestimado**, e como o payback divide investimento pela economia, ele sai **otimista demais** (SOL-202608-0006 fechou em 1 ano e 1 mês). O cálculo de retorno está certo; o que entra nele é que não |
| ~~`Inversor.potencia_kw = 6000.00`~~ | ✅ Corrigido (2026-08-16). O model agora valida a faixa (0,1–500 kW) e rejeita potência digitada em W; módulo idem (50–2000 Wp). A sugestão de inversor voltou a funcionar (81,3% para 4,88 kWp) |
| ~~Nada avisa que a proposta está incompleta~~ | ✅ Feito (2026-08-16). `PropostaSolar.pendencias` + card na tela de detalhe: aponta falta de módulo/inversor/estrutura/material, mão de obra zerada, item com preço zerado e ausência de tarifa. Não bloqueia o envio — avisa |
| Tabela de preços pode envelhecer em silêncio | `PrecoEquipamentoSolar` tem vigência, mas nada alerta quando o preço vence |
| Mojibake em 24 produtos do estoque | Nomes aparecem corrompidos na tela. Não afeta o PDF solar, mas afeta o balcão |

---

## 2. Aguardando dado externo

Coisas que não dependem de código — dependem de um documento ou de uma decisão de fora.

| Item | O que falta |
|---|---|
| **Validar o Ajuste do Fio B** | A hipótese `Ajuste GDII = TUSD_FioB × percentual do ano` está **consistente, não provada** (o ciclo 2025 não está carregado no datastore da ANEEL). **Previsão testável:** numa fatura GDII do ciclo 2026-07-04, o "Ajuste GDII - TRF Reduzida" deve sair em **R$ 0,264887/kWh** (= 0,441478 × 0,60). Se bater, provada; se não, revisar `TarifaDistribuidora.fio_b_kwh`. Usuário vai enviar quando localizar |
| Sincronizar HSP de outras UFs | Só o TO está sincronizado (139 municípios). Proposta em GO/PA/MA/MT cai no fallback `hsp=5.50` fixo, sem curva mensal no PDF. Rodar `importar_municipios --uf XX` + `sincronizar_hsp --uf XX` antes de atender essas UFs |
| Distribuidoras fora do TO não validadas | O seed tem 6 distribuidoras, mas só o CNPJ da Energisa TO foi conferido contra fatura real |

---

## 3. Reduz risco de regressão

Não afeta o cliente hoje, mas encurta o tempo de encontrar o próximo bug.

| Item | Situação |
|---|---|
| Testes em apps sem cobertura | `financeiro` coberto (2026-08-16). Faltam `clientes`, `servicos`, `pos_venda` |
| Validar tarifa digitada contra a ANEEL | Alertar quando o valor digitado destoar da tarifa homologada — hoje erro de dígito passa em silêncio |
| Type hints em views/services | ~3% de cobertura. Critério de conclusão: `ruff check --select ANN` limpo |
| Quebrar views grandes | `ordens_servico` 500 linhas, `estoque` 346, `servicos` 305, `financeiro` 305. Só `solar` foi quebrado |
| Inline styles nos templates | 1.249 ocorrências. Dívida de manutenção, **sem risco financeiro** — por isso está aqui e não na seção 1 |
| 14 migrations em `solar` | Considerar squash quando o schema estabilizar |
| N+1 em `LancamentoListView` e `VendaListView` | KPIs em loop Python sobre queryset. Só dói com volume |

---

## 4. Evolução do produto

Capacidade nova, não correção.

| Item | Observação |
|---|---|
| Alimentar preços automaticamente | Pesquisado (2026-08-16): **Intelbras e Belenus não têm API pública documentada** — ambas operam por portal de parceiro (pedido manual/e-commerce), sem feed de catálogo. O `estoque` app já resolve isso hoje por upload manual de planilha `.xlsb`; o caminho realista pro `solar` é o mesmo padrão, não uma API. Discussão pausada pelo usuário para tratar antes a descoberta do modelo de negócio (venda direta sem margem — ver seção 1) |
| Financiamento bancário | Lógica própria (Price), diferente da tabela de cartão. Fora de escopo por decisão do usuário |
| `pos_venda`: SLAs, garantias, relatórios | CRUD, interações e histórico já existem |
| Async views / background tasks | Só faz sentido com volume. Candidatos: `financeiro.dashboard`, baixa de estoque do balcão, atualização de `status=vencido` em lote |
| Google Solar API | Área de telhado e sombreamento por endereço. Custa ~US$ 0,005/consulta — ver skill solar-domain §13 |

---

## 5. Só importa no dia do deploy

**Deliberadamente adiado.** Nada aqui bloqueia o desenvolvimento.

| Item | Situação |
|---|---|
| Hospedagem com suporte a Python | O plano atual (Hostinger Business) **não roda Django** — Python exige root, disponível só no VPS. Publicar exige VPS ou plataforma gerenciada. A landing (`optimus-landing`, PHP estático) continua onde está |
| Agendar `backup_db` em produção | O comando existe e foi testado com restauração real; falta agendar |
| Checklist de deploy | Validar `DJANGO_ENV` e `SECRET_KEY` forte antes de subir. O hardening já é automático sob `DJANGO_ENV=production`, mas nada impede subir sem a variável |

---

## ✅ Concluído

Arquivo histórico — o "porquê" de cada um está no `DIARIO.md` e nas skills.

**Módulo solar (o coração da ferramenta)**
- Payback/economia conforme Lei 14.300, verificado contra 2 faturas reais (2026-08-16) — skill §8
- Tarifas automáticas da ANEEL, API CKAN sem chave (2026-08-16) — skill §8
- HSP por município via IBGE + NASA POWER, com curva de geração mês a mês (2026-08-16) — skill §1
- Financiamento no cartão com tabela real Intelbras (2026-08-15) — skill §11.2
- Resumo de fechamento para WhatsApp (2026-08-13) — skill §11.1
- PDF da proposta via `window.print()`, sem lib externa (2026-08-13) — skill §12
- Sugestão automática de inversor compatível (2026-08-13) — skill §2.1

**Integridade de dados (auditoria externa de 2026-08-16)**
- Faturamento duplicado corrigido — provado em teste: R$ 10k viravam R$ 20k. Zero dano real
- Corrupção de itens na edição — `formset.save(commit=False)` só devolve linhas alteradas
- Travas de estado em proposta fechada (`SomenteRascunhoMixin`, no `dispatch`)
- Transações atômicas nas transições de status
- Teste que falha se app for incluído sem namespace (fecha o fail-open do RBAC)

**Infraestrutura**
- RBAC por grupos, matriz central em `core/permissoes.py` (2026-08-09)
- Hardening de produção sob `DJANGO_ENV` (2026-08-09)
- PostgreSQL via `DATABASE_URL` (2026-08-09)
- Comando `backup_db` com restauração testada (2026-08-09)
- Formatação de moeda `R$ 1.234.567,89` em todo o app (2026-08-16)
- `AGENTS.md` unificado + `scripts/check.ps1`
- Quebra de `solar/views.py` em subpacote
