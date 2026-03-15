Executa os testes Django do Optimus.

Com argumento (app específico):
`python manage.py test $ARGUMENTS --verbosity=2`

Sem argumento (todos os testes):
`python manage.py test --verbosity=2`

Após executar, reporte:
- Quantos testes passaram, falharam ou deram erro
- Para falhas/erros: traceback completo e sugestão de correção
- Se 0 testes foram encontrados: lembre que arquivos de teste devem se chamar `test_*.py` e as classes devem herdar de `django.test.TestCase`