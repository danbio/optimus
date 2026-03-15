Execute as migrations Django no ERP Optimus.

Rode em sequência a partir da raiz do projeto:

0. Verificar se há migrations pendentes (sem aplicar ainda):
   `python manage.py migrate --check`
   - Se retornar código 0: tudo aplicado, perguntar se quer rodar makemigrations mesmo assim.
   - Se retornar código 1: há migrations não aplicadas, prosseguir.

1. `python manage.py makemigrations`

2. `python manage.py migrate`

3. Mostrar estado final:
   `python manage.py showmigrations`
   - Reportar quais apps têm `[ ]` (não aplicado) vs `[X]` (aplicado)
   - Se qualquer app mostrar `[ ]` após o migrate, sinalizar como erro e investigar

Reporte:
- Quais apps geraram novas migrations (se houver)
- Se o migrate completou sem erros
- Em caso de erro, mostre o traceback completo e sugira a correção

Nunca pule o makemigrations — rode sempre os dois passos juntos.
