Executa verificações de qualidade no projeto Optimus.

Execute em sequência:

1. Ruff — diagnóstico sem auto-fix (apenas reporta):
   `ruff check .`

2. Django system check — valida models, URLs e configurações:
   `python manage.py check`

Para cada problema encontrado:
- Explique o que significa a violação
- Sugira como corrigir
- Indique o arquivo e linha exatos quando possível

Esta é uma operação somente leitura — não aplique correções automaticamente.