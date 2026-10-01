"""Tests du harnais de benchmark (R14) : déterminisme, format, non-régression."""

import unittest

from demineur.benchmark import benchmark_to_json, format_table, run_benchmark
from demineur.solvers.classic import ClassicSolver
from demineur.solvers.random_solver import RandomSolver
from demineur.solvers.rule_solver import RuleSolver


class TestBenchmark(unittest.TestCase):
    def test_resultats_coherents(self):
        résultats = run_benchmark(
            solvers={"random": RandomSolver, "rule": RuleSolver, "classic": ClassicSolver},
            difficulty="beginner",
            seeds=list(range(10)),
        )
        self.assertEqual(len(résultats), 3)
        for r in résultats.values():
            self.assertEqual(r.seeds, 10)
            self.assertEqual(r.wins + r.losses + r.gave_ups, 10)
            self.assertAlmostEqual(r.win_rate, r.wins / 10)
            self.assertGreaterEqual(r.avg_moves, 1)

    def test_determinisme_strict(self):
        # même seeds -> résultats identiques (validité scientifique des mesures)
        r1 = run_benchmark({"classic": ClassicSolver}, "beginner", seeds=range(20))
        r2 = run_benchmark({"classic": ClassicSolver}, "beginner", seeds=range(20))
        self.assertEqual(
            benchmark_to_json(r1), benchmark_to_json(r2)
        )

    def test_classic_domine_random(self):
        r = run_benchmark(
            {"random": RandomSolver, "classic": ClassicSolver},
            "beginner", seeds=range(20),
        )
        self.assertGreater(r["classic"].win_rate, r["random"].win_rate)

    def test_format_table_markdown(self):
        r = run_benchmark({"classic": ClassicSolver}, "beginner", seeds=range(5))
        table = format_table(r)
        self.assertIn("| solveur |", table)
        self.assertIn("classic", table)
        self.assertIn("win-rate", table.lower())

    def test_json_round_trip(self):
        r = run_benchmark({"classic": ClassicSolver}, "beginner", seeds=range(3))
        data = benchmark_to_json(r)
        self.assertEqual(data["difficulty"], "beginner")
        self.assertIn("classic", data["results"])
        self.assertEqual(data["results"]["classic"]["wins"],
                         r["classic"].wins)


if __name__ == "__main__":
    unittest.main()
