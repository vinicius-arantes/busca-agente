import random

from othello.game import OthelloGame, bits, flips_mask, moves_mask
from othello.heuristics import evaluate, explain_move, terminal_score
from othello.search import AlphaBeta


def plain_minimax(own, opp, depth):
    """Negamax SEM poda (referência)."""
    moves = moves_mask(own, opp)
    if not moves:
        if not moves_mask(opp, own):
            return terminal_score(own, opp)
        return -plain_minimax(opp, own, depth)
    if depth <= 0:
        return evaluate(own, opp)
    best = -1e18
    for i in bits(moves):
        m = 1 << i
        f = flips_mask(own, opp, m)
        best = max(best, -plain_minimax(opp & ~f, own | m | f, depth - 1))
    return best


def random_position(rng, n_moves):
    g = OthelloGame()
    for _ in range(n_moves):
        if g.is_over():
            break
        g.make_move(rng.choice(g.valid_moves()))
    return g


def test_alphabeta_equals_plain_minimax():
    rng = random.Random(3)
    for _ in range(25):
        g = random_position(rng, rng.randint(4, 30))
        if g.is_over():
            continue
        own, opp = g.own_opp()
        r = AlphaBeta(depth=3, endgame=0).rank_moves(g)
        assert abs(r.score - plain_minimax(own, opp, 3)) < 1e-6
        assert abs(AlphaBeta(depth=3, endgame=0).best_move(g).score - r.score) < 1e-6


def test_exact_endgame():
    rng = random.Random(5)
    checked = 0
    while checked < 10:
        g = random_position(rng, rng.randint(54, 57))
        if g.is_over() or g.empties() > 7:
            continue
        own, opp = g.own_opp()
        r = AlphaBeta(depth=2, endgame=10).best_move(g)
        assert r.score == plain_minimax(own, opp, 64)
        checked += 1


def test_explain_move_flags_corner():
    g = OthelloGame()
    a = explain_move(g, "d3")
    assert a["valida"] and a["pecas_viradas"] == 1 and not a["eh_canto"]
    assert explain_move(g, "a1")["valida"] is False
