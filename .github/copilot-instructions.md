# GitHub Copilot — ERP Optimus

> **Leia `AGENTS.md` na raiz do projeto antes de sugerir código.**

## Resumo de convenções

- CSS puro (`intelbras.css`) — **sem Bootstrap framework, Tailwind, React, Vue**
- Cores via variáveis CSS: `var(--verde)`, nunca literal
- Ícones: `bi bi-nome` (Bootstrap Icons CDN)
- Forms: `field.widget.attrs["class"] = "form-control"`
- Models: herdam de `core.models.BaseModel`
- HTMX: `hx-target` e `hx-swap` sempre explícitos

Todas as regras detalhadas estão em `AGENTS.md`.
