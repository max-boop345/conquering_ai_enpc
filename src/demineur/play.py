"""Jeu au clavier (A14) : ``python -m demineur.play --seed 42 --w 9 --h 9 --mines 10``.

Commandes : ``r x y`` (révéler), ``f x y`` (drapeau), ``u x y`` (retirer), ``q`` (quitter).
Le module expose ``run`` testable avec des flux d'E/S injectés.
"""

from __future__ import annotations

import argparse

from demineur.game import Game, GameState
from demineur.render import render_header, render_view


def run(game: Game, input_stream, output_stream) -> tuple[Game, list[dict]]:
    """Boucle interactive sur des flux injectés ; retourne (jeu, journal des coups).

    Un coup illégal affiche une erreur mais ne termine pas la partie.
    """
    journal: list[dict] = []
    numero = 0
    print(render_header(game.view()), file=output_stream)
    for ligne in input_stream:
        ligne = ligne.strip()
        if not ligne:
            continue
        morceaux = ligne.split()
        try:
            if morceaux[0] == "q":
                break
            if len(morceaux) != 3 or morceaux[0] not in ("r", "f", "u"):
                print(f"commande invalide: {ligne!r}", file=output_stream)
                continue
            x, y = int(morceaux[1]), int(morceaux[2])
            if morceaux[0] == "r":
                reveals = game.reveal(x, y)
                journal.append({"move": numero, "action": ["reveal", x, y], "revealed": len(reveals)})
            elif morceaux[0] == "f":
                game.flag(x, y)
                journal.append({"move": numero, "action": ["flag", x, y], "revealed": 0})
            else:  # "u"
                game.unflag(x, y)
                journal.append({"move": numero, "action": ["unflag", x, y], "revealed": 0})
            numero += 1
            print(render_header(game.view()), file=output_stream)
            print(render_view(game.view()), file=output_stream)
            if game.state is not GameState.PLAYING:
                print(
                    "GAGNÉ" if game.state is GameState.WON else "PERDU — mine touchée",
                    file=output_stream,
                )
                break
        except ValueError as err:
            print(f"erreur: {err}", file=output_stream)
    return game, journal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="demineur.play", description="Démineur jouable au clavier")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--w", type=int, default=9)
    parser.add_argument("--h", type=int, default=9)
    parser.add_argument("--mines", type=int, default=10)
    args = parser.parse_args(argv)
    jeu = Game(width=args.w, height=args.h, mines_count=args.mines, seed=args.seed)
    print(render_view(jeu.view()), end="\n")
    print("commandes: r x y | f x y | u x y | q")
    run(jeu, input_stream=__import__("sys").stdin, output_stream=__import__("sys").stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
