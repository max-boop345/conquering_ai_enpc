"""Mode duel (F03) : solveur classique vs humain sur la même grille seedée.

Le duel se joue sur deux instances de ``Game`` créées avec la même seed :
le hasard est identique, seule la stratégie diffère. L'humain joue au clavier
(``r x y`` | ``f x y`` | ``u x y`` | ``q``) ; après chaque coup humain, le
solveur joue un coup sur sa propre grille.
"""

from __future__ import annotations

from demineur.actions import Action, Flag, Reveal, Unflag
from demineur.game import Game, GameState
from demineur.render import render_view
from demineur.solvers.base import Solver


def _grilles_côte_à_côte(vue_h, vue_s) -> str:
    """Deux grilles texte juxtaposées avec un séparateur."""
    lignes_h = render_view(vue_h).splitlines()
    lignes_s = render_view(vue_s).splitlines()
    largeur = max(len(l) for l in lignes_h) if lignes_h else 0
    sortie = []
    for i in range(max(len(lignes_h), len(lignes_s))):
        gauche = lignes_h[i] if i < len(lignes_h) else ""
        droite = lignes_s[i] if i < len(lignes_s) else ""
        sortie.append(f"{gauche:<{largeur}}  |  {droite}")
    return "\n".join(sortie)


def run_duel(
    jeu_humain: Game,
    jeu_solveur: Game,
    solver: Solver,
    input_stream,
    output_stream,
) -> dict:
    """Boucle de duel ; retourne l'état final des deux parties."""
    print("=== DUEL — vous vs solveur (même seed, mêmes mines) ===", file=output_stream)
    print("gauche: votre grille | droite: solveur", file=output_stream)
    coups_solveur = 0
    for ligne in input_stream:
        ligne = ligne.strip()
        if not ligne:
            continue
        morceaux = ligne.split()
        if morceaux[0] == "q":
            break
        if len(morceaux) != 3 or morceaux[0] not in ("r", "f", "u"):
            print(f"commande invalide: {ligne!r}", file=output_stream)
            continue
        x, y = int(morceaux[1]), int(morceaux[2])
        action = {"r": Reveal, "f": Flag, "u": Unflag}[morceaux[0]](x, y)
        try:
            if isinstance(action, Reveal):
                jeu_humain.reveal(x, y)
            elif isinstance(action, Flag):
                jeu_humain.flag(x, y)
            else:
                jeu_humain.unflag(x, y)
        except ValueError as err:
            print(f"erreur: {err}", file=output_stream)
            continue
        # le solveur répond sur sa grille
        if jeu_solveur.state is GameState.PLAYING:
            vue = jeu_solveur.view()
            action_s = solver.decide(vue)
            if isinstance(action_s, Reveal):
                jeu_solveur.reveal(action_s.x, action_s.y)
            elif isinstance(action_s, Flag):
                jeu_solveur.flag(action_s.x, action_s.y)
            elif isinstance(action_s, Unflag):
                jeu_solveur.unflag(action_s.x, action_s.y)
            coups_solveur += 1
        print(_grilles_côte_à_côte(jeu_humain.view(), jeu_solveur.view()),
              file=output_stream)
        fin_h = jeu_humain.state is not GameState.PLAYING
        fin_s = jeu_solveur.state is not GameState.PLAYING
        if fin_h or fin_s:
            print(
                f"fin — vous: {jeu_humain.state.value}, solveur: {jeu_solveur.state.value}",
                file=output_stream,
            )
            break
    return {
        "human_state": jeu_humain.state,
        "solver_state": jeu_solveur.state,
        "solver_moves": coups_solveur,
    }
