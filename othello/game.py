"""Motor do jogo Othello (Reversi).

Representação por *bitboards*: cada cor é um inteiro de 64 bits em que o bit
``i = linha * 8 + coluna`` indica a presença de uma peça. Coluna 0 = 'a',
linha 0 = '1' (notação padrão, a mesma usada no eOthello).

Regras implementadas:
* tabuleiro 8x8 com a posição inicial padrão (d4/e5 brancas, e4/d5 pretas);
* jogada válida = casa vazia que cerca, em linha reta (8 direções), uma ou
  mais peças adversárias contíguas terminando numa peça própria;
* captura/inversão de todas as linhas cercadas;
* passe obrigatório quando o jogador da vez não possui jogada válida;
* fim de jogo quando nenhum dos dois jogadores pode jogar.
"""
from __future__ import annotations

from dataclasses import dataclass, field

EMPTY, BLACK, WHITE = 0, 1, -1
COLOR_NAME = {BLACK: "Pretas", WHITE: "Brancas"}
COLOR_SYMBOL = {BLACK: "B", WHITE: "W", EMPTY: "."}

MASK = 0xFFFFFFFFFFFFFFFF
NOT_A = 0xFEFEFEFEFEFEFEFE  # zera a coluna 'a' (evita "dar a volta" pela borda)
NOT_H = 0x7F7F7F7F7F7F7F7F  # zera a coluna 'h'


def _e(x): return (x << 1) & NOT_A
def _w(x): return (x >> 1) & NOT_H
def _s(x): return (x << 8) & MASK
def _n(x): return x >> 8
def _se(x): return (x << 9) & NOT_A & MASK
def _sw(x): return (x << 7) & NOT_H & MASK
def _ne(x): return (x >> 7) & NOT_A
def _nw(x): return (x >> 9) & NOT_H


SHIFTS = (_e, _w, _s, _n, _se, _sw, _ne, _nw)
COLS = "abcdefgh"


def to_coord(idx: int) -> str:
    return f"{COLS[idx % 8]}{idx // 8 + 1}"


def to_index(coord: str) -> int:
    c = coord.strip().lower()
    if len(c) != 2 or c[0] not in COLS or c[1] not in "12345678":
        raise ValueError(f"Coordenada inválida: {coord!r} (use letra a-h + número 1-8, ex.: 'd3')")
    return (int(c[1]) - 1) * 8 + COLS.index(c[0])


def bits(x: int):
    """Itera sobre os índices dos bits ligados."""
    while x:
        low = x & -x
        yield low.bit_length() - 1
        x ^= low


def popcount(x: int) -> int:
    return x.bit_count()


def moves_mask(own: int, opp: int) -> int:
    """Bitboard com todas as jogadas válidas para ``own``."""
    empty = ~(own | opp) & MASK
    moves = 0
    for sh in SHIFTS:
        x = sh(own) & opp
        x |= sh(x) & opp
        x |= sh(x) & opp
        x |= sh(x) & opp
        x |= sh(x) & opp
        x |= sh(x) & opp
        moves |= sh(x) & empty
    return moves


def flips_mask(own: int, opp: int, move_bit: int) -> int:
    """Peças adversárias invertidas ao jogar em ``move_bit``."""
    flips = 0
    for sh in SHIFTS:
        line = 0
        x = sh(move_bit)
        while x & opp:
            line |= x
            x = sh(x)
        if x & own:
            flips |= line
    return flips


class IllegalMoveError(ValueError):
    pass


@dataclass
class MoveRecord:
    number: int            # nº do lance (1, 2, ...), contando passes
    player: int            # BLACK ou WHITE
    move: str | None       # coordenada ou None para passe
    flipped: list[str] = field(default_factory=list)
    score_after: tuple[int, int] = (0, 0)  # (pretas, brancas)
    reasoning: str = ""    # justificativa (preenchida pelos agentes LLM)


