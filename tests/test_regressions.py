"""Tests des cas limites (R13, R17, R18) : fixtures par règle, repli, performance."""

import time
import unittest

from demineur.game import GameState
from demineur.solvers.classic import ClassicSolver, analyze
from demineur.solvers.classic.analysis import extract_constraints
from demineur.solvers.classic.classic_solver import _clusters
from demineur.view import GameView


def vue(numbers, flags=(), width=4, height=2, mines=2) -> GameView:
    return GameView(width, height, mines, GameState.PLAYING, frozenset(flags), numbers)


def grande_vue() -> GameView:
    """Frontière alternée 1-2 longue : composante unique non déductible par règles."""
    numbers = {(x, 0): (1 if x % 2 == 0 else 2) for x in range(1, 39)}
    return GameView(40, 2, 30, GameState.PLAYING, frozenset(), numbers)


class TestFixturesRegles(unittest.TestCase):
    """R13 : une fixture par règle, y compris motifs classiques et devinette forcée."""

    def test_motif_1_2_2_1(self):
        # motif 1-2-2-1: mines au centre, extrémités sûres
        v = vue({(0, 0): 1, (1, 0): 2, (2, 0): 2, (3, 0): 1}, width=4, height=2, mines=2)
        a = analyze(v)
        self.assertIn((0, 1), a.safe)
        self.assertIn((3, 1), a.safe)

    def test_devinette_forcee_50_50(self):
        # deux cases, une mine: aucune déduction possible -> guess
        v = vue({(1, 0): 1}, width=3, height=1, mines=1)
        a = analyze(v)
        self.assertEqual(a.safe, {})
        self.assertEqual(a.mines, {})

    def test_flag_moins_de_mines_que_affiche(self):
        # une contrainte '2' avec un drapeau: 1 mine restante sur 1 case
        v = vue({(1, 0): 2}, flags={(0, 0)}, width=3, height=1, mines=2)
        a = analyze(v)
        self.assertIn((2, 0), a.mines)


class TestRepliR17(unittest.TestCase):
    """R17 : composante trop grande -> décomposition, jamais d'échec silencieux."""

    def _grande_vue(self):
        return grande_vue()

    def test_analyse_repli_non_exact(self):
        a = analyze(self._grande_vue())
        self.assertFalse(a.exact)
        # probabilités uniformes de repli
        cachées = [p for p in a.probabilities]
        self.assertTrue(all(abs(a.probabilities[p] - a.probabilities[cachées[0]]) < 1e-12
                            for p in cachées))

    def test_solver_decide_malgre_repli(self):
        solver = ClassicSolver()
        action = solver.decide(self._grande_vue())
        self.assertIsNotNone(action)
        self.assertIn("R17", solver.last_justification)

    def test_clusters_decoupent(self):
        contraintes = extract_constraints(self._grande_vue())
        cellules = sorted(set().union(*[c.cells for c in contraintes]))
        # contraintes et cases en grand nombre
        self.assertGreater(len(cellules), 30)
        clusters = _clusters(contraintes, 30)
        self.assertGreater(len(clusters), 1)
        for cluster in clusters:
            tailles = len(set().union(*[c.cells for c in cluster]))
            self.assertLessEqual(tailles, 30 + 8)  # une contrainte peut dépasser


class TestBudgetPerformance(unittest.TestCase):
    """R18 : plafond de temps par coup documenté et testé (pire cas expert)."""

    def test_analyse_grande_composante_rapide(self):
        début = time.monotonic()
        analyze(grande_vue())
        self.assertLess(time.monotonic() - début, 1.0)

    def test_partie_expert_par_coup(self):
        # plafond documenté: 1.0 s par coup sur grille expert (docs/classic_solver.md)
        from demineur.game import Game
        from demineur.runner import GameRunner
        jeu = Game(30, 16, 99, seed=42)
        runner = GameRunner(jeu)
        solver = ClassicSolver()
        pire = 0.0
        from demineur.game import GameState as GS
        while jeu.state is GS.PLAYING:
            vue = jeu.view()
            début = time.monotonic()
            action = solver.decide(vue)
            pire = max(pire, time.monotonic() - début)
            runner.apply(action, solver.last_justification)
            if runner.gave_up:
                break
        self.assertLess(pire, 1.0, f"pire coup: {pire:.2f}s > plafond 1.0s")


if __name__ == "__main__":
    unittest.main()
