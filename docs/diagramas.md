# Diagramas do Sistema ERP

> Gerado com Mermaid. Renderiza no GitHub, GitLab, Obsidian e VSCode (extensão Mermaid Preview).

---

## 1. Arquitetura Geral — Apps e Dependências

```mermaid
flowchart LR
    subgraph "Base"
        CORE[core\nBaseModel]
    end

    subgraph "Compartilhados (base)"
        CLI[clientes]
        EST[estoque]
        FIN[financeiro]
    end

    subgraph "Linhas de negócio"
        SOL[solar]
        SER[servicos]
        BAL[balcao]
    end

    subgraph "Operações"
        OS[ordens_servico]
        PV[pos_venda]
    end

    CORE -.->|herança| CLI
    CORE -.->|herança| EST
    CORE -.->|herança| FIN

    CLI --> SOL
    CLI --> SER
    CLI --> BAL
    CLI --> OS

    SOL --> OS
    SER --> OS

    EST --> SOL
    EST --> SER
    EST --> BAL

    OS  --> FIN
    BAL --> FIN
    OS  --> PV
```

---

## 2. Ciclo de Vida Completo de uma Venda

```mermaid
flowchart TD
    A([Lead / Cliente]) --> B{Qual linha?}

    B -->|Solar| C[Dimensionamento técnico]
    B -->|Serviço| D[Proposta de serviço]
    B -->|Balcão| E[Venda direta]

    C --> F[Proposta Solar]
    F --> G{Cliente aprova?}
    G -->|Não| F
    G -->|Sim| H[Entrada / sinal]

    D --> I{Cliente aprova?}
    I -->|Não| D
    I -->|Sim| H

    H --> J[Compra / pedido de equipamentos]
    J --> K[Ordem de Serviço]
    K --> L[Instalação]
    L --> M[Recebimento final]
    M --> N[Pós-venda / garantia]

    E --> O[Recebimento]
    O --> P([Fim — sem OS])
```

---

## 3. Fluxo Solar — Detalhado

```mermaid
flowchart TD
    A([Cliente]) --> B[Cadastro / qualificação]
    B --> C[Levantamento de consumo kWh]
    C --> D[Dimensionamento\nkWp · painéis · inversor\nHSP Tocantins = 5,2]
    D --> E[Proposta Solar\ncom payback e TIR]
    E --> F{Aprovada?}
    F -->|Revisão| E
    F -->|Sim| G[Contrato + entrada]
    G --> H[Pedido equipamentos\nno estoque / fornecedor]
    H --> I{Equipamentos\ndisponíveis?}
    I -->|Não| J[Aguardar entrega]
    J --> I
    I -->|Sim| K[Abertura da OS]
    K --> L[Instalação + checklist]
    L --> M[Fotos + assinatura cliente]
    M --> N[Homologação ANEEL\n+ distribuidora]
    N --> O[Recebimento final]
    O --> P([Pós-venda])
```

---

## 4. Fluxo Serviços — Segurança / Automação / Acesso

```mermaid
flowchart TD
    A([Cliente]) --> B[Visita técnica / levantamento]
    B --> C{Tipo de serviço}

    C -->|Segurança eletrônica| D[Proposta câmeras / alarme]
    C -->|Automação residencial| E[Proposta automação]
    C -->|Controle de acesso\ninterfones · portões| F[Proposta acesso]

    D & E & F --> G{Aprovada?}
    G -->|Revisão| C
    G -->|Sim| H[Entrada]
    H --> I[Separação de materiais\nno estoque]
    I --> J[Abertura da OS]
    J --> K[Instalação + configuração]
    K --> L[Treinamento do cliente]
    L --> M[Assinatura + fotos]
    M --> N[Recebimento final]
    N --> O([Pós-venda])
```

---

## 5. Fluxo Balcão — Venda Direta

```mermaid
flowchart LR
    A([Cliente chega]) --> B[Atendimento]
    B --> C{Produto\nem estoque?}
    C -->|Não| D[Informar prazo\nou alternativa]
    D --> B
    C -->|Sim| E[Emissão da venda]
    E --> F{Forma de\npagamento}
    F -->|À vista| G[Recebimento imediato]
    F -->|Parcelado| H[Registro de parcelas\nno financeiro]
    G & H --> I[Baixa no estoque]
    I --> J([Fim])
```

---

## 6. Entidades e Relacionamentos Principais

