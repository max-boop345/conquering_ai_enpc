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


@unittest.skipUnless(NODE, "node non disponible")
class TestCspJS(unittest.TestCase):
    def test_composantes(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c1 = {cells: new Set(['0,0','0,1']), count: 1};\n"
            "const c2 = {cells: new Set(['0,1','0,2']), count: 1};\n"
            "const c3 = {cells: new Set(['5,5','6,5']), count: 1};\n"
            "console.log(S.composantes([c1, c2, c3]).length);"
        )
        self.assertIn("2", sortie)

    def test_énumération_2_solutions(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = [{cells: new Set(['0,0','1,0']), count: 1}];\n"
            "console.log(S.énumérer(['0,0','1,0'], c).length);"
        )
        self.assertIn("2", sortie)

    def test_classification(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const r = S.classer(['0,0','1,0'], [new Set(['0,0'])]);\n"
            "console.log(Array.from(r.toujours).join(','),"
            "            Array.from(r.jamais).join(','));"
        )
        self.assertIn("0,0 1,0", sortie)

    def test_plafond_cellules(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const cellules = [];\n"
            "for (let i = 0; i < 40; i++) cellules.push(i + ',0');\n"
            "const c = [{cells: new Set(cellules), count: 20}];\n"
            "try { S.énumérer(cellules, c); console.log('pas-derreur'); }\n"
            "catch (e) { console.log(e.name); }"
        )
        self.assertIn("ComponentTooLarge", sortie)

    def test_configuration_impossible(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = [{cells: new Set(['0,0','1,0']), count: 2},\n"
            "           {cells: new Set(['0,0','1,0']), count: 1}];\n"
            "try { S.énumérer(['0,0','1,0'], c); console.log('pas-derreur'); }\n"
            "catch (e) { console.log(e.name); }"
        )
        self.assertIn("ConfigurationImpossible", sortie)


@unittest.skipUnless(NODE, "node non disponible")
class TestProbabilitésJS(unittest.TestCase):
    def test_cinquante_cinquante(self):
        fixture = vue_fixture({(1, 0): 1}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(a.probabilities['0,0'].toFixed(2),"
            "            a.probabilities['2,0'].toFixed(2), a.exact);",
            {"vue": fixture},
        )
        self.assertIn("0.50 0.50 true", sortie)

    def test_hors_frontière_déduite(self):
        fixture = vue_fixture({(1, 0): 1}, width=4, height=1, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(a.probabilities['0,0'].toFixed(2),"
            "            a.probabilities['3,0'].toFixed(2));",
            {"vue": fixture},
        )
        self.assertIn("0.50 1.00", sortie)

    def test_somme_égale_mines_restantes(self):
        specs = [({}, 3, 1, 1), ({(1, 0): 1}, 4, 1, 2), ({(1, 0): 1, (2, 0): 1}, 5, 1, 2)]
        for numbers, w, _h, mines in specs:
            fixture = vue_fixture(numbers, width=w, height=1, mines=mines)
            sortie = node_exec(
                "const S = " + SOLVER + ";\n"
                "const a = S.analyser(@fixture:vue);\n"
                "let somme = 0;\n"
                "Object.keys(a.probabilities).forEach(k => { somme += a.probabilities[k]; });\n"
                "console.log(somme.toFixed(6));",
                {"vue": fixture},
            )
            self.assertAlmostEqual(float(sortie.strip()), mines, places=5,
                                   msg=str(numbers))

    def test_aucune_contrainte_uniforme(self):
        fixture = vue_fixture({}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(a.probabilities['1,0'].toFixed(4), a.exact);",
            {"vue": fixture},
        )
        self.assertIn("0.3333 true", sortie)


@unittest.skipUnless(NODE, "node non disponible")
class TestDéciderJS(unittest.TestCase):
    def test_premier_coup(self):
        fixture = vue_fixture({}, width=9, height=9, mines=10)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind, d.justification.indexOf('guess') >= 0);",
            {"vue": fixture},
        )
        self.assertIn("reveal true", sortie)

    def test_coup_sûr_avant_guess(self):
        # Tie-break conforme à Python (classic_solver.py:230) : à égalité de
        # voisins cachés — (2,0) et (2,1) ont chacune exactement 4 voisins
        # cachés ici — max sur (-y, -x) garde le plus petit y puis x -> (2,0).
        fixture = vue_fixture({(1, 0): 1}, flags={(0, 0)})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind, d.action.x, d.action.y,"
            "            d.justification.indexOf('R02') === 0);",
            {"vue": fixture},
        )
        self.assertIn("reveal 2 0 true", sortie)

    def test_drapeau_sur_toujours_mine(self):
        fixture = vue_fixture({(1, 0): 2}, width=3, height=1, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind);",
            {"vue": fixture},
        )
        self.assertIn("flag", sortie)

    def test_comptage_global_p0(self):
        fixture = vue_fixture({(1, 0): 1}, width=4, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.x, d.action.y,"
            "            d.justification.indexOf('R07') === 0);",
            {"vue": fixture},
        )
        self.assertIn("3 0 true", sortie)

    def test_guess_justifié(self):
        fixture = vue_fixture({(1, 0): 1}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind, d.justification.indexOf('guess') >= 0,"
            "            d.justification.indexOf('p=0.500') >= 0);",
            {"vue": fixture},
        )
        self.assertIn("reveal true true", sortie)

    def test_partie_experte_complète(self):
        # moteur + solveur JS, une partie experte entière, zéro coup illégal
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const E = " + web_js("engine.js") + ";\n"
            "const t0 = Date.now();\n"
            "const jeu = new E.Jeu(30, 16, 99, 1);\n"
            "const runner = new E.RunnerJS(jeu);\n"
            "const s = new S.SolveurClassique();\n"
            "let illégaux = 0;\n"
            "while (jeu.state === 'playing' && !runner.abandon && !runner.plein()) {\n"
            "  const d = s.décider(jeu.vue());\n"
            "  const e = runner.appliquer(d.action, d.justification);\n"
            "  if (e.result === 'illegal') illégaux++;\n"
            "}\n"
            "console.log(jeu.state, illégaux, Date.now() - t0 < 10000);"
        )
        self.assertIn("won 0 true", sortie)

    def test_déterminisme(self):
        fixture = vue_fixture({(1, 0): 1}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = new S.SolveurClassique().décider(@fixture:vue);\n"
            "const b = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(JSON.stringify(a) === JSON.stringify(b));",
            {"vue": fixture},
        )
        self.assertIn("true", sortie)


