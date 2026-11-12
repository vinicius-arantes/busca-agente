"""Laço de uma partida Agente x Agente (usado por experimentos e torneio)."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from .game import BLACK, EMPTY, WHITE, OthelloGame


@dataclass
class GameResult:
    black: str
    white: str
    winner: str            # "black" | "white" | "draw"
    score_black: int
    score_white: int
    n_moves: int           # lances efetivos (sem contar passes)
    duration: float
    moves: str
    turns: list = field(default_factory=list)   # [(cor, TurnInfo)]


def random_opening(n_plies: int, seed: int) -> list[str]:
    """Sequência de ``n_plies`` lances aleatórios (diversifica as partidas)."""
    rng = random.Random(seed)
    g = OthelloGame()
    for _ in range(n_plies):
        g.make_move(rng.choice(g.valid_moves()))
    return [r.move for r in g.history if r.move]


def play_game(black, white, verbose: bool = False, on_turn=None, opening: list[str] | None = None) -> GameResult:
    game = OthelloGame()
    for mv in opening or []:
        game.make_move(mv, "[abertura sorteada]")
    black.reset(BLACK)
    white.reset(WHITE)
    players = {BLACK: black, WHITE: white}
    turns = []
    t0 = time.perf_counter()
    while not game.is_over():
        color = game.current
        info = players[color].play(game)
        turns.append((color, info))
        if verbose:
            b, w = game.score()
            print(f"{len(turns):2d}. {'B' if color == BLACK else 'W'} {players[color].name:<18} "
                  f"{info.move}  ({b}x{w})  {info.elapsed:5.2f}s  {info.reasoning[:90]}")
        if on_turn:
            on_turn(game, color, info)
    b, w = game.score()
    win = game.winner()
    return GameResult(black.name, white.name,
                      {BLACK: "black", WHITE: "white", EMPTY: "draw"}[win], b, w,
                      sum(1 for r in game.history if r.move), time.perf_counter() - t0,
                      game.moves_string(), turns)
