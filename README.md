# TP05 — Agente Inteligente para Othello (GCC 128)

**Dupla:** Vinícius Arantes e Mariana Rufo · **Vídeo:** <LINK DO VÍDEO> · **Relatório:** `relatorio/relatorio.pdf`

Agente que joga Othello usando **LLM (Groq) + ferramentas + LangGraph**. O agente
observa o tabuleiro, consulta ferramentas, analisa alternativas, decide, executa a
jogada e memoriza o que fez, repetindo o ciclo até o fim da partida.

## Instalação

```bash
python3 -m venv .venv && source .venv/bin/activate     # ou: uv venv
pip install -r requirements.txt
cp .env.example .env    # e coloque sua GROQ_API_KEY
```

Modelo padrão: `openai/gpt-oss-120b` (Groq). Os experimentos usaram `gpt-oss-120b` e
`gpt-oss-20b`. A demonstração do vídeo usou `qwen/qwen3.8-27b`, porque as cotas gratuitas
dos gpt-oss acabaram no dia (detalhes na seção 9 do relatório). Para trocar: `GROQ_MODEL` no `.env` ou
`--model` nos experimentos (ex.: `--model openai/gpt-oss-20b`). No plano gratuito, se a
cota diária acabar, o experimento para e mostra o `--start N` para continuar depois.

## Como jogar

```bash
python main.py                                        # interface gráfica com menu
python main.py --black humano --white llm-planejador --start   # Humano x Agente direto
python main.py --black llm-basico --white llm-planejador --start   # Agente x Agente
python main.py --cli --black humano --white minimax   # no terminal
```

Jogadores: `humano`, `aleatorio`, `heuristico`, `minimax`, `llm-basico`, `llm-planejador`.

Na interface: clique numa casa marcada para jogar · `ESPAÇO` pausa · `+`/`-` muda o
atraso entre lances · `R` reinicia · `ESC` volta ao menu. O painel lateral mostra a
**justificativa** de cada jogada do agente, as ferramentas chamadas, o plano, o tempo e os tokens.

## Experimentos e torneio

```bash
python -m experiments.run_experiments --preset classicos --games 50
python -m experiments.run_experiments --pair llm-basico:llm-planejador --games 10
python -m experiments.tournament --players aleatorio heuristico minimax llm-planejador
python -m experiments.analyze            # tabelas + gráficos em results/
pytest -q                                # testes das regras e da busca
python relatorio/build.py --autores "Vinícius Arantes e Mariana Rufo"   # gera o PDF
```

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `othello/` | regras (bitboards), heurística, Minimax Alpha-Beta, laço de partida |
| `agent/` | ferramentas LangChain, memória, grafos LangGraph (básico e planejador) |
| `players/` | interface comum de jogadores (também usada no torneio) |
| `ui/` | interface Pygame |
| `experiments/` | experimentos, torneio e análise |
| `tests/` | testes pytest |

## Agentes

* **LLM Básico**: laço ReAct (LLM ⇄ ferramentas) só com as 4 ferramentas obrigatórias
  (`get_board_state`, `get_valid_moves`, `make_move`, `get_game_status`).
* **LLM Planejador**: grafo `observe → analyze ⇄ tools → decide → execute → memorize`.
  Usa também `evaluate_move`, `search_best_moves` (Alpha-Beta) e `get_move_history`,
  valida a jogada com feedback do ambiente e mantém histórico, justificativas e plano.
* **Heurístico**, **Minimax (d4)** e **Aleatório**: linhas de base sem LLM.

## Torneio entre grupos

Para participar, um agente só precisa implementar `choose_move(game) -> (coordenada, justificativa)`
(ver `players/base.py`) e ser registrado em `players/__init__.py`.
