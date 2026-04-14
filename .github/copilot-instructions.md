# GitHub Copilot — Instruções do Projeto ERP Optimus

Para este projeto, siga rigorosamente a política de **Single Source of Truth (SSOT)** centralizada em `.agent/`.

> **Leia `.agent/INSTRUCTIONS.md` antes de sugerir qualquer código.**

---

## Regras Ativas de Desenvolvimento

1. **Stack e o que NÃO fazer:** Consulte `.agent/INSTRUCTIONS.md` — identidade visual é CSS puro Intelbras (sem Bootstrap framework, **sem Tailwind**, sem React, sem Vue).
2. **Dívida Técnica e Roadmap:** Não sugira refatorações arquiteturais sem antes consultar `.agent/ROADMAP.md`.
3. **Estado atual:** Todos os apps Django estão criados e funcionando. Nunca sugira recriar estruturas existentes.

## Convenções Rápidas

- CSS: sempre `var(--verde)`, nunca cor literal
- Ícones: `bi bi-nome` (Bootstrap Icons CDN)
- Forms: `field.widget.attrs["class"] = "form-control"`
- Models: herdam de `core.models.BaseModel`
- HTMX com `hx-target` e `hx-swap` **explícitos** — nunca defaults implícitos

*Todas as ferramentas LLM usadas no projeto (Copilot, Claude Code, Gemini Antigravity) compartilham desta base referencial.*
