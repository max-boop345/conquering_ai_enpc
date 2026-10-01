"""Tests de la vue joueur (support B01) : aucune fuite d'information sur les mines."""

import unittest

from demineur.game import Game, GameState
from demineur.view import GameView


class TestGameView(unittest.TestCase):
    def setUp(self):
        self.game = Game(width=5, height=5, mines_count=3, seed=4)
        self.game.reveal(0, 0)
        self.view = self.game.view()

    def test_dimensions_et_mines(self):
        self.assertEqual(self.view.width, 5)
        self.assertEqual(self.view.height, 5)
        self.assertEqual(self.view.mines_count, 3)
        self.assertEqual(self.view.state, GameState.PLAYING)

    def test_pas_de_fuite_dinformation(self):
        # la vue ne doit exposer aucune information sur les mines cachées
        data = self.view.to_json()
        self.assertNotIn("mines", data)
        for row in data["grid"]:
            for cell in row:
                self.assertNotIn("is_mine", cell)
                if cell["state"] == "hidden":
                    self.assertNotIn("adjacent_mines", cell)

    def test_etats_visibles(self):
        self.game.flag(4, 4)
        view = self.game.view()
        self.assertTrue(view.is_revealed((0, 0)))
        self.assertTrue(view.is_flagged((4, 4)))
        self.assertTrue(view.is_hidden((2, 3)))
        self.assertTrue(view.is_flagged((2, 3)) is False)

    def test_compteur_visible(self):
        # une case révélée expose son compteur de mines adjacentes
        cell = self.view.cell(0, 0)
        self.assertIn(cell["adjacent_mines"], range(0, 9))

    def test_position_hors_grille(self):
        with self.assertRaises(ValueError):
            self.view.cell(9, 9)

    def test_cases_cachees(self):
        cachees = set(self.view.hidden_cells())
        self.assertNotIn((0, 0), cachees)
        self.assertEqual(len(cachees), 25 - len(self.view.revealed_cells()))


if __name__ == "__main__":
    unittest.main()
