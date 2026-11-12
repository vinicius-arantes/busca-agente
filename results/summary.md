# Resultados dos experimentos

## Por confronto (A = primeiro agente do confronto)

| Confronto | Partidas | Vitórias A | Empates | Vitórias B | Taxa vitória A | Saldo médio de peças (A) | Lances médios | Duração média (s) | Fallbacks (A+B) | Erros API (A+B) |
|---|---|---|---|---|---|---|---|---|---|---|
| Heurístico x Aleatório | 50 | 49 | 0 | 1 | 98% | 38.20 | 59.24 | 0.02 | 0 | 0 |
| Minimax-d4 x Aleatório | 50 | 50 | 0 | 0 | 100% | 50.72 | 58.60 | 0.51 | 0 | 0 |
| Minimax-d4 x Heurístico | 50 | 50 | 0 | 0 | 100% | 48.34 | 58.70 | 0.60 | 0 | 0 |
| LLM-Planejador (gpt-oss-120b) x Heurístico | 1 | 1 | 0 | 0 | 100% | 26.00 | 60.00 | 500.56 | 0 | 2 |
| LLM-Básico (gpt-oss-120b) x Heurístico | 3 | 0 | 0 | 3 | 0% | -43.00 | 59.00 | 219.33 | 0 | 0 |
| LLM-Básico (gpt-oss-20b) x LLM-Planejador (gpt-oss-20b) | 1 | 0 | 0 | 1 | 0% | -54.00 | 60.00 | 1189.35 | 0 | 6 |

## Por agente

| Agente | Partidas | V | E | D | Taxa de vitória | Lances | Tempo médio/lance (s) | Chamadas LLM/lance | Latência LLM/lance (s) | Tokens/lance | Tool calls/lance | Jogadas inválidas | Fallbacks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LLM-Planejador (gpt-oss-120b) | 1 | 1 | 0 | 0 | 100% | 29 | 17.26 | 2.55 | 17.13 | 3118.52 | 5.28 | 0 | 0 |
| LLM-Planejador (gpt-oss-20b) | 1 | 1 | 0 | 0 | 100% | 30 | 27.11 | 3.20 | 27.02 | 4038.30 | 5.57 | 0 | 0 |
| LLM-Básico (gpt-oss-120b) | 3 | 0 | 0 | 3 | 0% | 74 | 8.89 | 2.73 | 8.87 | 1717.31 | 2.73 | 8 | 0 |
| LLM-Básico (gpt-oss-20b) | 1 | 0 | 0 | 1 | 0% | 26 | 14.46 | 2.96 | 14.45 | 2112.19 | 2.65 | 0 | 0 |
| Minimax-d4 | 100 | 100 | 0 | 0 | 100% | 2938 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0 |
| Heurístico | 104 | 52 | 0 | 52 | 50% | 2860 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0 |
| Aleatório | 100 | 1 | 0 | 99 | 1% | 2547 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0 |

## Uso de ferramentas (agentes LLM)

| Agente | Ferramenta | Chamadas | Por lance |
|---|---|---|---|
| LLM-Básico (gpt-oss-120b) | make_move | 82 | 1.11 |
| LLM-Básico (gpt-oss-120b) | get_valid_moves | 50 | 0.68 |
| LLM-Básico (gpt-oss-120b) | get_board_state | 37 | 0.50 |
| LLM-Básico (gpt-oss-120b) | get_game_status | 33 | 0.45 |
| LLM-Básico (gpt-oss-20b) | get_board_state | 26 | 1.00 |
| LLM-Básico (gpt-oss-20b) | make_move | 26 | 1.00 |
| LLM-Básico (gpt-oss-20b) | get_valid_moves | 17 | 0.65 |
| LLM-Planejador (gpt-oss-120b) | get_game_status | 29 | 1.00 |
| LLM-Planejador (gpt-oss-120b) | get_board_state | 29 | 1.00 |
| LLM-Planejador (gpt-oss-120b) | get_valid_moves | 29 | 1.00 |
| LLM-Planejador (gpt-oss-120b) | make_move | 29 | 1.00 |
| LLM-Planejador (gpt-oss-120b) | search_best_moves | 27 | 0.93 |
| LLM-Planejador (gpt-oss-120b) | evaluate_move | 10 | 0.34 |
| LLM-Planejador (gpt-oss-20b) | get_game_status | 30 | 1.00 |
| LLM-Planejador (gpt-oss-20b) | get_board_state | 30 | 1.00 |
| LLM-Planejador (gpt-oss-20b) | get_valid_moves | 30 | 1.00 |
| LLM-Planejador (gpt-oss-20b) | make_move | 30 | 1.00 |
| LLM-Planejador (gpt-oss-20b) | search_best_moves | 29 | 0.97 |
| LLM-Planejador (gpt-oss-20b) | evaluate_move | 18 | 0.60 |

