"""RuleSolver minimal (B06) : uniquement la règle single-point (R02).

Version de démarrage volontairement simple ; absorbée puis remplacée par le
solveur classique complet de la phase R (R10).
"""

from __future__ import annotations

import random

from demineur.actions import Action, Flag, GiveUp, Reveal
from demineur.solvers.base import Solver
from demineur.view import GameView


def single_point(view: GameView):
    """Balaye les contraintes single-point ; retourne (action, justification) ou None.

    Contrainte = case révélée de nombre n : mines restantes = n - drapeaux voisins.
    - restantes == 0 → toutes les cases cachées voisines sont sûres (révéler) ;
    - restantes == nombre de cachées → toutes des mines (drapeau).
    """
    for pos in sorted(view.numbers):
        n = view.number(pos)
        voisins = _voisins(view, pos)
        cachées = [v for v in voisins if view.is_hidden(v)]
        drapeaux = sum(1 for v in voisins if view.is_flagged(v))
        restantes = n - drapeaux
        if restantes == 0 and cachées:
            cible = cachées[0]
            return Reveal(*cible), f"R02: single-point → {cible} sûr"
        if restantes == len(cachées) and cachées:
            cible = cachées[0]
            return Flag(*cible), f"R02: single-point → {cible} mine"
    return None


def _voisins(view: GameView, pos):
    x, y = pos
    return [
        (vx, vy)
        for vx in range(max(0, x - 1), min(view.width, x + 2))
        for vy in range(max(0, y - 1), min(view.height, y + 2))
        if (vx, vy) != pos
    ]


class RuleSolver(Solver):
    """Single-point (R02), sinon devinette aléatoire déterministe."""

    name = "rule"

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self.last_justification: str | None = None

    def decide(self, view: GameView) -> Action:
        trouvé = single_point(view)
        if trouvé is not None:
            action, justification = trouvé
            self.last_justification = justification
            return action
        candidates = sorted(
            pos for pos in view.hidden_cells() if not view.is_flagged(pos)
        )
        if not candidates:
            self.last_justification = "aucune case cachée disponible"
            return GiveUp("aucune case cachée disponible")
        pos = self._rng.choice(candidates)
        self.last_justification = f"aucune règle applicable → guess aléatoire"
        return Reveal(*pos)
