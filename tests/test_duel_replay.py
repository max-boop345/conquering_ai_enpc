"""Tests des modes duel (F03) et spectateur (F04)."""

import io
import tempfile
import unittest

from demineur.artifacts import save_game
from demineur.duel import run_duel
from demineur.game import Game, GameState
from demineur.replay import format_event, replay_text
from demineur.runner import GameRunner
from demineur.solvers.classic import ClassicSolver


class TestDuel(unittest.TestCase):
    """F03 : solveur classique vs humain sur la même grille seedée."""

    def test_duel_humain_abandonne(self):
        humain = Game(width=5, height=5, mines_count=3, seed=4)
        solveur = Game(width=5, height=5, mines_count=3, seed=4)
        entrée = io.StringIO("q\n")
        sortie = io.StringIO()
        résultat = run_duel(humain, solveur, ClassicSolver(),
                            input_stream=entrée, output_stream=sortie)
        self.assertIn("duel", sortie.getvalue().lower())
        self.assertIn(résultat["solver_state"], (GameState.WON, GameState.LOST,
                                                 GameState.PLAYING))
        self.assertIn(résultat["human_state"], (GameState.PLAYING, GameState.WON,
                                                GameState.LOST))

    def test_duel_humain_joue(self):
        humain = Game(width=5, height=5, mines_count=3, seed=4)
        solveur = Game(width=5, height=5, mines_count=3, seed=4)
        entrée = io.StringIO("r 0 0\nq\n")
        sortie = io.StringIO()
        run_duel(humain, solveur, ClassicSolver(),
                 input_stream=entrée, output_stream=sortie)
        self.assertTrue(len(humain.revealed) > 0)
        self.assertTrue(len(solveur.revealed) > 0)  # le solveur a joué au moins un coup

    def test_memes_seed_memes_grilles(self):
        g1 = Game(width=9, height=9, mines_count=10, seed=7)
        g2 = Game(width=9, height=9, mines_count=10, seed=7)
        g1.reveal(0, 0)
        g2.reveal(0, 0)
        self.assertEqual(g1.board.mines, g2.board.mines)


class TestSpectateur(unittest.TestCase):
    """F04 : rejouer une partie loggée coup par coup dans le terminal."""

    def _sauve_partie(self, d):
        runner = GameRunner(Game(width=5, height=5, mines_count=3, seed=4))
        runner.run(ClassicSolver())
        return save_game(d, runner, meta={"seed": 4, "solver": "classic"})

    def test_format_event(self):
        from demineur.artifacts import load_game
        with tempfile.TemporaryDirectory() as d:
            chemin = self._sauve_partie(d)
            _, events, _ = load_game(chemin)
            ligne = format_event(events[0])
            self.assertIn("#000", ligne)
            self.assertIn("reveal", ligne)

    def test_replay_text(self):
        from demineur.artifacts import load_game
        with tempfile.TemporaryDirectory() as d:
            chemin = self._sauve_partie(d)
            header, events, result = load_game(chemin)
            sortie = io.StringIO()
            replay_text(header, events, result, output_stream=sortie)
            texte = sortie.getvalue()
            self.assertIn("seed", texte)
            self.assertIn("#000", texte)
            self.assertIn(result["state"], texte)


if __name__ == "__main__":
    unittest.main()
