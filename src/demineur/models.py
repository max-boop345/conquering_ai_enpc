"""Types de base du démineur (A03).

Une position est un tuple ``(x, y)`` avec ``0 <= x < largeur`` et ``0 <= y < hauteur``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

Pos = tuple[int, int]


class CellState(Enum):
    """État visible d'une case."""

    HIDDEN = "hidden"
    REVEALED = "revealed"
    FLAGGED = "flagged"


@dataclass(frozen=True)
class Cell:
    """Case immuable : état visible, présence d'une mine, compteur de mines voisines."""

    x: int
    y: int
    state: CellState = CellState.HIDDEN
    is_mine: bool = False
    adjacent_mines: int = 0

    @property
    def pos(self) -> Pos:
        return (self.x, self.y)
