"""Tests CLI (R15, F01) : solve --explain, benchmark, new, play."""

import io
import unittest
from contextlib import redirect_stdout

from demineur.cli import main


def exécute(argv):
    sortie = io.StringIO()
    code = 0
    with redirect_stdout(sortie):
        code = main(argv)
    return code, sortie.getvalue()


class TestSolve(unittest.TestCase):
    """R15 : demineur solve --seed X --method classic --explain."""

    def test_solve_classic_explain(self):
        code, sortie = exécute([
            "solve", "--seed", "3", "--w", "9", "--h", "9", "--mines", "10",
            "--method", "classic", "--explain",
        ])
        self.assertEqual(code, 0)
        self.assertIn("gagné" if "gagné" in sortie else "perdu", sortie)
        self.assertIn("R0", sortie)  # justifications présentes

    def test_solve_difficulty(self):
        code, sortie = exécute([
            "solve", "--seed", "1", "--difficulty", "beginner", "--method", "classic",
        ])
        self.assertEqual(code, 0)
        self.assertIn("beginner", sortie)

    def test_solve_method_inconnue(self):
        # argparse refuse les valeurs hors choices avec SystemExit(2)
        sortie = io.StringIO()
        with redirect_stdout(sortie):
            with self.assertRaises(SystemExit):
                main(["solve", "--seed", "1", "--method", "turbo"])

    def test_solve_random(self):
        # code 0 = victoire, 1 = défaite (un solveur aléatoire peut perdre)
        code, _ = exécute([
            "solve", "--seed", "1", "--difficulty", "beginner", "--method", "random",
        ])
        self.assertIn(code, (0, 1))

    def test_solve_sauvegarde_artefact(self):
        # l'artefact JSONL produit est relu par load_game (replay/serve)
        import os
        import tempfile

        from demineur.artifacts import load_game

        with tempfile.TemporaryDirectory() as d:
            code, sortie = exécute([
                "solve", "--seed", "9", "--difficulty", "beginner",
                "--method", "classic", "--save", d,
            ])
            self.assertEqual(code, 0)
            fichiers = [f for f in os.listdir(d) if f.endswith(".jsonl")]
            self.assertEqual(len(fichiers), 1)
            header, events, result = load_game(os.path.join(d, fichiers[0]))
            self.assertEqual(header["solver"], "classic")
            self.assertGreater(len(events), 0)
            self.assertIn("sauvegardée", sortie)


class TestBenchmarkCLI(unittest.TestCase):
    def test_benchmark_petit(self):
        code, sortie = exécute([
            "benchmark", "--difficulty", "beginner", "--seeds", "4",
            "--solvers", "classic,random",
        ])
        self.assertEqual(code, 0)
        self.assertIn("win-rate", sortie.lower())

    def test_benchmark_sauvegarde(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "bench.md")
            code, _ = exécute([
                "benchmark", "--difficulty", "beginner", "--seeds", "3",
                "--solvers", "classic", "--save", chemin,
            ])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(chemin))


class TestNew(unittest.TestCase):
    def test_new(self):
        code, sortie = exécute(["new", "--seed", "42", "--difficulty", "beginner"])
        self.assertEqual(code, 0)
        self.assertIn("9x9", sortie)


if __name__ == "__main__":
    unittest.main()
