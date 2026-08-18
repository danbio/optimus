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

**Achado novo (print do usuário, 2026-08-18):** ao preencher CEP + rua +
bairro, um **mapa do Google embutido** aparece abaixo do formulário com um
pino na localização — confirmação visual imediata do endereço, sem sair da
tela. Menu lateral também revela, quando "Novo Projeto" está expandido, a
taxonomia completa de tipos de projeto que a plataforma oferece (só
exploramos "On Grid → Dimensionado" até agora):

```
Avulso
On Grid
  Dimensionado   ← o que exploramos
  Personalizado  ← provavelmente sem motor de sugestão automática
  Kits           ← pacotes pré-configurados
  Híbrido
    Dimensionado
Off Grid
  Dimensionado
  Kits
```

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
  consumo do cliente"** — dois modos de entrada.

  **Detalhe do segundo modo (print do usuário, 2026-08-18)**, que é o mais
  parecido com o que já temos, mas bem mais rico: ao selecioná-lo, abre
  **"Do mês" / "Até o mês"** (dois seletores de mês/ano, ex.: Mai/2026 a
  Jun/2026) definindo uma janela, e então **um campo de consumo em kWh por
  cada mês daquele intervalo** (ex.: Mai/2026 → 250,00, Jun/2026 → 423,00).
  Só depois disso um botão **"CALCULAR POTÊNCIA"** preenche a "Potência
  desejada em kWp" (read-only).

  Ou seja: em vez de um único campo "consumo médio mensal" (o que
  `PropostaSolar.consumo_medio_kwh` faz hoje), eles pedem o **histórico
  real de consumo mês a mês** direto das últimas faturas do cliente, e a
  média/dimensionamento sai daí. É mais fiel ao consumo real (que varia por
  mês, principalmente em imóvel com ar-condicionado sazonal) do que um
  número médio digitado de memória pelo vendedor. Contraponto: mais campos
  pra preencher — bate direto no princípio dele de "não travar por
  informação faltante", já que aqui a informação detalhada que ajudaria a
  precisão não é obrigatória (o modo 1, potência direta, continua
  disponível pra quem não tem os dados em mãos).

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

- **Tipo de proposta** — dropdown com pelo menos duas opções, confirmadas
  em duas explorações diferentes:
  - **"Apenas gerador sem instalação"** — só o equipamento.
  - **"Gerador com instalação"** — revela um campo a mais, **"Valor do
    serviço líquido (R$)"**, digitado manualmente pelo vendedor (não
    calculado — ex.: R$ 5.000,00 no print do usuário).

  Confirma formalmente (na visão do próprio fabricante) que equipamento e
  instalação são tratados como coisas separadas — igual ao que fizemos com
  `valor_equipamentos` (repasse) vs `valor_instalacao` (receita).

  **Achado novo (print do usuário, 2026-08-18) — gross-up de imposto no
  serviço:** o vendedor digitou "Valor do serviço líquido" = R$ 5.000,00,
  mas o painel "Valores:" à direita mostra **"Valor do serviço da revenda
  com PIS/COFINS" = R$ 5.500,55** (ícone ⓘ do lado, não explorado). Isso é
  um gross-up de ~10,01% aplicado ao valor líquido digitado — ou seja, a
  Intelbras faz pro **serviço da revenda** o mesmo tipo de conta que fizemos
  pro **consumo de energia** em `aplicar_tributos()` (`solar/services.py`):
  o vendedor digita o valor líquido que quer receber, o sistema mostra o
  valor bruto com tributo embutido pro cliente. Não temos isso hoje —
  `valor_instalacao` é digitado e usado direto, sem gross-up de ISS/PIS/
  COFINS sobre o serviço. Vale investigar se a Optimus tem tributação sobre
  o serviço de instalação que hoje não está sendo refletida no valor
  mostrado ao cliente (pergunta pro usuário, não decisão minha).

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
  esperada dado que são fontes/anos diferentes; **confirmado idêntico em
  duas explorações**, então é fixo por local, não varia com o sistema),
  potência do gerador, **peso do gerador (kg)** e **peso do gerador no
  telhado (kg)** — dado de engenharia que não expomos hoje, e que já temos
  a matéria-prima pra calcular (`peso` já existe em `ModuloFotovoltaico`).
  Exemplos reais capturados: 5,58 kWp → 338,15 kg / 328,90 kg no telhado;
  3,10 kWp → 180,39 kg / 174,99 kg no telhado (a diferença entre peso total
  e peso "no telhado" deve ser o peso do inversor, que geralmente não fica
  no telhado).

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

