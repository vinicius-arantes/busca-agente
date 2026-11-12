"""Memória do agente: histórico da partida + justificativas e plano corrente."""
from __future__ import annotations

from othello.game import COLOR_NAME, OthelloGame


class AgentMemory:
    def __init__(self):
        self.reset()

    def reset(self):
        self.last_plan = ""

    def history_text(self, game: OthelloGame, last_n: int = 10) -> str:
        if not game.history:
            return "Nenhum lance ainda (início da partida)."
        lines = [f"Sequência completa: {game.moves_string()}"]
        for r in game.history[-last_n:]:
            who = COLOR_NAME[r.player]
            if r.move is None:
                lines.append(f"{r.number}. {who}: passou")
            else:
                why = f" — motivo: {r.reasoning}" if r.reasoning else ""
                lines.append(f"{r.number}. {who}: {r.move} (virou {len(r.flipped)}; placar {r.score_after[0]}x{r.score_after[1]}){why}")
        return "\n".join(lines)

    def summary(self, game: OthelloGame, color: int) -> str:
        """Resumo compacto enviado à LLM a cada turno (economiza tokens)."""
        mine = [r for r in game.history if r.player == color and r.move][-3:]
        opp = [r.move for r in game.history if r.player == -color][-5:]
        parts = [f"Lances até agora: {game.moves_string() or '(nenhum)'}"]
        if mine:
            parts.append("Suas últimas decisões: " + " | ".join(f"{r.move}: {r.reasoning[:120]}" for r in mine))
        if opp:
            parts.append("Últimos lances do oponente: " + ", ".join(m or "passou" for m in opp))
        if self.last_plan:
            parts.append(f"Seu plano anterior: {self.last_plan}")
        return "\n".join(parts)
