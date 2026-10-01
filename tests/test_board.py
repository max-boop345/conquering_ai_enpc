"""Tests unitaires du noyau : Cell, Board (A03→A06), invariants A12."""

import unittest

from demineur.board import Board
from demineur.models import Cell, CellState, Pos


class TestCell(unittest.TestCase):
    """A03 : structure immuable Cell."""

    def test_cell_immuable(self):
        cell = Cell(x=1, y=2, state=CellState.HIDDEN, is_mine=False, adjacent_mines=0)
        with self.assertRaises(Exception):
            cell.x = 5

    def test_cell_valeurs_par_defaut(self):
        cell = Cell(x=0, y=0)
        self.assertEqual(cell.state, CellState.HIDDEN)
        self.assertFalse(cell.is_mine)
        self.assertEqual(cell.adjacent_mines, 0)


class TestBoard(unittest.TestCase):
    """A04/A06 : grille, compteurs, génération déterministe (seed)."""

    def setUp(self):
        self.mines = {(2, 2)}
        self.board = Board(width=5, height=5, mines=frozenset(self.mines))

    def test_dimensions(self):
        self.assertEqual(self.board.width, 5)
        self.assertEqual(self.board.height, 5)
        self.assertEqual(self.board.mines_count, 1)

    def test_voisins_coin(self):
        voisins = sorted(self.board.neighbors((0, 0)))
        self.assertEqual(voisins, [(0, 1), (1, 0), (1, 1)])

    def test_voisins_centre(self):
        voisins = sorted(self.board.neighbors((2, 3)))
        self.assertEqual(len(voisins), 8)
        self.assertIn((2, 2), voisins)

    def test_compteur_autour_mine(self):
        # A06 : compteurs de mines adjacentes
        self.assertEqual(self.board.adjacent_mines((1, 1)), 1)
        self.assertEqual(self.board.adjacent_mines((2, 2)), 0)
        self.assertEqual(self.board.adjacent_mines((4, 4)), 0)

    def test_hors_grille(self):
        self.assertFalse(self.board.in_bounds((5, 0)))
        self.assertTrue(self.board.in_bounds((4, 4)))
        with self.assertRaises(ValueError):
            self.board.neighbors((-1, 0))

    def test_trop_de_mines(self):
        with self.assertRaises(ValueError):
            Board(width=2, height=2, mines=frozenset({(0, 0), (1, 1), (0, 1), (1, 0)}))

    def test_determinisme_seed(self):
        # A04 : même seed -> même grille
        import random

        rng1 = random.Random(42)
        rng2 = random.Random(42)
        b1 = Board.random(9, 9, 10, rng1, forbidden=set())
        b2 = Board.random(9, 9, 10, rng2, forbidden=set())
        self.assertEqual(b1.mines, b2.mines)

    def test_zone_interdite_respectee(self):
        import random

        interdites = {(0, 0)} | set(Board(width=5, height=5, mines=frozenset()).neighbors((0, 0)))
        b = Board.random(9, 9, 10, random.Random(1), forbidden=interdites)
        for pos in interdites:
            self.assertFalse(pos in b.mines, f"mine dans la zone interdite: {pos}")

    def test_placement_impossible(self):
        import random

        with self.assertRaises(ValueError):
            Board.random(3, 3, 8, random.Random(0), forbidden={(0, 0)})


if __name__ == "__main__":
    unittest.main()
