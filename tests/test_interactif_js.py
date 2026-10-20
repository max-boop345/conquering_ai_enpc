"""Tests node des contrôleurs interactifs JS — payloads au format de l'API Python."""

import json
import unittest

from tests.js_harness import NODE, node_exec, web_js

INTERACTIF = web_js("interactif.js")


@unittest.skipUnless(NODE, "node non disponible")
class TestLiveJS(unittest.TestCase):
    def test_partie_complete(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const live = new I.LiveJS(1, 5, 5, 3);\n"
            "for (let i = 0; i < 60; i++) {\n"
            "  live.étape();\n"
            "  if (live.payload().state !== 'playing') break;\n"
            "}\n"
            "const p = live.payload();\n"
            "console.log(JSON.stringify({state: p.state, kind: p.view.kind,"
            "            moves: p.moves, aUnEvenement: p.event !== null,"
            "            justification: p.event && p.event.justification !== null,"
            "            nbMines: (p.mines || []).length}));"
        )
        d = json.loads(sortie)
        self.assertIn(d["state"], ("won", "lost"))
        self.assertEqual(d["kind"], "view")
        self.assertGreater(d["moves"], 0)
        self.assertIs(d["aUnEvenement"], True)
        self.assertIs(d["justification"], True)
        self.assertGreaterEqual(d["nbMines"], 2)

    def test_payload_initial(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const p = new I.LiveJS(1, 5, 5, 3).payload();\n"
            "console.log(p.state, p.moves, p.view.width, p.event === null);"
        )
        self.assertIn("playing 0 5 true", sortie)


@unittest.skipUnless(NODE, "node non disponible")
class TestDuelJS(unittest.TestCase):
    def test_humain_perd_solveur_continue(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const duel = new I.DuelJS(5, 5, 5, 3);\n"
            "const p0 = duel.coupHumain({kind: 'reveal', x: 0, y: 0});\n"
            "const mine = duel.humain.positionsMines()[0];\n"
            "const p1 = duel.coupHumain({kind: 'reveal', x: mine[0], y: mine[1]});\n"
            "console.log(JSON.stringify({"
            "  p0: {human_state: p0.human_state, solver_state: p0.solver_state,"
            "       human_mines_absentes: p0.human_mines === undefined},"
            "  p1: {human_state: p1.human_state, solver_state: p1.solver_state,"
            "       human_mines: p1.human_mines}"
            "}));"
        )
        d = json.loads(sortie)
        p0, p1 = d["p0"], d["p1"]
        self.assertEqual(p0["human_state"], "playing")
        self.assertEqual(p0["solver_state"], "playing")
        self.assertIs(p0["human_mines_absentes"], True)
        self.assertEqual(p1["human_state"], "lost")
        self.assertNotEqual(p1["solver_state"], "playing")
        self.assertIsInstance(p1["human_mines"], list)
        self.assertGreaterEqual(len(p1["human_mines"]), 2)

    def test_coup_illégal_rejeté(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const duel = new I.DuelJS(5, 5, 5, 3);\n"
            "duel.coupHumain({kind: 'reveal', x: 0, y: 0});\n"
            "try { duel.coupHumain({kind: 'reveal', x: 0, y: 0});\n"
            "     console.log('pas-derreur'); }\n"
            "catch (e) { console.log('erreur: ' + (e.message.length > 0)); }"
        )
        self.assertIn("erreur: true", sortie)

    def test_mines_exposées_aux_deux_camps_finis(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const duel = new I.DuelJS(5, 5, 5, 3);\n"
            "duel.coupHumain({kind: 'reveal', x: 0, y: 0});\n"
            "const mine = duel.humain.positionsMines()[0];\n"
            "const p = duel.coupHumain({kind: 'reveal', x: mine[0], y: mine[1]});\n"
            "console.log(JSON.stringify({human_mines: p.human_mines,"
            "            solver_state: p.solver_state,"
            "            solver_mines: p.solver_mines}));"
        )
        d = json.loads(sortie)
        self.assertIsInstance(d["human_mines"], list)
        self.assertNotEqual(d["solver_state"], "playing")
        self.assertIsInstance(d["solver_mines"], list)


if __name__ == "__main__":
    unittest.main()
