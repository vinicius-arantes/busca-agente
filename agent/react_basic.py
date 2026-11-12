"""Agente LLM BÁSICO: laço ReAct (LLM <-> ferramentas) com apenas as 4 tools
obrigatórias. A própria LLM decide quando observar e quando jogar.

    START -> agent --(tool_calls)--> tools --(não jogou)--> agent
               |                       '----(jogou)-------> END
               '--(sem tool_calls e não jogou)--> nudge -> agent
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from othello.game import COLOR_NAME

from .tools import GameEnv, add_usage, build_tools, timed_invoke

MAX_LLM_CALLS = 6

SYSTEM = """Você é um agente que joga Othello (Reversi) com as peças {cor}.
A cada turno: observe o ambiente com as ferramentas (get_game_status, get_board_state,
get_valid_moves) e então execute UMA jogada válida com make_move(position, reasoning).
Coordenadas: coluna a-h + linha 1-8 (ex.: 'd3'). Escreva o reasoning em português, em 1 frase."""


class BasicState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_basic_graph(llm, env: GameEnv):
    tools = build_tools(env)
    base_tools = [tools[n] for n in ("get_board_state", "get_valid_moves", "make_move", "get_game_status")]
    llm_tools = llm.bind_tools(base_tools)

    def agent(state: BasicState):
        msg = timed_invoke(llm_tools, state["messages"], env)
        add_usage(msg, env)
        return {"messages": [msg]}

    def nudge(state: BasicState):
        return {"messages": [HumanMessage("Você ainda não jogou. Chame make_move com uma jogada válida.")]}

    def route_agent(state: BasicState):
        if state["messages"][-1].tool_calls:
            return "tools"
        if env.executed is None and env.stats.llm_calls < MAX_LLM_CALLS:
            return "nudge"
        return END

    def route_tools(state: BasicState):
        if env.executed is not None or env.stats.llm_calls >= MAX_LLM_CALLS:
            return END
        return "agent"

    g = StateGraph(BasicState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(base_tools, handle_tool_errors=True))
    g.add_node("nudge", nudge)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route_agent, ["tools", "nudge", END])
    g.add_conditional_edges("tools", route_tools, ["agent", END])
    g.add_edge("nudge", "agent")
    return g.compile()


def basic_initial_state(env: GameEnv) -> BasicState:
    g = env.game
    return {"messages": [
        SystemMessage(SYSTEM.format(cor=COLOR_NAME[env.color])),
        HumanMessage(f"Sua vez (lance {len(g.history) + 1}). Histórico da partida: "
                     f"{g.moves_string() or '(início)'}. Observe e jogue."),
    ]}
