"""Jogadores sem LLM: aleatório, heurístico guloso e Minimax Alpha-Beta."""
from __future__ import annotations

import random

from othello.game import OthelloGame
from othello.heuristics import explain_move
from othello.search import AlphaBeta

from .base import Player, TurnInfo


class RandomPlayer(Player):
    name = "Aleatório"

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_move(self, game):
        return self.rng.choice(game.valid_moves()), "Escolha aleatória entre as jogadas válidas."


class GreedyPlayer(Player):
    """Avalia cada jogada 1 lance à frente com a função heurística."""
    name = "Heurístico"

    def choose_move(self, game: OthelloGame):
        analyses = [explain_move(game, m) for m in game.valid_moves()]
        best = max(analyses, key=lambda a: a["score_heuristico"])
        return best["jogada"], (f"Maior score heurístico 1-lance ({best['score_heuristico']}); "
                                f"vira {best['pecas_viradas']} peças, oponente fica com "
                                f"{best['mobilidade_oponente_apos']} jogadas.")


class MinimaxPlayer(Player):
    def __init__(self, depth: int = 4, endgame: int = 10):
        self.search = AlphaBeta(depth, endgame)
        self.name = f"Minimax-d{depth}"

    def choose_move(self, game: OthelloGame):
        r = self.search.best_move(game)
        self._last_info = TurnInfo(r.move, nodes=r.nodes)
        return r.move, f"Alpha-Beta prof. {r.depth}: score {r.score:.1f} ({r.nodes} nós)."
