# Referência de UX — Fluxo de Propostas Solares em Fornecedores

> **Por quê este arquivo existe:** o usuário pediu (2026-08-18) para estudar
> o fluxo de dimensionamento/proposta da Intelbras e, em seguida, da Belenus,
> como inspiração para redesenhar `solar/templates/solar/proposta_form.html`
> e o funil de status da `PropostaSolar`. Intenção dele, nas próprias
> palavras:
>
> - Imitar a **lógica e o layout** de preenchimento — não é capricho
>   estético: a equipe dele já está habituada a esse fluxo (treino zero) e
>   ele acha o fluxo logicamente bem construído.
> - **Informação faltante não trava a proposta** — mas quanto mais o
>   vendedor preenche, mais completa ela fica. Isso já é parcialmente o que
>   fizemos com `valor_equipamentos_manual` e `PropostaSolar.pendencias`
>   (avisa, não bloqueia), mas vale revisar o formulário inteiro sob essa
>   ótica.
> - Gosta muito do **"roadmap visual"** — as etapas que faltam percorrer
>   ficam visíveis o tempo todo.
> - Confirmado nesta sessão: **a base de tarifa da Intelbras está
>   desatualizada** (R$ 0,98/kWh vs R$ 1,38 real da fatura Energisa TO) —
>   não usar como fonte de tarifa, só como referência de UX/fluxo.
>
> Este documento é só **registro de observação**, não plano de ação. Nada
> aqui foi implementado. Ver ROADMAP.md quando houver decisão do que
> construir.

---

## 1. Intelbras — Portal Projetos Solar (`projetos-solar.intelbras.com.br`)

Explorado via sessão assistida (Claude in Chrome, usuário logado como
`REVENDA_GESTOR`). Conta real tem **1.292 projetos**.

### 1.1 O wizard tem DOIS roadmaps visuais, não um

Isso é o achado mais importante pra imitar:

1. **Roadmap dentro da criação** — 5 abas fixas no topo, sempre visíveis,
   cada uma vira ✅ verde ao ser validada:
   `CONFIGURAÇÕES → MÓDULOS → INVERSORES → SOLUÇÃO → VALOR TOTAL`
