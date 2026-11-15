# Waterlearning

Prática de vestibular sem atrito: você abre o site e já tem uma questão na tela. Sem cadastro, sem boas-vindas, sem menu no caminho. Matemática, Física e História, com **7.254 questões**: ENEM, FUVEST, UNICAMP, ITA, EsPCEx, Colégio Naval, EPCAr, federais, PUC, FGV, Mackenzie, concursos (Banco do Brasil, prefeituras), livros didáticos e questões autorais.

A ideia que guia tudo: **você estuda a teoria em outro lugar e vem aqui praticar, como na lista de exercícios de um bom livro**, só que com muito mais variedade.

```bash
bun install
bun run dev        # http://localhost:5173
bun run data       # reconstrói o banco (pipeline Python + auditorias)
bun run test       # testes do núcleo (Elo, revisão espaçada, streak, filtros…)
bun run deploy     # publica em https://nbbm01.github.io/waterlearning/ (branch gh-pages)
```

---

## O que tem

| Superfície | O que faz |
|---|---|
| **Prática** (abertura) | Questão na tela em menos de 2 s. Teclas `1–5` / `A–E` respondem e `Enter` avança. Fórmulas em KaTeX. Quando você erra, aparecem a alternativa certa e a resolução, sem vermelho agressivo e sem som de erro. |
| **Busca de tópico** | Digite "equação do primeiro grau" e as questões aparecem na hora. A busca casa palavra a palavra e entende ordinais (primeiro = 1º). |
| **Filtros** | Matéria, vestibular, tópico, subtópico (134), ano e dificuldade (Fácil, Médio, Difícil ou **Progressivo**). Também há atalhos: revisões pendentes, inéditas, clássicas, militares, com resolução e aprofundamento. A contagem aparece em tempo real ("142 questões encontradas"). |
| **Socorro teórico** | Depois de 4 erros seguidos no mesmo tópico, aparece um card discreto com o conceito-chave e a página do livro de origem. Nunca bloqueia a tela. |
| **Revisão** (aba própria) | Revisão espaçada automática ("Anki sem configurar"): o que você erra volta depois de alguns dias. |
| **Simulado** | Você escolhe N questões e os filtros. O modo militar tem cronômetro rígido proporcional ao tempo oficial, não mostra o gabarito durante a prova e, no fim, compara sua nota com a nota de corte histórica. |
| **Topo** | 🔥 streak, meta do dia (anel), meta semanal e o botão "Continuar estudando". Nada mais. |
| **Treinador** | Uma sugestão por vez acima da questão: revisões vencendo, o ponto a fortalecer ou o quanto falta para a meta. É um convite com um clique e some com outro. |
| **Detalhes** | Horas líquidas, heatmap de dias, Elo por matéria, domínio por tópico, histórico de simulados, Pomodoro e escudos de streak (1 a cada 7 dias, no máximo 2). |

Modo escuro por padrão. Sons sintetizados (Web Audio) só para acertos e marcos, com botão de mudo. Tudo fica salvo no navegador (IndexedDB/Dexie), sem conta.

## Arquitetura

```
pipeline/                 Python: importa, classifica, calibra e audita
  sources/*.py            um importador por fonte → pipeline/out/<fonte>.json
  taxonomy.json           matérias → 37 tópicos → 134 subtópicos (com palavras-chave)
  build.py                junta tudo, aplica pré-requisitos e níveis, gera public/data
  levels.json             auditoria humana: correções feitas olhando a questão
  theory/                 cards de teoria (referenciam capítulo e página dos livros)
  validate.py, audit_*.py gabarito, renderização KaTeX, quarentena
public/data/
  index.json              uma linha compacta por questão (filtra 6.7 mil no cliente, instantâneo)
  chunks/N.json           enunciados em blocos de 60, carregados sob demanda
  meta.json               taxonomia, bancas, teoria, notas de corte, versão
src/core/                 Elo, revisão espaçada, streak, Progressivo, busca, sons (testados)
src/views/                Prática, Filtros, Revisão, Simulado, Detalhes
```

O site é estático (Vite + React). O índice carrega primeiro e a primeira questão sai do primeiro bloco. Por isso abre rápido.

---

## História do desenvolvimento

Tudo foi construído em uma sequência de sessões com o Claude Code (Claude Opus 5.5), a partir do pedido original: *zero fricção, volume, didática de livro*.

### 1. A plataforma e o ENEM
O primeiro passo foi o esqueleto completo, antes de existir volume: a prática por teclado, os filtros com contagem, a revisão espaçada, o simulado padrão e militar, o Elo, a sequência com escudos, o Pomodoro e os sons. O primeiro banco veio do dataset aberto do ENEM (Matemática, Física e História).

