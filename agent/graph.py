"""Agente LLM PLANEJADOR (StateGraph do LangGraph).

Ciclo percepção -> raciocínio -> ação -> memória:

    START -> observe -> think --(tool_calls)--> tools --(jogou)--> memorize -> END
                          ^                       |
                          '----(analisou/erro)----'   (até MAX_THINK rodadas)
                          |                       '--(limite)--> decide
                          '--(respondeu sem ferramenta)--------> decide
    decide (make_move obrigatório) -> execute --(ok)--> memorize
                 ^                       |
                 '-------(inválida)------'--(esgotou)--> fallback -> memorize

* observe : consulta get_game_status / get_board_state / get_valid_moves e
            injeta a memória (histórico, justificativas, plano anterior).
* think   : a LLM escolhe as ferramentas de análise (evaluate_move,
            search_best_moves, get_move_history) e, quando decide, chama make_move.
* tools   : executa as ferramentas; um make_move inválido volta como erro
            (feedback do ambiente) para a LLM corrigir.
* decide  : rede de segurança: força a LLM a chamar make_move.
* fallback: se a LLM falhar repetidamente, usa a melhor jogada do Alpha-Beta.
* memorize: grava o plano/justificativa na memória do agente.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from othello.game import COLOR_NAME
from othello.search import AlphaBeta

from .tools import DailyLimitError, GameEnv, add_usage, build_tools, timed_invoke

MAX_THINK = 3      # rodadas de raciocínio com ferramentas por lance
MAX_DECIDE = 2     # tentativas extras forçando make_move

SYSTEM = """Você é um agente especialista em Othello jogando com {cor}.
Princípios estratégicos:
1. Cantos (a1, h1, a8, h8) nunca são revertidos: capture-os e não os entregue.
2. Evite casas X (b2, g2, b7, g7) e C (b1, a2, g1, h2, a7, b8, g8, h7) com o canto vizinho vazio.
3. Abertura/meio-jogo: maximize sua mobilidade e reduza a do oponente; virar muitas peças cedo é ruim.
4. Prefira jogadas silenciosas e bordas estáveis. Final (<= 14 vazias): maximize a contagem de peças.
Procedimento: (1) analise as candidatas chamando search_best_moves (planejamento Minimax/Alpha-Beta)
e/ou evaluate_move, em paralelo, numa única rodada; (2) chame make_move(position, reasoning, plan).
Você pode discordar da busca se tiver um motivo estratégico concreto.
reasoning: 1-2 frases em português com critérios concretos. plan: objetivo curto para os próximos lances."""

OBSERVATION = """Lance {n} · fase: {fase} · {vazias} casas vazias
{board}
Jogadas válidas (peças viradas): {moves}
Memória:
{memory}"""

DECIDE = "Decida agora: chame make_move com uma destas jogadas: {moves}."


class PlannerState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    think_rounds: int
    decide_attempts: int
    fallback: bool


def build_planner_graph(llm, env: GameEnv):
    tools = build_tools(env)
    act_tools = [tools["search_best_moves"], tools["evaluate_move"], tools["get_move_history"], tools["make_move"]]
    llm_think = llm.bind_tools(act_tools)
    llm_decide = llm.bind_tools([tools["make_move"]], tool_choice="make_move")

    # --------------------------------------------------------------- nós
    def observe(state: PlannerState):
        g = env.game
        tools["get_game_status"].invoke({})
        board = tools["get_board_state"].invoke({})
        moves = tools["get_valid_moves"].invoke({})
        obs = OBSERVATION.format(n=len(g.history) + 1, fase=g.phase(), vazias=g.empties(), board=board,
                                 moves=moves, memory=env.memory.summary(g, env.color))
        return {"messages": [SystemMessage(SYSTEM.format(cor=COLOR_NAME[env.color])), HumanMessage(obs)],
                "think_rounds": 0, "decide_attempts": 0, "fallback": False}

    def think(state: PlannerState):
        try:
            msg = timed_invoke(llm_think, state["messages"], env)
            add_usage(msg, env)
        except DailyLimitError:
            raise
        except Exception as e:  # erro de API: a decisão forçada assume
            msg = AIMessage(f"(raciocínio indisponível: {type(e).__name__})")
        return {"messages": [msg], "think_rounds": state["think_rounds"] + 1}

    def decide(state: PlannerState):
        prompt = HumanMessage(DECIDE.format(moves=", ".join(env.game.valid_moves())))
        try:
            msg = timed_invoke(llm_decide, state["messages"] + [prompt], env)
            add_usage(msg, env)
        except DailyLimitError:
            raise
        except Exception as e:
            msg = AIMessage(f"(falha ao decidir: {type(e).__name__})")
        return {"messages": [prompt, msg], "decide_attempts": state["decide_attempts"] + 1}

    def fallback(state: PlannerState):
        r = AlphaBeta(depth=4).best_move(env.game)
        env.executed = env.game.make_move(r.move, "[fallback] melhor jogada do Alpha-Beta após falha da LLM.")
        env.fallback = True
        return {"fallback": True}

    def memorize(state: PlannerState):
        # make_move já gravou o plano; após um fallback o plano antigo perde validade
        if state.get("fallback"):
            env.memory.last_plan = ""
        return {}

    # ------------------------------------------------------------- rotas
    def has_calls(state):
        return bool(getattr(state["messages"][-1], "tool_calls", None))

    def route_think(state: PlannerState):
        return "tools" if has_calls(state) else "decide"

    def route_tools(state: PlannerState):
        if env.executed is not None:
            return "memorize"
        return "think" if state["think_rounds"] < MAX_THINK else "decide"

    def route_decide(state: PlannerState):
        if has_calls(state):
            return "execute"
        return "decide" if state["decide_attempts"] < MAX_DECIDE else "fallback"

    def route_execute(state: PlannerState):
        if env.executed is not None:
            return "memorize"
        return "decide" if state["decide_attempts"] < MAX_DECIDE else "fallback"

    g = StateGraph(PlannerState)
    g.add_node("observe", observe)
    g.add_node("think", think)
    g.add_node("tools", ToolNode(act_tools, handle_tool_errors=True))
    g.add_node("decide", decide)
    g.add_node("execute", ToolNode([tools["make_move"]], handle_tool_errors=True))
    g.add_node("fallback", fallback)
    g.add_node("memorize", memorize)

    g.add_edge(START, "observe")
    g.add_edge("observe", "think")
    g.add_conditional_edges("think", route_think, ["tools", "decide"])
    g.add_conditional_edges("tools", route_tools, ["memorize", "think", "decide"])
    g.add_conditional_edges("decide", route_decide, ["execute", "decide", "fallback"])
    g.add_conditional_edges("execute", route_execute, ["memorize", "decide", "fallback"])
    g.add_edge("fallback", "memorize")
    g.add_edge("memorize", END)
    return g.compile()
