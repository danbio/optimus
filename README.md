# ERP Optimus

ERP interno para revenda Intelbras — Tocantins/BR.

Três módulos de negócio: **Energia Solar**, **Segurança/Automação** e **Venda Balcão**.

---

## Setup rápido

```powershell
# 1. Ativar ambiente virtual
.venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
copy .env.example .env
# editar .env e definir SECRET_KEY

# 4. Aplicar migrações
python manage.py migrate

# 5. Criar superusuário
python manage.py createsuperuser

# 6. Subir servidor
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/

---

## Stack

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| Python | 3.13 | — |
| Django | 6.0.3 | Framework principal |
| SQLite | — | Banco de dados (dev) |
| CSS puro | — | `static/css/intelbras.css` |
| Bootstrap Icons | CDN | Ícones (`bi bi-nome`) |
| HTMX | CDN | Interatividade parcial |
| WhiteNoise | 6.x | Arquivos estáticos |
| python-dotenv | 1.x | Variáveis de ambiente |

---

## Apps Django

| App | Descrição |
|-----|-----------|
| `core` | `BaseModel` com auditoria (`criado_em`, `atualizado_em`) |
| `clientes` | Cadastro PF/PJ, validação CPF/CNPJ, busca CEP/CNPJ |
| `estoque` | Catálogo Intelbras, importação de tabela `.xlsb` |
| `solar` | Dimensionamento técnico, proposta comercial, catálogo de equipamentos |
| `servicos` | Proposta para segurança eletrônica, automação e controle de acesso |
| `ordens_servico` | OS unificada com checklist, fotos e técnico responsável |
| `financeiro` | Lançamentos, parcelas, baixas, dashboard de fluxo de caixa |
| `balcao` | PDV com carrinho HTMX, baixa de estoque e lançamento financeiro |
| `pos_venda` | Chamados, interações e histórico do cliente |

---

## Comandos úteis (Claude Code slash commands)

| Comando | O que faz |
|---------|-----------|
| `/newapp <nome>` | Cria estrutura completa de um novo app Django |
| `/scaffold <app> <Model>` | Gera CRUD completo (model, form, views, urls, templates) |
| `/migrate` | Roda `makemigrations` + `migrate` |
| `/check` | Roda `python manage.py check` |
| `/test` | Roda a suíte de testes |
| `/commit` | Formata e executa commit semântico |

---

## Documentação para Agentes de IA

Os agentes de IA (Claude Code, Copilot, Gemini Antigravity) usam a pasta `.agent/` como base de conhecimento compartilhada:

- `.agent/INSTRUCTIONS.md` — Stack, convenções e regras do projeto
- `.agent/ROADMAP.md` — Dívida técnica e próximos passos
- `.agent/DIARIO.md` — Logbook de sessões (inclui TL;DR do estado atual)

---

## Estrutura de pastas

```
Optimus/
├── .agent/            # Conhecimento compartilhado (SSOT multi-agente)
├── .claude/           # Comandos e skills do Claude Code
├── .github/           # Instruções do Copilot
├── config/            # settings.py, urls.py, wsgi.py, asgi.py
├── core/              # BaseModel abstrato
├── templates/         # base.html global
├── static/css/        # intelbras.css
├── <apps>/            # cada app na raiz do projeto
├── manage.py
├── requirements.txt
└── .env               # não versionar (adicione ao .gitignore)
```
