"""Ferramentas (LangChain tools) que conectam o agente ao ambiente Othello.

Obrigatórias: get_board_state, get_valid_moves, make_move, get_game_status.
Extras de análise: evaluate_move, search_best_moves, get_move_history.

As tools são criadas por ``build_tools(env)`` e operam sobre ``env.game``
(o jogo real). Cada chamada é registrada em ``env.stats`` para as métricas.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field

from langchain_core.tools import tool

from othello.game import COLOR_NAME, IllegalMoveError, MoveRecord, OthelloGame
from othello.heuristics import explain_move
from othello.search import AlphaBeta

from .memory import AgentMemory


@dataclass
class TurnStats:
    llm_calls: int = 0
    llm_time: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    llm_errors: int = 0
    tools: list[str] = field(default_factory=list)
    invalid_attempts: int = 0


class GameEnv:
    """Estado compartilhado entre o agente e suas ferramentas."""

    def __init__(self, color: int, memory: AgentMemory):
        self.color = color
        self.memory = memory
        self.game: OthelloGame | None = None
        self.executed: MoveRecord | None = None
        self.fallback = False
        self.stats = TurnStats()

    def new_turn(self, game: OthelloGame):
        self.game = game
        self.executed = None
        self.fallback = False
        self.stats = TurnStats()


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def board_text(game: OthelloGame, color: int) -> str:
    b, w = game.score()
    return (f"{game.to_text()}\n"
            f"Legenda: B=pretas, W=brancas, .=vazia, *=jogada válida para quem está na vez. "
            f"Linha 1 = borda de cima, linha 8 = borda de baixo, coluna a = esquerda, h = direita.\n"
            f"Você joga com {COLOR_NAME[color]} ({'B' if color == 1 else 'W'}). "
            f"Vez de: {COLOR_NAME[game.current]}. Placar: pretas {b} x {w} brancas.")


def build_tools(env: GameEnv) -> dict:
    def log(name):
        env.stats.tools.append(name)

    @tool
    def get_board_state() -> str:
        """Retorna o tabuleiro 8x8 atual (colunas a-h, linhas 1-8), de quem é a vez e o placar."""
        log("get_board_state")
        return board_text(env.game, env.color)

    @tool
    def get_valid_moves() -> str:
        """Lista as jogadas válidas do jogador da vez e quantas peças cada uma vira."""
        log("get_valid_moves")
        g = env.game
        return _dump({m: len(g.flips_for(m)) for m in g.valid_moves()} or "nenhuma jogada válida")

    @tool
    def get_game_status() -> str:
        """Situação da partida: em andamento ou encerrada, vez, placar, nº do lance, fase e vencedor."""
        log("get_game_status")
        g = env.game
        b, w = g.score()
        win = g.winner()
        return _dump({
            "encerrada": g.is_over(),
            "vez": COLOR_NAME[g.current],
            "voce_joga_com": COLOR_NAME[env.color],
            "placar": {"pretas": b, "brancas": w},
            "lance": len(g.history) + 1,
            "casas_vazias": g.empties(),
            "fase": g.phase(),
            "vencedor": None if win is None else COLOR_NAME.get(win, "empate"),
        })

    @tool
    def make_move(position: str, reasoning: str = "", plan: str = "") -> str:
        """Executa sua jogada na casa `position` (ex.: 'd3').
        `reasoning`: justificativa curta da escolha. `plan`: plano para os próximos lances."""
        log("make_move")
        g = env.game
        if env.executed is not None:
            return "Você já jogou neste turno. Aguarde o oponente."
        if g.current != env.color:
            return "Não é a sua vez."
        try:
            rec = g.make_move(position, reasoning)
        except (IllegalMoveError, ValueError) as e:
            env.stats.invalid_attempts += 1
            return f"ERRO: {e}"
        env.executed = rec
        env.memory.last_plan = plan or env.memory.last_plan
        b, w = g.score()
        return (f"OK: {position} executada, virou {len(rec.flipped)} peça(s) ({', '.join(rec.flipped)}). "
                f"Placar: pretas {b} x {w} brancas. Turno encerrado.")

    @tool
    def evaluate_move(position: str) -> str:
        """Analisa uma jogada candidata SEM executá-la: peças viradas, se é canto/borda,
        se é casa perigosa (X/C), se entrega canto ao oponente, mobilidade resultante e score heurístico."""
        log("evaluate_move")
        try:
            return _dump(explain_move(env.game, position))
        except ValueError as e:
            return f"ERRO: {e}"

    @tool
    def search_best_moves(k: int = 3, depth: int = 4) -> str:
        """Planejamento: busca Minimax com poda Alpha-Beta (`depth` lances à frente, máx. 5)
        e retorna as `k` melhores jogadas com seus scores (maior = melhor para você)."""
        log("search_best_moves")
        depth = max(1, min(int(depth), 5))
        r = AlphaBeta(depth=depth, endgame=10).rank_moves(env.game)
        return _dump({"profundidade": r.depth, "nos_visitados": r.nodes,
                      "ranking": [{"jogada": m, "score": round(s, 1)} for m, s in r.ranked[:max(1, int(k))]]})

    @tool
    def get_move_history(last_n: int = 10) -> str:
        """Histórico da partida (memória): últimos lances de ambos e suas justificativas anteriores."""
        log("get_move_history")
        return env.memory.history_text(env.game, last_n)

    return {t.name: t for t in (get_board_state, get_valid_moves, make_move, get_game_status,
                                evaluate_move, search_best_moves, get_move_history)}


class DailyLimitError(RuntimeError):
    """Cota diária da API esgotada: não adianta tentar de novo hoje."""


MALFORMED_RETRIES = 3


def timed_invoke(llm, messages, env: GameEnv):
    """Invoca a LLM registrando chamadas, latência e tokens.

    Chamadas de ferramenta malformadas (o Groq devolve 400 "tool_use_failed",
    p.ex. nome 'make_move<|channel|>commentary' nos modelos gpt-oss) são
    estocásticas: a chamada é repetida até MALFORMED_RETRIES vezes."""
    for attempt in range(MALFORMED_RETRIES + 1):
        t0 = time.perf_counter()
        try:
            return llm.invoke(messages)
        except Exception as e:
            env.stats.llm_errors += 1
            msg = str(e)
            print(f"  [LLM] {type(e).__name__}: {msg[:120]}", file=sys.stderr, flush=True)
            if "per day" in msg or "TPD" in msg or "RPD" in msg:
                raise DailyLimitError(msg) from e
            malformed = "tool_use_failed" in msg or "Tool call validation failed" in msg
            if not malformed or attempt == MALFORMED_RETRIES:
                raise
        finally:
            env.stats.llm_calls += 1
            env.stats.llm_time += time.perf_counter() - t0


def add_usage(msg, env: GameEnv):
    u = getattr(msg, "usage_metadata", None) or {}
    env.stats.tokens_in += u.get("input_tokens", 0)
    env.stats.tokens_out += u.get("output_tokens", 0)
