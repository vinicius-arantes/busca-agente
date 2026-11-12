"""Análise dos experimentos: tabelas (Markdown) e gráficos (PNG) em results/.

    python -m experiments.analyze
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"

# cor fixa por agente (a cor acompanha a entidade, nunca a posição)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
NEUTRAL = "#b4b2ab"
TEXT, TEXT2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e2dc", "#fcfcfb"
AGENT_ORDER = ["LLM-Planejador", "LLM-Básico", "Minimax", "Heurístico", "Aleatório"]


def agent_color(name: str) -> str:
    for i, prefix in enumerate(AGENT_ORDER):
        if name.startswith(prefix):
            return SERIES[i]
    return NEUTRAL


def short(name: str) -> str:
    """Rótulo curto para gráficos: 'LLM-Planejador (gpt-oss-120b)' -> 'Planejador·120b'."""
    import re
    m = re.match(r"LLM-(\w+) \(gpt-oss-(\w+)\)", name)
    return f"{m.group(1)}·{m.group(2)}" if m else name


TYPE_LABEL = {"LLM-Planejador": "LLM Planejador", "LLM-Básico": "LLM Básico", "Minimax": "Minimax",
              "Heurístico": "Heurístico", "Aleatório": "Aleatório"}


def style(ax, title, xlabel=None):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=12, color=TEXT, pad=10)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT2, labelsize=9, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=TEXT2, fontsize=9)


def save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout()
    fig.savefig(FIGS / name, dpi=160)
    plt.close(fig)


def load():
    games = pd.read_csv(RESULTS / "games.csv")
    turns = pd.read_csv(RESULTS / "turns.csv")
    return games, turns


# ------------------------------------------------------------------ tabelas
def matchup_table(games: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for match, g in games.groupby("match", sort=False):
        a, b = g["agent_a"].iloc[0], g["agent_b"].iloc[0]
        diff_a = [(r.score_black - r.score_white) * (1 if r.black == a else -1) for r in g.itertuples()]
        n = len(g)
        wa, wb = (g["winner_agent"] == a).sum(), (g["winner_agent"] == b).sum()
        rows.append({"Confronto": match, "Partidas": n, "Vitórias A": wa, "Empates": n - wa - wb,
                     "Vitórias B": wb, "Taxa vitória A": wa / n, "Saldo médio de peças (A)": sum(diff_a) / n,
                     "Lances médios": g["n_moves"].mean(), "Duração média (s)": g["duration"].mean(),
                     "Fallbacks (A+B)": int(g["fallbacks_a"].sum() + g["fallbacks_b"].sum()),
                     "Erros API (A+B)": int(g["llm_errors_a"].sum() + g["llm_errors_b"].sum())})
    return pd.DataFrame(rows)


def agent_table(games: pd.DataFrame, turns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for agent, t in turns.groupby("agent", sort=False):
        mine = games[(games["agent_a"] == agent) | (games["agent_b"] == agent)]
        w = (mine["winner_agent"] == agent).sum()
        d = (mine["winner_agent"] == "empate").sum()
        n = len(mine)
        rows.append({
            "Agente": agent, "Partidas": n, "V": w, "E": d, "D": n - w - d, "Taxa de vitória": w / n if n else 0,
            "Lances": len(t), "Tempo médio/lance (s)": t["elapsed"].mean(),
            "Chamadas LLM/lance": t["llm_calls"].mean(), "Latência LLM/lance (s)": t["llm_time"].mean(),
            "Tokens/lance": (t["tokens_in"] + t["tokens_out"]).mean(),
            "Tool calls/lance": t["tool_calls"].mean(),
            "Jogadas inválidas": int(t["invalid_attempts"].sum()),
            "Fallbacks": int(t["fallback"].astype(bool).sum()),
        })
    df = pd.DataFrame(rows)
    df["_o"] = df["Agente"].map(lambda a: next((i for i, p in enumerate(AGENT_ORDER) if a.startswith(p)), 99))
    return df.sort_values("_o").drop(columns="_o")


def tool_usage(turns: pd.DataFrame) -> pd.DataFrame:
    llm = turns[turns["llm_calls"] > 0].copy()
    llm["tools_used"] = llm["tools_used"].fillna("")
    rows = []
    for agent, t in llm.groupby("agent"):
        counts = t["tools_used"].str.split(",").explode().value_counts()
        for tool, c in counts.items():
            if tool:
                rows.append({"Agente": agent, "Ferramenta": tool, "Chamadas": c, "Por lance": c / len(t)})
    return pd.DataFrame(rows)


def to_md(df: pd.DataFrame) -> str:
    fmt = df.copy()
    for c in fmt.columns:
        if fmt[c].dtype == float:
            fmt[c] = fmt[c].map(lambda v: "-" if v != v else f"{v:.0%}" if "Taxa" in c else f"{v:.2f}")
    head = "| " + " | ".join(fmt.columns) + " |\n|" + "---|" * len(fmt.columns) + "\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in fmt.itertuples(index=False))


def move_records(games: pd.DataFrame, turns: pd.DataFrame) -> pd.DataFrame:
    """Reproduz as partidas com LLM e gera 1 registro por lance (após a abertura sorteada):
    jogada escolhida x ranking do Alfa-Beta (prof. 4, final exato), perda de score e riscos."""
    sys.path.insert(0, str(ROOT))
    from othello.game import BLACK, OthelloGame, to_index
    from othello.heuristics import CORNERS, WIN_SCORE, explain_move
    from othello.search import AlphaBeta

    ab = AlphaBeta(depth=4, endgame=10)
    recs = []
    llm_games = games[games["model"].fillna("").astype(str) != ""]
    for r in llm_games.itertuples():
        n_open = len(r.opening.split()) if isinstance(r.opening, str) else 0
        tg = turns[(turns["match"] == r.match) & (turns["game"] == r.game) & (turns["run_id"] == r.run_id)]
        tg = tg.set_index("turn")
        g = OthelloGame()
        played = k = 0
        for mv in str(r.moves).split():
            if mv == "--":
                continue
            if played >= n_open:
                agent = r.black if g.current == BLACK else r.white
                ranked = ab.rank_moves(g).ranked
                scores = dict(ranked)
                best_mv, best_sc = ranked[0]
                info = explain_move(g, mv)
                corners_avail = [m for m in scores if to_index(m) in CORNERS]
                row = tg.loc[k] if k in tg.index else None
                won_lost = abs(best_sc) >= WIN_SCORE / 2 or abs(scores[mv]) >= WIN_SCORE / 2
                recs.append({
                    "agente": agent, "match": r.match, "game": r.game, "lance": played + 1, "fase": g.phase(),
                    "jogada": mv, "melhor": best_mv, "n_validas": len(ranked),
                    "rank": [m for m, _ in ranked].index(mv) + 1,
                    "perda": best_sc - scores[mv], "muda_resultado": won_lost and (best_sc > 0) != (scores[mv] > 0),
                    "canto_disp": bool(corners_avail), "canto_tomado": mv in corners_avail,
                    "x_perigosa": bool(info.get("casa_perigosa")) and info["casa_perigosa"].startswith("X"),
                    "entrega_canto": bool(info.get("entrega_canto_ao_oponente")),
                    "reasoning": "" if row is None or not isinstance(row["reasoning"], str) else row["reasoning"],
                })
                k += 1
            g.make_move(mv)
            played += 1
    return pd.DataFrame(recs)


def quality_table(mr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for agent, m in mr.groupby("agente", sort=False):
        ca = m[m["canto_disp"]]
        rows.append({"Agente": agent, "Lances analisados": len(m),
                     "Taxa concordância c/ Alfa-Beta d4": (m["rank"] == 1).mean(),
                     "Rank médio da jogada": m["rank"].mean(),
                     "Taxa canto tomado (quando disponível)": ca["canto_tomado"].mean() if len(ca) else float("nan"),
                     "Vezes c/ canto disponível": len(ca),
                     "Taxa casa X perigosa": m["x_perigosa"].mean(),
                     "Taxa entrega canto": m["entrega_canto"].mean()})
    return pd.DataFrame(rows)


def divergence_table(mr: pd.DataFrame) -> pd.DataFrame:
    """Quando o agente NÃO joga o top-1 da busca, quanto isso custa?"""
    rows = []
    for agent, m in mr.groupby("agente", sort=False):
        d = m[m["rank"] > 1]
        finite = d[~d["muda_resultado"] & (d["perda"].abs() < 50_000)]
        rows.append({"Agente": agent, "Lances": len(m), "Divergências": len(d),
                     "Taxa divergência": len(d) / len(m) if len(m) else 0,
                     "Perda mediana (pts)": finite["perda"].median() if len(finite) else float("nan"),
                     "Divergências quase equivalentes (perda < 15)": int((finite["perda"] < 15).sum()),
                     "Divergências graves (perda >= 100)": int((finite["perda"] >= 100).sum()),
                     "Divergências que mudam o resultado (final exato)": int(d["muda_resultado"].sum())})
    return pd.DataFrame(rows)


def divergence_examples(mr: pd.DataFrame, agent_prefix="LLM-Planejador", n=6) -> str:
    d = mr[mr["agente"].str.startswith(agent_prefix) & (mr["rank"] > 1)].copy()
    if d.empty:
        return ""
    d["perda_cap"] = d["perda"].clip(upper=10_000)
    d = d.sort_values("perda_cap")
    pick = pd.concat([d.head(n // 2), d.tail(n - n // 2)]).drop_duplicates()
    lines = []
    for r in pick.itertuples():
        perda = "muda o resultado" if r.muda_resultado else f"perda {r.perda:.0f}"
        lines.append(f"* **{r.agente}**, lance {r.lance} ({r.fase}): jogou **{r.jogada}** "
                     f"(rank {r.rank}/{r.n_validas}), busca preferia **{r.melhor}** ({perda}). "
                     f"Justificativa: \"{r.reasoning}\"")
    return "\n".join(lines)


# ----------------------------------------------------------------- gráficos
def fig_matchups(mt: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(mt) + 1.6))
    y = range(len(mt))[::-1]
    for yi, r in zip(y, mt.itertuples()):
        a, b = r.Confronto.split(" x ")
        n = r.Partidas
        segs = [(r._3 / n, agent_color(a), f"{a}: {r._3}"), (r.Empates / n, NEUTRAL, f"empates: {r.Empates}"),
                (r._5 / n, agent_color(b), f"{b}: {r._5}")]
        left = 0
        for frac, col, lab in segs:
            if frac > 0:
                ax.barh(yi, frac, left=left, height=0.55, color=col, edgecolor=SURFACE, linewidth=2)
                if frac >= 0.12:
                    ax.text(left + frac / 2, yi, lab.split(":")[-1].strip(), ha="center", va="center",
                            fontsize=9, color="white" if col != NEUTRAL else TEXT)
            left += frac
    ax.set_yticks(list(y))
    ax.set_yticklabels([" x ".join(short(a) for a in c.split(" x ")) + f"  (n={n})"
                        for c, n in zip(mt["Confronto"], mt["Partidas"])], color=TEXT)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    style(ax, "Resultado por confronto (proporção das partidas)")
    present = {p for c in mt["Confronto"] for a in c.split(" x ") for p in AGENT_ORDER if a.startswith(p)}
    types = [p for p in AGENT_ORDER if p in present]
    handles = [plt.Rectangle((0, 0), 1, 1, color=SERIES[AGENT_ORDER.index(p)]) for p in types] + [plt.Rectangle((0, 0), 1, 1, color=NEUTRAL)]
    ax.legend(handles, [f"vitórias {TYPE_LABEL[p]}" for p in types] + ["empates"], loc="upper center",
              bbox_to_anchor=(0.4, -0.13), ncol=3, frameon=False, fontsize=8, labelcolor=TEXT2)
    save(fig, "resultados_confrontos.png")


def fig_time(at: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(at) + 1.2))
    y = list(range(len(at)))[::-1]
    vals = at["Tempo médio/lance (s)"]
    ax.barh(y, vals, height=0.55, color=[agent_color(a) for a in at["Agente"]])
    for yi, v in zip(y, vals):
        ax.text(v, yi, f"  {v:.3f}s" if v < 1 else f"  {v:.1f}s", va="center", fontsize=9, color=TEXT)
    ax.set_xscale("symlog", linthresh=0.01)
    ax.set_yticks(y)
    ax.set_yticklabels([short(a) for a in at["Agente"]], color=TEXT)
    style(ax, "Tempo médio de decisão por lance", "segundos (escala log)")
    save(fig, "tempo_por_lance.png")


def fig_llm_cost(at: pd.DataFrame):
    llm = at[at["Chamadas LLM/lance"] > 0]
    if llm.empty:
        return
    metrics = [("Chamadas LLM/lance", "Chamadas à LLM"), ("Tool calls/lance", "Tool calls"),
               ("Tokens/lance", "Tokens"), ("Latência LLM/lance (s)", "Latência LLM (s)")]
    fig, axes = plt.subplots(1, len(metrics), figsize=(12, 0.55 * len(llm) + 1.6), sharey=True)
    y = list(range(len(llm)))[::-1]
    for ax, (col, title) in zip(axes, metrics):
        vals = llm[col]
        ax.barh(y, vals, height=0.55, color=[agent_color(a) for a in llm["Agente"]])
        for yi, v in zip(y, vals):
            ax.text(v, yi, f" {v:.0f}" if v >= 100 else f" {v:.1f}", va="center", fontsize=9, color=TEXT)
        ax.set_xlim(0, vals.max() * 1.35)
        style(ax, title)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([short(a) for a in llm["Agente"]], color=TEXT)
    fig.suptitle("Custo médio por lance dos agentes LLM", x=0.01, ha="left", fontsize=12, color=TEXT)
    save(fig, "custo_llm.png")


def fig_tools(tu: pd.DataFrame):
    if tu.empty:
        return
    agents = sorted(tu["Agente"].unique(), key=lambda a: (not a.startswith("LLM-Plan"), a))
    ncol = 2
    nrow = (len(agents) + 1) // 2
    fig, axes = plt.subplots(nrow, ncol, figsize=(10, 2.9 * nrow), squeeze=False)
    for ax in axes.flat[len(agents):]:
        ax.set_visible(False)
    for ax, agent in zip(axes.flat, agents):
        t = tu[tu["Agente"] == agent].sort_values("Por lance")
        ax.barh(t["Ferramenta"], t["Por lance"], height=0.55, color=agent_color(agent))
        for yi, v in enumerate(t["Por lance"]):
            ax.text(v, yi, f" {v:.2f}", va="center", fontsize=9, color=TEXT)
        ax.set_xlim(0, t["Por lance"].max() * 1.3)
        ax.tick_params(axis="y", labelcolor=TEXT)
        style(ax, f"{short(agent)}: chamadas por lance")
    save(fig, "uso_ferramentas.png")


def fig_quality(mr: pd.DataFrame):
    if mr.empty:
        return
    q = quality_table(mr)
    q["_o"] = q["Agente"].map(lambda a: next((i for i, p in enumerate(AGENT_ORDER) if a.startswith(p)), 99))
    q = q.sort_values("_o")
    metrics = [("Taxa concordância c/ Alfa-Beta d4", "Joga a melhor jogada da busca", True),
               ("Taxa casa X perigosa", "Joga casa X com canto vazio", True),
               ("Taxa entrega canto", "Entrega canto ao oponente", True)]
    fig, axes = plt.subplots(1, 3, figsize=(11, 0.55 * len(q) + 1.7), sharey=True)
    y = list(range(len(q)))[::-1]
    for ax, (col, title, pct) in zip(axes, metrics):
        vals = q[col]
        ax.barh(y, vals, height=0.55, color=[agent_color(a) for a in q["Agente"]])
        for yi, v in zip(y, vals):
            ax.text(v, yi, f" {v:.0%}", va="center", fontsize=9, color=TEXT)
        ax.set_xlim(0, max(vals.max() * 1.35, 0.1))
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        style(ax, title)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([f"{short(a)}  (n={n})" for a, n in zip(q["Agente"], q["Lances analisados"])], color=TEXT)
    fig.suptitle("Qualidade dos lances nas partidas com LLM (n = lances analisados)", x=0.01, ha="left", fontsize=12, color=TEXT)
    save(fig, "qualidade_lances.png")


def main():
    if not (RESULTS / "games.csv").exists():
        sys.exit("Sem resultados: rode experiments.run_experiments primeiro.")
    games, turns = load()
    mt, at, tu = matchup_table(games), agent_table(games, turns), tool_usage(turns)
    fig_matchups(mt)
    fig_time(at)
    fig_llm_cost(at)
    fig_tools(tu)
    md = ["# Resultados dos experimentos", "", "## Por confronto (A = primeiro agente do confronto)", "",
          to_md(mt), "", "## Por agente", "", to_md(at), ""]
    if not tu.empty:
        md += ["## Uso de ferramentas (agentes LLM)", "", to_md(tu), ""]
    mr = move_records(games, turns)
    if not mr.empty:
        mr.to_csv(RESULTS / "move_quality.csv", index=False)
        fig_quality(mr)
        md += ["## Qualidade dos lances (partidas com LLM, após a abertura sorteada)", "", to_md(quality_table(mr)), "",
               "## Divergências em relação ao Alfa-Beta (prof. 4)", "", to_md(divergence_table(mr)), "",
               "### Exemplos de divergência do Planejador", "", divergence_examples(mr), ""]
    (RESULTS / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\nGráficos em {FIGS}")


if __name__ == "__main__":
    main()
