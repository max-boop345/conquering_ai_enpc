"""Vue joueur (B01) : tout ce qu'un solveur est autorisé à voir.

La vue ne divulgue jamais l'emplacement des mines (INV1) : seules les cases
révélées (avec leur compteur) et les drapeaux sont exposés.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from demineur.game import GameState
from demineur.models import Pos


@dataclass(frozen=True)
class GameView:
    """Photo de l'état visible d'une partie."""

    width: int
    height: int
    mines_count: int
    state: GameState
    flags: frozenset[Pos]
    numbers: dict[Pos, int]  # compteurs des cases révélées uniquement

    # ------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------

    def in_bounds(self, pos: Pos) -> bool:
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def is_revealed(self, pos: Pos) -> bool:
        return pos in self.numbers

    def is_flagged(self, pos: Pos) -> bool:
        return pos in self.flags

    def is_hidden(self, pos: Pos) -> bool:
        return not self.is_revealed(pos) and not self.is_flagged(pos)

    def number(self, pos: Pos) -> int:
        """Compteur d'une case révélée ; ``KeyError`` sinon."""
        return self.numbers[pos]

    def revealed_cells(self) -> frozenset[Pos]:
        return frozenset(self.numbers)

    def hidden_cells(self):
        """Toutes les cases non révélées (drapeaux inclus), ordre stable."""
        for y in range(self.height):
            for x in range(self.width):
                if not self.is_revealed((x, y)):
                    yield (x, y)

    def cell(self, x: int, y: int) -> dict:
        """Représentation JSON d'une case visible (aucune donnée sur les mines)."""
        pos = (x, y)
        if not self.in_bounds(pos):
            raise ValueError(f"position hors grille: {pos}")
        if self.is_revealed(pos):
            return {"state": "revealed", "adjacent_mines": self.numbers[pos]}
        if self.is_flagged(pos):
            return {"state": "flagged"}
        return {"state": "hidden"}

    # ------------------------------------------------------------
    # Sérialisation (A15, format "vue joueur")
    # ------------------------------------------------------------

    def to_json(self) -> dict:
        return {
            "version": 1,
            "kind": "view",
            "width": self.width,
            "height": self.height,
            "mines_count": self.mines_count,
            "state": self.state.value,
            "grid": [[self.cell(x, y) for x in range(self.width)] for y in range(self.height)],
        }

    def to_json_text(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False, sort_keys=True)


def view_from_json(data: dict) -> GameView:
    """Reconstruit une vue depuis son JSON versionné (strict, rétro-compatible)."""
    if not isinstance(data, dict):
        raise ValueError("vue: objet JSON attendu")
    version = data.get("version")
    if version != 1:
        raise ValueError(f"version de format non supportée: {version}")
    for champ in ("width", "height", "mines_count", "state", "grid"):
        if champ not in data:
            raise ValueError(f"vue: champ manquant '{champ}'")
    width, height = data["width"], data["height"]
    grid = data["grid"]
    if len(grid) != height or any(len(row) != width for row in grid):
        raise ValueError("vue: dimensions de grille incohérentes")
    numbers: dict[Pos, int] = {}
    flags: set[Pos] = set()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            state = cell.get("state")
            if state == "revealed":
                if "adjacent_mines" not in cell:
                    raise ValueError(f"vue: case révélée sans compteur en {(x, y)}")
                numbers[(x, y)] = int(cell["adjacent_mines"])
            elif state == "flagged":
                flags.add((x, y))
            elif state != "hidden":
                raise ValueError(f"vue: état inconnu '{state}' en {(x, y)}")
    return GameView(
        width=width,
        height=height,
        mines_count=int(data["mines_count"]),
        state=GameState(data["state"]),
        flags=frozenset(flags),
        numbers=numbers,
    )
