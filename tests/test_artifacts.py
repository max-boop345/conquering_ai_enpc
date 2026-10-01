"""Tests des artefacts de parties (B10/W03) : sauvegarde/chargement JSONL."""

import os
import tempfile
import unittest

from demineur.artifacts import list_games, load_game, save_game
from demineur.game import Game
from demineur.runner import GameRunner
from demineur.solvers.classic import ClassicSolver


def partie_loggée():
    runner = GameRunner(Game(width=9, height=9, mines_count=10, seed=42))
    runner.run(ClassicSolver())
    return runner


class TestArtefacts(unittest.TestCase):
    def test_sauvegarde_et_lecture(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = save_game(d, partie_loggée(), meta={
                "seed": 42, "solver": "classic", "difficulty": "beginner",
            })
            self.assertTrue(os.path.exists(chemin))
            header, events, result = load_game(chemin)
            self.assertEqual(header["seed"], 42)
            self.assertEqual(header["solver"], "classic")
            self.assertGreater(len(events), 5)
            self.assertIn(result["state"], ("won", "lost"))
            # les événements enchaînent les vues (B10)
            self.assertEqual(events[0]["move"], 0)
            self.assertEqual(events[1]["view_before"], events[0]["view_after"])

    def test_liste_les_parties(self):
        with tempfile.TemporaryDirectory() as d:
            for seed in (1, 2):
                runner = GameRunner(Game(5, 5, 2, seed=seed))
                runner.run(ClassicSolver())
                save_game(d, runner, meta={"seed": seed, "solver": "classic"})
            parties = list_games(d)
            self.assertEqual(len(parties), 2)
            self.assertTrue(all(p["header"]["kind"] == "game_header" for p in parties))

    def test_repertoire_absent_vide(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(list_games(os.path.join(d, "inexistant")), [])

    def test_fichier_corrompu_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "bad.jsonl")
            with open(chemin, "w") as f:
                f.write("pas du json\n")
            with self.assertRaises(ValueError):
                load_game(chemin)


if __name__ == "__main__":
    unittest.main()
