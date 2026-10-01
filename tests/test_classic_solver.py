"""Tests du solveur classique complet (R08→R12) : coup sûr, guess, boucle, explicabilité."""

import time
import unittest

from demineur.actions import Flag, GiveUp, Reveal
from demineur.game import Game, GameState
from demineur.runner import GameRunner
from demineur.solvers.classic import ClassicSolver, analyze
from demineur.solvers.random_solver import RandomSolver
from demineur.view import GameView


def vue(numbers, flags=(), width=4, height=2, mines=2) -> GameView:
    return GameView(width, height, mines, GameState.PLAYING, frozenset(flags), numbers)


class TestCoupSur(unittest.TestCase):
    """R08 : révéler en priorité une case jamais-mine."""

    def test_case_sure_revelee(self):
        # '1' avec drapeau voisin -> l'autre voisine est sûre
        solver = ClassicSolver()
        action = solver.decide(vue({(1, 0): 1}, flags={(0, 0)}))
        self.assertEqual(action, Reveal(2, 0))

    def test_drapeau_sur_toujours_mine(self):
        # '2' saturée -> drapeau posé avant tout guess
        solver = ClassicSolver()
        action = solver.decide(vue({(1, 0): 2}, width=3, height=1, mines=2))
        self.assertIsInstance(action, Flag)

    def test_premier_coup_deterministe(self):
        solver = ClassicSolver()
        action = solver.decide(GameView(9, 9, 10, GameState.PLAYING, frozenset(), {}))
        self.assertIsInstance(action, Reveal)

    def test_determinisme(self):
        v = vue({(1, 0): 1})
        a1 = ClassicSolver().decide(v)
        a2 = ClassicSolver().decide(v)
        self.assertEqual(a1, a2)


class TestGuess(unittest.TestCase):
    """R09 : heuristique de devinette — minimiser la probabilité de mine."""

    def test_guess_probabilite_minimale(self):
        # '1' entre deux cases, aucune autre information: devinette forcée à 0.5
        solver = ClassicSolver()
        action = solver.decide(vue({(1, 0): 1}, width=3, height=1, mines=1))
        self.assertIn(action, [Reveal(0, 0), Reveal(2, 0)])
        self.assertIn("guess", solver.last_justification.lower())

    def test_comptage_global_case_sure(self):
        # 1 mine dans {a,b}: la case hors frontière restante est certainement sûre
        solver = ClassicSolver()
        action = solver.decide(vue({(1, 0): 1}, width=4, height=1, mines=1))
        self.assertEqual(action, Reveal(3, 0))
        self.assertIn("R07", solver.last_justification)

    def test_guess_prefere_probabilite_basse(self):
        # contrainte A: 8 cases / 1 mine (p=0.125) ; B: 3 cases / 1 mine (p=1/3)
        # mines=3 -> 1 mine hors frontière sur 2 cases (p=0.5): guess dans A
        v = GameView(5, 3, 3, GameState.PLAYING, frozenset(), {(1, 1): 1, (4, 0): 1})
        solver = ClassicSolver()
        action = solver.decide(v)
        cellules_a = {(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)}
        self.assertIsInstance(action, Reveal)
        self.assertIn((action.x, action.y), cellules_a)

    def test_hors_frontiere_moins_risqueuse(self):
        # 3 mines: 1 dans {a,b} et 2 forcément ailleurs sur 2 cases hors frontière
        # cases hors frontière: p=1.0; frontière: 0.5 -> guess dans la frontière
        solver = ClassicSolver()
        action = solver.decide(vue({(1, 0): 1}, width=5, height=1, mines=3))
        self.assertIn(action, [Reveal(0, 0), Reveal(2, 0)])


class TestExplicabilite(unittest.TestCase):
    """R11 : chaque décision émet une justification courte."""

    def test_justification_r02(self):
        solver = ClassicSolver()
        solver.decide(vue({(1, 0): 1}, flags={(0, 0)}))
        self.assertIn("R02", solver.last_justification)

    def test_justification_guess_contient_probabilite(self):
        solver = ClassicSolver()
        solver.decide(vue({(1, 0): 1}, width=3, height=1, mines=1))
        self.assertRegex(solver.last_justification, r"p=[01]\.[0-9]+")


class TestConfigurationImpossible(unittest.TestCase):
    """R12 : vue corrompue -> abandon explicite, jamais de crash."""

    def test_vue_incoherente(self):
        # '2' avec une seule voisine cachée: impossible
        solver = ClassicSolver()
        action = solver.decide(vue({(0, 0): 2}, width=3, height=1, mines=2))
        self.assertIsInstance(action, GiveUp)
        self.assertIn("impossible", solver.last_justification.lower())


class TestAnalyse(unittest.TestCase):
    """analyse() expose données utilisées par le web (W08, W09)."""

    def test_analyse_contient_probabilites(self):
        a = analyze(vue({(1, 0): 1}, width=4, height=1, mines=1))
        self.assertAlmostEqual(a.probabilities[(0, 0)], 0.5)
        self.assertAlmostEqual(a.probabilities[(2, 0)], 0.5)
        self.assertAlmostEqual(a.probabilities[(3, 0)], 0.0)
        self.assertTrue(a.exact)

    def test_analyse_composantes(self):
        a = analyze(vue({(1, 0): 1, (5, 0): 1}, width=7, height=1, mines=2))
        self.assertEqual(len(a.components), 2)


class TestBoucleComplete(unittest.TestCase):
    """R10 : résolution complète de bouts en bouts via GameRunner."""

    def test_gagne_grille_facile(self):
        gagnées = 0
        for seed in range(10):
            runner = GameRunner(Game(width=9, height=9, mines_count=10, seed=seed))
            résultat = runner.run(ClassicSolver())
            gagnées += résultat.won
            self.assertIn(résultat.state, (GameState.WON, GameState.LOST))
            # aucun événement illégal: le solveur ne propose que des coups légaux
            self.assertTrue(all(e.result == "ok" for e in runner.events if e.result != "gave_up"))
        self.assertGreaterEqual(gagnées, 5, "attendu >= 50% de victoires sur grilles faciles")

    def test_bat_le_solveur_random(self):
        victoires_classic = sum(
            GameRunner(Game(9, 9, 10, seed=s)).run(ClassicSolver()).won
            for s in range(15)
        )
        victoires_random = sum(
            GameRunner(Game(9, 9, 10, seed=s)).run(RandomSolver(seed=s)).won
            for s in range(15)
        )
        self.assertGreater(victoires_classic, victoires_random)

    def test_expert_termine_rapidement(self):
        # R18: une partie experte doit se dérouler en moins de 10s au total
        début = time.monotonic()
        runner = GameRunner(Game(30, 16, 99, seed=1))
        runner.run(ClassicSolver())
        self.assertLess(time.monotonic() - début, 10.0)


if __name__ == "__main__":
    unittest.main()
