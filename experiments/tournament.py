"""Torneio todos-contra-todos: vitória = 3, empate = 1, derrota = 0.

    python -m experiments.tournament --players aleatorio heuristico minimax llm-planejador --rounds 2

Cada par joga ``rounds`` partidas por cor (cores alternadas). Desempate:
saldo de peças. Para incluir o agente de outro grupo, basta registrá-lo em
``players.REGISTRY`` com uma classe que implemente ``choose_move(game)``.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from othello.arena import play_game, random_opening  # noqa: E402
from players import LABELS, make_player  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results"


def run_tournament(keys, rounds=1, opening=4, seed=7):
    players = {k: make_player(k) for k in keys}
    table = {k: {"J": 0, "V": 0, "E": 0, "D": 0, "saldo": 0, "pts": 0} for k in keys}
    games = []
    for ka, kb in itertools.combinations(keys, 2):
        for r in range(rounds):
            op = random_opening(opening, seed + r)
            for black_k, white_k in ((ka, kb), (kb, ka)):
                res = play_game(players[black_k], players[white_k], opening=op)
                diff = res.score_black - res.score_white
                for k, d in ((black_k, diff), (white_k, -diff)):
                    t = table[k]
                    t["J"] += 1
                    t["saldo"] += d
                    if d > 0:
                        t["V"] += 1; t["pts"] += 3
                    elif d == 0:
                        t["E"] += 1; t["pts"] += 1
                    else:
                        t["D"] += 1
                games.append((LABELS[black_k], LABELS[white_k], res.score_black, res.score_white))
                print(f"{LABELS[black_k]:>15} (B) {res.score_black:2d} x {res.score_white:2d} (W) {LABELS[white_k]}", flush=True)
    ranking = sorted(table.items(), key=lambda kv: (-kv[1]["pts"], -kv[1]["saldo"]))
    print("\nClassificação")
    print(f"{'#':>2} {'Agente':<16} {'Pts':>4} {'J':>3} {'V':>3} {'E':>3} {'D':>3} {'Saldo':>6}")
    for i, (k, t) in enumerate(ranking, 1):
        print(f"{i:>2} {LABELS[k]:<16} {t['pts']:>4} {t['J']:>3} {t['V']:>3} {t['E']:>3} {t['D']:>3} {t['saldo']:>+6}")
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "tournament.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pos", "agente", "pts", "J", "V", "E", "D", "saldo"])
        for i, (k, t) in enumerate(ranking, 1):
            w.writerow([i, LABELS[k], t["pts"], t["J"], t["V"], t["E"], t["D"], t["saldo"]])
    return ranking, games


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--players", nargs="+", default=["aleatorio", "heuristico", "minimax"])
    ap.add_argument("--rounds", type=int, default=1, help="partidas por cor em cada confronto")
    ap.add_argument("--opening", type=int, default=4)
    args = ap.parse_args()
    run_tournament(args.players, args.rounds, args.opening)


if __name__ == "__main__":
    main()
