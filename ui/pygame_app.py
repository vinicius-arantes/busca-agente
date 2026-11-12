"""Interface gráfica (Pygame): Humano x Agente e Agente x Agente.

Controles: clique para jogar | ESPAÇO pausa (A x A) | +/- velocidade |
R reinicia | ESC volta ao menu.
Os agentes rodam numa thread separada para a janela não travar enquanto a LLM pensa.
"""
from __future__ import annotations

import os
import sys
import threading
import time

import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from othello.game import BLACK, EMPTY, WHITE, COLOR_NAME, OthelloGame, to_coord, to_index  # noqa: E402
from players import LABELS, make_player  # noqa: E402

W, H = 1200, 780
CELL, BX, BY = 82, 50, 60
BOARD = CELL * 8
PX = BX + BOARD + 40          # início do painel lateral
PW = W - PX - 30

C_BG = (24, 28, 34)
C_PANEL = (36, 41, 50)
C_BOARD = (22, 120, 74)
C_GRID = (12, 70, 42)
C_TEXT = (230, 233, 238)
C_MUTED = (150, 158, 170)
C_ACCENT = (240, 190, 70)
C_HINT = (255, 255, 255)
C_BTN = (58, 66, 80)
C_BTN_ON = (80, 120, 200)

KEYS = list(LABELS)


def font(size, bold=False):
    return pygame.font.SysFont("dejavusans,arial,liberationsans", size, bold=bold)


def wrap(text, fnt, width):
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            test = f"{line} {word}".strip()
            if fnt.size(test)[0] <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


class Button:
    def __init__(self, rect, label, action):
        self.rect, self.label, self.action = pygame.Rect(rect), label, action

    def draw(self, surf, fnt, active=False):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        color = C_BTN_ON if active else tuple(min(255, c + 18) for c in C_BTN) if hover else C_BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        t = fnt.render(self.label, True, C_TEXT)
        surf.blit(t, t.get_rect(center=self.rect.center))


