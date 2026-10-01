"""Moteur de partie de démineur (A05→A12).

Le ``Game`` orchestre une partie : placement différé des mines au premier coup
(zone sûre 3x3), révélation en cascade, drapeaux, détection de fin.
Le ``Board`` est créé une seule fois puis figé (A12).
"""

from __future__ import annotations

import random
from enum import Enum

from demineur.board import Board
from demineur.models import Cell, CellState, Pos


class GameState(Enum):
    """État d'une partie (A11)."""

    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class Game:
    """Partie de démineur, reproductible via ``seed`` (A04)."""

    def __init__(self, width: int, height: int, mines_count: int, seed: int | None = None):
        if width <= 0 or height <= 0:
            raise ValueError("dimensions strictement positives requises")
        if not 0 <= mines_count <= width * height:
            raise ValueError("nombre de mines invalide")
        self.width = width
        self.height = height
        self.mines_count = mines_count
        self._rng = random.Random(seed)
        self._board: Board | None = None
        self._revealed: set[Pos] = set()
        self._flags: set[Pos] = set()
        self.state = GameState.PLAYING

    # ------------------------------------------------------------
    # Accès
    # ------------------------------------------------------------

    @property
    def board(self) -> Board | None:
        """Grille figée ; ``None`` tant que le premier coup n'a pas été joué."""
        return self._board

    @property
    def revealed(self) -> frozenset[Pos]:
        return frozenset(self._revealed)

    @property
    def flags(self) -> frozenset[Pos]:
        return frozenset(self._flags)

    @property
    def mines_remaining(self) -> int:
        """A09 : mines restantes = total - drapeaux posés."""
        return self.mines_count - len(self._flags)

    def is_flagged(self, pos: Pos) -> bool:
        return pos in self._flags

    def _require_playing(self) -> None:
        if self.state is not GameState.PLAYING:
            raise ValueError(f"partie terminée ({self.state.value})")

    def _require_in_bounds(self, pos: Pos) -> None:
        if not (0 <= pos[0] < self.width and 0 <= pos[1] < self.height):
            raise ValueError(f"position hors grille: {pos}")

    # ------------------------------------------------------------
    # Actions du joueur
    # ------------------------------------------------------------

    def reveal(self, x: int, y: int) -> list[Pos]:
        """Révèle une case ; retourne la liste des cases révélées (cascade incluse).

        Lève ``ValueError`` si le coup est illégal. Le premier coup place les
        mines en garantissant une zone sûre (case + voisines, A05).
        """
        pos = (x, y)
        self._require_playing()
        self._require_in_bounds(pos)
        if pos in self._revealed:
            raise ValueError(f"case déjà révélée: {pos}")
        if pos in self._flags:
            raise ValueError(f"case marquée d'un drapeau: {pos}")

        if self._board is None:
            # A05 + A12 : placement différé, figé ensuite
            interdites = {pos}
            # zone sûre = case + voisines ; on utilise un Board vide pour le voisinage
            interdites.update(Board(self.width, self.height, frozenset()).neighbors(pos))
            self._board = Board.random(
                self.width, self.height, self.mines_count, self._rng, forbidden=interdites
            )

        if self._board.is_mine(pos):
            # A11 : défaite — seule la case minée est révélée
            self._revealed.add(pos)
            self.state = GameState.LOST
            return [pos]

        return self._reveal_cascade(pos)

    def _reveal_cascade(self, start: Pos) -> list[Pos]:
        """A08 : flood fill — révèle la case puis propage tant que compteurs nuls."""
        board = self._board
        assert board is not None
        file: list[Pos] = [start]
        revelées: list[Pos] = []
        while file:
            pos = file.pop()
            if pos in self._revealed or pos in self._flags:
                continue
            self._revealed.add(pos)
            revelées.append(pos)
            if board.adjacent_mines(pos) == 0:
                file.extend(v for v in board.neighbors(pos) if v not in self._revealed)
        if len(self._revealed) == self.width * self.height - self.mines_count:
            # A10 : toutes les cases sans mine sont révélées
            self.state = GameState.WON
        return revelées

    def flag(self, x: int, y: int) -> None:
        """A09 : pose un drapeau sur une case cachée."""
        pos = (x, y)
        self._require_playing()
        self._require_in_bounds(pos)
        if pos in self._revealed:
            raise ValueError(f"case déjà révélée: {pos}")
        if pos in self._flags:
            raise ValueError(f"drapeau déjà posé: {pos}")
        self._flags.add(pos)

    def unflag(self, x: int, y: int) -> None:
        pos = (x, y)
        self._require_playing()
        self._require_in_bounds(pos)
        if pos not in self._flags:
            raise ValueError(f"pas de drapeau en {pos}")
        self._flags.remove(pos)

    # ------------------------------------------------------------
    # Lecture de l'état
    # ------------------------------------------------------------

    def view(self):
        """Vue joueur (B01) : aucune information sur les mines cachées."""
        from demineur.view import GameView

        numbers = {}
        if self._board is not None:
            numbers = {pos: self._board.adjacent_mines(pos) for pos in self._revealed}
        return GameView(
            width=self.width,
            height=self.height,
            mines_count=self.mines_count,
            state=self.state,
            flags=frozenset(self._flags),
            numbers=numbers,
        )


    def cell(self, x: int, y: int) -> Cell:
        """Cellule du point de vue du moteur (mine visible)."""
        pos = (x, y)
        if pos in self._flags:
            state = CellState.FLAGGED
        elif pos in self._revealed:
            state = CellState.REVEALED
        else:
            state = CellState.HIDDEN
        is_mine = self._board.is_mine(pos) if self._board is not None else False
        adjacent = self._board.adjacent_mines(pos) if self._board is not None else 0
        return Cell(x=x, y=y, state=state, is_mine=is_mine, adjacent_mines=adjacent)
