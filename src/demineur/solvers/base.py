"""Contrat Solver (B01).

Tout solveur (IA ou humain) reçoit uniquement une ``GameView`` — jamais le
plateau réel (INV1, anti-fuite d'information) — et retourne une ``Action``.
La justification textuelle du dernier coup, si le solveur en produit une,
est lue par le ``GameRunner`` via ``last_justification`` (R11).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from demineur.actions import Action
from demineur.view import GameView


class Solver(ABC):
    """Contrat unique de tous les solveurs."""

    name: str = "solver"
    last_justification: str | None = None

    @abstractmethod
    def decide(self, view: GameView) -> Action:
        """Choisit l'action suivante à partir de la seule vue visible."""
        raise NotImplementedError
