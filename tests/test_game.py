import random

import pytest

from othello.game import (BLACK, WHITE, EMPTY, IllegalMoveError, OthelloGame,
                          to_coord, to_index)

DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


# ---------------------------------------------------------- referência ingênua
def naive_flips(board, r, c, p):
    if board[r][c] != EMPTY:
        return []
    out = []
    for dr, dc in DIRS:
        line, rr, cc = [], r + dr, c + dc
        while 0 <= rr < 8 and 0 <= cc < 8 and board[rr][cc] == -p:
            line.append((rr, cc))
            rr, cc = rr + dr, cc + dc
        if line and 0 <= rr < 8 and 0 <= cc < 8 and board[rr][cc] == p:
            out += line
    return out


def naive_moves(board, p):
    return sorted(f"{'abcdefgh'[c]}{r + 1}" for r in range(8) for c in range(8)
                  if naive_flips(board, r, c, p))


def to_matrix(g):
    return [[g.cell(r * 8 + c) for c in range(8)] for r in range(8)]


def set_board(g, black, white, current=BLACK):
    g.black = sum(1 << to_index(x) for x in black)
    g.white = sum(1 << to_index(x) for x in white)
    g.current = current


# ------------------------------------------------------------------- testes
def test_coord_roundtrip():
    for i in range(64):
        assert to_index(to_coord(i)) == i
    assert to_index("a1") == 0 and to_index("h8") == 63 and to_index("D3") == 19
    with pytest.raises(ValueError):
        to_index("i9")


def test_initial_position():
    g = OthelloGame()
    assert g.score() == (2, 2)
    assert g.current == BLACK
    assert sorted(g.valid_moves()) == ["c4", "d3", "e6", "f5"]


def test_first_move_flips():
    g = OthelloGame()
    rec = g.make_move("d3")
    assert rec.flipped == ["d4"]
    assert g.score() == (4, 1)
    assert g.current == WHITE
    assert sorted(g.valid_moves()) == ["c3", "c5", "e3"]


def test_illegal_move_raises():
    g = OthelloGame()
    with pytest.raises(IllegalMoveError):
        g.make_move("a1")
    with pytest.raises(IllegalMoveError):
        g.make_move("d4")  # ocupada


def test_flips_in_all_eight_directions():
    g = OthelloGame()
    # d4 cercada por brancas em todas as direções e pretas na borda externa
    white = ["c3", "d3", "e3", "c4", "e4", "c5", "d5", "e5"]
    black = ["b2", "d2", "f2", "b4", "f4", "b6", "d6", "f6"]
    set_board(g, black, white)
    assert sorted(g.flips_for("d4")) == sorted(white)
    g.make_move("d4")
    b, w = g.score()
    assert w == 0 and b == 17


def test_no_wrap_around_edges():
    g = OthelloGame()
    # h1 branca, a2 preta: jogar em ... não deve "dar a volta" pela borda
    set_board(g, black=["a2"], white=["h1"])
    assert g.valid_moves() == []
    set_board(g, black=["a1"], white=["b1", "c1"])
    assert g.valid_moves() == ["d1"]


def test_auto_pass_and_game_over():
    g = OthelloGame()
    # Preta joga a1 e encerra (nenhum dos dois terá jogadas)
    set_board(g, black=["c1"], white=["b1"])
    assert g.valid_moves() == ["a1"]
    g.make_move("a1")
    assert g.is_over() and g.winner() == BLACK and g.score() == (3, 0)

    # Passe: procura em partidas aleatórias uma jogada após a qual o oponente
    # fica sem jogada mas o jogador atual ainda tem -> passe automático
    rng = random.Random(7)
    found = False
    while not found:
        g = OthelloGame()
        while not g.is_over() and not found:
            p = g.current
            g.make_move(rng.choice(g.valid_moves()))
            if not g.is_over() and g.history[-1].move is None:
                assert g.history[-1].player == -p   # oponente passou
                assert g.current == p               # vez volta para quem jogou
                assert g.valid_moves_mask(-p) == 0
                found = True


def test_random_games_match_naive_reference():
    rng = random.Random(42)
    for _ in range(300):
        g = OthelloGame()
        while not g.is_over():
            m = to_matrix(g)
            assert sorted(g.valid_moves()) == naive_moves(m, g.current)
            mv = rng.choice(g.valid_moves())
            r, c = int(mv[1]) - 1, "abcdefgh".index(mv[0])
            expected = {f"{'abcdefgh'[cc]}{rr + 1}" for rr, cc in naive_flips(m, r, c, g.current)}
            rec = g.make_move(mv)
            assert set(rec.flipped) == expected
            # passe só acontece quando o oponente realmente não tem jogada
            if g.history[-1].move is None:
                assert naive_moves(to_matrix(g), g.history[-1].player) == []
        b, w = g.score()
        assert naive_moves(to_matrix(g), BLACK) == [] and naive_moves(to_matrix(g), WHITE) == []
        assert b + w <= 64