## 2. Belenus — "Gerador Personalizado" (`belenus.com.br/energy/modulo`)

Explorado pelo próprio usuário (prints, 2026-08-18), logado como `Optimus
Empreendimentos L...`. Veredito dele, nas próprias palavras: **"O fluxo é
muito semelhante mas a experiência da Intelbras é mais agradável."** — ver
§3 pra síntese do porquê.

### 2.1 Estrutura do wizard — 6 passos, começa pelo técnico, não pelo cliente

```
1 Módulo → 2 Inversor → 3 Estrutura → 4 Componentes Elétricos CC
  → 5 Componentes Elétricos CA → 6 Confirmação
```

**Diferença estrutural mais importante em relação à Intelbras:** aqui o
fluxo começa **sem identificar o cliente nenhum** — só pede de onde comprar
(UF de faturamento) e a potência do sistema. O cliente só é anexado no
**último passo** (Confirmação), como campo opcional ("Cadastrar cliente").
É o oposto exato da Intelbras, que abre pedindo nome/UF/cidade do cliente
antes de qualquer cálculo técnico.

### 2.2 Passo 1 — Módulo

- `1º) ESCOLHA POR ONDE QUER COMPRAR:` — UF de faturamento (já veio
  preenchido "BELENUS - GO", com link "Alterar")
- `2º) INFORME A POTÊNCIA DO SISTEMA:` — um único campo `kWp` + botão `›`.
  Sem alternativa de "calcular a partir do consumo" nesta tela (diferente
  da Intelbras, que oferece os dois modos já no passo 1).
- Depois de informar a potência, lista os módulos disponíveis (os mesmos 3
  que já cadastramos: RONMA 585W, TCL 615W, Astronergy 715W) numa tabela:
  Produto | Potência (W) | **Qtd. Módulo sistema** (editável, +/-) |
  **Potência do sistema (kWp)** (recalcula ao vivo conforme a quantidade)
  | Selecionar (radio).
  Ordenação por "Menor Preço Por Watt" — outra forma de comparar módulos
  que não é só preço total.

### 2.3 Passo 2 — Inversor

- Barra de resumo fixa no topo: `Qtd. Módulos: 9 | Potência do sistema:
  5.26 kWp` — esse resumo acompanha o usuário nas telas seguintes também
  (mesmo princípio da caixa "Premissas de Cálculo" da Intelbras, mas com
  números do projeto em vez de metodologia).
- Filtros: tipo de inversor (String On-Grid), tipo de ligação (Monofásico),
  tensão de saída (127/220V), **fabricante — multi-select com checkbox**
  (Auxsol, Deye, Growatt, Huawei, Solis, Sungrow, com busca).
  Texto de ajuda memorável: *"Ao selecionar todos os fabricantes ou manter
  este campo em branco a plataforma selecionará a opção de melhor
  custo-benefício em nosso catálogo."* — ou seja, filtro vazio não é "sem
  resultado", é "deixa o sistema escolher o melhor pra você". Um padrão de
  default inteligente que vale considerar.