@unittest.skipUnless(NODE, "node non disponible")
class TestConformitéJS(unittest.TestCase):
    """Correctifs de conformité vs classic_solver.py (revue lot B)."""

    def test_r12_contrainte_négative_après_réduction(self):
        # (3,0)=2 + drapeau (4,0) -> contrainte {2,0}:1 -> mine (2,0) ;
        # la contrainte du 0 en (1,0) devient count -1 après réduction :
        # analyser doit lever "contrainte impossible" (comme _réduis Python).
        fixture = vue_fixture({(1, 0): 0, (3, 0): 2}, flags={(4, 0)},
                              width=5, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "try { S.analyser(@fixture:vue); console.log('pas-derreur'); }\n"
            "catch (e) { console.log(e.message); }",
            {"vue": fixture},
        )
        self.assertIn("contrainte impossible", sortie)

    def test_découper_union_pas_somme(self):
        # Deux contraintes de 6 cases partageant 3 cases : union 9, somme 12.
        # Avec tailleMax=10, l'union garde un seul cluster (comme _clusters).
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c1 = {cells: new Set(['0,0','1,0','2,0','3,0','4,0','5,0']),"
            " count: 3};\n"
            "const c2 = {cells: new Set(['3,0','4,0','5,0','6,0','7,0','8,0']),"
            " count: 3};\n"
            "console.log(S.découper([c1, c2], 10).length);"
        )
        self.assertIn("1", sortie)

    def test_tri_numérique_sorties(self):
        # "10,0" doit venir après "2,0" ; ordre (x,y) comme sorted() Python.
        fixture = vue_fixture({(3, 0): 1, (5, 0): 1, (7, 0): 1, (9, 0): 1},
                              width=11, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(JSON.stringify(a.components[0].cells),"
            "            JSON.stringify(a.constraints[0].cells));",
            {"vue": fixture},
        )
        self.assertIn("[[2,0],[4,0],[6,0],[8,0],[10,0]]", sortie)
        self.assertIn("[[2,0],[4,0]]", sortie)
        # cas 2D : ordre (x,y) comme sorted() Python — (0,2) avant (1,0)
        fixture2 = vue_fixture({(1, 1): 1}, width=3, height=3, mines=1)
        sortie2 = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(JSON.stringify(a.components[0].cells));",
            {"vue": fixture2},
        )
        self.assertIn("[[0,0],[0,1],[0,2],[1,0],[1,2],[2,0],[2,1],[2,2]]",
                      sortie2)

    def test_exact_false_sans_case_cachée(self):
        # Python (classic_solver.py:141-142) : probabilités vides -> exact=False.
        fixture = vue_fixture({(0, 0): 0}, width=1, height=1, mines=0)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(a.exact, Object.keys(a.probabilities).length);",
            {"vue": fixture},
        )
        self.assertIn("false 0", sortie)


