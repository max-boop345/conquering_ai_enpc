"""Tests CSP : composantes (R05), classification (R06), impossible (R12), repli (R17)."""

import unittest

from demineur.solvers.classic.analysis import Constraint
from demineur.solvers.classic.csp import (
    ComponentTooLarge,
    ConfigurationImpossible,
    classify,
    components,
    enumerate_solutions,
)


def c(cells, count):
    return Constraint(frozenset(cells), count)


class TestComposantes(unittest.TestCase):
    """R05 : partition en composantes connexes indépendantes."""

    def test_contraintes_isolees(self):
        comps = components([c([(0, 0), (0, 1)], 1), c([(2, 2), (2, 3)], 1)])
        self.assertEqual(len(comps), 2)

    def test_contraintes_reliees(self):
        comps = components([c([(0, 0), (0, 1)], 1), c([(0, 1), (0, 2)], 1)])
        self.assertEqual(len(comps), 1)
        self.assertEqual(len(comps[0]), 2)

    def test_une_par_cellule_partagee(self):
        comps = components([c([(0, 0), (1, 0)], 1), c([(1, 0), (2, 0)], 1),
                            c([(5, 5), (6, 5)], 1)])
        self.assertEqual(len(comps), 2)
        self.assertEqual(len(comps[0]), 2)  # reliées par la case (1,0)


class TestEnumeration(unittest.TestCase):
    """R05 : énumération exacte des solutions par composante."""

    def test_solution_unique(self):
        sols = enumerate_solutions(
            [(0, 0), (1, 0)],
            [c([(0, 0)], 1), c([(0, 0), (1, 0)], 1)],
        )
        self.assertEqual(sols, [frozenset({(0, 0)})])

    def test_deux_solutions(self):
        sols = enumerate_solutions([(0, 0), (1, 0)], [c([(0, 0), (1, 0)], 1)])
        self.assertEqual(set(sols), {frozenset({(0, 0)}), frozenset({(1, 0)})})

    def test_contrainte_satisfaite_par_plusieurs(self):
        sols = enumerate_solutions(
            [(0, 0), (1, 0), (2, 0)],
            [c([(0, 0), (1, 0)], 1), c([(1, 0), (2, 0)], 1)],
        )
        self.assertEqual(set(sols), {frozenset({(0, 0), (2, 0)}), frozenset({(1, 0)})})

    def test_cap_de_taille(self):
        # R17 : une composante trop grande doit être signalée, jamais bloquer
        grandes = [c([(x, 0) for x in range(40)], 20)]
        with self.assertRaises(ComponentTooLarge):
            enumerate_solutions([(x, 0) for x in range(40)], grandes, max_cells=30)

    def test_cap_de_solutions(self):
        cellules = [(x, 0) for x in range(24)]
        contraintes = [c(cellules, 12)]
        with self.assertRaises(ComponentTooLarge):
            enumerate_solutions(cellules, contraintes, max_solutions=100)


class TestClassification(unittest.TestCase):
    """R06 : toujours-mine / jamais-mine / incertaine."""

    def test_toujours_et_jamais_mine(self):
        sols = [frozenset({(0, 0)})]
        toujours, jamais = classify([(0, 0), (1, 0)], sols)
        self.assertEqual(toujours, {(0, 0)})
        self.assertEqual(jamais, {(1, 0)})

    def test_incertaine(self):
        sols = [frozenset({(0, 0)}), frozenset({(1, 0)})]
        toujours, jamais = classify([(0, 0), (1, 0)], sols)
        self.assertEqual(toujours, set())
        self.assertEqual(jamais, set())


class TestConfigurationImpossible(unittest.TestCase):
    """R12 : CSP sans solution = bug moteur ou vue corrompue (fail-fast)."""

    def test_contraintes_contradictoires(self):
        with self.assertRaises(ConfigurationImpossible):
            enumerate_solutions(
                [(0, 0), (1, 0)],
                [c([(0, 0), (1, 0)], 2), c([(0, 0), (1, 0)], 1)],
            )


if __name__ == "__main__":
    unittest.main()
