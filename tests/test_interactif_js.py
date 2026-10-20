"""Tests node des contrôleurs interactifs JS — payloads identiques à l'API."""

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
            "console.log(p.state, p.view.kind, p.moves > 0,"
            "            p.event !== null, p.event.justification !== null,"
            "            (p.mines || []).length >= 2);"
        )
        self.assertIn("true true true", sortie)

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
            "console.log('coup1:', p0.human_state, p0.solver_state,"
            "            p0.human_mines === undefined);\n"
            "const mine = duel.humain.positionsMines()[0];\n"
            "const p1 = duel.coupHumain({kind: 'reveal', x: mine[0], y: mine[1]});\n"
            "console.log('fin:', p1.human_state, p1.solver_state,"
            "            Array.isArray(p1.human_mines));"
        )
        self.assertIn("coup1: playing playing true", sortie)
        self.assertIn("fin: lost", sortie)

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
            "console.log(Array.isArray(p.human_mines),"
            "            p.solver_state !== 'playing' ?"
            "              Array.isArray(p.solver_mines) : true);"
        )
        self.assertIn("true true", sortie)


if __name__ == "__main__":
    unittest.main()
