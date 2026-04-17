# ERP Optimus — Briefing para Agentes de IA

> **Leia este arquivo antes de qualquer ação.** Ele define o contexto, stack, convenções e o estado atual do projeto.
> Outros agentes (Claude Code, GitHub Copilot, Gemini Antigravity, Cline) compartilham esta mesma base.

---

## Contexto do Projeto

ERP interno para empresa de Tocantins/BR com 3 linhas de negócio:

- **Energia Solar** — dimensionamento técnico, proposta comercial, OS e pós-venda
- **Segurança Eletrônica / Automação / Controle de Acesso** — proposta, OS
- **Venda Balcão** — venda direta de produtos com baixa de estoque e lançamento financeiro automático

**Perfil:** Dev solo. Manutenção feita pelo próprio dono. Prioridade: simplicidade e legibilidade acima de elegância técnica.

---

## Estado Atual do Projeto (atualizado: 2026-04-14)

> ⚠️ O projeto **está em produção local** com todos os apps criados e funcionando. **Não recriar estruturas existentes.**

### Apps implementados e status:

| App              | Status     | Observações                                                                                |
| ---------------- | ---------- | ------------------------------------------------------------------------------------------ |
| `core`           | ✅ Completo | `BaseModel` abstrato com `criado_em`/`atualizado_em`                                       |
| `clientes`       | ✅ Completo | CRUD PF/PJ, validação CPF/CNPJ, busca CEP/CNPJ                                             |
| `estoque`        | ✅ Completo | Produtos Intelbras, importação `.xlsb`/`.xlsx`                                             |
| `solar`          | ✅ Completo | Dimensionamento HTMX, proposta, catálogo de equipamentos com preços, quantidades editáveis |
| `servicos`       | ✅ Completo | Proposta por tipo (segurança, automação, acesso)                                           |
| `ordens_servico` | ✅ Completo | OS unificada, checklist, fotos, técnico                                                    |
| `financeiro`     | ✅ Completo | Lançamentos, parcelas, baixas, dashboard                                                   |
| `balcao`         | ✅ Completo | PDV com carrinho HTMX, baixa de estoque, lançamento financeiro                             |
| `pos_venda`      | 🔲 Pendente | App criado, sem implementação ainda                                                        |

### Dívida técnica em andamento (ver `.agent/ROADMAP.md`):

1. **Type Hints** — faltam em todas as views e services
2. **Async-First** — dashboards e finalizações ainda são síncronos
3. **RBAC** — sem controle de permissão por grupo ainda

---

## Stack

- **Python:** 3.13
- **Django:** 6.0.3 (produção local via `py manage.py runserver`)
- **Banco de dados:** SQLite (dev) → PostgreSQL (produção futura)
- **CSS:** CSS puro em `static/css/intelbras.css` — **sem Bootstrap, sem Tailwind**
- **Ícones:** Bootstrap Icons via CDN (`bi bi-nome`) — apenas ícones, não o framework
- **Interatividade:** HTMX via CDN — uso cirúrgico, só onde agrega
- **Controle de versão:** Git
- **Ambiente:** Windows, rede local

---

## Estrutura de Arquivos do Projeto

```mermaid
Optimus/
├── .agent/              # ← Base de conhecimento compartilhada (SSOT)
│   ├── INSTRUCTIONS.md  # este arquivo
│   ├── DIARIO.md        # logbook de sessões
│   └── ROADMAP.md       # dívidas técnicas e roadmap
├── .claude/             # específico do Claude Code
│   ├── commands/        # slash commands (/newapp, /scaffold, /migrate...)
│   └── skills/          # skills de domínio e frontend
├── .github/
│   └── copilot-instructions.md
├── .venv/
├── config/              # settings.py, urls.py, wsgi.py, asgi.py
├── core/                # BaseModel abstrato
├── templates/           # base.html global
├── static/css/          # intelbras.css
├── clientes/ estoque/ solar/ servicos/ ordens_servico/ financeiro/ balcao/ pos_venda/
├── manage.py
├── requirements.txt
└── .env                 # não versionar
```

Apps ficam na **raiz do projeto** (ex: `clientes/`), não em `apps/clientes/`.
Settings module: `config.settings`.

---

## Estrutura de Apps Django

```
Optimus/
├── clientes/          # Cadastro PF/PJ, contatos
├── financeiro/        # Parcelas, recebimentos, fluxo de caixa
├── estoque/           # Produtos Intelbras
├── solar/             # Dimensionamento + proposta solar + catálogo equipamentos
├── servicos/          # Proposta para segurança/automação/acesso
├── balcao/            # Venda direta (produto + qtd + recebimento)
├── ordens_servico/    # OS unificada (solar ou serviços)
└── pos_venda/         # Chamados, garantia, histórico (pendente)
```

---

## Regras de Arquitetura

### Apps core (compartilhadas)

`clientes`, `financeiro` e `estoque` são usados por todos os outros apps via ForeignKey. **Nunca duplicar dados de cliente.**

### Solar vs Serviços

- `solar` tem fluxo próprio: dimensionamento técnico → proposta → OS
- `servicos` cobre segurança eletrônica, automação residencial e controle de acesso (interfones, portões). Usa campo `tipo_servico` para diferenciar — **sem apps separados**.

### OS Unificada

`ordens_servico` tem dois campos nullable com validação XOR (nunca os dois ao mesmo tempo):