### 2. Volume: livros, ITA, FUVEST, BLUEX, EsPCEx
- **Fundamentos de Matemática Elementar** (8 volumes, em `~/Downloads/conteudo`): as questões de vestibular entram como **recortes fiéis da página** com o gabarito do livro. O PDF não preserva fórmulas bem o bastante para virar texto confiável.
- **ITA 2008–2025** e **EsPCEx** via API das Questões, **FUVEST 2006–2017** (PDFs em duas colunas) e **FUVEST/UNICAMP 2018–2024** pelo dataset aberto BLUEX.
- **37 cards de teoria**, cada um apontando para o capítulo e a página do livro de onde saiu.
- Blocos versionados: uma aba aberta com índice antigo percebe a troca e recarrega.

### 3. Subtópicos
"Funções" é largo demais para quem quer praticar *função afim*. A taxonomia ganhou 134 subtópicos com palavras-chave, e a classificação usa a pista da fonte (capítulo do livro, tópico da API) com peso triplo. Sem pista, a questão só é classificada quando a vantagem é clara: uma questão "nada a ver" num subtópico estraga o treino mais do que uma questão sem subtópico.

### 4. Questões autorais e níveis didáticos
Questões reais de vestibular quase nunca são "fáceis". Elas pressupõem que você já domina o básico. Para ter a base da curva didática, foram criados **geradores de questões autorais** para os assuntos básicos. Cada questão traz:
- a resolução passo a passo (exemplo resolvido);
- alternativas erradas que são **erros típicos**, e a resolução diz qual engano cada uma representa;
- conferência por computador (`audit_autoral.py` refaz as contas).

A dificuldade passou a seguir uma escala única, na lógica de um livro:

| Nível | No livro | No Waterlearning |
|---|---|---|
| **Fácil** | exercício de fixação | conta direta: "resolva 3x + 5 = 2x + 1" |
| **Médio** | problema | modelagem e aplicação: enunciado que vira equação |
| **Difícil** | "desafio" / vestibular exigente | militares, FUVEST/UNICAMP e discussão com parâmetro |
| *Aprofundamento* | apêndice | ITA, IME, olimpíada: fora do treino normal, liberado quando o Elo chega lá |

O **Progressivo** começa na Fixação e sobe quando o degrau está dominado (veja a seção 6). Dentro de cada degrau, escolhe a questão pela chance de acerto prevista pelo Elo do subtópico (82% → 74% → 65%: a zona de desenvolvimento proximal).

### 5. Qualidade: "no médio de equação do 1º grau já tem inequação"
O problema relatado: em *Equações do 1º grau → Médio* apareciam inequações, mesmo para quem ainda não tinha estudado inequação. A investigação encontrou três causas:

1. **Bug de classificação.** O capítulo "Inequações do primeiro grau" do livro *Tópicos de Álgebra Elementar* casava com a palavra-chave "primeiro grau" de *equação do 1º grau*. Os 13 exercícios desse capítulo foram parar no assunto errado. Como eram recortes de imagem, a verificação de texto que já existia (procurar `<`, `≥`, "inequação") não os pegava.
2. **Livro de aprofundamento tratado como livro comum.** Esse livro é preparatório militar do primeiro ao último exercício: contar divisores, discutir parâmetro ("possível e indeterminada quando…"), produto telescópico. Mesmo assim, os primeiros exercícios de cada capítulo viravam "fácil/médio".
3. **OCR perde detalhes.** Em `(4x² − 9)…` o expoente sumiu, e uma equação do 2º grau passou por equação do 1º grau.

A solução foi um sistema de **pré-requisitos na ordem do livro** (`build.py`, função `prerequisites`):
- Uma questão que exige um assunto *posterior* sobe para esse assunto. Inequação sai de equação. `x²` sai de 1º grau e vai para 2º grau. Módulo vai para função modular. Log vai para logaritmos. A pista do capítulo também conta, então "Inequações do primeiro grau" nunca mais é equação.
- **Discussão com parâmetro** é o fim do capítulo, então vai direto para *Difícil*.
- O *Tópicos de Álgebra Elementar* inteiro vai para **Aprofundamento**.
- Exercício de concurso com enunciado longo é problema (Médio), não treino (Fácil).
- **`pipeline/levels.json`**: uma camada de auditoria humana. Cada correção feita olhando o recorte vem com o motivo e vence as regras automáticas.

