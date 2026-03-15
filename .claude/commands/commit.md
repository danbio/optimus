Cria um commit Git com mensagem padronizada para o ERP Optimus.

Execute em sequência:

1. Verificar o estado atual:
   `git status`
   `git diff --staged`

   Se não houver arquivos staged, perguntar ao usuário quais arquivos incluir antes de prosseguir.

2. Gerar mensagem de commit seguindo o formato:
   `<prefixo>(<app>): <descrição imperativa em português>`

   Prefixos válidos:
   - `feat` — nova funcionalidade
   - `fix` — correção de bug
   - `refactor` — refatoração sem mudança de comportamento
   - `migration` — nova migration Django
   - `chore` — configuração, dependências, arquivos não-funcionais
   - `docs` — documentação

   App: nome do app Django afetado (clientes, estoque, solar, etc.) ou `config` para settings/urls globais.

   Exemplos:
   - `feat(clientes): adiciona validação de CPF e CNPJ`
   - `migration(estoque): adiciona campo preco_custo em Produto`
   - `fix(financeiro): corrige cálculo de parcelas com desconto`

   Máximo 72 caracteres na linha do assunto.

3. Mostrar a mensagem gerada e aguardar confirmação antes de commitar.

4. Após confirmação:
   `git commit -m "<mensagem>"`

5. Confirmar resultado:
   `git log --oneline -5`
