"""Tests du noyau d'analyse (R01) et des règles déterministes (R02, R03, R04)."""

import unittest

from demineur.game import GameState
from demineur.solvers.classic.analysis import Constraint, extract_constraints
from demineur.solvers.classic.rules import deduce
from demineur.view import GameView


def vue(numbers: dict, flags=(), width=4, height=2, mines=2) -> GameView:
    return GameView(width, height, mines, GameState.PLAYING,
                    frozenset(flags), numbers)


class TestExtractionContraintes(unittest.TestCase):
    """R01 : contraintes (ensemble de cases frontière, nombre de mines)."""

    def test_contrainte_simple(self):
        v = vue({(1, 0): 1})
        contraintes = extract_constraints(v)
        self.assertEqual(len(contraintes), 1)
        c = contraintes[0]
        self.assertEqual(c.cells, frozenset({(0, 0), (2, 0), (0, 1), (1, 1), (2, 1)}))
        self.assertEqual(c.count, 1)

    def test_drapeaux_soustraits(self):
        # drapeau voisin d'une case '2' -> contrainte à 1 mine restante
        v = vue({(1, 0): 2}, flags={(0, 0)})
        contraintes = extract_constraints(v)
        self.assertEqual(len(contraintes), 1)
        c = contraintes[0]
        self.assertNotIn((0, 0), c.cells)
        self.assertEqual(c.count, 1)

    def test_case_revelee_zero_ignores_si_pas_de_voisine_cachee(self):
        v = vue({(0, 0): 0}, width=1, height=1)
        self.assertEqual(extract_constraints(v), [])

    def test_case_sans_voisine_cachee_pas_de_contrainte(self):
        v = vue({(0, 0): 3}, width=3, height=1, flags={(1, 0), (2, 0)})
        # toutes les voisines sont drapeaux -> plus de case cachée -> pas de contrainte
        self.assertEqual(extract_constraints(v), [])

    def test_contrainte_immuable(self):
        c = Constraint(frozenset({(0, 0)}), 1)
        with self.assertRaises(Exception):
            c.count = 2


class TestRegles(unittest.TestCase):
    """R02/R03/R04 : single-point, subset, intersection croisée."""

    def test_r02_contrainte_satisfaite(self):
        # '1' avec un drapeau voisin -> l'autre voisine cachée est sûre
        v = vue({(1, 0): 1}, flags={(0, 0)})
        déduction = deduce(extract_constraints(v))
        self.assertIn((2, 0), déduction.safe)
        self.assertIn("R02", déduction.safe[(2, 0)])

    def test_r02_contrainte_saturee(self):
        # '2' avec exactement deux voisines cachées -> les deux sont des mines
        v = vue({(1, 0): 2}, width=3, height=1)
        déduction = deduce(extract_constraints(v))
        self.assertEqual(set(déduction.mines), {(0, 0), (2, 0)})

    def test_r03_motif_1_2_1(self):
        # motif classique: les mines sont aux extrémités, le centre est sûr
        v = vue({(0, 0): 1, (1, 0): 2, (2, 0): 1}, width=3, height=2, mines=2)
        déduction = deduce(extract_constraints(v))
        self.assertIn((0, 1), déduction.mines)
        self.assertIn((2, 1), déduction.mines)
        self.assertIn((1, 1), déduction.safe)
        self.assertIn("R03", déduction.mines[(0, 1)])

    def test_r04_propagation_mines_connues(self):
        # une mine identifiée satisfait une contrainte -> révèle une case sûre
        contraintes = [
            Constraint(frozenset({(0, 1), (1, 1)}), 1),
            Constraint(frozenset({(0, 1), (1, 1), (2, 1)}), 2),
        ]
        déduction = deduce(contraintes)
        # subset donne (2,1) mine; puis R04: (0,1),(1,1) -> ...
        self.assertIn((2, 1), déduction.mines)

    def test_aucune_deduction(self):
        v = vue({(1, 0): 1})
        déduction = deduce(extract_constraints(v))
        self.assertEqual(déduction.safe, {})
        self.assertEqual(déduction.mines, {})


if __name__ == "__main__":
    unittest.main()
