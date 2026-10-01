"""Noyau d'analyse (R01) : extraction des contraintes depuis la vue joueur.

Une contrainte relie un ensemble de cases frontière (cachées, non drapeautées)
au nombre de mines qu'il contient : ``nombre affiché - drapeaux voisins``.
"""

from __future__ import annotations

from dataclasses import dataclass

from demineur.models import Pos
from demineur.view import GameView


@dataclass(frozen=True)
class Constraint:
    """Exactement ``count`` mines parmi ``cells``."""

    cells: frozenset[Pos]
    count: int

    def __post_init__(self):
        if self.count < 0 or self.count > len(self.cells):
            raise ValueError(f"contrainte impossible: {self.count}/{len(self.cells)}")


def voisins(view: GameView, pos: Pos) -> list[Pos]:
    """Voisins 8-connexes dans les limites de la grille."""
    x, y = pos
    return [
        (vx, vy)
        for vx in range(max(0, x - 1), min(view.width, x + 2))
        for vy in range(max(0, y - 1), min(view.height, y + 2))
        if (vx, vy) != pos
    ]


def extract_constraints(view: GameView) -> list[Constraint]:
    """Liste des contraintes déduites des cases révélées (R01).

    Les cases sans voisine cachée ne produisent pas de contrainte. Une
    contrainte avec ``count < 0`` ou ``count > |cells|`` signale une vue
    corrompue (R12) et lève immédiatement.
    """
    contraintes: list[Constraint] = []
    for pos in sorted(view.numbers):
        n = view.number(pos)
        voisins_ = voisins(view, pos)
        cachées = frozenset(v for v in voisins_ if view.is_hidden(v))
        if not cachées:
            continue
        drapeaux = sum(1 for v in voisins_ if view.is_flagged(v))
        contraintes.append(Constraint(cachées, n - drapeaux))
    return contraintes
