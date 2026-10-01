"""Tests des solveurs étalons (B05, B06, B08) et du GameRunner (B09, B10, B07)."""

import unittest

from demineur.actions import Flag, GiveUp, Reveal
from demineur.game import Game, GameState
from demineur.runner import GameRunner, MoveEvent, RunResult
from demineur.solvers.base import Solver
from demineur.solvers.random_solver import RandomSolver
from demineur.solvers.rule_solver import RuleSolver
from demineur.view import GameView


def vue_minimaliste() -> GameView:
    """Grille 1x3 : case (1,0) révélée '2', voisines cachées → toutes mines."""
    return GameView(
        width=3, height=1, mines_count=2, state=GameState.PLAYING,
        flags=frozenset(), numbers={(1, 0): 2},
    )


def vue_satisfaite() -> GameView:
    """Grille 1x3 : case (1,0) révélée '1', (0,0) déjà drapeau → (2,0) sûre."""
    return GameView(
        width=3, height=1, mines_count=1, state=GameState.PLAYING,
        flags=frozenset({(0, 0)}), numbers={(1, 0): 1},
    )


class TestContratSolver(unittest.TestCase):
    """B01 : contrat — le solveur ne voit que la vue, retourne une Action."""

    def test_contrat_solver_abstrait(self):
        with self.assertRaises(TypeError):
            Solver()  # type: ignore[abstract]

    def test_random_solver_action_legale(self):
        solver = RandomSolver(seed=0)
        action = solver.decide(vue_minimaliste())
        self.assertIn(action, [Reveal(0, 0), Reveal(2, 0)])

    def test_random_solver_determinisme(self):
        vues = [vue_minimaliste() for _ in range(5)]
        actions1 = [RandomSolver(seed=42).decide(v) for v in vues]
        actions2 = [RandomSolver(seed=42).decide(v) for v in vues]
        self.assertEqual(actions1, actions2)

    def test_random_solver_aucune_case(self):
        vue = GameView(1, 1, 0, GameState.PLAYING, frozenset(), {})
        # case unique révélée -> plus rien de caché
        vue = GameView(1, 1, 0, GameState.PLAYING, frozenset(), {(0, 0): 0})
        action = RandomSolver(seed=0).decide(vue)
        self.assertIsInstance(action, GiveUp)

    def test_justification_disponible(self):
        solver = RandomSolver(seed=0)
        solver.decide(vue_minimaliste())
        self.assertIsInstance(solver.last_justification, str)


class TestRuleSolver(unittest.TestCase):
    """B06 : single-point uniquement (contrainte satisfaite / saturée)."""

    def test_contrainte_saturee_flag(self):
        action = RuleSolver(seed=0).decide(vue_minimaliste())
        self.assertIsInstance(action, Flag)

    def test_contrainte_satisfaite_reveal(self):
        action = RuleSolver(seed=0).decide(vue_satisfaite())
        self.assertEqual(action, Reveal(2, 0))

    def test_justification_r02(self):
        solver = RuleSolver(seed=0)
        solver.decide(vue_satisfaite())
        self.assertIn("R02", solver.last_justification)

    def test_fallback_random_quand_aucune_regle(self):
        # aucune contrainte exploitable -> devinette aléatoire (déterministe par seed)
        vue = GameView(
            width=3, height=3, mines_count=2, state=GameState.PLAYING,
            flags=frozenset(), numbers={(0, 0): 1},
        )
        a1 = RuleSolver(seed=7).decide(vue)
        a2 = RuleSolver(seed=7).decide(vue)
        self.assertEqual(a1, a2)
        self.assertIsInstance(a1, Reveal)


class TestGameRunner(unittest.TestCase):
    """B09 : actions légales/illégales, politique de rejet ; B10 : événements."""

    def _jeu(self, seed=0):
        return GameRunner(Game(width=5, height=5, mines_count=3, seed=seed))

    def test_event_format(self):
        # B10 : (numéro, vue avant, action, justification, vue après, résultat)
        runner = self._jeu(seed=4)
        event = runner.apply(Reveal(0, 0))
        self.assertIsInstance(event, MoveEvent)
        self.assertEqual(event.move, 0)
        self.assertEqual(event.action, {"kind": "reveal", "x": 0, "y": 0})
        self.assertIn("grid", event.view_before)
        self.assertIn("grid", event.view_after)
        self.assertEqual(event.result, "ok")

    def test_action_illegale_rejetee(self):
        runner = self._jeu(seed=4)
        runner.apply(Reveal(0, 0))
        event = runner.apply(Reveal(0, 0))  # déjà révélée
        self.assertEqual(event.result, "illegal")
        self.assertEqual(len(runner.events), 2)
        self.assertEqual(runner.game.state, GameState.PLAYING)

    def test_abandon_apres_n_rejets(self):
        runner = GameRunner(Game(width=5, height=5, mines_count=3, seed=4), max_rejections=3)
        for _ in range(4):
            runner.apply(Reveal(9, 9))  # hors grille, toujours illégal
        self.assertEqual(runner.events[-1].result, "gave_up")

    def test_giveup(self):
        runner = self._jeu()
        event = runner.apply(GiveUp("test"))
        self.assertEqual(event.result, "gave_up")
        self.assertEqual(runner.game.state, GameState.PLAYING)

    def test_chainage_des_vues(self):
        runner = self._jeu(seed=4)
        runner.apply(Reveal(0, 0))
        runner.apply(Flag(4, 4))
        self.assertEqual(runner.events[0].view_after, runner.events[1].view_before)

    def test_limite_de_coups(self):
        # B07 : un solveur qui boucle ne bloque pas la partie
        class BoucleInfinie(Solver):
            name = "boucle"
            def decide(self, view):
                return GiveUp("stop") if len(view.numbers) > 0 else Reveal(0, 0)
        runner = GameRunner(Game(width=5, height=5, mines_count=3, seed=4), max_moves=2)
        resultat = runner.run(BoucleInfinie())
        self.assertLessEqual(resultat.moves, 3)  # 2 coups + arrêt
        self.assertIsInstance(resultat, RunResult)

    def test_run_random_solver_termine(self):
        # B08 : le solveur aléatoire termine toujours
        for seed in range(5):
            runner = GameRunner(Game(width=5, height=5, mines_count=3, seed=seed))
            resultat = runner.run(RandomSolver(seed=seed))
            self.assertIn(resultat.state, (GameState.WON, GameState.LOST, GameState.PLAYING))
            self.assertLess(resultat.moves, 100)

    def test_run_rule_solver_gagne_grille_facile(self):
        # B08 : RuleSolver gagne sur des grilles faciles seedées
        for seed in range(10):
            runner = GameRunner(Game(width=9, height=9, mines_count=10, seed=seed))
            resultat = runner.run(RuleSolver(seed=seed))
            if resultat.state is GameState.WON:
                break
        else:
            self.fail("RuleSolver n'a gagné aucune des 10 grilles faciles")

    def test_evenements_json(self):
        import json
        runner = self._jeu(seed=4)
        runner.apply(Reveal(0, 0))
        data = runner.events[0].to_json()
        json.dumps(data)  # sérialisable sans erreur
        self.assertEqual(data["move"], 0)


if __name__ == "__main__":
    unittest.main()
