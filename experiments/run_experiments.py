"""Experimentos Agente x Agente.

Exemplos:
    python -m experiments.run_experiments --pair heuristico:aleatorio --games 50
    python -m experiments.run_experiments --pair llm-basico:llm-planejador --games 10
    python -m experiments.run_experiments --preset classicos

Cada confronto alterna as cores (partidas 2k e 2k+1 usam a mesma abertura
sorteada com cores trocadas). Os resultados são gravados incrementalmente em
results/games.csv (1 linha por partida) e results/turns.csv (1 linha por
lance), para que nada se perca se a API atingir o limite no meio do caminho.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from othello.arena import play_game, random_opening  # noqa: E402
from othello.game import BLACK  # noqa: E402
from players import make_player  # noqa: E402
from agent.tools import DailyLimitError  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results"

PRESETS = {
    "classicos": ["heuristico:aleatorio", "minimax:aleatorio", "minimax:heuristico"],
    "llm": ["llm-basico:heuristico", "llm-planejador:heuristico", "llm-basico:llm-planejador",
            "llm-planejador:minimax"],
}

GAME_FIELDS = ["run_id", "match", "game", "agent_a", "agent_b", "black", "white", "winner",
               "winner_agent", "score_black", "score_white", "n_moves", "duration", "opening", "moves",
               "model", "llm_errors_a", "llm_errors_b", "fallbacks_a", "fallbacks_b"]
TURN_FIELDS = ["run_id", "match", "game", "turn", "agent", "color", "move", "elapsed", "llm_calls",
               "llm_time", "tokens_in", "tokens_out", "tool_calls", "tools_used", "invalid_attempts",
               "fallback", "nodes", "llm_errors", "reasoning", "plan"]


def _append(path: Path, fields, rows):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def run_match(key_a: str, key_b: str, games: int, opening_plies: int, seed: int,
              verbose: bool = False, pause: float = 0.0, model: str | None = None, start: int = 0):
    kw = {"model": model} if model else {}
    a = make_player(key_a, **(kw if key_a.startswith("llm") else {}))
    b = make_player(key_b, **(kw if key_b.startswith("llm") else {}))
    if a.name == b.name:  # mesmo tipo dos dois lados: diferencia nos registros
        a.name, b.name = a.name + " #1", b.name + " #2"
    match = f"{a.name} x {b.name}"
    run_id = uuid.uuid4().hex[:8]
    wins = {a.name: 0, b.name: 0, "empate": 0}
    print(f"\n=== {match}: {games} partidas (run {run_id}) ===")
    for i in range(start, games):
        opening = random_opening(opening_plies, seed + i // 2)
        black, white = (a, b) if i % 2 == 0 else (b, a)
        try:
            res = play_game(black, white, verbose=verbose, opening=opening)
        except DailyLimitError as e:
            print(f"\n!! Cota diária da API esgotada na partida {i + 1}; ela foi descartada. "
                  f"Retome amanhã com --start {i}.\n   {str(e)[:200]}")
            sys.exit(2)
        win_agent = {"black": black.name, "white": white.name, "draw": "empate"}[res.winner]
        wins[win_agent] += 1
        side = {a.name: [i for c, i in res.turns if (black if c == BLACK else white) is a],
                b.name: [i for c, i in res.turns if (black if c == BLACK else white) is b]}
        _append(RESULTS / "games.csv", GAME_FIELDS, [{
            "run_id": run_id, "match": match, "game": i, "agent_a": a.name, "agent_b": b.name,
            "black": black.name, "white": white.name, "winner": res.winner, "winner_agent": win_agent,
            "score_black": res.score_black, "score_white": res.score_white, "n_moves": res.n_moves,
            "duration": round(res.duration, 3), "opening": " ".join(opening), "moves": res.moves,
            "model": model or os.getenv("GROQ_MODEL", "") if (a.uses_llm or b.uses_llm) else "",
            "llm_errors_a": sum(t.llm_errors for t in side[a.name]),
            "llm_errors_b": sum(t.llm_errors for t in side[b.name]),
            "fallbacks_a": sum(t.fallback for t in side[a.name]),
            "fallbacks_b": sum(t.fallback for t in side[b.name]),
        }])
        rows = []
        for n, (color, t) in enumerate(res.turns):
            p = black if color == BLACK else white
            d = t.as_dict()
            d.update(run_id=run_id, match=match, game=i, turn=n, agent=p.name,
                     color="B" if color == BLACK else "W")
            rows.append(d)
        _append(RESULTS / "turns.csv", TURN_FIELDS, rows)
        print(f"  partida {i + 1:3d}/{games}: {black.name} (B) {res.score_black} x {res.score_white} "
              f"{white.name} (W) -> {win_agent}  [{res.duration:.1f}s]", flush=True)
        if pause:
            time.sleep(pause)
    print(f"  placar final: {wins}")
    return wins


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", action="append", default=[], help="agenteA:agenteB (pode repetir)")
    ap.add_argument("--preset", choices=PRESETS, help="conjunto pronto de confrontos")
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--opening", type=int, default=4, help="lances aleatórios de abertura")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--model", help="modelo Groq (padrão: GROQ_MODEL do .env)")
    ap.add_argument("--pause", type=float, default=0.0, help="pausa entre partidas (s)")
    ap.add_argument("--start", type=int, default=0, help="índice da 1ª partida (para retomar)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    pairs = args.pair + PRESETS.get(args.preset, [])
    if not pairs:
        ap.error("informe --pair ou --preset")
    RESULTS.mkdir(exist_ok=True)
    for p in pairs:
        ka, kb = p.split(":")
        run_match(ka, kb, args.games, args.opening, args.seed, args.verbose, args.pause, args.model, args.start)


if __name__ == "__main__":
    main()
