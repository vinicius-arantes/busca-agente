# Roteiro do vídeo, com falas (≈ 9 min 30 s)

**Legenda:** **V** = Vinícius · **M** = Mariana (troquem à vontade) · `[Tela]` = o que aparece ·
`[colchetes]` = preencher com o que acontecer ao vivo.

> **Antes de gravar**
> - `source .venv/bin/activate` e confira se o `.env` está com `GROQ_MODEL=qwen/qwen3.8-27b`.
> - Abra os slides em modo de apresentação, o VS Code com `agent/graph.py` e `agent/tools.py`,
>   um terminal na pasta do projeto e o `relatorio/relatorio.pdf`.
> - **Não ensaie partidas inteiras com LLM**: a cota do qwen é limitada. Ensaie com
>   `python main.py --black humano --white minimax --start`, que não gasta cota.
> - Durante as partidas com LLM, aperte `+` para aumentar o atraso e `ESPAÇO` para pausar e
>   comentar.

---

## 1. Abertura · 0:00–0:40

`[Tela] Slide 1 — Capa`

**V:** Olá! Eu sou o Vinícius Arantes.

**M:** E eu sou a Mariana Rufo. Este é o nosso Trabalho Prático 5 de Inteligência
Artificial: um agente inteligente que joga Othello.

**V:** A proposta não era simplesmente mandar o tabuleiro para uma LLM e pedir uma jogada.
Construímos um **agente** que percebe o ambiente, usa ferramentas, decide, age e guarda
memória. Usamos Python, LangChain com LangGraph, modelos da Groq e uma interface em Pygame.

**M:** Um aviso antes de começar: nos experimentos usamos os modelos gpt-oss-120b e
gpt-oss-20b. A cota gratuita deles acabou no dia da entrega, então a demonstração ao vivo usa
o qwen3.8-27b. Explicamos isso melhor no final.

---

## 2. Objetivo · 0:40–1:05

`[Tela] Slide 2 — Objetivo (ciclo do agente)`

**V:** A cada turno, o agente passa por este ciclo. Ele **percebe**: lê o tabuleiro, o status
da partida e as jogadas válidas. Ele **analisa**: a própria LLM escolhe quais ferramentas de
análise chamar. Ele **decide** a jogada, com uma justificativa e um plano. Ele **age**:
quem executa a jogada no ambiente é ele, pela ferramenta `make_move`. E ele **memoriza** o
que fez para o próximo turno.

**M:** E se a LLM propõe uma jogada inválida, o ambiente devolve o erro com a lista de
jogadas válidas, e ela corrige. É esse ciclo de realimentação que faz disso um agente.

---

## 3. Arquitetura · 1:05–1:45

`[Tela] Slide 3 — Arquitetura`

**V:** O projeto tem quatro partes. Em `othello/` estão as regras do jogo, implementadas com
*bitboards*, em que cada cor é um número de 64 bits. Isso deixa a geração de jogadas muito
rápida.

`[Tela] Terminal: rodar pytest -q`

**V:** As regras têm 11 testes automatizados. Um deles compara nosso motor, lance a lance, com
uma implementação simples em 300 partidas aleatórias. Todos passam.

`[Tela] Voltar ao slide 3`

**M:** Em `players/` fica uma interface única de jogador, usada por tudo: a interface gráfica,
os experimentos, o torneio e o modo terminal. Temos cinco jogadores: Aleatório, Heurístico,
Minimax, LLM Básico e LLM Planejador. Em `agent/` ficam os grafos do LangGraph, a memória e as
ferramentas. Detalhe importante: os agentes LLM só mexem no jogo **através das ferramentas**.

---

## 4. Ferramentas · 1:45–2:10

`[Tela] Slide 4 — Ferramentas (pode alternar com agent/tools.py no VS Code)`

**M:** São sete ferramentas. As quatro pedidas no enunciado: `get_board_state`,
`get_valid_moves`, `make_move` e `get_game_status`. O `make_move` executa de verdade e, se a
jogada for inválida, devolve o erro.

**V:** Criamos mais três de análise. O `evaluate_move` diz os riscos de uma jogada: se é casa
perigosa, se entrega um canto, como fica a mobilidade. O `search_best_moves` roda um Minimax
com poda Alfa-Beta e devolve as melhores jogadas. E o `get_move_history` dá acesso à
memória da partida.

---

## 5. Grafo do Planejador · 2:10–2:45

`[Tela] Slide 5 — Grafo (ou agent/graph.py no VS Code)`

**V:** Este é o grafo do nosso agente principal, o Planejador. O nó **observe** consulta o
ambiente e monta a observação com a memória: os lances da partida, as últimas justificativas e
o plano anterior.