- **Achado direto pra nós:** a tabela de resultado mostra, por inversor,
  três números na coluna "Potências": `4 kW (Potência Nominal)` / `5.26
  kWp (Potência Sistema)` / **`31,50% Overload utilizado`**. Esse
  "% Overload" é a mesma conta que já fazemos em
  `inversores_compativeis()` (`ratio_pct = kwp / potencia_kw × 100`), só
  que a Belenus expõe direto na tabela de escolha (positivo = sistema
  acima da potência nominal do inversor; negativo = inversor
  superdimensionado, ex. `-47,40%`) em vez de só marcar
  compatível/incompatível como fazemos hoje. Mostrar o percentual bruto,
  não só um badge, dá mais contexto pro vendedor decidir.

### 2.4 Passo 3 — Estrutura

- Barra de resumo cresce a cada passo: agora mostra também `Qtd.
  Inversores`, `Máx. potência de entrada`, `Máx. potência saída`.
- Toggle `Com Estrutura` / `Sem Estrutura`.
- Por "Arranjo" (suporta múltiplos arranjos — `+ Adicionar arranjo` —
  pensado pra telhados com mais de uma água/orientação): tipo de
  estrutura, detalhe do modelo específico (dropdown dentro do tipo — ex.
  "Haste de aço inoxidável - Modelo com 200mm..."), número de linhas,
  módulos por linha, tipo de orientação (retrato/paisagem).
- `Layout dos Módulos: Você utilizou 9 dos 9 módulos selecionados` — mesmo
  contador da Intelbras ("módulos restantes"), só que contando pra cima em
  vez de para baixo.