```python
proposta_solar   = models.ForeignKey('solar.PropostaSolar',    null=True, blank=True, ...)
proposta_servico = models.ForeignKey('servicos.PropostaServico', null=True, blank=True, ...)
```

**Nunca usar GenericForeignKey — manter simples.**

### OS Registra Obrigatoriamente

- Responsável / técnico
- Data e horário de execução
- Checklist de instalação
- Fotos (upload)
- Assinatura do cliente (campo de confirmação)

### Venda Balcão

Fluxo: produto + quantidade + forma de recebimento. **Não gera OS.** Gera lançamento financeiro automaticamente ao finalizar.

---

## Convenções de Código

- Português para nomes de campos, `verbose_name` e labels de formulário
- `snake_case` para tudo (variáveis, funções, arquivos)
- Views baseadas em classe (CBV) preferidas para CRUD
- Templates em `<app>/templates/<app>/` dentro de cada app
- Um arquivo `urls.py` por app, incluído no `urls.py` principal
- Sempre usar `{% url 'namespace:name' %}` — nunca URLs hardcoded nos templates
- Formulários Django para toda entrada de dados — nunca HTML puro
- `__str__` definido em todos os models
- Todos os models herdam de `core.models.BaseModel`
- **Type Hints obrigatórios** em views e services (dívida técnica a pagar)

---

## Frontend

- CSS puro em `static/css/intelbras.css` — identidade visual Intelbras (Revenda Referência)
- Bootstrap Icons via CDN — usar sempre `bi bi-nome` para ícones
- HTMX via CDN — usar só para atualizações parciais simples
- **Sem Bootstrap framework, sem Tailwind, sem React, sem Vue**
- Sem JavaScript customizado complexo — prefira HTMX se precisar de interatividade
- Layout: topbar verde `#00a335` + sidebar verde com links brancos, conteúdo em `<div class="main">`
- Cores **sempre** via variáveis CSS: `var(--verde)`, `var(--texto-titulo)`, `var(--fundo-alt)`, etc.
- Mensagens Django tratadas no `base.html` com classes `alerta alerta-sucesso/info/aviso/erro`

### Padrão obrigatório em `forms.py`

```python
class MeuForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        # Campos de data: self.fields["data"].widget.attrs["type"] = "date"
        # Campos datetime: self.fields["dt"].widget.attrs["type"] = "datetime-local"
```

---

## Segurança e Acesso

- Django auth nativo (login/logout)
- Grupos de permissão por área (admin, vendedor, técnico) — **implementação pendente (ROADMAP)**
- Acesso via rede local — não expor na internet nesta fase

---

## O que NÃO Fazer

- ❌ Criar apps separados para segurança, automação e acesso — tudo em `servicos/`
- ❌ Usar GenericForeignKey
- ❌ Usar Bootstrap (framework), Tailwind, React, Vue
- ❌ Usar estilos inline — exceto `max-width`, `width` e `padding` pontuais
- ❌ Hardcodar cores no HTML — sempre usar variáveis CSS (`var(--verde)`, etc.)
- ❌ Criar classes CSS novas sem antes verificar se já existe em `intelbras.css`
- ❌ Criar lógica complexa de JS — se precisar de interatividade, usar HTMX
- ❌ Hardcodar URLs nos templates
- ❌ Pular migrações — sempre `makemigrations` + `migrate` após alterar models
- ❌ Criar models sem herdar de `BaseModel`

---

## Como Trabalhar Neste Projeto

Este projeto é gerenciado em parceria multi-agente:

- **Gemini Antigravity** (VSCode) — análise, planejamento, execução de code changes
- **Claude Code** (CLI/VSCode) — implementação com slash commands (`/scaffold`, `/newapp`, `/migrate`)
- **GitHub Copilot** (VSCode inline) — autocomplete assistido pelas instruções em `.github/copilot-instructions.md`

**Regras:**

- Perguntar antes de implementar em caso de dúvida arquitetural
- Implementar um app/feature por vez, validar, depois avançar
- Atualizar `.agent/DIARIO.md` ao final de cada sessão significativa
- Consultar `.agent/ROADMAP.md` antes de iniciar qualquer feature nova

---

## Skills Disponíveis (Claude Code — `.claude/skills/`)

| Arquivo                 | Conteúdo                                                |
| ----------------------- | ------------------------------------------------------- |
| `frontend-intelbras.md` | Paleta, tipografia, classes CSS, padrões de template    |
| `intelbras-theme.md`    | Paleta de cores e decisões de UI                        |
| `django-models.md`      | Padrões de model (TextChoices, Meta, __str__)           |
| `django-forms.md`       | Padrões de form (class, autocomplete, overrides)        |
| `django-views.md`       | Padrões de CBV (LoginRequiredMixin, select_related)     |
| `solar-domain.md`       | Domínio solar: fórmulas, fluxo, campos esperados        |
| `financeiro-domain.md`  | Domínio financeiro: models, services, regras de negócio |
| `clientes-domain.md`    | Domínio clientes: validações, campos, integrações       |

---

## Context7 MCP — Documentação Django

Para consultar documentação Django atualizada, usar o MCP Context7:

- ID da biblioteca Django: `/django/django`
- Usar quando precisar de referência sobre: QuerySets, CBVs, formulários, migrations, auth, FileField, Tasks, Async Views

---

## Ambiente Virtual

Fica em `.venv/` na raiz. Ativar no Windows:

```powershell
.venv\Scripts\activate
```

Verificar se o venv está ativo antes de qualquer `python manage.py`.
