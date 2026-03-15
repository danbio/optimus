# ERP Optimus — Briefing para Claude Code

## Contexto do projeto

ERP interno para empresa de Tocantins/BR com 3 linhas de negócio:

- Energia Solar (residencial e comercial)
- Segurança Eletrônica / Automação / Controle de Acesso
- Venda Balcão (venda direta de produtos)

Dev solo. Manutenção feita pelo próprio dono. Prioridade: simplicidade e legibilidade acima de elegância técnica.

---

## Stack

- Python 3.13
- Django (versão mais recente estável)
- CSS puro: `static/css/intelbras.css` (tema Revenda Referência Intelbras)
- Bootstrap Icons via CDN (apenas ícones — sem o framework Bootstrap)
- HTMX (uso mínimo e cirúrgico — só onde agrega)
- SQLite em desenvolvimento → PostgreSQL em produção
- Git para controle de versão
- Windows (desenvolvimento local)
- Rede local (acesso da equipe via IP local)

---

## Estrutura de apps Django

```
Optimus/
├── clientes/          # Cadastro PF/PJ, contatos
├── financeiro/        # Parcelas, recebimentos, fluxo de caixa
├── estoque/           # Produtos, fornecedores, entradas/saídas
├── solar/             # Dimensionamento + proposta solar
├── servicos/          # Proposta para segurança/automação/acesso
├── balcao/            # Venda direta (produto + qtd + recebimento)
├── ordens_servico/    # OS unificada (solar ou serviços)
└── pos_venda/         # Chamados, garantia, histórico
```

---

## Regras de arquitetura

### Apps core (compartilhadas)

`clientes`, `financeiro` e `estoque` são usados por todos os outros apps via ForeignKey. Nunca duplicar dados de cliente.

### Solar vs Serviços

- `solar` tem fluxo próprio: dimensionamento técnico → proposta → OS
- `servicos` cobre segurança eletrônica, automação residencial e controle de acesso (interfones, portões). Usa campo `tipo_servico` para diferenciar — sem apps separados.

### OS unificada

`ordens_servico` tem dois campos nullable:

```python
proposta_solar = models.ForeignKey('solar.PropostaSolar', null=True, blank=True, ...)
proposta_servico = models.ForeignKey('servicos.PropostaServico', null=True, blank=True, ...)
```

Nunca usar GenericForeignKey — manter simples.

### OS registra obrigatoriamente

- Responsável / técnico
- Data e horário de execução
- Checklist de instalação
- Fotos (upload)
- Assinatura do cliente (campo de confirmação)

### Venda Balcão

Fluxo simples: produto + quantidade + forma de recebimento. Não gera OS.

---

## Convenções de código

- Português para nomes de campos, verbose_name e labels de formulário
- snake_case para tudo (variáveis, funções, arquivos)
- Views baseadas em classe (CBV) preferidas para CRUD
- Templates em `templates//` dentro de cada app
- Um arquivo `urls.py` por app, incluído no urls.py principal
- Sempre usar `{% url %}` — nunca URLs hardcoded nos templates
- Formulários Django para toda entrada de dados (nunca HTML puro)
- `__str__` definido em todos os models

---

## Frontend

- CSS puro em `static/css/intelbras.css` — identidade visual Intelbras (Revenda Referência)
- Bootstrap Icons via CDN — usar sempre `bi bi-nome` para ícones
- HTMX via CDN — usar só para atualizações parciais simples (ex: busca de cliente sem reload)
- Sem Bootstrap framework, sem Tailwind, sem React, sem Vue
- Sem JavaScript customizado complexo
- Layout: topbar verde (#00a335) + sidebar verde com links brancos, conteúdo em `<div class="main">`
- Cores via variáveis CSS: `var(--verde)`, `var(--texto-titulo)`, `var(--fundo-alt)`, etc.
- Mensagens Django tratadas no `base.html` com classes `alerta alerta-sucesso/info/aviso/erro`

### Formulários — padrão obrigatório em forms.py

```python
class MeuForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
```

Campos de data/hora precisam de override adicional de type:
```python
self.fields["data"].widget.attrs["type"] = "date"
self.fields["data_hora"].widget.attrs["type"] = "datetime-local"
```

---

## Segurança e acesso

- Django auth nativo (login/logout)
- Grupos de permissão por área (admin, vendedor, técnico)
- Acesso via rede local — não expor na internet nesta fase

---

## O que NÃO fazer

- Não criar apps separados para segurança, automação e controle de acesso — tudo em `servicos/`
- Não usar GenericForeignKey
- Não usar Bootstrap (framework), não usar Tailwind
- Não usar estilos inline — exceto `max-width` e `width` em casos pontuais
- Não hardcodar cores no HTML — sempre usar variáveis CSS (`var(--verde)`, etc.)
- Não criar classes CSS novas sem antes verificar se já existe em `intelbras.css`
- Não criar lógica complexa de JS — se precisar de interatividade, usar HTMX
- Não hardcodar URLs
- Não pular migrações — sempre `makemigrations` + `migrate` após alterar models

---

## Como trabalhar neste projeto

Este projeto é gerenciado em parceria:

- Arquitetura e decisões → discutidas no claude.ai antes de implementar
- Implementação → Claude Code no VSCode
- Quando tiver dúvida sobre arquitetura, **perguntar antes de implementar**
- Implementar um app por vez, validar, depois avançar
- Ordem sugerida: clientes → estoque → solar → servicos → ordens_servico → financeiro → balcao → pos_venda

---

## Estado atual do projeto

- Fase: configuração inicial — nenhum app Django criado ainda
- Django ainda não instalado — primeiro passo é criar o venv e instalar dependências
- Criar app `core` (BaseModel com campos de auditoria) antes dos apps de negócio
- Ordem de implementação: clientes → estoque → solar → servicos → ordens_servico → financeiro → balcao → pos_venda

---

## Ambiente virtual

Fica em `.venv/` na raiz. Ativar no Windows:

```bash
.venv\Scripts\activate
```

Verificar se o venv está ativo antes de qualquer `python manage.py`.

---

## Estrutura de arquivos esperada

```
Optimus/
├── .claude/
│   ├── settings.local.json
│   └── commands/
├── .venv/
├── config/            # settings.py, urls.py, wsgi.py, asgi.py
├── templates/         # base.html global
├── static/            # assets CSS/JS globais
├── clientes/          # apps ficam na raiz (não em apps/)
├── ...
├── manage.py
├── requirements.txt
├── pyproject.toml
└── .env               # não versionar
```

Apps ficam na **raiz do projeto** (ex: `clientes/`), não em `apps/clientes/`.
Settings module: `config.settings`.

---

## Context7 MCP — Documentação Django

Para consultar documentação Django atualizada, usar o MCP Context7:

- ID da biblioteca Django: `/django/django`
- Usar quando precisar de referência sobre: QuerySets, CBVs, formulários, migrations, auth, FileField

Exemplo: "use context7 to look up Django CreateView"