**M:** No nó **think** a LLM escolhe as ferramentas, normalmente a busca e a avaliação de
candidatas, chamadas em paralelo. Depois ela chama o `make_move` com a jogada, a justificativa
e o plano. Se a jogada for inválida, o erro volta e ela tenta de novo.

**V:** Em azul estão os nós que chamam a LLM. O **decide** e o **fallback** são redes de
segurança: o decide obriga a LLM a jogar, e o fallback usa o Alfa-Beta se tudo falhar. Nos
experimentos o fallback **nunca** precisou ser usado.

---

## 6. Estratégia · 2:45–3:05

`[Tela] Slide 6 — Estratégia`

**M:** A estratégia tem duas peças. A heurística valoriza os cantos, que nunca são virados,
penaliza as casas X e C perto de cantos vazios, considera mobilidade, fronteira e
estabilidade, e muda os pesos conforme a fase do jogo. A busca é um Minimax com poda
Alfa-Beta de profundidade 4, que resolve o final de forma exata.

**V:** As duas servem de adversários sem LLM e também viram **ferramentas** do agente. O
Planejador pode até discordar da busca, mas precisa justificar.

---

## 7. Demonstração: Humano × Agente · 3:05–4:45

`[Tela] Slide 7 — "Vamos jogar"; depois o terminal`

**M:** Agora vamos jogar. Eu vou de pretas contra o Planejador.

`[Tela] python main.py --black humano --white llm-planejador --start`

**M:** As casas com círculo branco são as minhas jogadas válidas. Vou jogar em `[casa]`.

`[Tela] Esperar o agente jogar; apontar o painel lateral`

**V:** Enquanto ele pensa aparece "pensando…" e o tempo. Ele jogou `[casa]`. No painel dá para
ler a justificativa: `[ler a justificativa]`. E o plano para os próximos lances:
`[ler o plano]`.

**V:** Aqui embaixo aparecem as ferramentas que ele chamou: a busca e `[n]` avaliações de
candidatas, em paralelo. E o custo: `[n]` chamadas à LLM e `[n]` tokens nesse lance.

`[Tela] Jogar mais 2 ou 3 lances`

**M:** Vou tentar oferecer um canto para ver o que ele faz… `[comentar: pegou o canto / evitou
a armadilha / evitou casa X]`.

*(Se o agente fizer algo errado:)* **V:** Olha que interessante: ele justificou com
`[trecho]`, mas `[o que está errado]`. Isso aparece na nossa análise: a LLM às vezes erra a
orientação do tabuleiro ou dá uma explicação que não bate com a jogada.

---

## 8. Demonstração: Agente × Agente · 4:45–6:00

`[Tela] ESC; python main.py --black llm-basico --white llm-planejador --start`

**V:** Agora, agente contra agente: o LLM Básico de pretas contra o Planejador de brancas, os
dois com o mesmo modelo.

**M:** O Básico é um laço ReAct simples: ele só tem as quatro ferramentas obrigatórias e
decide sozinho quando olhar o tabuleiro e quando jogar. O Planejador tem o grafo completo e as
ferramentas de análise.

`[Tela] ESPAÇO para pausar após alguns lances`

**V:** Pausando aqui. Repare nas ferramentas de cada um: o Básico chamou `[ferramentas]`,
enquanto o Planejador consultou a busca e avaliou candidatas. O Básico jogou `[casa]` dizendo
`[justificativa]`; `[comentar se foi casa X ou entregou canto]`.

**M:** Placar agora: `[placar]`. Não vamos esperar até o fim para não gastar a cota, mas nos
experimentos o Planejador venceu o Básico por 59 a 5.

*(Opcional, 15 s)* `[Tela] ESC; escolher Clássicos (Heurístico × Minimax) e INICIAR`

**V:** Só para comparar a velocidade: os agentes clássicos jogam a partida inteira em menos de
um segundo, enquanto a LLM leva de 10 a 30 segundos por lance.

---

## 9. Resultados: linhas de base · 6:00–6:25

`[Tela] Slide 9 — Linhas de base`

**M:** Vamos aos resultados. Primeiro, os agentes sem LLM, com 50 partidas por confronto,
aberturas sorteadas e cores alternadas. O Minimax venceu o Heurístico 50 a 0, e o Heurístico
venceu o Aleatório 49 a 1. No torneio de pontos corridos, com vitória valendo 3, o Minimax fez
60 pontos, o Heurístico 24 e o Aleatório 6. Isso confirma que a heurística e a busca, que o
agente usa como ferramentas, funcionam.

---

## 10. Resultados: agentes LLM · 6:25–6:55

`[Tela] Slide 10 — Básico 0 de 3 × Planejador 2 de 2`

