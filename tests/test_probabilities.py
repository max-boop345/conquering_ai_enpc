"""Tests des probabilités exactes (R07) : combinatoire composantes + hors frontière."""

import unittest

from demineur.game import GameState
from demineur.solvers.classic.analysis import extract_constraints
from demineur.solvers.classic.csp import components, enumerate_solutions
from demineur.solvers.classic.probabilities import exact_probabilities
from demineur.view import GameView


def probas(numbers, flags=(), width=4, height=1, mines=2) -> dict:
    view = GameView(width, height, mines, GameState.PLAYING, frozenset(flags), numbers)
    contraintes = extract_constraints(view)
    comps = []
    for groupe in components(contraintes):
        cellules = sorted(set().union(*[c.cells for c in groupe]))
        comps.append((cellules, enumerate_solutions(cellules, groupe)))
    return exact_probabilities(view, comps)


class TestProbabilitesExactes(unittest.TestCase):
    def test_aucune_contrainte_uniforme(self):
        # début de partie: toutes les cases cachées ont la même probabilité
        p = probas({}, width=3, height=1, mines=1)
        self.assertAlmostEqual(p[(0, 0)], 1 / 3)
        self.assertAlmostEqual(p[(1, 0)], 1 / 3)
        self.assertAlmostEqual(p[(2, 0)], 1 / 3)

    def test_mine_certaine(self):
        # '1' avec une seule voisine cachée
        p = probas({(1, 0): 1}, width=2, height=1, mines=1)
        self.assertAlmostEqual(p[(0, 0)], 1.0)

    def test_fifty_fifty(self):
        # '1' sur deux voisines: 0.5 chacune
        p = probas({(1, 0): 1}, width=3, height=1, mines=1)
        self.assertAlmostEqual(p[(0, 0)], 0.5)
        self.assertAlmostEqual(p[(2, 0)], 0.5)

    def test_hors_frontiere_deduite(self):
        # 2 mines, '1' entre deux cases: la mine restante est hors frontière
        p = probas({(1, 0): 1}, width=4, height=1, mines=2)
        self.assertAlmostEqual(p[(0, 0)], 0.5)
        self.assertAlmostEqual(p[(2, 0)], 0.5)
        self.assertAlmostEqual(p[(3, 0)], 1.0)  # certainement une mine

    def test_somme_egale_mines_restantes(self):
        # invariant: la somme des probabilités sur les cases cachées = mines restantes
        specs = [
            (dict(), 3, 1, 1, ()),               # (numbers, width, height, mines, flags)
            ({(1, 0): 1}, 4, 1, 2, ()),
            ({(1, 0): 1, (2, 0): 1}, 5, 1, 2, ()),
            ({(1, 0): 2}, 5, 2, 3, ((2, 0),)),   # un drapeau sur une voisine
        ]
        for numbers, w, h, mines, flags in specs:
            view = GameView(w, h, mines, GameState.PLAYING, frozenset(flags), numbers)
            contraintes = extract_constraints(view)
            comps = []
            for groupe in components(contraintes):
                cellules = sorted(set().union(*[c.cells for c in groupe]))
                comps.append((cellules, enumerate_solutions(cellules, groupe)))
            p = exact_probabilities(view, comps)
            m_restantes = mines - len(flags)
            self.assertAlmostEqual(sum(p.values()), m_restantes, places=9,
                                   msg=f"spec={numbers}")

    def test_composantes_independantes(self):
        # deux '1' disjoints, 2 mines: chaque paire à 50/50
        p = probas({(1, 0): 1, (4, 0): 1}, width=6, height=1, mines=2)
        self.assertAlmostEqual(p[(0, 0)], 0.5)
        self.assertAlmostEqual(p[(2, 0)], 0.5)
        self.assertAlmostEqual(p[(3, 0)], 0.5)
        self.assertAlmostEqual(p[(5, 0)], 0.5)


if __name__ == "__main__":
    unittest.main()