@unittest.skipUnless(NODE, "node non disponible")
class TestRevueQualitéJS(unittest.TestCase):
    """Passe qualité finale lot B : précalculs réutilisés, e2e R17 et R12."""

    def test_analyser_réutilise_précalculs(self):
        # analyser(vue, contraintes, déduction) doit consommer la déduction
        # passée (comme analyze_from Python) au lieu de recalculer.
        fixture = vue_fixture({(1, 0): 1}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = S.extraireContraintes(@fixture:vue);\n"
            "const a = S.analyser(@fixture:vue, c,"
            "                    {safe: {'9,9': 'TEST: sûr'}, mines: {}});\n"
            "console.log(a.safe['9,9'] || 'absent');",
            {"vue": fixture},
        )
        self.assertIn("TEST: sûr", sortie)

    def test_analyser_précalculs_cohérents(self):
        # Précalculs passés = même résultat que le calcul interne.
        fixture = vue_fixture({(1, 0): 1}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = S.extraireContraintes(@fixture:vue);\n"
            "const a1 = S.analyser(@fixture:vue);\n"
            "const a2 = S.analyser(@fixture:vue, c, S.déduire(c));\n"
            "console.log(JSON.stringify(a1) === JSON.stringify(a2));",
            {"vue": fixture},
        )
        self.assertIn("true", sortie)

    def test_r17_repli_bout_en_bout(self):
        # Frontière alternée 1-2 (comme test_regressions.grande_vue) :
        # composante > 30 cases -> repli R17, analyse non exacte,
        # probabilités uniformes, justification R17.
        numbers = {(x, 0): (1 if x % 2 == 0 else 2) for x in range(1, 39)}
        fixture = vue_fixture(numbers, width=40, height=2, mines=30)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "let uniforme = true, p0 = a.probabilities['0,1'];\n"
            "Object.keys(a.probabilities).forEach(function (k) {\n"
            "  if (Math.abs(a.probabilities[k] - p0) > 1e-12) uniforme = false;\n"
            "});\n"
            "console.log(a.exact, uniforme,"
            "            d.justification.indexOf('R17') >= 0);",
            {"vue": fixture},
        )
        self.assertIn("false true true", sortie)

    def test_r17_guess_uniforme_bout_en_bout(self):
        # Frontière tout-à-1 : le repli R17 ne classe rien -> guess uniforme.
        numbers = {(x, 0): 1 for x in range(1, 39)}
        fixture = vue_fixture(numbers, width=40, height=2, mines=30)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind,"
            "            d.justification.indexOf('R17: guess uniforme') === 0);",
            {"vue": fixture},
        )
        self.assertIn("reveal true", sortie)

    def test_r12_giveup_via_décider(self):
        # Triangle {a,b}:1 {b,c}:1 {c,a}:1 : les règles ne déduisent rien,
        # le CSP est insatisfiable -> giveup R12 (fail-fast).
        fixture = vue_fixture({(0, 0): 2, (2, 0): 2, (1, 2): 4},
                              flags={(1, 1), (0, 2), (2, 2)},
                              width=3, height=3, mines=3)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const r = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(Object.keys(r.safe).length +"
            "                Object.keys(r.mines).length, d.action.kind,"
            "            d.action.reason.indexOf('configuration impossible') >= 0,"
            "            d.justification.indexOf('R12: configuration impossible')"
            "                === 0);",
            {"vue": fixture},
        )
        self.assertIn("0 giveup true true", sortie)


if __name__ == "__main__":
    unittest.main()