- **Achado rico que a Intelbras não tinha:** descrição técnica detalhada
  do componente específico escolhido (ex. explica que é "ideal para telhas
  de fibrocimento com estruturas de terças em madeira", medidas exatas),
  **galeria de fotos** do produto (parafusos, hastes, suporte) e **vídeos
  embutidos** — "Montagem em telhado" e "Montagem do conjunto". A
  Intelbras só tinha um aviso de texto pra "consultar o datasheet"; aqui
  tem tutorial em vídeo dentro do próprio fluxo.

### 2.5 Passos 4/5 — Componentes Elétricos CC / CA

Mesma lógica de "receita automática" que a Intelbras (§1.7) — a partir do
arranjo de estrutura, sugere quantidade de cada material, mas com marca
própria (**BelEnergy**, não Belenus) em todos os itens:

```
Garra Aterramento 2 peças        (qtd sugerida 1)
Grampo Final 30mm 4 peças        (qtd sugerida 1)
Grampo Intermediário 2 peças     (qtd sugerida 8)
Haste Solar 10mm x 200mm 2 peças (qtd sugerida 6)
Junção para Perfil 1 peça        (qtd sugerida 8)
Perfil Fixação 1,23m             (qtd sugerida 2)
Perfil Fixação 2,36m             (qtd sugerida 8)
Suporte Pé em L Fibrocimento     (qtd sugerida 6)
```

Cada linha tem quantidade editável (+/-) **e um ícone de lixeira pra
remover o item da lista inteiro** — a Intelbras só deixava zerar a
quantidade, não removia a linha.

**Isso confirma com um segundo fornecedor** que o motor de "receita de
materiais a partir do arranjo físico" (§1.7 e ideia já anotada) não é
peculiaridade de uma empresa — é o padrão esperado do setor. Reforça a
prioridade dessa ideia se um dia for implementada.

### 2.6 Passo 6 — Confirmação

- **Resumo do Orçamento** (potência, qtd. módulos, qtd. inversores*,
  potência máx. entrada/saída) + link "Ver detalhe dos itens" que expande
  uma lista rolável com logo da marca, quantidade e nome de cada item
  (módulos, inversor, todos os componentes de fixação).

  *bug observado no site deles, não replicar: o card "Qtd. Inversores"
  mostrou "5.26" (igual à potência do sistema) em vez de "1" — aparente
  erro de binding no formulário deles.

- **Só aqui** aparecem: nome da proposta, e "Dados de entrega" (UF/cidade
  — não pede mais que isso) com botão "Cadastrar cliente" — de novo, o
  cliente é anexado no fim, não no início.
- **Valor dos produtos** (R$) — separado.
- **Valor dos serviços** — campo vazio com aviso: *"O valor do frete
  poderá ser alterado caso haja um valor de serviço."* ⚠️ Aqui "serviço"
  parece se referir a **frete/logística de entrega**, não instalação —
  sentido diferente do "Valor do Serviço" da Intelbras (que era mão de
  obra de instalação). Não confundir os dois ao comparar.
- **Seguro de instalação** — toggle opcional. Produto que não existe na
  Intelbras nem na Optimus hoje.
- **Cupons disponíveis** — sistema de cupom de desconto.
- **"Vantagens de financiar com a gente"** — 3 cards de desconto
  (6% / 5% / 5%) por forma de financiamento (BelEnergy, e dois bancos
  parceiros), cada um já mostrando o valor de desconto em R$. Empilha
  incentivo de financiamento com desconto — mais agressivo comercialmente
  que a Intelbras (que só linkava "simular financiamento").
- Botões finais: **Voltar / Baixar PDF / Salvar / Comprar Agora**.

### 2.7 O flavor geral é "carrinho de e-commerce", não "proposta comercial"

Ao longo do fluxo aparecem elementos claramente herdados de loja virtual:
"ADICIONAR AO CARRINHO" na navegação de catálogo, ícone de carrinho no
header, cupom de desconto, "Comprar Agora" como call-to-action final. É
coerente — a Belenus é, antes de tudo, um distribuidor com loja online, e
o "Gerador Personalizado" parece ser essa mesma engine de e-commerce
reaproveitada para montar um kit. Contraste com a Intelbras, que é
construída do zero como ferramenta de **gestão de propostas** (tem funil
de vendas, dashboard, "menu de projetos" com 1.292 registros — ver §1.1 e
§1.9) e só depois conecta com a compra dos produtos.

---

## 3. Diagnóstico — por que a Intelbras "é mais agradável" (síntese)

Veredito do usuário, comparando os dois fluxos que acabou de percorrer
lado a lado. Acho que dá pra apontar 3 diferenças estruturais que
explicam a percepção, não só "polish" visual:

1. **Personalização desde o primeiro clique vs. só no fim.** A Intelbras
   abre perguntando o nome do cliente — a sensação é "estou montando a
   proposta do Fulano" do início ao fim. A Belenus constrói um kit
   genérico e só amarra num cliente na última tela — a sensação é "estou
   configurando um produto", e o cliente é quase um detalhe de checkout.
   Pra um vendedor cujo trabalho é justamente gerenciar propostas de
   clientes específicos (não vender peça avulsa), o primeiro modelo casa
   melhor com a tarefa mental que ele já está fazendo.
2. **Ferramenta de gestão vs. loja reaproveitada.** A Intelbras tem funil
   de vendas, dashboard, lista de projetos com 1.292 registros — foi
   desenhada pra alguém acompanhar múltiplas propostas ao longo do tempo.
   A Belenus tem cupom de desconto e botão "Comprar Agora" — foi desenhada
   pra fechar uma compra. São otimizações diferentes: uma pra "gerenciar
   relacionamento comercial", outra pra "converter carrinho". A Optimus
   (ver skill financeiro-domain — venda direta, sem margem, faturamento
   vem de instalação/manutenção) se parece mais com o primeiro caso: o
   valor do negócio dela está em administrar bem o relacionamento e o
   serviço, não em vender peça.
3. **Confiança/transparência visível o tempo todo.** A caixa fixa
   "Premissas de Cálculo" da Intelbras aparece em toda tela do wizard,
   sempre visível — dá segurança que a metodologia é conhecida e estável
   página a página. A Belenus não repete esse tipo de rodapé explicativo
   (compensa em outro lugar — fotos/vídeo do produto — mas não no mesmo
   nível de "aqui está a fórmula que estou usando").

**Implicação pro nosso desenho, se formos adotar o padrão wizard:** manter
os dados do cliente como ponto de partida (já é assim hoje —
`PropostaSolar.cliente` é o primeiro campo do form) parece a escolha certa
a preservar, não uma coisa a questionar. O ganho de imitar a Intelbras
está mais na **estrutura de passos com resumo fixo/premissas visíveis** e
no **motor de materiais a partir do arranjo físico** (confirmado por dois
fornecedores agora) do que em copiar a ordem do fluxo Belenus.

---

## 4. Ideias de aplicação — só anotadas, nada decidido

Não é lista de tarefas. É o que ficou de "isso poderia inspirar X" pra
revisitar quando o usuário decidir o que priorizar. Já cobre as duas
referências (Intelbras + Belenus).

- Formulário de proposta com **passos/abas visíveis** (tipo wizard) em vez
  de um formulário longo único — mais parecido com o que a equipe já
  conhece. **Manter os dados do cliente como primeiro passo** (padrão
  Intelbras, não Belenus — ver §3, item 1: casa melhor com o trabalho real
  do vendedor).
- **Resumo fixo/crescente no topo do wizard** conforme o vendedor avança
  (ex.: "Qtd. módulos: 9 · Potência: 5,26 kWp · Qtd. inversores: 1 · Máx.
  entrada: 6 kW") — confirmado nos dois fornecedores, dá contexto sem
  precisar rolar a tela pra cima.
- **Motor de "receita" de materiais** por {tipo de estrutura} × {fileiras}
  — confirmado em **dois** fornecedores agora (Intelbras §1.7, Belenus
  §2.5), não é peculiaridade de um só. É a maior alavanca pra resolver o
  catálogo vazio de estrutura/material, mas também a peça de maior esforço
  de implementação de tudo isso.
- Mostrar o **percentual de overload/subdimensionamento** direto na tabela
  de seleção de inversor (ex. "31,50% Overload utilizado"), não só um
  badge compatível/incompatível — é a mesma conta que `ratio_pct` já faz
  em `inversores_compativeis()`, só falta expor o número.
- **Default inteligente quando o filtro fica vazio** ("não selecionar
  nenhuma marca = deixamos o sistema escolher o melhor custo-benefício")
  em vez de "sem resultado" — vale considerar em qualquer filtro nosso que
  hoje trata vazio como ausência de critério.
- Permitir **remover uma linha de material inteira** (não só zerar
  quantidade) na lista de itens sugeridos — Belenus tem, Intelbras não.
- Fotos/vídeo de instalação embutidos na tela de escolha de estrutura —
  ideia de conteúdo, não de dado; baixo prioridade técnica mas alto valor
  de confiança pro cliente que vê o material depois.
- Padronizar visualmente quais campos são realmente obrigatórios (poucos)
  vs opcionais (a maioria), e deixar isso claro na tela — hoje o form tem
  bastante `<span class="obrigatorio">*</span>` espalhado, vale revisar se
  todos precisam ser mesmo.
- Considerar um segundo modo de dimensionamento: **potência desejada
  direto**, além do "a partir do consumo" que já existe.
- Trocar o campo único "consumo médio mensal" por **consumo mês a mês**
  (janela de datas + um valor por mês) — mais fiel ao histórico real de
  fatura do cliente, ao custo de mais campos (mas nenhum obrigatório).
- Mapa embutido (Google Maps) na tela de endereço do cliente — feedback
  visual imediato, baixo esforço se já tivermos uma API key de mapas
  disponível (verificar).
- **Investigar se o serviço de instalação da Optimus tem tributo (ISS?)
  que deveria aparecer como gross-up no valor mostrado ao cliente** —
  achado da Intelbras (serviço líquido digitado vs. bruto com PIS/COFINS
  mostrado) sugere que isso é prática comum no setor. Pergunta pro
  usuário, não decisão técnica.
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
