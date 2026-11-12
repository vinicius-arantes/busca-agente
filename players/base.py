"""Interface comum de jogadores.

Qualquer jogador (inclusive agentes de outros grupos no torneio) só precisa
implementar ``choose_move(game) -> (coordenada, justificativa)``. Agentes que
agem sobre o ambiente via ferramentas (os agentes LLM) sobrescrevem ``play``,
pois são eles próprios que executam ``make_move`` no jogo.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from othello.game import OthelloGame


@dataclass
class TurnInfo:
    move: str
    reasoning: str = ""
    elapsed: float = 0.0          # tempo total da decisão (s)
    llm_calls: int = 0
    llm_time: float = 0.0         # tempo gasto esperando a LLM (s)
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: int = 0
    tools_used: list[str] = field(default_factory=list)
    invalid_attempts: int = 0     # jogadas inválidas propostas pela LLM
    fallback: bool = False        # True se a jogada veio do mecanismo de segurança
    nodes: int = 0                # nós visitados na busca (Alpha-Beta)
    llm_errors: int = 0           # exceções da API (rate limit, tool call malformada...)
    plan: str = ""                # plano de curto prazo (agente planejador)

    def as_dict(self):
        d = asdict(self)
        d["tools_used"] = ",".join(self.tools_used)
        return d


class Player:
    name = "player"
    is_human = False
    uses_llm = False

    def reset(self, color: int):
        """Chamado no início de cada partida."""
        self.color = color

    def choose_move(self, game: OthelloGame) -> tuple[str, str]:
        raise NotImplementedError

    def play(self, game: OthelloGame) -> TurnInfo:
        t0 = time.perf_counter()
        move, why = self.choose_move(game.clone())
        game.make_move(move, why)
        info = getattr(self, "_last_info", None) or TurnInfo(move)
        info.move, info.reasoning, info.elapsed = move, why, time.perf_counter() - t0
        self._last_info = None
        return info
