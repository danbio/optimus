# AGENTS.md — ERP Optimus

> **Ponto de entrada único para todos os agentes de IA** (Claude Code, Copilot, Gemini, Cline).
> Este arquivo substitui instruções espalhadas. Não crie silos em subpastas próprias.

---

## 1. Setup rápido

```powershell
# Windows (PowerShell) — único ambiente suportado
.venv\Scripts\activate
python manage.py check
python manage.py test --verbosity=1
```

**Script de verificação completa:** `scripts/check.ps1` (lint + testes + migrations + deploy check).

---

## 2. Projeto

ERP interno para empresa em Tocantins/BR. Três linhas de negócio:

| Linha | App principal | Apps auxiliares |
|-------|--------------|-----------------|
| Energia Solar | `solar` | `clientes`, `estoque`, `financeiro`, `ordens_servico`, `pos_venda` |
| Segurança / Automação / Acesso | `servicos` | `clientes`, `financeiro`, `ordens_servico`, `pos_venda` |
| Venda Balcão | `balcao` | `clientes`, `estoque`, `financeiro` |

**Perfil:** Dev solo. Prioridade absoluta: simplicidade e legibilidade.

---

## 3. Stack (não negociável)

| Camada | Tecnologia | Nota |
|--------|-----------|------|
| Backend | Python 3.13 · Django 6.0.3 | CBVs para CRUD, FBVs para ações pontuais |
| Banco | SQLite (dev) → PostgreSQL (futuro) | |
| CSS | CSS puro `static/css/intelbras.css` | **Sem Bootstrap framework, Tailwind, React, Vue** |
| Ícones | Bootstrap Icons CDN | Apenas ícones (`bi bi-nome`) |
| Interatividade | HTMX CDN | Uso cirúrgico, `hx-target` e `hx-swap` sempre explícitos |
| Ambiente | Windows, rede local | Usar sempre `python manage.py`, nunca `py` ou `python3` |

---

## 4. Apps — estado atual

| App | Status | Descrição |
|-----|--------|-----------|
| `core` | ✅ | `BaseModel` abstrato (`criado_em`/`atualizado_em`) |
| `clientes` | ✅ | CRUD PF/PJ, validação CPF/CNPJ, busca CEP/CNPJ |
| `estoque` | ✅ | Produtos Intelbras, importação `.xlsb`/`.xlsx` |
| `solar` | ✅ | Dimensionamento HTMX, proposta, catálogo com preços |
| `servicos` | ✅ | Proposta por tipo (segurança, automação, acesso) |
| `ordens_servico` | ✅ | OS unificada, checklist, fotos, técnico |
| `financeiro` | ✅ | Lançamentos, parcelas, baixas, dashboard |
| `balcao` | ✅ | PDV carrinho HTMX, baixa estoque, lançamento automático |
| `pos_venda` | ✅ | Chamados, interações, histórico do cliente |

---

## 5. Arquitetura — regras fundamentais

### 5.1 Estrutura de arquivos

```
Optimus/
├── AGENTS.md            ← este arquivo (SSOT para agentes)
├── config/              settings.py, urls.py, wsgi.py
├── core/                BaseModel abstrato
├── templates/           base.html global
├── static/css/          intelbras.css
├── <app>/               cada app na raiz (não em apps/<app>/)
│   ├── models.py
│   ├── views/           subpacote quando >300 linhas
│   │   ├── __init__.py  re-exporta tudo
│   │   ├── propostas.py
│   │   └── catalogo.py
│   ├── forms.py
│   ├── urls.py
│   └── templates/<app>/
├── scripts/             check.ps1
├── manage.py
└── .env                 (não versionar)
```

### 5.2 Regras de domínio

- `clientes`, `financeiro`, `estoque` são compartilhados — nunca duplicar dados de cliente
- `servicos` cobre segurança + automação + acesso via `tipo_servico` — **sem apps separados**
- `ordens_servico` usa dois FKs nullable com validação XOR (solar ou serviço, nunca ambos)
- `balcao` não gera OS — gera lançamento financeiro direto
- **Nunca usar GenericForeignKey**

### 5.3 Convenções de código