**V:** Agora os agentes LLM. O Básico perdeu as três partidas para o Heurístico, que só olha um
lance à frente, e perdeu feio: 1 a 62, 24 a 40 e 5 a 57. O Planejador venceu as duas que
jogou: 45 a 19 contra o Heurístico e 59 a 5 contra o próprio Básico.

**M:** Sabemos que são poucas partidas: a cota gratuita da API não permitiu mais. Por isso
analisamos também **lance a lance**, o que dá dezenas de observações por agente.

---

## 11. Qualidade dos lances · 6:55–7:15

`[Tela] Slide 11 — Gráfico de qualidade`

**M:** Reproduzimos cada partida e comparamos cada lance com a busca. O Básico **entregou um
canto ao oponente em 16% dos lances** e jogou em casa X em 8%. São os dois erros clássicos de
quem está aprendendo Othello. O Planejador: zero e zero.

---

## 12. Divergências da busca · 7:15–7:40

`[Tela] Slide 12 — Divergências`

**V:** Esta é a análise mais interessante: o que acontece quando a LLM **discorda** da
ferramenta de busca? O Planejador com o 120b discordou em 17% dos lances e, na mediana,
perdeu pontos. A pior divergência foi no final da partida: ele jogou g6 porque "virava 9
peças", exatamente a gula que o prompt mandava evitar. Já o 20b seguiu a busca em 100% dos
lances.

**M:** Ou seja: a força do agente vem da ferramenta de planejamento. O papel da LLM é
**orquestrar**, decidindo o que consultar e mantendo um plano, e **explicar** as decisões.

---

## 13. Custo · 7:40–7:55

`[Tela] Slide 13 — Custo`

**V:** Isso tem custo. O Planejador gasta cerca de 3 mil tokens e de 17 a 27 segundos por
lance, contra 0,02 segundo do Minimax. O Básico, livre para escolher, só olhou as jogadas
válidas em 68% dos lances. Por isso tentou 8 jogadas inválidas, todas corrigidas pelo
feedback do ambiente.

---

## 14. Análise qualitativa · 7:55–8:15

`[Tela] Slide 14 — Citações`

**M:** Alguns exemplos reais. Uma boa explicação do Planejador: "Captura canto a8, reduz
mobilidade do oponente e mantém estabilidade". O Básico, jogando numa casa X: "captura duas
peças e aproxima um canto", e com isso entregou o canto. E dois problemas da LLM: uma
justificativa que contradiz a jogada, "maximiza mobilidade do oponente", e erros de
orientação, como chamar de "borda inferior" uma casa que fica em cima.

---

## 15. Dificuldades · 8:15–9:15

`[Tela] Slide 15 — Limites da API gratuita`

**V:** Tivemos várias dificuldades. O modelo que planejamos usar, o Llama 3.3 70B, foi
descontinuado, e migramos para o gpt-oss-120b. O plano gratuito limita a 8 mil tokens por
minuto e 200 mil por dia, e uma partida do Planejador custa uns 90 mil. Então otimizamos o
grafo: de 4,2 mil para 3,1 mil tokens por lance.

**M:** Quando a cota acabava no meio de uma partida, ela era descartada, para que jogadas de
emergência não contaminassem os resultados. Como o prazo era no mesmo dia, rodamos em paralelo
no gpt-oss-20b, que tem cota própria. E as cotas acabaram antes da gravação; por isso este
vídeo usa o qwen.

`[Tela] Slide 16 — Comportamento da LLM`

**V:** Também houve problemas de comportamento. O gpt-oss-20b às vezes corrompia o nome da
ferramenta na chamada; resolvemos repetindo a chamada automaticamente. A LLM confunde cima e
baixo no tabuleiro: colocamos uma legenda explícita e deixamos os cálculos geométricos para o
`evaluate_move`, o que reduziu o problema, mas não eliminou.

**M:** E como as justificativas nem sempre são fiéis, medimos a qualidade lance a lance em vez
de confiar só no texto. Tudo isso está documentado na seção 9 do relatório.

---

## 16. Conclusão · 9:15–9:45

`[Tela] Slide 17 — Conclusão`

**V:** Para concluir: sozinha, a LLM joga como iniciante, perde para um heurístico simples e
entrega cantos. Com as ferramentas certas, o agente vence e não comete esses erros.

**M:** O valor da LLM não está em calcular a jogada, isso a busca faz melhor e mais barato. O
valor está em orquestrar as ferramentas, manter um plano e explicar cada decisão. Como
próximos passos: mais partidas com uma cota paga, chamar a LLM só nos lances mais disputados
e participar do torneio entre os grupos.

**V e M:** Obrigado!
