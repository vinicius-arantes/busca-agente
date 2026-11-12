"""Minimax (formulação negamax) com poda Alpha-Beta.

* ordenação de jogadas pelo peso posicional da casa (cantos primeiro) para
  aumentar o número de podas;
* busca exata (até o fim) quando restam ``endgame`` casas vazias ou menos;
* passes tratados explicitamente; posições terminais valem +-WIN_SCORE.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .game import OthelloGame, bits, flips_mask, moves_mask, popcount, to_coord
from .heuristics import WEIGHTS, evaluate, terminal_score

INF = math.inf


@dataclass
class SearchResult:
    move: str | None
    score: float
    depth: int
    nodes: int
    ranked: list[tuple[str, float]] = field(default_factory=list)


def _ordered(moves: int) -> list[int]:
    return sorted(bits(moves), key=lambda i: -WEIGHTS[i])


class AlphaBeta:
    def __init__(self, depth: int = 4, endgame: int = 10):
        self.depth = depth
        self.endgame = endgame
        self.nodes = 0

    def _negamax(self, own: int, opp: int, depth: int, alpha: float, beta: float) -> float:
        self.nodes += 1
        moves = moves_mask(own, opp)
        if not moves:
            if not moves_mask(opp, own):
                return terminal_score(own, opp)
            return -self._negamax(opp, own, depth, -beta, -alpha)  # passe
        if depth <= 0:
            return evaluate(own, opp)
        best = -INF
        for i in _ordered(moves):
            m = 1 << i
            f = flips_mask(own, opp, m)
            v = -self._negamax(opp & ~f, own | m | f, depth - 1, -beta, -alpha)
            if v > best:
                best = v
                if v > alpha:
                    alpha = v
                    if alpha >= beta:
                        break
        return best

    def _effective_depth(self, own: int, opp: int) -> int:
        empties = 64 - popcount(own | opp)
        return empties if empties <= self.endgame else self.depth

    def best_move(self, game: OthelloGame) -> SearchResult:
        """Melhor jogada (busca com janela alpha-beta na raiz)."""
        self.nodes = 0
        own, opp = game.own_opp()
        depth = self._effective_depth(own, opp)
        best_move, alpha = None, -INF
        for i in _ordered(moves_mask(own, opp)):
            m = 1 << i
            f = flips_mask(own, opp, m)
            v = -self._negamax(opp & ~f, own | m | f, depth - 1, -INF, -alpha)
            if v > alpha or best_move is None:
                alpha, best_move = v, to_coord(i)
        return SearchResult(best_move, alpha, depth, self.nodes)

    def rank_moves(self, game: OthelloGame) -> SearchResult:
        """Avalia TODAS as jogadas com janela completa (scores exatos para cada
        uma) e as devolve ordenadas. Mais caro que ``best_move``."""
        self.nodes = 0
        own, opp = game.own_opp()
        depth = self._effective_depth(own, opp)
        ranked = []
        for i in _ordered(moves_mask(own, opp)):
            m = 1 << i
            f = flips_mask(own, opp, m)
            v = -self._negamax(opp & ~f, own | m | f, depth - 1, -INF, INF)
            ranked.append((to_coord(i), v))
        ranked.sort(key=lambda t: -t[1])
        top = ranked[0] if ranked else (None, 0.0)
        return SearchResult(top[0], top[1], depth, self.nodes, ranked)
