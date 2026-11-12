"""Função de avaliação heurística do Othello.

Critérios clássicos (cada um normalizado e ponderado conforme a fase do jogo):

* posicional   - matriz de pesos por casa (cantos ótimos, casas X/C perigosas
                 enquanto o canto vizinho estiver vazio);
* mobilidade   - nº de jogadas próprias vs. do oponente;
* fronteira    - peças vizinhas de casas vazias (quanto menos, melhor);
* cantos       - posse dos 4 cantos;
* estabilidade - peças que não podem mais ser viradas (aprox.: ancoradas
                 nos cantos ao longo das bordas);
* paridade     - diferença de peças (só pesa no final).
"""
from __future__ import annotations

from .game import (MASK, SHIFTS, OthelloGame, bits, flips_mask, moves_mask,
                   popcount, to_coord, to_index)

WEIGHTS = [
    100, -20, 10, 5, 5, 10, -20, 100,
    -20, -50, -2, -2, -2, -2, -50, -20,
    10, -2, 1, 1, 1, 1, -2, 10,
    5, -2, 1, 0, 0, 1, -2, 5,
    5, -2, 1, 0, 0, 1, -2, 5,
    10, -2, 1, 1, 1, 1, -2, 10,
    -20, -50, -2, -2, -2, -2, -50, -20,
    100, -20, 10, 5, 5, 10, -20, 100,
]

CORNERS = (0, 7, 56, 63)
CORNER_MASK = sum(1 << c for c in CORNERS)
# casa X (diagonal) e casas C (adjacentes) de cada canto
X_OF = {0: 9, 7: 14, 56: 49, 63: 54}
C_OF = {0: (1, 8), 7: (6, 15), 56: (48, 57), 63: (55, 62)}
X_SQUARES = {v: k for k, v in X_OF.items()}
C_SQUARES = {c: k for k, cs in C_OF.items() for c in cs}
EDGE_MASK = 0xFF000000000000FF | 0x8181818181818181
# direções ao longo das bordas a partir de cada canto (passo de índice)
EDGE_WALKS = {0: (1, 8), 7: (-1, 8), 56: (1, -8), 63: (-1, -8)}

WIN_SCORE = 100_000

# pesos por fase: (posicional, mobilidade, fronteira, cantos, estabilidade, paridade)
PHASE_WEIGHTS = {
    "abertura": (1.0, 5.0, 3.0, 30.0, 2.0, 0.0),
    "meio-jogo": (1.0, 4.0, 2.0, 30.0, 3.0, 1.0),
    "final": (0.5, 2.0, 0.5, 30.0, 4.0, 5.0),
}


def phase_of(empties: int) -> str:
    return "abertura" if empties > 44 else "meio-jogo" if empties > 14 else "final"


def _ratio(a: int, b: int) -> float:
    return 100.0 * (a - b) / (a + b) if a + b else 0.0


def positional(own: int, opp: int) -> int:
    occupied = own | opp
    total = 0
    for i in bits(own | opp):
        w = WEIGHTS[i]
        # casas X/C só são ruins enquanto o canto correspondente estiver vazio
        corner = X_SQUARES.get(i, C_SQUARES.get(i))
        if corner is not None and occupied >> corner & 1:
            w = 5
        total += w if own >> i & 1 else -w
    return total


def frontier(disks: int, empty: int) -> int:
    near_empty = 0
    for sh in SHIFTS:
        near_empty |= sh(empty)
    return popcount(disks & near_empty)


def stable_edge(disks: int) -> int:
    """Peças estáveis aproximadas: sequências contíguas ao longo das bordas
    que partem de um canto ocupado pela mesma cor."""
    stable = 0
    for corner, steps in EDGE_WALKS.items():
        if not disks >> corner & 1:
            continue
        stable |= 1 << corner
        for step in steps:
            i = corner
            for _ in range(7):
                i += step
                if not disks >> i & 1:
                    break
                stable |= 1 << i
    return popcount(stable)


def terminal_score(own: int, opp: int) -> float:
    d = popcount(own) - popcount(opp)
    return WIN_SCORE + d if d > 0 else -WIN_SCORE + d if d < 0 else 0.0


def components(own: int, opp: int) -> dict[str, float]:
    empty = ~(own | opp) & MASK
    return {
        "posicional": positional(own, opp),
        "mobilidade": _ratio(popcount(moves_mask(own, opp)), popcount(moves_mask(opp, own))),
        "fronteira": -_ratio(frontier(own, empty), frontier(opp, empty)),
        "cantos": 25.0 * (popcount(own & CORNER_MASK) - popcount(opp & CORNER_MASK)),
        "estabilidade": 10.0 * (stable_edge(own) - stable_edge(opp)),
        "paridade": _ratio(popcount(own), popcount(opp)),
    }


def evaluate(own: int, opp: int) -> float:
    """Avaliação do ponto de vista de ``own`` (positivo = bom para ``own``)."""
    if not moves_mask(own, opp) and not moves_mask(opp, own):
        return terminal_score(own, opp)
    empties = 64 - popcount(own | opp)
    w = PHASE_WEIGHTS[phase_of(empties)]
    c = components(own, opp)
    return (w[0] * c["posicional"] + w[1] * c["mobilidade"] + w[2] * c["fronteira"]
            + w[3] * c["cantos"] / 25.0 * 4 + w[4] * c["estabilidade"] + w[5] * c["paridade"])


def evaluate_game(game: OthelloGame, player: int) -> float:
    own, opp = game.own_opp(player)
    return evaluate(own, opp)


def explain_move(game: OthelloGame, coord: str) -> dict:
    """Análise detalhada de uma jogada (usada pela ferramenta ``evaluate_move``)."""
    idx = to_index(coord)
    own, opp = game.own_opp()
    b = 1 << idx
    if not moves_mask(own, opp) & b:
        return {"jogada": coord, "valida": False}
    f = flips_mask(own, opp, b)
    n_own, n_opp = own | b | f, opp & ~f
    opp_moves = moves_mask(n_opp, n_own)
    occupied = n_own | n_opp
    corner = X_SQUARES.get(idx, C_SQUARES.get(idx))
    risky = corner is not None and not (occupied >> corner & 1)
    return {
        "jogada": coord,
        "valida": True,
        "pecas_viradas": popcount(f),
        "eh_canto": idx in CORNERS,
        "eh_borda": bool(EDGE_MASK >> idx & 1),
        "casa_perigosa": ("X" if idx in X_SQUARES else "C") + f" (vizinha do canto {to_coord(corner)} vazio)" if risky else None,
        "entrega_canto_ao_oponente": [to_coord(c) for c in CORNERS if opp_moves >> c & 1],
        "mobilidade_oponente_apos": popcount(opp_moves),
        "minha_mobilidade_apos": popcount(moves_mask(n_own, n_opp)),
        "pecas_estaveis_apos": stable_edge(n_own),
        "valor_posicional_casa": WEIGHTS[idx],
        "score_heuristico": round(evaluate(n_own, n_opp), 1),
    }