```mermaid
erDiagram
    Cliente ||--o{ PropostaSolar     : "solicita"
    Cliente ||--o{ PropostaServico   : "solicita"
    Cliente ||--o{ VendaBalcao       : "realiza"
    Cliente ||--o{ OrdemServico      : "possui"
    Cliente ||--o{ Chamado           : "abre"

    PropostaSolar   ||--o| OrdemServico  : "gera"
    PropostaServico ||--o| OrdemServico  : "gera"

    OrdemServico ||--o{ Parcela      : "gera"
    VendaBalcao  ||--o{ Parcela      : "gera"

    OrdemServico ||--o{ Chamado      : "origina"

    Produto ||--o{ ItemVendaBalcao   : "compõe"
    Produto ||--o{ ItemProposta      : "compõe"
    VendaBalcao  ||--|{ ItemVendaBalcao : "contém"
    PropostaSolar ||--|{ ItemProposta   : "contém"
    PropostaServico ||--|{ ItemProposta : "contém"

    Fornecedor ||--o{ Produto        : "fornece"
```

---

## 7. Estados de uma Ordem de Serviço

```mermaid
stateDiagram-v2
    [*] --> Aberta : OS criada

    Aberta --> Agendada      : técnico designado + data definida
    Agendada --> EmExecucao  : técnico inicia no local
    EmExecucao --> Concluida : checklist + fotos + assinatura
    Concluida --> Faturada   : recebimento registrado

    Agendada --> Reagendada  : cliente ou empresa solicita
    Reagendada --> Agendada  : nova data definida

    EmExecucao --> Suspensa  : falta de material / imprevisto
    Suspensa --> Agendada    : problema resolvido

    Concluida --> [*]
    Faturada  --> [*]

    note right of Concluida : Dispara pós-venda\nautomaticamente
```

---

## 8. Fluxo de Pós-venda / Chamados

```mermaid
flowchart TD
    A([Cliente reporta problema]) --> B[Abertura de chamado\nvinculado à OS ou cliente]
    B --> C{Tipo}

    C -->|Garantia| D[Verificar prazo\nde garantia]
    C -->|Suporte técnico| E[Diagnóstico remoto]
    C -->|Manutenção| F[Agendamento\nde visita técnica]

    D --> G{Dentro\ndo prazo?}
    G -->|Sim| H[Atendimento\nsem custo]
    G -->|Não| I[Orçamento\nde reparo]

    E --> J{Resolvido\nremotamente?}
    J -->|Sim| K[Chamado encerrado]
    J -->|Não| F

    F --> L[Visita técnica]
    L --> M[Resolução]
    H & I --> M
    M --> N[Encerramento\ncom registro]
    N --> K
    K --> O([Histórico do cliente])
```

---

## 9. Estrutura de Pastas do Projeto

```mermaid
flowchart LR
    ROOT[Optimus/] --> CONFIG[config/\nDjango settings]
    ROOT --> STATIC[static/\ncss · js · img]
    ROOT --> TEMPLATES[templates/\nbase.html]
    ROOT --> DOCS[docs/\ndiagramas.md]
    ROOT --> DOTCLAUDE[.claude/\nsettings.local.json · commands/]
    ROOT --> CLAUDEMD[CLAUDE.md]

    ROOT --> A0[core/\nBaseModel auditoria]
    ROOT --> A1[clientes/]
    ROOT --> A2[solar/]
    ROOT --> A3[servicos/]
    ROOT --> A4[balcao/]
    ROOT --> A5[ordens_servico/]
    ROOT --> A6[financeiro/]
    ROOT --> A7[estoque/]
    ROOT --> A8[pos_venda/]

    A1 & A2 & A3 & A4 & A5 & A6 & A7 & A8 --> PATTERN[models.py\nviews.py\nurls.py\nforms.py\ntemplates/app/]
```

## 10. Fluxo de Dimensionamento Solar — Processo Completo

