"""Tests frontend (W15) : rendu de grille depuis un JSON de fixture, sans DOM.

Exécute les fonctions pures de ``web/app.js`` sous Node si disponible ;
le test est sinon sauté (aucune dépendance obligatoire ajoutée).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from demineur.game import Game

NODE = shutil.which("node") if shutil.which else None
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(RACINE, "web", "app.js")


def _vue_fixture() -> dict:
    jeu = Game(width=5, height=5, mines_count=3, seed=4)
    jeu.reveal(0, 0)
    jeu.flag(4, 4)
    return jeu.view().to_json()


def _node_exec(script: str, fichiers: dict) -> str:
    with tempfile.TemporaryDirectory() as d:
        for nom, contenu in fichiers.items():
            chemin = f"{d}/{nom}"
            with open(chemin, "w", encoding="utf-8") as f:
                f.write(contenu)
        cmd = ["node", "-e", script.replace("@fixture@", f"{d}/fixture.json")]
        retour = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                cwd=d)
        if retour.returncode != 0:
            raise RuntimeError(f"node a échoué: {retour.stderr}")
        return retour.stdout


@unittest.skipUnless(NODE, "node non disponible")
class TestRenduGrille(unittest.TestCase):
    """W05 : rendu de la grille depuis un JSON de fixture (format A15)."""

    def test_grille_complete(self):
        vue = _vue_fixture()
        script = (
            "const app = require(" + json.dumps(APP_JS) + ");"
            "const fs = require('fs');"
            "const vue = JSON.parse(fs.readFileSync('@fixture@', 'utf8'));"
            "console.log(app.gridHtml(vue));"
        )
        html = _node_exec(script, {"fixture.json": json.dumps(vue)})
        # nombre correct de cases
        self.assertEqual(html.count('class="case'), vue["width"] * vue["height"])
        # le drapeau est rendu
        self.assertIn("drapeau", html)
        self.assertIn(">F<", html)
        # une case révélée porte son compteur
        self.assertRegex(html, r'n\d?"')
        # coordonnées data-x/data-y présentes pour le mode interactif (W14)
        self.assertIn('data-x="0" data-y="0"', html)

    def test_etats_distincts(self):
        vue = _vue_fixture()
        script = (
            "const app = require(" + json.dumps(APP_JS) + ");"
            "const fs = require('fs');"
            "const vue = JSON.parse(fs.readFileSync('@fixture@', 'utf8'));"
            "const html = app.gridHtml(vue);"
            "console.log(JSON.stringify({"
            "cache: html.includes('cachée'), "
            "revelee: html.includes('révélée'), "
            "drapeau: html.includes('drapeau')}));"
        )
        données = json.loads(_node_exec(script, {"fixture.json": json.dumps(vue)}))
        self.assertTrue(données["cache"])
        self.assertTrue(données["revelee"])
        self.assertTrue(données["drapeau"])


@unittest.skipUnless(NODE, "node non disponible")
class TestFonctionsPures(unittest.TestCase):
    def test_event_summary(self):
        event = {"move": 3, "action": {"kind": "reveal", "x": 2, "y": 3},
                 "justification": "R02: → (2,3) sûr", "result": "ok"}
        script = (
            "const app = require(" + json.dumps(APP_JS) + ");"
            "console.log(app.eventSummary(" + json.dumps(event) + "));"
        )
        sortie = _node_exec(script, {})
        self.assertIn("#003", sortie)
        self.assertIn("R02", sortie)

    def test_benchmark_table(self):
        results = {"classic": {"win_rate": 0.9, "wins": 9, "losses": 1,
                               "gave_ups": 0, "avg_moves": 20},
                   "random": {"win_rate": 0.0, "wins": 0, "losses": 10,
                              "gave_ups": 0, "avg_moves": 3}}
        script = (
            "const app = require(" + json.dumps(APP_JS) + ");"
            "console.log(app.benchmarkTable(" + json.dumps(results) + "));"
        )
        sortie = _node_exec(script, {})
        self.assertIn("classic", sortie)
        self.assertIn("90.0%", sortie)
        # tri par win-rate décroissant
        self.assertLess(sortie.index("classic"), sortie.index("random"))

    def test_benchmarks_sections_par_difficulte(self):
        data = {"kind": "benchmarks", "benchmarks": [
            {"difficulty": "beginner", "seeds": 30,
             "grid": {"width": 9, "height": 9, "mines": 10},
             "results": {"classic": {"win_rate": 0.967, "wins": 29, "losses": 1,
                                     "gave_ups": 0, "avg_moves": 20}}},
            {"difficulty": "expert", "seeds": 20,
             "grid": {"width": 30, "height": 16, "mines": 99},
             "results": {"classic": {"win_rate": 0.45, "wins": 9, "losses": 11,
                                     "gave_ups": 0, "avg_moves": 240}}},
        ]}
        script = (
            "const app = require(" + json.dumps(APP_JS) + ");"
            "const html = app.benchmarksSections(" + json.dumps(data) + ");"
            "console.log(JSON.stringify({"
            "beginner: html.includes('<h3>beginner'), "
            "expert: html.includes('<h3>expert'), "
            "tables: (html.match(/<table>/g) || []).length, "
            "svgs: (html.match(/<svg/g) || []).length, "
            "pct: html.includes('96.7%') && html.includes('45.0%')}));"
        )
        données = json.loads(_node_exec(script, {}))
        self.assertTrue(données["beginner"])
        self.assertTrue(données["expert"])
        self.assertEqual(données["tables"], 2)
        self.assertEqual(données["svgs"], 2)
        self.assertTrue(données["pct"])

    def test_benchmarks_sections_vide(self):
        script = (
            "const app = require(" + json.dumps(APP_JS) + ");"
            "console.log(app.benchmarksSections({benchmarks: []}).includes('Aucun'));"
        )
        self.assertIn("true", _node_exec(script, {}))

    def test_heat_opacity_borne(self):
        script = (
            "const app = require(" + json.dumps(APP_JS) + ");"
            "console.log(app.heatOpacity(0) + ' ' + app.heatOpacity(1) + ' ' + app.heatOpacity(2));"
        )
        sortie = _node_exec(script, {}).split()
        self.assertAlmostEqual(float(sortie[0]), 0.05, places=6)
        self.assertAlmostEqual(float(sortie[1]), 0.8, places=6)
        self.assertAlmostEqual(float(sortie[2]), 0.8, places=6)


class TestAssetsLocaux(unittest.TestCase):
    """W19 : le site fonctionne hors ligne, aucune ressource chargée à distance.

    Exception : le lien de navigation vers le repo GitHub (pied de page)
    — un clic, pas un chargement de ressource.
    """

    def test_aucune_ressource_distante(self):
        motifs = ['src="http', "src='http", 'fetch("http', "fetch('http",
                  "url(http"]
        for fichier in ("index.html", "style.css", "app.js"):
            with open(f"{RACINE}/web/{fichier}", encoding="utf-8") as f:
                contenu = f.read()
            for motif in motifs:
                self.assertNotIn(motif, contenu, f"{fichier} charge du distant")
            # tout lien http(s) est limité au repo GitHub du projet
            for lien in __import__("re").findall(r'href="https?://[^"]+"', contenu):
                self.assertIn("github.com/max-boop345", lien,
                              f"{fichier}: lien externe non autorisé: {lien}")

    def test_pied_de_page_auteurs_et_repo(self):
        with open(f"{RACINE}/web/index.html", encoding="utf-8") as f:
            contenu = f.read()
        self.assertIn("https://github.com/max-boop345/conquering_ai_enpc", contenu)
        self.assertIn("Maxime Novo Frelicot", contenu)
        self.assertIn("Joris Saint-Genes", contenu)

    def test_fichiers_present(self):
        for fichier in ("index.html", "style.css", "app.js"):
            self.assertTrue(__import__("os").path.isfile(f"{RACINE}/web/{fichier}"))


if __name__ == "__main__":
    unittest.main()