Resultado em *Equações do 1º grau* no treino normal: **166 fáceis** (contas diretas), **56 médias** (problemas de modelagem) e as difíceis restantes são de colégios militares. Nenhuma inequação, nenhum `x²`, nenhum parâmetro antes da hora. O build imprime cada movimentação ("pré-requisito: 13 de mat-equacao-1grau → mat-inequacoes") para que a próxima regressão apareça logo.

### 6. Auditoria como aluno
Em vez de olhar só os dados, o site foi usado como um estudante usaria: busca, resolução, erros de propósito, socorro teórico. Primeiro com um Chrome automatizado (Playwright), depois no Chrome do autor. O que apareceu e o que mudou:

- **O Progressivo dizia "Aplicação" e continuava dando Fácil.** Ele escolhia só pela chance de acerto do Elo. Agora o degrau manda e o Elo escolhe *dentro* do degrau.
- **Subir com 3 acertos seguidos era pouco.** Isso premiava sorte e tirava o aluno da fixação cedo. Agora vale aprendizagem para o domínio: **7 acertos nas últimas 8** do degrau para subir, e só **3 erros em 4** para descer. Um erro isolado não derruba ninguém. A barra mostra quanto falta para dominar.
- **O Elo que escolhe as questões era da matéria inteira.** Quem dominava equação do 1º grau entrava em 2º grau como se já soubesse. Agora cada subtópico tem o próprio Elo, que escolhe as questões e libera o aprofundamento. O Elo da matéria fica como número geral.
- **Trocar de assunto herdava o degrau anterior.** Agora assunto novo começa na Fixação, como capítulo novo de livro.
- **Fácil = fixação.** Só conta direta (questões autorais). Problema de concurso é no mínimo Médio. Os degraus se chamam Fixação, Aplicação e Desafio.
- **O socorro teórico mostrava Bhaskara para quem errava equação do 1º grau,** porque o card era do tópico inteiro. Agora há cards por subtópico (1º grau, inequações, 2º grau, produtos notáveis, função afim e quadrática), cada um só com o que aquele capítulo pressupõe.
- **O filtro de variedade esvaziava o degrau.** Com poucos moldes autorais, todos ficavam "recentes" e só sobrava questão difícil. Agora a variedade é preferência dentro do degrau (com teste).
- **Mais pré-requisitos:** fatorial sai de equação (é Combinatória), f⁻¹/f(g(x)) sai de Introdução às funções, e expoente com incógnita (x^{2x−1}) sai de inequação do 1º grau.
- **Aprofundamento escondia 37% do banco.** A regra pegava todo difícil de FUVEST/EsPCEx. Agora só ITA, IME e material de olimpíada.
- **Recortes com defeito:** numa amostra de 24 recortes do TQM Fundamental, 9 tinham texto cortado ou questões grudadas, e o livro saiu do build até o recorte ser refeito. Duas questões do ITA perderam o π no PDF e uma do FME perdeu uma fórmula. Todas estão em `levels.json` com o motivo.
- **Apresentação:** vírgula decimal no KaTeX ("0, 5" → "0,5", sem estragar "P(2,2)" nem "[1,2]"), "3x² + 1x + 0" virou "3x² + x", palavras que a API deixava dentro das fórmulas ("x³temcomo") voltaram a ser texto, e "R$ 1.851,00" deixou de ser alternativa ao lado de "R$ 1.850,00".
- **Psicologia:** depois de um erro aparece só a resolução, sem "−14 Elo". O ganho continua visível e o Elo completo fica nos Detalhes.
- **Volume no começo da escada:** 15 geradores novos (equação com MMC, múltiplos consecutivos e x no denominador no estilo do TQM, idades, frações do restante, ingressos, sistemas 2×2, inequações, 2º grau incompleta, soma e produto, problemas de área, função quadrática). Os 415 gabaritos foram conferidos por força bruta, por um caminho independente do gerador.

| Subtópico | Fácil | Médio | Difícil |
|---|---|---|---|
| Equação do 1º grau | 196 | 105 | 76 |
| Sistemas | 40 | 32 | 21 |
| Inequações | 51 | 55 | 3 |
| Equação do 2º grau | 78 | 52 | 1 |
| Função quadrática | 60 | 79 | 31 |

