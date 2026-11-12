"""Ponto de entrada.

    python main.py                                   # interface gráfica (menu)
    python main.py --black humano --white llm-planejador --start
    python main.py --cli --black llm-basico --white minimax   # partida no terminal

Jogadores: humano, aleatorio, heuristico, minimax, llm-basico, llm-planejador
"""
from __future__ import annotations

import argparse

from players import REGISTRY


def cli_game(black_key: str, white_key: str):
    from othello.arena import play_game
    from othello.game import BLACK, COLOR_NAME, EMPTY
    from players import make_player
    from players.base import TurnInfo

    class TerminalHuman(make_player("humano").__class__):
        def play(self, game):
            print(game.to_text())
            while True:
                mv = input(f"{COLOR_NAME[game.current]} — sua jogada ({', '.join(game.valid_moves())}): ")
                if game.is_valid(mv):
                    game.make_move(mv)
                    return TurnInfo(mv.lower())
                print("Jogada inválida.")

    def mk(k):
        return TerminalHuman() if k == "humano" else make_player(k)

    res = play_game(mk(black_key), mk(white_key), verbose=True)
    print(f"\nFim: pretas {res.score_black} x {res.score_white} brancas -> "
          f"{ {'black': 'pretas vencem', 'white': 'brancas vencem', 'draw': 'empate'}[res.winner] }")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--black", default="humano", choices=REGISTRY)
    ap.add_argument("--white", default="llm-planejador", choices=REGISTRY)
    ap.add_argument("--start", action="store_true", help="pula o menu e começa direto")
    ap.add_argument("--cli", action="store_true", help="joga no terminal (sem interface gráfica)")
    args = ap.parse_args()
    if args.cli:
        cli_game(args.black, args.white)
    else:
        from ui.pygame_app import main as gui
        gui(args.black, args.white, args.start)


if __name__ == "__main__":
    main()
