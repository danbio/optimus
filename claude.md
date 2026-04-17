# Claude Code — ERP Optimus

> **Leia `AGENTS.md` antes de qualquer ação.** Ele é a fonte única de verdade para todos os agentes.

## Referências rápidas

- 📋 **Regras e stack:** `AGENTS.md`
- 🛣️ **Dívida técnica:** `.agent/ROADMAP.md`
- 📓 **Log de sessões:** `.agent/DIARIO.md`
- 🎨 **Skills de domínio:** `.claude/skills/*.md`

## Verificação

Sempre rodar antes de commitar:

```powershell
.\scripts\check.ps1
```

Ou manualmente: `ruff check . && python manage.py test && python manage.py makemigrations --check --dry-run`