## Qualidade dos lances (partidas com LLM, após a abertura sorteada)

| Agente | Lances analisados | Taxa concordância c/ Alfa-Beta d4 | Rank médio da jogada | Taxa canto tomado (quando disponível) | Vezes c/ canto disponível | Taxa casa X perigosa | Taxa entrega canto |
|---|---|---|---|---|---|---|---|
| LLM-Planejador (gpt-oss-120b) | 29 | 83% | 1.31 | 100% | 4 | 0% | 0% |
| Heurístico | 118 | 53% | 2.22 | 92% | 12 | 3% | 5% |
| LLM-Básico (gpt-oss-120b) | 74 | 41% | 2.93 | 50% | 2 | 8% | 16% |
| LLM-Básico (gpt-oss-20b) | 26 | 54% | 2.35 | - | 0 | 8% | 15% |
| LLM-Planejador (gpt-oss-20b) | 30 | 100% | 1.00 | 100% | 4 | 0% | 0% |

## Divergências em relação ao Alfa-Beta (prof. 4)

| Agente | Lances | Divergências | Taxa divergência | Perda mediana (pts) | Divergências quase equivalentes (perda < 15) | Divergências graves (perda >= 100) | Divergências que mudam o resultado (final exato) |
|---|---|---|---|---|---|---|---|
| LLM-Planejador (gpt-oss-120b) | 29 | 5 | 17% | 39.99 | 2 | 2 | 0 |
| Heurístico | 118 | 55 | 47% | 27.66 | 18 | 12 | 0 |
| LLM-Básico (gpt-oss-120b) | 74 | 44 | 59% | 84.94 | 4 | 16 | 0 |
| LLM-Básico (gpt-oss-20b) | 26 | 12 | 46% | 80.29 | 2 | 5 | 0 |
| LLM-Planejador (gpt-oss-20b) | 30 | 0 | 0% | - | 0 | 0 | 0 |

### Exemplos de divergência do Planejador

* **LLM-Planejador (gpt-oss-120b)**, lance 29 (meio-jogo): jogou **e1** (rank 3/16), busca preferia **g8** (perda 5). Justificativa: "Jogada segura na borda inferior, captura 1 peça, não abre casas X/C e aumenta mobilidade sem ceder cantos."
* **LLM-Planejador (gpt-oss-120b)**, lance 35 (meio-jogo): jogou **b4** (rank 3/12), busca preferia **b8** (perda 10). Justificativa: "Jogada segura na borda esquerda, captura 6 peças, não abre casas X/C e aumenta nossa mobilidade enquanto pressiona a coluna b."
* **LLM-Planejador (gpt-oss-120b)**, lance 45 (meio-jogo): jogou **b3** (rank 2/10), busca preferia **b1** (perda 40). Justificativa: "Jogada segura na linha 3, vira 2 peças, mantém mobilidade e não abre cantos nem casas C críticas."
* **LLM-Planejador (gpt-oss-120b)**, lance 31 (meio-jogo): jogou **a5** (rank 4/15), busca preferia **g8** (perda 108). Justificativa: "Jogada na borda segura, captura 3 peças, aumenta nossa mobilidade e não abre casas X ou C próximas a cantos vazios."
* **LLM-Planejador (gpt-oss-120b)**, lance 49 (final): jogou **g6** (rank 2/7), busca preferia **b1** (perda 503). Justificativa: "G6 vira 9 peças, aumenta vantagem e mantém mobilidade controlada sem abrir cantos ou casas críticas."
