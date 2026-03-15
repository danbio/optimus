# Skill: Tema Visual Intelbras

## Decisões de arquitetura

- CSS puro, sem framework — seguir o guia Intelbras fielmente
- Layout: topbar verde (#00a335) + sidebar verde (#00a335) com itens brancos
- Arquivo principal: `static/css/intelbras.css` (importado no base.html)
- Ícones: Bootstrap Icons via CDN (apenas ícones, não o CSS de grid/componentes)
- HTMX via CDN — somente onde agrega valor real

## Paleta de cores

```
Verde primário:     #00a335   (botões, sidebar, topbar, links)
Verde escuro/hover: #00863F   (hover de botão primário)
Verde claro:        #87c984   (hover de sidebar, badges secundários)

Texto título:       #3e5055
Texto corpo:        #8b979f
Texto desabilitado: #bbcad2

Fundo página:       #f5f6f7   (levemente cinza para contrastar com cards)
Fundo card:         #ffffff
Fundo alternado:    #ebeeee   (linhas pares de tabela, inputs focados)

Borda input:        #8b979f
Borda fraca:        #d6dfe1
Borda fraquíssima:  #bbcad2

Erro:       #d72735   fundo: #fdebed
Sucesso:    #00a335   fundo: #e5f6ed
Alerta:     #EAB42A
Info:       #6A90A7
```

## Tipografia

```
font-family: "Roboto", "Arial", "Helvetica", sans-serif;
Títulos/botões: font-weight 600 (semibold)
Corpo: font-weight 400
Placeholder: #8b979f, 13px, peso normal
Input preenchido: #3e5055, 15px, peso 600
```

## border-radius

Sempre 3px — conforme guia Intelbras (não arredondar demais)

## Regras críticas

- NUNCA usar azul Bootstrap padrão (#0d6efd) para ações principais
- Verde #00a335 é a única cor de ação primária
- Textos de aviso/erro sempre com ícone + texto (não só cor)
- Botão primário: fundo #00a335, texto branco
- Botão secundário: fundo branco, borda #8b979f, texto #3e5055
