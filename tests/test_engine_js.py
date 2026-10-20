"""Tests node du moteur JS (port de game.py/board.py) : A04-A06, vue A15."""

import json
import unittest

from tests.js_harness import NODE, node_exec, web_js

ENGINE = web_js("engine.js")


@unittest.skipUnless(NODE, "node non disponible")
class TestMoteurJS(unittest.TestCase):
    def script(self, corps):
        return "const E = " + ENGINE + ";\n" + corps

    def test_dimensions_et_vue(self):
        sortie = node_exec(self.script(
            "const jeu = new E.Jeu(5, 5, 3, 4);\n"
            "const vue = jeu.vue();\n"
            "console.log(JSON.stringify({w: vue.width, h: vue.height,"
            "m: vue.mines_count, state: vue.state, kind: vue.kind,"
            "cell00: vue.grid[0][0].state}));"
        ))
        d = json.loads(sortie)
        self.assertEqual((d["w"], d["h"], d["m"]), (5, 5, 3))
        self.assertEqual(d["state"], "playing")
        self.assertEqual(d["kind"], "view")
        self.assertEqual(d["cell00"], "hidden")

    def test_premier_coup_toujours_sur(self):
        sortie = node_exec(self.script(
            "let ok = true;\n"
            "for (let seed = 0; seed < 20; seed++) {\n"
            "  const jeu = new E.Jeu(6, 6, 4, seed);\n"
            "  jeu.révéler(2, 2);\n"
            "  const zone = [[2,2],[1,1],[2,1],[3,1],[1,2],[3,2],[1,3],[2,3],[3,3]];\n"
            "  zone.forEach(p => { if (jeu.estMine(p[0], p[1])) ok = false; });\n"
            "}\n"
            "console.log(ok);"
        ))
        self.assertIn("true", sortie)

    def test_determinisme_seed(self):
        sortie = node_exec(self.script(
            "const a = new E.Jeu(9, 9, 10, 7);\n"
            "const b = new E.Jeu(9, 9, 10, 7);\n"
            "a.révéler(0, 0); b.révéler(0, 0);\n"
            "const pa = a.positionsMines().map(m => m.join(',')).sort().join(';');\n"
            "const pb = b.positionsMines().map(m => m.join(',')).sort().join(';');\n"
            "console.log(pa === pb);"
        ))
        self.assertIn("true", sortie)

    def test_placement_impossible(self):
        sortie = node_exec(self.script(
            "const jeu = new E.Jeu(3, 3, 8, 0);\n"
            "try { jeu.révéler(0, 0); console.log('pas-derreur'); }\n"
            "catch (e) { console.log('erreur: ' + (e.message.indexOf('impossible') >= 0)); }"
        ))
        self.assertIn("erreur: true", sortie)

    def test_vue_sans_fuite(self):
        sortie = node_exec(self.script(
            "const jeu = new E.Jeu(5, 5, 3, 4);\n"
            "jeu.révéler(0, 0);\n"
            "console.log(JSON.stringify(jeu.vue()).indexOf('is_mine') === -1);"
        ))
        self.assertIn("true", sortie)


if __name__ == "__main__":
    unittest.main()