### 7. Diagnóstico do erro e resoluções escritas por IA
- **"Você marcou a C: os sinais ficaram trocados…"** Cada alternativa errada das questões geradas pode trazer o erro que leva a ela (`Why` em `autoral.py`, campo `why` da alternativa). O site mostra esse diagnóstico antes da resolução. Já são 555 diagnósticos (2º grau, discriminante, soma e produto, inequações).
- **História não tinha nenhuma resolução** (785 questões), e quem errava só via a letra certa. Começou a curadoria em `pipeline/curated/<assunto>.json`. Cada questão é lida, o gabarito é conferido e a resolução diz por que a certa é certa e por que as tentadoras são erradas. O piloto foi *Era Vargas*: 27 resolvidas, gabaritos todos conferidos, e **9 delas estavam no assunto errado** (Ditadura, República Populista, Primeira República) e foram reclassificadas. A classificação de História por palavra-chave é o próximo ponto fraco.

### Comparação com o QConcursos
O QConcursos tem ~95 mil questões de Matemática (1.200 de equação do 2º grau), todas reais, com muitas provas de prefeitura que rendem questões fáceis *de verdade*, e estatística de acerto por questão. Por outro lado:
- **A etiqueta de assunto é larga:** na lista de "Equação de 2º grau" aparecem área de terreno, PA/PG, equação trigonométrica e conjuntos. É exatamente o problema de pré-requisito que o Waterlearning trata.
- **Lista paginada,** não fluxo de uma questão por vez. Não há progressão por domínio nem revisão automática, e ~15% das questões têm comentário. Aqui, todas as autorais têm resolução.
- **Exige cadastro e é pago.** Os termos não permitem coleta automática, então nada foi copiado de lá.

O que vale trazer de lá: **mais questões reais fáceis** (provas de prefeitura são públicas, publicadas pelas bancas) e **% de acerto por questão** (precisa de servidor).

### Sobre o QConcursos
Não foi feita raspagem do QConcursos. O conteúdo é pago e os termos de uso proíbem coleta automatizada. As questões de concursos do banco vêm de fontes abertas (API das Questões). Para crescer, o caminho é seguir com provas oficiais publicadas pelas bancas (INEP, COMVEST, FUVEST e as forças armadas publicam provas e gabaritos) e com mais geradores autorais.

### 8. Treinador, psicologia positiva e provas de concurso
- **Treinador (`src/core/coach.ts`, funções puras e testadas).** Acima da questão aparece no máximo uma sugestão: revisões vencendo, o assunto com aproveitamento abaixo de 65% em pelo menos 6 questões, ou o quanto falta para a meta do dia. Toda sugestão é um convite e pode ser dispensada (autodeterminação).
- **Elogio ao processo, não ao talento** (mentalidade de crescimento). A frase depois da resposta depende do que aconteceu: acerto demorado elogia a persistência, questão difícil elogia o raciocínio, e acertar uma questão que você já tinha errado ganha "antes não saía, agora saiu".
- **Erros recuperados.** Os Detalhes abrem com "O que você já construiu": quantas questões você errou e depois acertou, acertos somados e onde você já vai bem. Logo abaixo, "Onde focar agora" lista os pontos fracos com um botão Treinar.
- **Meta do dia.** A meta semanal dividida em cinco dias vira um anel no topo. Ao bater a meta, o aviso diz que parar é mérito e seguir é bônus.
- **Pausa só quando faz sentido.** Se as últimas respostas vêm rápidas e erradas depois de um bom começo, o site sugere cinco minutos de pausa, uma vez por sessão.
- **Leitura.** Enunciados, alternativas e resoluções em serifa (Source Serif 4), coluna de leitura mais estreita, tema claro em tom de papel. Interface em Inter. As fontes vão junto no build.
- **Banco do Brasil e prefeituras.** `python3 pipeline/sources/qdq_fetch.py concursos` baixa Matemática do Banco do Brasil, da Caixa e de provas de prefeitura pela API das Questões. A cota é de 500 por dia e o comando retoma de onde parou. Primeira leva: 43 do Banco do Brasil e 147 de prefeituras. Prova de prefeitura entra no começo do degrau de Aplicação.
- **Publicação.** O site roda em subpasta no GitHub Pages, então os caminhos de dados e imagens usam `import.meta.env.BASE_URL`. O link "abrir no livro" só aparece no servidor local, onde os PDFs existem.

## Limites conhecidos e próximos passos
- Recortes de livro dependem de OCR para a classificação. As regras pegam o padrão, mas uma revisão visual por subtópico (como a feita em equação do 1º grau) é o que garante. Os próximos candidatos são equação do 2º grau, inequações e funções.
- Geradores autorais para mais assuntos (inequações, sistemas, função afim), para que cada subtópico tenha Fácil e Médio de sobra.
- Física e História ainda não têm questões autorais de fixação. Ali o "fácil" é a questão de vestibular mais direta.
