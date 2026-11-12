"""Registro de jogadores disponíveis (usado pela UI, CLI, experimentos e torneio)."""
from __future__ import annotations

from .base import Player, TurnInfo
from .classic import GreedyPlayer, MinimaxPlayer, RandomPlayer


class HumanPlayer(Player):
    name = "Humano"
    is_human = True


def _basic(**kw):
    from .llm_players import BasicLLMPlayer
    return BasicLLMPlayer(**kw)


def _planner(**kw):
    from .llm_players import PlannerLLMPlayer
    return PlannerLLMPlayer(**kw)


REGISTRY = {
    "humano": lambda **kw: HumanPlayer(),
    "aleatorio": lambda seed=None, **kw: RandomPlayer(seed),
    "heuristico": lambda **kw: GreedyPlayer(),
    "minimax": lambda depth=4, **kw: MinimaxPlayer(depth),
    "llm-basico": _basic,
    "llm-planejador": _planner,
}

LABELS = {"humano": "Humano", "aleatorio": "Aleatório", "heuristico": "Heurístico",
          "minimax": "Minimax (d4)", "llm-basico": "LLM Básico", "llm-planejador": "LLM Planejador"}


def make_player(key: str, **kw) -> Player:
    if key not in REGISTRY:
        raise KeyError(f"Jogador desconhecido: {key}. Opções: {', '.join(REGISTRY)}")
    return REGISTRY[key](**kw)


__all__ = ["Player", "TurnInfo", "HumanPlayer", "REGISTRY", "LABELS", "make_player"]
