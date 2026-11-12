Foi implementado um agente que **percebe, raciocina, usa ferramentas e age** no jogo
Othello, estruturado como um grafo LangGraph com memória, validação por feedback do
ambiente e mecanismos de segurança. Os experimentos levam a três conclusões principais:

1. **Uma LLM sozinha, apenas com acesso ao ambiente, joga mal.** O LLM Básico perdeu
   todas as partidas para um heurístico de 1 lance. Ele entregou cantos em 16% dos lances e
   jogou em casas X, com justificativas gulosas ("captura duas peças e aproxima um canto").
2. **As ferramentas certas transformam o agente.** Com `search_best_moves` (Alfa-Beta) e
   `evaluate_move`, o Planejador venceu todas as suas partidas, inclusive o Básico com o
   mesmo modelo por 59 × 5. Ele não entregou nenhum canto e não jogou nenhuma casa X.
3. **A força vem do planejamento; o valor da LLM está na orquestração e na explicação.**
   Quando o Planejador diverge da busca (17% dos lances no 120b, 0% no 20b), a divergência
   tende a custar pontos. O que a LLM acrescenta é decidir quais análises fazer, integrar
   critérios, manter um plano entre turnos, corrigir jogadas inválidas a partir do feedback
   e **explicar cada decisão** em linguagem natural. As explicações, porém, nem sempre são
   fiéis à decisão.

O custo dessa arquitetura é alto: 2,5–3,2 chamadas à LLM, ~3–4 mil tokens e ~17–27 s por
lance, contra 0,02 s do Minimax. Como trabalhos futuros, destacam-se:

* mais partidas com LLM, com cota paga, para estimar taxas de vitória com intervalos de
  confiança;
* chamar a LLM apenas nos lances em que a busca indica jogadas próximas, reduzindo o custo;
* dar à LLM ferramentas de busca mais profundas ou um ajuste dos pesos heurísticos por
  *self-play*;
* participar do torneio entre grupos usando a interface comum de jogadores já implementada.
