"""Solveur aléatoire légal (B05) : étalon bas de comparaison."""

from __future__ import annotations

import random

from demineur.actions import Action, GiveUp, Reveal
from demineur.solvers.base import Solver
from demineur.view import GameView


class RandomSolver(Solver):
    """Révèle une case cachée au hasard (déterministe si seed fournie)."""

    name = "random"

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self.last_justification: str | None = None

    def decide(self, view: GameView) -> Action:
        candidates = sorted(
            pos for pos in view.hidden_cells() if not view.is_flagged(pos)
        )
        if not candidates:
            self.last_justification = "aucune case cachée disponible"
            return GiveUp("aucune case cachée disponible")
        pos = self._rng.choice(candidates)
        self.last_justification = f"guess aléatoire parmi {len(candidates)} cases"
        return Reveal(*pos)