2. **Roadmap do ciclo de vida do projeto** — depois de criado, o projeto
   entra num funil comercial/logístico próprio (`Etapa de Venda`), e a
   **lista de projetos** mostra um banner por card dizendo qual é a
   próxima ação:
   > "PRÓXIMA AÇÃO DISPONÍVEL — Este projeto já está pronto para avançar
   > para a próxima etapa do processo" + botão de ação (`CONFIRMAR VISITA
   > TÉCNICA`)

   Isso é diferente de simplesmente mostrar o status atual (como nosso
   badge `rascunho/enviada/aprovada/...`) — é dizer explicitamente **o que
   fazer em seguida**, sem o vendedor ter que adivinhar.

### 1.2 Etapas do funil comercial (`Etapa de Venda`)

```
Pré-orçamento
Proposta Final
Projeto cancelado
Pagamento reconhecido
Processando Informações do Pedido
Em Trânsito
Produto Entregue
Projeto Finalizado
```

⚠️ Metade disso (`Pagamento reconhecido`, `Processando Informações do
Pedido`, `Em Trânsito`, `Produto Entregue`) é **logística de entrega física
do equipamento pela Intelbras** — não se aplica 1:1 à Optimus, porque a
Optimus não entrega nada fisicamente (venda direta fornecedor→cliente, ver
skill financeiro-domain). O que vale copiar é a *forma* (funil visível,
etapa clara, ação sugerida), não necessariamente os nomes das etapas.

### 1.3 Tela 1 — Dados do cliente

Campos, e quais tinham `*` (obrigatório) vs sem asterisco (opcional):

| Campo | Obrigatório? |
|---|---|
| Título do projeto | não |
| Nome do cliente | **sim** |
| E-mail | não |
| CPF/CNPJ | não |
| CEP | não |
| UF | **sim** |
| Cidade | **sim** |
| Rua, Número, Bairro, Telefone | não |

Ou seja: o mínimo pra começar é nome + UF + cidade. Tudo que dá acabamento
(endereço completo, contato) é opcional — o vendedor preenche depois, ou
nunca, sem travar.

### 1.4 Tela 2 — Configurações do Gerador

Campo mais rico do fluxo. Campos:

- **Tensão da rede da concessionária** (127/220 ou 220/380)
- **Número de fases** (Monofásico / Bifásico / Trifásico)
- **Concessionária** — dropdown que busca por **sigla** (ex.: `ETO` pra
  Energisa Tocantins — a mesma sigla que já usamos, vinda da ANEEL).
  Confirma que `Distribuidora.sigla` é o identificador certo a expor pro
  vendedor, não o nome completo.
- **Fator de perdas (%)** — validação embutida: *"O fator de perdas
  sugerido mínimo é 15%"* (equivale a um fator de eficiência máximo de
  0,85; nosso padrão de 0,75 = 25% de perdas está dentro da faixa aceita
  por eles).
- **Tipo de inversor** (Inversor / outros — não explorei as opções)
- **Tipo de projeto** (Grupo B / Grupo A — classificação tarifária)
- **Preço do kWh com imposto** — **preenche sozinho** assim que a
  concessionária é escolhida (base de tarifa própria deles — confirmado
  desatualizada, ver acima)
- **Simultaneidade (%)** — com sugestão inline: *"Sugestão: 25% residencial
  e 50% comercial"*. Bate quase exato com o que já documentamos pra
  `autoconsumo_simultaneo_pct` na skill solar-domain.
- **Potência desejada (kWp)**
- Toggle: **"Informar a potência desejada"** vs **"Calcular com base no
  consumo do cliente"** — dois modos de entrada. Hoje só temos o segundo
  (a partir do consumo).

Uma caixa fixa **"Premissas de Cálculo"** aparece em todas as telas do
wizard, documentando a metodologia (fonte do HSP, fórmula de geração
mensal, o que assume sobre inclinação/sombreamento). É basicamente uma
versão visível-pro-usuário do que documentamos na skill solar-domain, mas
dentro do próprio formulário.

### 1.5 Tela 3 — Módulos

- Lista os módulos do catálogo próprio (só 2 disponíveis: um Intelbras, um
  parceiro FINAME/BYD — confirma o que o usuário já tinha dito, catálogo
  solar da Intelbras é bem limitado).
- Cada linha mostra: nome, fabricante/tecnologia, **quais inversores são
  compatíveis** (ícones), **quantidade sugerida** (calculada a partir da
  potência desejada — pré-preenchida, editável com +/-), link pro
  datasheet.
- **"Disposição dos módulos e fileiras"** — aqui está o achado mais valioso
  de toda a exploração:
  - Posição do módulo (Retrato / Paisagem)
  - Tipo de estrutura — dropdown com **exatamente os mesmos valores** que
    já temos em `EstruturaFixacao.tipo`: telha cerâmica, fibrocimento,
    metálica perfil, metálica mini-trilho, laje, solo.
  - Módulos em sequência / Fileiras iguais / botão "+ Adicionar Fileira"
  - Mostra "Metragem total" e "Módulos restantes" (contador que zera
    quando a disposição bate com a quantidade sugerida)
  - Esse layout físico (fileiras × posição × tipo de estrutura) é o que
    **alimenta automaticamente a lista de materiais** na tela seguinte.

### 1.6 Tela 4 — Inversores

- Escolhe uma "linha" (ex.: `IONS`, `RGT` — linhas próprias Intelbras)
- Lista os modelos da linha com quantidade **pré-sugerida** — o mais
  próximo da potência desejada já vem com `1` marcado. Mesma lógica que
  `inversores_compativeis()` (ordenar pelos mais próximos de 100% da
  relação CC:CA), só que a Intelbras já cravam a sugestão em vez de só
  mostrar compatibilidade.

### 1.7 Tela 5 — Solução (a peça que resolve nosso catálogo vazio)

A partir do layout de fileiras/estrutura da tela 3, gera **automaticamente**
uma lista de materiais com quantidade sugerida (editável com +/-):

- Kit de fixação (específico pro tipo de telha escolhido)
- Perfil (par)
- Grampo intermediário / grampo final
- Kit de junção
- Protetor elétrico / string box (múltiplas variantes por corrente/entradas)
- Cabo solar por cor e bitola (vermelho/preto/verde, 4mm/6mm, só em
  múltiplos de 25m)
- Medidor de energia trifásico, transformador de corrente
- Dispositivo de monitoramento (logger), dispositivo de desligamento
  rápido (RSD), transmissor de sinal

Cada item tem um texto "Informações" explicando regra de uso (ex.: *"Já
disponível dentro dos kits de fixação, verificar quantidades extras"*,
*"Utilizar a cada 2 módulos"*).

**Isso é, em essência, uma tabela de "receita" (BOM — bill of materials)
por combinação de {tipo de estrutura} × {quantidade de módulos/fileiras}.**
É o que resolveria de vez o problema anotado no ROADMAP ("catálogo
praticamente vazio de estrutura/material") sem depender só de cadastro
manual item a item.

### 1.8 Tela 6 — Valor Total ("Valor do Serviço")

- **Tipo de proposta** — dropdown, vi a opção **"Apenas gerador sem
  instalação"**. Confirma formalmente (na visão do próprio fabricante) que
  equipamento e instalação são tratados como coisas separadas — igual ao
  que fizemos com `valor_equipamentos` (repasse) vs `valor_instalacao`
  (receita).
- **Custo anual com manutenção** — campo que não temos. Como manutenção é
  uma das duas pernas do faturamento real da Optimus (a outra é
  instalação), pode valer a pena um campo equivalente.
- Ícones de bandeira de cartão + bancos de financiamento (BV, Santander,
  Credz) — visual, não funcional pra nós (financiamento bancário
  continua fora de escopo).
- Botão **"Simular Financiamento"**, com aviso explícito: *"Sem a
  simulação, o financiamento não será incluído na proposta"* — financiamento
  é opt-in, não afeta o valor base se ignorado.
- **Resumo do projeto**: título, HSP médio (**5,28** pra Gurupi/TO, base
  INPE 2006 — vs nosso **5,58** via NASA POWER; diferença de ~5,7%,
  esperada dado que são fontes/anos diferentes), potência do gerador,
  **peso do gerador (kg)** e **peso do gerador no telhado (kg)** — dado de
  engenharia que não expomos hoje, e que já temos a matéria-prima pra
  calcular (`peso` já existe em `ModuloFotovoltaico`).

### 1.9 Menu Projetos (lista) — card rico

Cada card mostra, sem precisar abrir o detalhe:

- Código do projeto + badge de etapa (`PRÉ-ORÇAMENTO` etc.) + nome do cliente
- Botões: Detalhes / Editar / Ações
- Grid: Potência do Gerador (kWp) | Valor Total | Criado em
- **Valor dos produtos Intelbras | Valor dos produtos com desconto | Valor
  do Serviço PIS/COFINS** — de novo a separação equipamento vs serviço,
  agora com o imposto do serviço destacado à parte
- Pagamento | Status de pagamento | Desconto
- Previsão de faturamento | Pedido | Nota fiscal
- Cliente | Revenda (com CNPJ) | Distribuidor (com CNPJ)
- Criado por | Executivo de vendas
- Nota quando aplicável: *"Projeto clonado de PROJ..."* — **funcionalidade
  de clonar proposta existente**, não vimos isso anotado antes.
- Faixa diagonal vermelha no canto: **"Expira em N dias"** — indicador de
  validade da proposta, visualmente agressivo (chama atenção sem precisar
  abrir o card).
- Filtros disponíveis: código do projeto, título, segmento, status de
  pagamento, etapa de venda, + filtro avançado.

### 1.10 Dashboard

KPIs (com filtro de período por data de criação + etapa de venda):

- Total de propostas emitidas
- Ticket médio por gerador
- Valor total dos geradores
- Potência total dos geradores (kW)
- Potência média por gerador (kW)
- **Valor do serviço** (destacado à parte do valor do gerador — mesmo
  princípio de novo)

Dois gráficos por tempo: quantidade de propostas (barras) e **valor dos
projetos vs valor dos serviços** (duas linhas separadas) — exatamente o
tipo de separação `receita`/`repasse` que já implementamos em
`LancamentoFinanceiro.tipo`. Dá ideia de como visualizar isso num dashboard
nosso (hoje `financeiro/dashboard.html` já separa os KPIs de receita do
card de repasse, mas não tem gráfico de série temporal comparando os dois).

---

## 2. Belenus — Portal do Parceiro

*(a preencher — usuário vai mostrar o fluxo em seguida)*

---

## 3. Ideias de aplicação — só anotadas, nada decidido

Não é lista de tarefas. É o que ficou de "isso poderia inspirar X" pra
revisitar quando o usuário decidir o que priorizar, depois de ver a
Belenus também.

- Formulário de proposta com **passos/abas visíveis** (tipo wizard) em vez
  de um formulário longo único — mais parecido com o que a equipe já
  conhece.
- Padronizar visualmente quais campos são realmente obrigatórios (poucos)
  vs opcionais (a maioria), e deixar isso claro na tela — hoje o form tem
  bastante `<span class="obrigatorio">*</span>` espalhado, vale revisar se
  todos precisam ser mesmo.
- Considerar um segundo modo de dimensionamento: **potência desejada
  direto**, além do "a partir do consumo" que já existe.
- Motor de "receita" de materiais por {tipo de estrutura} × {fileiras} —
  maior alavanca pra resolver o catálogo vazio de estrutura/material,
  mas é a peça de maior esforço de implementação de tudo isso.
- Peso do gerador (total e "no telhado") no PDF/detalhe — baixo esforço,
  já temos o dado (`peso` do módulo).
- "Próxima ação sugerida" na tela de detalhe/lista de propostas, não só o
  status atual — se cruza com `PropostaSolar.pendencias`, que já existe
  mas hoje só lista o que falta, não sugere a próxima ação em si.
- Indicador visual de validade da proposta (a faixa "Expira em N dias") —
  já temos `PropostaSolar.validade`, só falta destacar visualmente.
- Clonar proposta existente — não temos essa ação hoje.
- Campo de custo anual de manutenção — só faz sentido se/quando o módulo
  de manutenção recorrente for modelado (hoje só existe `ordens_servico`
  pontual e `pos_venda`, sem contrato recorrente).