class OthelloGame:
    def __init__(self):
        d4, e4, d5, e5 = (to_index(c) for c in ("d4", "e4", "d5", "e5"))
        self.black = (1 << e4) | (1 << d5)
        self.white = (1 << d4) | (1 << e5)
        self.current = BLACK
        self.history: list[MoveRecord] = []
        self._over = False

    # ------------------------------------------------------------------ util
    def clone(self) -> "OthelloGame":
        g = OthelloGame.__new__(OthelloGame)
        g.black, g.white, g.current, g._over = self.black, self.white, self.current, self._over
        g.history = list(self.history)
        return g

    def own_opp(self, player: int | None = None) -> tuple[int, int]:
        p = self.current if player is None else player
        return (self.black, self.white) if p == BLACK else (self.white, self.black)

    def cell(self, idx: int) -> int:
        if (self.black >> idx) & 1:
            return BLACK
        if (self.white >> idx) & 1:
            return WHITE
        return EMPTY

    def score(self) -> tuple[int, int]:
        return popcount(self.black), popcount(self.white)

    def empties(self) -> int:
        return 64 - popcount(self.black | self.white)

    # ---------------------------------------------------------------- regras
    def valid_moves_mask(self, player: int | None = None) -> int:
        own, opp = self.own_opp(player)
        return moves_mask(own, opp)

    def valid_moves(self, player: int | None = None) -> list[str]:
        if self._over:
            return []
        return [to_coord(i) for i in bits(self.valid_moves_mask(player))]

    def flips_for(self, coord: str, player: int | None = None) -> list[str]:
        own, opp = self.own_opp(player)
        b = 1 << to_index(coord)
        if (own | opp) & b:
            return []
        return [to_coord(i) for i in bits(flips_mask(own, opp, b))]

    def is_valid(self, coord: str) -> bool:
        try:
            idx = to_index(coord)
        except ValueError:
            return False
        return not self._over and bool(self.valid_moves_mask() >> idx & 1)

    def make_move(self, coord: str, reasoning: str = "") -> MoveRecord:
        """Executa a jogada do jogador da vez. Faz passes automáticos quando
        o próximo jogador não tem jogada e detecta o fim de jogo."""
        if self._over:
            raise IllegalMoveError("A partida já terminou.")
        idx = to_index(coord)
        b = 1 << idx
        own, opp = self.own_opp()
        if not (moves_mask(own, opp) & b):
            raise IllegalMoveError(
                f"Jogada {coord} inválida para {COLOR_NAME[self.current]}. "
                f"Jogadas válidas: {', '.join(self.valid_moves()) or 'nenhuma'}")
        f = flips_mask(own, opp, b)
        own |= b | f
        opp &= ~f
        if self.current == BLACK:
            self.black, self.white = own, opp
        else:
            self.white, self.black = own, opp
        rec = MoveRecord(len(self.history) + 1, self.current, to_coord(idx),
                         [to_coord(i) for i in bits(f)], self.score(), reasoning)
        self.history.append(rec)
        self.current = -self.current
        self._resolve_passes()
        return rec

    def _resolve_passes(self):
        if self.valid_moves_mask(self.current):
            return
        if self.valid_moves_mask(-self.current):
            self.history.append(MoveRecord(len(self.history) + 1, self.current, None, [], self.score()))
            self.current = -self.current
        else:
            self._over = True

    def is_over(self) -> bool:
        return self._over

    def winner(self) -> int | None:
        """BLACK, WHITE, EMPTY (empate) ou None se a partida não terminou."""
        if not self._over:
            return None
        b, w = self.score()
        return BLACK if b > w else WHITE if w > b else EMPTY

    def phase(self) -> str:
        e = self.empties()
        return "abertura" if e > 44 else "meio-jogo" if e > 14 else "final"

    # ----------------------------------------------------------- exibição
    def to_text(self, show_moves: bool = True) -> str:
        valid = self.valid_moves_mask() if show_moves and not self._over else 0
        lines = ["    a b c d e f g h"]
        for r in range(8):
            row = []
            for c in range(8):
                i = r * 8 + c
                v = self.cell(i)
                row.append("*" if v == EMPTY and valid >> i & 1 else COLOR_SYMBOL[v])
            lines.append(f"  {r + 1} " + " ".join(row))
        return "\n".join(lines)

    def moves_string(self) -> str:
        return " ".join(r.move or "--" for r in self.history)