```mermaid
flowchart TD
    A([Cliente interessado]) --> B[Coleta de dados\nde consumo]
    B --> C{Tem conta\nde energia?}
    C -->|Sim| D[Extrair médias\ndas últimas 12 faturas\nkWh/mês]
    C -->|Não| E[Estimativa por\nequipamentos e horas de uso]
    D & E --> F[Definir consumo médio\nmensal em kWh]

    F --> G[Definir tensão\nda rede local\n220V · 127V · Bifásico · Trifásico]
    G --> H[Calcular kWp necessário\nkWp = kWh ÷ HSP ÷ 30 ÷ 0,75]
    H --> I[HSP Tocantins = 5,2\nh/dia]

    I --> J[Selecionar painéis\nPotência unitária Wp]
    J --> K[Calcular nº de painéis\nN = kWp × 1000 ÷ Wp do painel]
    K --> L[Selecionar inversor\nCompatível com kWp]

    L --> M{Sistema\nbifásico ou trifásico?}
    M -->|Monofásico| N[Inversor mono\naté 5 kWp]
    M -->|Bifásico| O[Inversor bi\naté 10 kWp]
    M -->|Trifásico| P[Inversor tri\nacima de 10 kWp]

    N & O & P --> Q[Calcular geração estimada\nkWh/mês = kWp × HSP × 30 × 0,75]
    Q --> R[Calcular economia mensal\nR$ = kWh gerado × tarifa local]
    R --> S[Calcular payback simples\nanos = custo total ÷ economia anual]

    S --> T{Payback\naceitável?}
    T -->|Não — ajustar sistema| J
    T -->|Sim| U[Montar proposta\ncom resumo técnico e financeiro]
    U --> V([Proposta entregue ao cliente])
```

---

## 11. Cálculos do Dimensionamento Solar — Fórmulas

```mermaid
flowchart LR
    subgraph "Entradas"
        E1[Consumo médio\nkWh/mês]
        E2[HSP Tocantins\n5,2 h/dia]
        E3[Eficiência do sistema\n75% = 0,75]
        E4[Potência do painel\nWp ex: 550 Wp]
        E5[Tarifa de energia\nR$/kWh]
        E6[Custo total\ndo sistema R$]
    end

    subgraph "Cálculos"
        C1["kWp necessário\n= kWh ÷ HSP ÷ 30 ÷ 0,75"]
        C2["Nº de painéis\n= kWp × 1000 ÷ Wp"]
        C3["Geração estimada\n= kWp × HSP × 30 × 0,75\nkWh/mês"]
        C4["Economia mensal\n= Geração × Tarifa\nR$/mês"]
        C5["Payback simples\n= Custo total ÷ Economia anual\nanos"]
    end

    subgraph "Saídas da proposta"
        S1[kWp do sistema]
        S2[Quantidade de painéis]
        S3[Modelo do inversor]
        S4[Geração estimada kWh/mês]
        S5[Economia estimada R$/mês]
        S6[Payback em anos]
        S7[Redução na fatura %]
    end

    E1 & E2 & E3 --> C1 --> S1
    C1 & E4 --> C2 --> S2
    C1 & E2 & E3 --> C3 --> S4
    C3 & E5 --> C4 --> S5
    C4 & E6 --> C5 --> S6
    E1 & C3 --> S7
```

---

## 12. Estados de uma Proposta Solar

```mermaid
stateDiagram-v2
    [*] --> Rascunho : técnico inicia dimensionamento

    Rascunho --> EmAnalise     : enviada para revisão interna
    EmAnalise --> Rascunho     : ajustes necessários
    EmAnalise --> EnviadaCliente : aprovada internamente

    EnviadaCliente --> EmNegociacao : cliente solicita ajustes
    EmNegociacao --> EnviadaCliente : nova versão enviada
    EnviadaCliente --> Aprovada     : cliente aceita
    EnviadaCliente --> Perdida      : cliente recusa

    Aprovada --> Contratada    : contrato assinado + entrada recebida
    Contratada --> EmExecucao  : OS aberta

    EmExecucao --> Concluida   : instalação finalizada + homologação
    Perdida --> [*]
    Concluida --> [*]

    note right of Aprovada    : Dispara criação\nautomática da OS
    note right of Concluida   : Inicia contagem\nde garantia
```

---

## 13. Homologação junto à Distribuidora

```mermaid
flowchart TD
    A([Sistema instalado]) --> B[Documentação técnica\nART · memorial descritivo\ndiagrama unifillar]
    B --> C[Envio do pedido\nà distribuidora]
    C --> D{Vistoria\naprovada?}
    D -->|Pendências| E[Correções técnicas\nou documentais]
    E --> C
    D -->|Aprovada| F[Instalação do\nmedidor bidirecional]
    F --> G[Ativação do\nsistema de compensação]
    G --> H[Monitoramento\nda geração]
    H --> I([Cliente em operação\npós-venda ativo])
```