- Português para campos, `verbose_name`, labels
- `snake_case` para tudo
- Templates em `<app>/templates/<app>/`
- `{% url 'namespace:name' %}` — nunca URLs hardcoded
- Formulários Django para toda entrada — nunca HTML puro
- `__str__` em todos os models
- Todos os models herdam de `core.models.BaseModel`

### 5.4 Frontend — obrigatório

- Cores **sempre** via variáveis CSS: `var(--verde)`, `var(--texto-titulo)`, etc.
- Layout: topbar verde `#00a335` + sidebar verde + conteúdo em `<div class="main">`
- Mensagens: classes `alerta alerta-sucesso/info/aviso/erro`
- **Sem inline style** exceto `max-width`, `width`, `padding` pontuais
- Verificar se classe já existe em `intelbras.css` antes de criar nova

### 5.5 Forms — padrão obrigatório

```python
class MeuForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
```

---

## 6. O que NÃO fazer

- ❌ Apps separados para segurança/automação/acesso — tudo em `servicos/`
- ❌ GenericForeignKey
- ❌ Bootstrap (framework), Tailwind, React, Vue
- ❌ Inline styles (exceto width/max-width/padding pontuais)
- ❌ Hardcodar cores — usar variáveis CSS
- ❌ JS complexo — usar HTMX
- ❌ URLs hardcoded em templates
- ❌ Pular `makemigrations` ao alterar models
- ❌ Models sem herdar de `BaseModel`
- ❌ Recriar apps/estruturas existentes sem verificar antes

---

## 7. Verificação antes de commitar

Rodar `scripts/check.ps1` ou manualmente:

```powershell
ruff check .
python manage.py test --verbosity=1
python manage.py makemigrations --check --dry-run
python manage.py check --deploy
```

Nenhum commit deve ser feito com falhas nesses 4 passos.

---

## 8. Dívida técnica (ver ROADMAP.md para detalhes)

| Prioridade | Item | Status |
|------------|------|--------|
| 🔴 Alta | Type hints em views/services | ~3% cobertura, meta: 100% |
| 🔴 Alta | Testes em clientes, servicos, financeiro, pos_venda | Sem cobertura |
| 🟡 Média | Quebrar views >300 linhas em subpacotes | solar já quebrado |
| 🟡 Média | Reduzir inline styles nos templates | ~1190 ocorrências |
| ✅ Feito | RBAC (permissões por grupo) | `core/permissoes.py` + middleware |
| 🟠 Baixa | Async views para dashboards | Depende de type hints |

### RBAC — como funciona

Três grupos: **Administrador**, **Vendedor**, **Técnico** (`python manage.py seed_grupos`).

O controle é **centralizado**, não espalhado por views: a matriz vive em
`core/permissoes.py` e é aplicada por `core/middleware.py`, que identifica o
módulo pelo *namespace* da URL. Para mudar quem acessa o quê, edite só a matriz
— nenhuma view precisa ser tocada. Views seguem responsáveis apenas por exigir
login (`LoginRequiredMixin` / `@login_required`).

Pontos de atenção:
- Usuário **sem grupo não acessa nada** (exceto dashboard/login). Ao criar
  usuário no admin, vincular o grupo — senão ele vê 403 em tudo.
- **Superusuário ignora a matriz**: é a conta de resgate.
- Testes que exercitam regra de negócio (não permissão) precisam colocar o
  usuário em um grupo, senão tomam 403. Ver `balcao/tests.py` como exemplo.

---

## 9. Referências (somente leitura)

| Arquivo | Conteúdo |
|---------|----------|
| `.agent/ROADMAP.md` | Fases e dívida técnica detalhada |
| `.agent/DIARIO.md` | Log de sessões (consulta histórica) |
| `.claude/skills/*.md` | Skills de domínio do Claude Code |
| `docs/diagramas.md` | Diagramas de arquitetura |

---

## 10. Protocolo de trabalho para agentes

1. **Antes de implementar:** ler este arquivo + `ROADMAP.md`
2. **Uma feature por vez:** implementar, testar, commitar
3. **Worktree limpa:** não iniciar feature com alterações pendentes
4. **Atualizar DIARIO.md** ao final de sessões significativas
5. **Em caso de dúvida arquitetural:** perguntar antes de implementar
