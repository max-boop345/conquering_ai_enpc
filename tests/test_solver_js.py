"""Tests node du solveur classique JS (port de solvers/classic/) — INV1 :
solver.js ne consomme que le JSON de vue, jamais le plateau réel."""

import json
import unittest

from tests.js_harness import NODE, node_exec, web_js

SOLVER = web_js("solver.js")


def vue_fixture(numbers, flags=(), width=4, height=2, mines=2):
    grid = [[{"state": "hidden"} for _ in range(width)] for _ in range(height)]
    for (x, y), n in numbers.items():
        grid[y][x] = {"state": "revealed", "adjacent_mines": n}
    for (x, y) in flags:
        grid[y][x] = {"state": "flagged"}
    return {"version": 1, "kind": "view", "width": width, "height": height,
            "mines_count": mines, "state": "playing", "grid": grid}


@unittest.skipUnless(NODE, "node non disponible")
class TestContraintesJS(unittest.TestCase):
    def test_extraction(self):
        fixture = vue_fixture({(1, 0): 1})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = S.extraireContraintes(@fixture:vue);\n"
            "console.log(c.length, c[0].count);",
            {"vue": fixture},
        )
        self.assertIn("1 1", sortie)

    def test_exclusion_drapeaux(self):
        fixture = vue_fixture({(1, 0): 2}, flags={(0, 0)})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = S.extraireContraintes(@fixture:vue);\n"
            "console.log(c[0].count, Array.from(c[0].cells).indexOf('0,0') === -1);",
            {"vue": fixture},
        )
        self.assertIn("1 true", sortie)


@unittest.skipUnless(NODE, "node non disponible")
class TestReglesJS(unittest.TestCase):
    def test_r02_satisfaite(self):
        # Fixture ajustée (leçon lot A) : en 4x2, (1,0) a 4 voisins cachés et
        # R02 marque les 4 sûrs -> la sortie serait "2,0,0,1,1,1,2,1 true".
        # En 3x1 il n'y a qu'un seul voisin caché -> "2,0 true".
        # Assertion identique au plan.
        fixture = vue_fixture({(1, 0): 1}, flags={(0, 0)},
                               width=3, height=1, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "console.log(Object.keys(d.safe).join(','),"
            "            (d.safe['2,0'] || '').indexOf('R02') === 0);",
            {"vue": fixture},
        )
        self.assertIn("2,0 true", sortie)

    def test_r02_saturée(self):
        fixture = vue_fixture({(1, 0): 2}, width=3, height=1, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "console.log(Object.keys(d.mines).sort().join(','));",
            {"vue": fixture},
        )
        self.assertEqual(sortie.strip(), "0,0,2,0")

    def test_r03_motif_1_2_1(self):
        fixture = vue_fixture({(0, 0): 1, (1, 0): 2, (2, 0): 1},
                              width=3, height=2, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "console.log(JSON.stringify({mines: Object.keys(d.mines).sort(),"
            "safe: Object.keys(d.safe).sort(),"
            "just: d.mines['0,1'] || ''}));",
            {"vue": fixture},
        )
        d = json.loads(sortie)
        self.assertEqual(d["mines"], ["0,1", "2,1"])
        self.assertEqual(d["safe"], ["1,1"])
        self.assertIn("R03", d["just"])

    def test_aucune_deduction(self):
        fixture = vue_fixture({(1, 0): 1})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "console.log(Object.keys(d.safe).length +"
            "            Object.keys(d.mines).length);",
            {"vue": fixture},
        )
        self.assertIn("0", sortie)


if __name__ == "__main__":
    unittest.main()
