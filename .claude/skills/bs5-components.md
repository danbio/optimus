# Skill: Frontend — CSS puro, tema Intelbras

## Arquitetura

- CSS puro em `static/css/intelbras.css` — sem Bootstrap
- Bootstrap Icons via CDN (apenas ícones — `bi bi-nome`)
- HTMX via CDN, uso cirúrgico
- Layout: topbar verde (#00a335) + sidebar verde (#00a335) com itens brancos
  ⚠️ Nota: o guia oficial Intelbras usa sidebar cinza (#ebeeee) — a sidebar verde é customização deste projeto.

---

## Variáveis CSS — obrigatório usar sempre, nunca hardcodar cor

```css
/* Paleta principal */
--verde:          #00a335;   /* ação primária, topbar, sidebar */
--verde-escuro:   #00863f;   /* hover de botões e links verdes */
--verde-claro:    #87c984;   /* acento secundário, hover sidebar (guia oficial) */

/* Texto */
--texto-titulo:   #3e5055;   /* títulos, headers de tabela */
--texto-corpo:    #8b979f;   /* texto secundário, placeholders */

/* Fundos */
--fundo-alt:      #ebeeee;   /* linhas alternadas de tabela, fundo sidebar oficial */
--fundo-foco:     #f2f4f4;   /* input em foco */

/* Status */
--erro:           #d72735;   /* erros, btn-danger */
--alerta:         #eab42a;   /* warning */
--info:           #6a90a7;   /* informativo */

/* Bordas */
--borda:          #d6dfe1;   /* bordas de tabela, inputs */

/* Estados de formulário */
--campo-valido-borda:   #00a335;
--campo-valido-fundo:   #e5f6ed;
--campo-invalido-borda: #d72735;
--campo-invalido-fundo: #fdebed;
```

---

## Tipografia

- **Font stack:** `"SF Pro", "Roboto", "Arial", "Helvetica", sans-serif`
- Corpo: Regular 15px, cor `var(--texto-corpo)`
- Títulos/headings: cor `var(--texto-titulo)`
- Botão primário: Semibold 16px — botão pequeno: Semibold 14px
- Tags/badges: Semibold 13px
- Placeholder: Regular 13px, cor `var(--texto-corpo)`

---

## Layout obrigatório

```
┌─────────────────────────────────────┐
│  TOPBAR verde #00a335 (fixo topo)   │
├──────────┬──────────────────────────┤
│ SIDEBAR  │  <div class="main">      │
│ verde    │    <div class="page-     │
│ #00a335  │      header">            │
│ (fixo    │    <div class="card">    │
│  lateral)│    ...                   │
└──────────┴──────────────────────────┘
```

Todo conteúdo de página fica dentro de `<div class="main">` no `base.html`.

---

## Padrão de página com listagem

```html
{% extends "base.html" %}
{% block title %}{{ titulo }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1><i class="bi bi-ICONE"></i> {{ titulo }}</h1>
  <a href="{% url 'app:novo' %}" class="btn-primary">
    <i class="bi bi-plus-lg"></i> Novo
  </a>
</div>

<div class="card">
  <table class="tabela">
    <thead>
      <tr>
        <th>Nome</th>
        <th>Status</th>
        <th>Valor</th>
        <th style="width: 80px">Ações</th>
      </tr>
    </thead>
    <tbody>
      {% for obj in object_list %}
      <tr>
        <td class="col-titulo">{{ obj }}</td>
        <td>
          <span class="badge {% if obj.ativo %}badge-verde{% else %}badge-cinza{% endif %}">
            {% if obj.ativo %}Ativo{% else %}Inativo{% endif %}
          </span>
        </td>
        <td>R$ {{ obj.valor_total }}</td>
        <td>
          <a href="{{ obj.get_absolute_url }}" title="Ver" style="color: var(--texto-corpo)">
            <i class="bi bi-eye"></i>
          </a>
        </td>
      </tr>
      {% empty %}
      <tr>
        <td colspan="4" class="text-center" style="padding: 30px; color: var(--texto-corpo)">
          Nenhum registro encontrado.
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% if is_paginated %}
<div class="paginacao">
  {% if page_obj.has_previous %}
    <a href="?page={{ page_obj.previous_page_number }}">Anterior</a>
  {% endif %}
  <span>{{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span>
  {% if page_obj.has_next %}
    <a href="?page={{ page_obj.next_page_number }}">Próxima</a>
  {% endif %}
</div>
{% endif %}
{% endblock %}
```

---

## Padrão de formulário

```html
{% extends "base.html" %}
{% block title %}{{ titulo }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>{{ titulo }}</h1>
</div>

<div class="card" style="max-width: 720px">
  <div class="card-body">
    <form method="post" novalidate>
      {% csrf_token %}
      {% for field in form %}
      <div class="form-group">
        <label for="{{ field.id_for_label }}">
          {{ field.label }}{% if field.field.required %}<span class="obrigatorio">*</span>{% endif %}
        </label>
        {{ field }}
        {% if field.errors %}
        <div class="form-error">
          <i class="bi bi-exclamation-circle"></i> {{ field.errors|join:", " }}
        </div>
        {% endif %}
        {% if field.help_text %}
        <div class="form-ajuda">{{ field.help_text }}</div>
        {% endif %}
      </div>
      {% endfor %}

      <div class="d-flex gap-1 mt-3">
        <button type="submit" class="btn-primary">
          <i class="bi bi-check-lg"></i> Salvar
        </button>
        <a href="{% url 'app:lista' %}" class="btn-secondary">Cancelar</a>
      </div>
    </form>
  </div>
</div>
{% endblock %}
```

---

## Modal (confirmação / alerta)

```html
<!-- Abrir modal: adicionar class "modal-ativo" ao overlay via HTMX ou JS mínimo -->
<div class="modal-overlay" id="modal-excluir">
  <div class="modal-box">
    <h3>Confirmar exclusão</h3>
    <p style="color: var(--texto-corpo)">Esta ação não pode ser desfeita.</p>
    <div class="d-flex gap-1 justify-between mt-3">
      <button class="btn-secondary" onclick="fecharModal('modal-excluir')">Cancelar</button>
      <form method="post" action="{% url 'app:excluir' obj.pk %}">
        {% csrf_token %}
        <button type="submit" class="btn-danger">
          <i class="bi bi-trash"></i> Excluir
        </button>
      </form>
    </div>
  </div>
</div>
```

Overlay do modal: `rgba(43, 46, 56, 0.9)` — já definido em `intelbras.css`.

---

## Classes CSS disponíveis — USE APENAS ESTAS

### Botões
| Classe | Uso |
|--------|-----|
| `btn-primary` | Ação principal (verde #00a335) |
| `btn-secondary` | Ação secundária (branco + borda cinza) |
| `btn-danger` | Exclusão / ação destrutiva (vermelho #d72735) |
| `btn-sm` | Versão menor de qualquer botão |

### Cards
| Classe | Uso |
|--------|-----|
| `card` | Container com sombra (`0 1px 2px rgba(0,0,0,.20)`) |
| `card-header` | Cabeçalho do card |
| `card-body` | Corpo com padding |

Cards têm hover shadow: `0 10px 20px rgba(0,0,0,0.19)`.

### Tabela
| Classe | Uso |
|--------|-----|
| `tabela` | Tabela completa (header #3e5055, linhas alternadas #ebeeee) |
| `col-titulo` | Coluna de nome/título (destaque) |
| `col-off` | Coluna desativada / secundária |

### Badges
| Classe | Cor |
|--------|-----|
| `badge badge-verde` | Verde — ativo, sucesso |
| `badge badge-cinza` | Cinza — inativo, desabilitado |
| `badge badge-alerta` | Amarelo #eab42a — atenção |
| `badge badge-erro` | Vermelho #d72735 — erro, urgente |
| `badge badge-info` | Azul #6a90a7 — informativo |

### Alertas Django (messages)
| Classe | Nível Django |
|--------|-------------|
| `alerta alerta-sucesso` | `messages.success` |
| `alerta alerta-info` | `messages.info` |
| `alerta alerta-aviso` | `messages.warning` |
| `alerta alerta-erro` | `messages.error` |

### Formulários
| Classe | Uso |
|--------|-----|
| `form-group` | Wrapper de campo (label + input + erro) |
| `form-control` | Inputs, selects, textareas |
| `form-error` | Mensagem de erro do campo |
| `form-ajuda` | Help text abaixo do campo |
| `obrigatorio` | Asterisco vermelho em labels obrigatórios |

### Utilitários
| Classe | CSS equivalente |
|--------|----------------|
| `d-flex` | `display: flex` |
| `gap-1` | `gap: 8px` |
| `gap-2` | `gap: 16px` |
| `align-center` | `align-items: center` |
| `justify-between` | `justify-content: space-between` |
| `text-center` | `text-align: center` |
| `w-100` | `width: 100%` |
| `mb-1/2/3` | margin-bottom 8/16/24px |
| `mt-1/2/3` | margin-top 8/16/24px |

### Componentes especiais
| Classe | Uso |
|--------|-----|
| `toggle` + `toggle-slider` | Switch liga/desliga |
| `paginacao` | Wrapper de paginação |

---

## Ícones por app — referência rápida

| App | Ícone Bootstrap |
|-----|----------------|
| clientes | `bi-people` |
| solar | `bi-sun` |
| serviços | `bi-tools` |
| balcão | `bi-shop` |
| ordens_servico | `bi-clipboard-check` |
| pos_venda | `bi-headset` |
| estoque | `bi-boxes` |
| financeiro | `bi-cash-coin` |
| configurações | `bi-gear` |
| usuários | `bi-person-circle` |

---

## Responsivo — breakpoints

| Breakpoint | Largura | Comportamento |
|------------|---------|---------------|
| Desktop | > 1000px | Sidebar visível, layout completo |
| Tablet | 630–1000px | Sidebar colapsada |
| Mobile | < 630px | Menu hambúrguer, layout empilhado |

---

## PROIBIDO

- Estilos inline — exceto `max-width`, `width` e `padding` pontuais
- Bootstrap framework (classes `container`, `row`, `col-*`, `btn-primary` do Bootstrap)
- Tailwind
- Cores hardcoded no HTML — sempre `var(--nome-da-variavel)`
- Criar CSS novo sem verificar se a classe já existe em `intelbras.css`
- JavaScript para o que é possível com HTML/CSS puro