class App:
    def __init__(self, black="humano", white="llm-planejador"):
        pygame.init()
        pygame.display.set_caption("Othello — Agentes Inteligentes (TP05)")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.f_small, self.f, self.f_big, self.f_title = font(15), font(18), font(24, True), font(40, True)
        self.sel = {BLACK: black, WHITE: white}
        self.state = "menu"
        self.delay = 0.6
        self.error = ""
        self.game = None

    # ---------------------------------------------------------------- partida
    def start_game(self):
        try:
            self.players = {c: make_player(self.sel[c]) for c in (BLACK, WHITE)}
        except Exception as e:
            self.error = f"Não foi possível criar o jogador: {e}"
            return
        for c, p in self.players.items():
            p.reset(c)
        self.game = OthelloGame()
        self.infos = {BLACK: None, WHITE: None}
        self.worker = None
        self.thinking_since = None
        self.next_ai_at = time.time() + 0.3
        self.paused = False
        self.error = ""
        self.state = "game"
        self.game_id = object()

    def ai_turn(self, game, player, color, gid):
        try:
            info = player.play(game)
        except Exception as e:  # nunca deixar a thread morrer em silêncio
            info = None
            self.error = f"Erro do agente: {type(e).__name__}: {e}"
        if gid is self.game_id:
            self.infos[color] = info
            self.thinking_since = None
            self.next_ai_at = time.time() + self.delay

    def update(self):
        g = self.game
        if self.state != "game" or g.is_over() or self.paused:
            return
        p = self.players[g.current]
        if p.is_human or (self.worker and self.worker.is_alive()):
            return
        if time.time() >= self.next_ai_at:
            self.thinking_since = time.time()
            self.worker = threading.Thread(target=self.ai_turn, args=(g, p, g.current, self.game_id), daemon=True)
            self.worker.start()

    def human_click(self, pos):
        g = self.game
        if g.is_over() or not self.players[g.current].is_human:
            return
        x, y = pos[0] - BX, pos[1] - BY
        if not (0 <= x < BOARD and 0 <= y < BOARD):
            return
        coord = to_coord((y // CELL) * 8 + x // CELL)
        if g.is_valid(coord):
            g.make_move(coord)
            self.next_ai_at = time.time() + 0.35

    # ------------------------------------------------------------------ desenho
    def draw_board(self):
        g = self.game
        s = self.screen
        pygame.draw.rect(s, C_BOARD, (BX, BY, BOARD, BOARD), border_radius=6)
        for i in range(9):
            pygame.draw.line(s, C_GRID, (BX + i * CELL, BY), (BX + i * CELL, BY + BOARD), 2)
            pygame.draw.line(s, C_GRID, (BX, BY + i * CELL), (BX + BOARD, BY + i * CELL), 2)
        for i in range(8):
            t = self.f_small.render("abcdefgh"[i], True, C_MUTED)
            s.blit(t, t.get_rect(center=(BX + i * CELL + CELL // 2, BY - 16)))
            t = self.f_small.render(str(i + 1), True, C_MUTED)
            s.blit(t, t.get_rect(center=(BX - 18, BY + i * CELL + CELL // 2)))
        for cx, cy in ((2, 2), (6, 2), (2, 6), (6, 6)):
            pygame.draw.circle(s, C_GRID, (BX + cx * CELL, BY + cy * CELL), 5)

        last = next((r for r in reversed(g.history) if r.move), None)
        flipped = {to_index(c) for c in last.flipped} if last else set()
        human_turn = not g.is_over() and self.players[g.current].is_human
        valid = set(g.valid_moves()) if human_turn else set()
        for idx in range(64):
            cx, cy = BX + (idx % 8) * CELL + CELL // 2, BY + (idx // 8) * CELL + CELL // 2
            v = g.cell(idx)
            if v != EMPTY:
                pygame.draw.circle(s, (0, 0, 0, 60), (cx + 2, cy + 3), CELL // 2 - 7)
                col = (20, 20, 22) if v == BLACK else (240, 240, 236)
                pygame.draw.circle(s, col, (cx, cy), CELL // 2 - 8)
                if idx in flipped:
                    pygame.draw.circle(s, C_ACCENT, (cx, cy), 5)
            elif to_coord(idx) in valid:
                pygame.draw.circle(s, C_HINT, (cx, cy), 8, 2)
        if last:
            idx = to_index(last.move)
            pygame.draw.rect(s, C_ACCENT, (BX + (idx % 8) * CELL + 3, BY + (idx // 8) * CELL + 3, CELL - 6, CELL - 6), 3, border_radius=6)

    def text(self, txt, pos, fnt=None, color=C_TEXT):
        surf = (fnt or self.f).render(txt, True, color)
        self.screen.blit(surf, pos)
        return surf.get_height()

    def draw_panel(self):
        g, s = self.game, self.screen
        pygame.draw.rect(s, C_PANEL, (PX - 15, 20, PW + 30, H - 40), border_radius=12)
        y = 36
        b, w = g.score()
        for color, cnt in ((BLACK, b), (WHITE, w)):
            col = (20, 20, 22) if color == BLACK else (240, 240, 236)
            pygame.draw.circle(s, col, (PX + 14, y + 14), 13)
            pygame.draw.circle(s, C_MUTED, (PX + 14, y + 14), 13, 1)
            mark = "▶ " if g.current == color and not g.is_over() else "   "
            self.text(f"{mark}{self.players[color].name}", (PX + 36, y + 2), self.f)
            self.text(str(cnt), (PX + PW - 40, y), self.f_big, C_ACCENT)
            y += 38
        y += 6
        if g.is_over():
            win = g.winner()
            msg = "Empate!" if win == EMPTY else f"Vitória das {COLOR_NAME[win]} ({self.players[win].name})"
            y += self.text(msg, (PX, y), self.f_big, C_ACCENT) + 4
        elif self.thinking_since:
            y += self.text(f"{self.players[g.current].name} pensando... {time.time() - self.thinking_since:4.1f}s",
                           (PX, y), self.f, C_ACCENT) + 4
        elif self.players[g.current].is_human:
            y += self.text("Sua vez: clique numa casa marcada.", (PX, y), self.f, C_ACCENT) + 4
        else:
            y += self.text("Pausado (ESPAÇO)" if self.paused else f"Lance {len(g.history) + 1} · {g.phase()}",
                           (PX, y), self.f, C_MUTED) + 4
        if g.history and g.history[-1].move is None:
            y += self.text(f"{COLOR_NAME[g.history[-1].player]} passaram a vez.", (PX, y), self.f_small, C_MUTED)
        y += 10

        for color in (BLACK, WHITE):
            info = self.infos[color]
            if not info:
                continue
            self.text(f"{COLOR_NAME[color]} jogou {info.move}", (PX, y), self.f, C_ACCENT)
            y += 24
            for line in wrap(info.reasoning or "-", self.f_small, PW)[:5]:
                y += self.text(line, (PX, y), self.f_small)
            meta = f"{info.elapsed:.2f}s"
            if info.llm_calls:
                meta += f" · {info.llm_calls} chamadas LLM · {info.tool_calls} tools · {info.tokens_in + info.tokens_out} tokens"
            if info.invalid_attempts:
                meta += f" · {info.invalid_attempts} inválida(s)"
            if info.fallback:
                meta += " · FALLBACK"
            y += self.text(meta, (PX, y + 2), self.f_small, C_MUTED) + 4
            if info.tools_used:
                tools = " → ".join(dict.fromkeys(info.tools_used))
                for line in wrap(f"Tools: {tools}", self.f_small, PW)[:2]:
                    y += self.text(line, (PX, y), self.f_small, C_MUTED)
            if info.plan:
                for line in wrap(f"Plano: {info.plan}", self.f_small, PW)[:2]:
                    y += self.text(line, (PX, y), self.f_small, C_MUTED)
            y += 12

        y = max(y, H - 230)
        self.text("Histórico", (PX, y), self.f, C_MUTED)
        y += 24
        moves = [f"{r.number}.{'B' if r.player == BLACK else 'W'}:{r.move or '--'}" for r in g.history]
        for line in wrap(" ".join(moves[-40:]), self.f_small, PW)[-6:]:
            y += self.text(line, (PX, y), self.f_small)
        self.text(f"ESPAÇO pausa · +/- atraso ({self.delay:.1f}s) · R reinicia · ESC menu",
                  (PX, H - 50), self.f_small, C_MUTED)
        if self.error:
            for i, line in enumerate(wrap(self.error, self.f_small, BOARD)[:2]):
                self.text(line, (BX, BY + BOARD + 12 + i * 18), self.f_small, (255, 120, 120))

    def menu_buttons(self):
        btns = []
        cx = W // 2
        for row, color in enumerate((BLACK, WHITE)):
            y = 290 + row * 110
            btns.append(Button((cx - 270, y, 50, 46), "<", lambda c=color: self.cycle(c, -1)))
            btns.append(Button((cx + 220, y, 50, 46), ">", lambda c=color: self.cycle(c, 1)))
        btns.append(Button((cx - 330, 540, 200, 50), "Humano × Agente", lambda: self.preset("humano", "llm-planejador")))
        btns.append(Button((cx - 100, 540, 200, 50), "Agente × Agente", lambda: self.preset("llm-basico", "llm-planejador")))
        btns.append(Button((cx + 130, 540, 200, 50), "Clássicos", lambda: self.preset("heuristico", "minimax")))
        btns.append(Button((cx - 120, 625, 240, 60), "INICIAR", self.start_game))
        return btns

    def cycle(self, color, d):
        self.sel[color] = KEYS[(KEYS.index(self.sel[color]) + d) % len(KEYS)]

    def preset(self, b, w):
        self.sel = {BLACK: b, WHITE: w}

    def draw_menu(self):
        s = self.screen
        t = self.f_title.render("Othello — Agentes Inteligentes", True, C_TEXT)
        s.blit(t, t.get_rect(center=(W // 2, 120)))
        t = self.f.render("LLM + Ferramentas + LangGraph · GCC 128", True, C_MUTED)
        s.blit(t, t.get_rect(center=(W // 2, 170)))
        for row, color in enumerate((BLACK, WHITE)):
            y = 290 + row * 110
            t = self.f.render(f"{COLOR_NAME[color]} (jogam {'primeiro' if color == BLACK else 'depois'})", True, C_MUTED)
            s.blit(t, t.get_rect(center=(W // 2, y - 22)))
            r = pygame.Rect(W // 2 - 205, y, 410, 46)
            pygame.draw.rect(s, C_PANEL, r, border_radius=8)
            t = self.f_big.render(LABELS[self.sel[color]], True, C_ACCENT)
            s.blit(t, t.get_rect(center=r.center))
        for b in self.buttons:
            b.draw(s, self.f_big if b.label == "INICIAR" else self.f, active=b.label == "INICIAR")
        if self.error:
            for i, line in enumerate(wrap(self.error, self.f_small, 900)[:3]):
                t = self.f_small.render(line, True, (255, 120, 120))
                s.blit(t, t.get_rect(center=(W // 2, 720 + i * 18)))

    # ------------------------------------------------------------------- laço
    def run(self, screenshot: str | None = None, max_seconds: float | None = None):
        self.buttons = self.menu_buttons()
        t_start = time.time()
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    return
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.state == "menu":
                        for b in self.buttons:
                            if b.rect.collidepoint(ev.pos):
                                b.action()
                    else:
                        self.human_click(ev.pos)
                if ev.type == pygame.KEYDOWN and self.state == "game":
                    if ev.key == pygame.K_ESCAPE:
                        self.state, self.game_id = "menu", object()
                    elif ev.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif ev.key == pygame.K_r:
                        self.start_game()
                    elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        self.delay = min(5.0, self.delay + 0.2)
                    elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.delay = max(0.0, self.delay - 0.2)
            self.screen.fill(C_BG)
            if self.state == "menu":
                self.draw_menu()
            else:
                self.update()
                self.draw_board()
                self.draw_panel()
            pygame.display.flip()
            self.clock.tick(30)
            if max_seconds and time.time() - t_start > max_seconds:
                if screenshot:
                    pygame.image.save(self.screen, screenshot)
                pygame.quit()
                return


def main(black="humano", white="llm-planejador", start=False):
    app = App(black, white)
    if start:
        app.start_game()
    app.run()


if __name__ == "__main__":
    main()
