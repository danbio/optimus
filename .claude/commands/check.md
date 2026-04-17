Executa verificações de qualidade no projeto Optimus.

Prefira usar o script centralizado:
`.\scripts\check.ps1`

Para modo rápido (só lint + migrations, sem testes):
`.\scripts\check.ps1 -Quick`

Se precisar rodar manualmente, execute em sequência:

1. Ruff lint:
   `ruff check .`

2. Testes:
   `python manage.py test --verbosity=1`

3. Migrations pendentes:
   `python manage.py makemigrations --check --dry-run`

4. Deploy check:
   `python manage.py check --deploy`

Para cada problema encontrado:
- Explique o que significa
- Sugira como corrigir
- Indique o arquivo e linha exatos
