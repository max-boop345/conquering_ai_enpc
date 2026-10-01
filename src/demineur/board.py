"""Grille de démineur (A04→A06) : voisins, compteurs, génération déterministe.

Un ``Board`` est immuable après construction : l'ensemble des mines est figé
(invariant A12 — anti-triche). La génération aléatoire passe par un
``random.Random`` fourni par l'appelant pour garantir la reproductibilité.
"""

from __future__ import annotations

import random

from demineur.models import Pos


class Board:
    """Grille figée : positions des mines et compteurs pré-calculés."""

    def __init__(self, width: int, height: int, mines: frozenset[Pos]):
        if width <= 0 or height <= 0:
            raise ValueError("dimensions strictement positives requises")
        if len(mines) >= width * height:
            raise ValueError("au moins une case sans mine est requise")
        for (x, y) in mines:
            if not (0 <= x < width and 0 <= y < height):
                raise ValueError(f"mine hors grille: {(x, y)}")
        self._width = width
        self._height = height
        self._mines = frozenset(mines)
        self._adjacent: dict[Pos, int] = {
            (x, y): sum(1 for v in self.neighbors((x, y)) if v in self._mines)
            for x in range(width)
            for y in range(height)
        }

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def mines(self) -> frozenset[Pos]:
        return self._mines

    @property
    def mines_count(self) -> int:
        return len(self._mines)

    def in_bounds(self, pos: Pos) -> bool:
        x, y = pos
        return 0 <= x < self._width and 0 <= y < self._height

    def neighbors(self, pos: Pos) -> tuple[Pos, ...]:
        """Les 8 voisins (ou moins en bord/coin) dans la grille, ordre stable."""
        if not self.in_bounds(pos):
            raise ValueError(f"position hors grille: {pos}")
        x, y = pos
        voisins = (
            (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
            (x - 1, y), (x + 1, y),
            (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
        )
        return tuple(p for p in voisins if self.in_bounds(p))

    def is_mine(self, pos: Pos) -> bool:
        if not self.in_bounds(pos):
            raise ValueError(f"position hors grille: {pos}")
        return pos in self._mines

    def adjacent_mines(self, pos: Pos) -> int:
        """A06 : nombre de mines adjacentes à une case."""
        if not self.in_bounds(pos):
            raise ValueError(f"position hors grille: {pos}")
        return self._adjacent[pos]

    @classmethod
    def random(
        cls,
        width: int,
        height: int,
        mines_count: int,
        rng: random.Random,
        forbidden: set[Pos] | None = None,
    ) -> Board:
        """Place ``mines_count`` mines de façon déterministe via ``rng``.

        Aucune mine dans ``forbidden`` (case cliquée + voisines au premier coup).
        Lève ``ValueError`` si le placement est impossible.
        """
        forbidden = forbidden or set()
        for pos in forbidden:
            if not (0 <= pos[0] < width and 0 <= pos[1] < height):
                raise ValueError(f"position interdite hors grille: {pos}")
        libres = [
            (x, y)
            for x in range(width)
            for y in range(height)
            if (x, y) not in forbidden
        ]
        if mines_count < 0 or mines_count >= len(libres):
            # une case libre non minée doit rester jouable après le premier coup
            raise ValueError(
                f"placement impossible: {mines_count} mines pour {len(libres)} cases libres"
            )
        return cls(width, height, frozenset(rng.sample(libres, mines_count)))
