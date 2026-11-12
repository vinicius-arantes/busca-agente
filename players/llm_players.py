"""Adaptadores que transformam os grafos LangGraph em jogadores."""
from __future__ import annotations

import random
import time

from agent.graph import build_planner_graph
from agent.llm import make_llm
from agent.memory import AgentMemory
from agent.react_basic import basic_initial_state, build_basic_graph
from agent.tools import DailyLimitError, GameEnv
from othello.game import OthelloGame

from .base import Player, TurnInfo


class _LLMPlayer(Player):
    uses_llm = True
    label = "LLM"

    def __init__(self, model: str | None = None, temperature: float = 0.2):
        self.llm = make_llm(model, temperature)
        self.model = self.llm.model_name
        self.name = f"{self.label} ({self.model.split('/')[-1]})"
        self.memory = AgentMemory()
        self.rng = random.Random(0)
        self.env = self.graph = None

    def reset(self, color: int):
        super().reset(color)
        self.memory.reset()
        self.env = GameEnv(color, self.memory)
        self.graph = self.build_graph()

    def build_graph(self):
        raise NotImplementedError

    def initial_state(self):
        raise NotImplementedError

    def emergency_move(self, game: OthelloGame) -> str:
        return self.rng.choice(game.valid_moves())

    def play(self, game: OthelloGame) -> TurnInfo:
        t0 = time.perf_counter()
        env = self.env
        env.new_turn(game)
        try:
            self.graph.invoke(self.initial_state(), {"recursion_limit": 40})
        except DailyLimitError:
            raise
        except Exception as e:  # falha inesperada do grafo/API
            env.stats.llm_errors += 1
            print(f"[{self.name}] erro no grafo: {type(e).__name__}: {str(e)[:200]}")
        if env.executed is None:  # mecanismo de segurança: o jogo nunca trava
            env.executed = game.make_move(self.emergency_move(game), "[fallback] LLM não produziu jogada válida.")
            env.fallback = True
        s = env.stats
        return TurnInfo(env.executed.move, env.executed.reasoning, time.perf_counter() - t0,
                        s.llm_calls, s.llm_time, s.tokens_in, s.tokens_out, len(s.tools), list(s.tools),
                        s.invalid_attempts, env.fallback, 0, s.llm_errors, self.memory.last_plan)


class BasicLLMPlayer(_LLMPlayer):
    """ReAct com as 4 ferramentas obrigatórias; fallback = jogada aleatória."""
    label = "LLM-Básico"

    def build_graph(self):
        return build_basic_graph(self.llm, self.env)

    def initial_state(self):
        return basic_initial_state(self.env)


class PlannerLLMPlayer(_LLMPlayer):
    """Observa -> analisa (busca + heurística) -> decide -> valida -> age -> memoriza."""
    label = "LLM-Planejador"

    def build_graph(self):
        return build_planner_graph(self.llm, self.env)

    def initial_state(self):
        return {"messages": [], "think_rounds": 0, "decide_attempts": 0, "fallback": False}
