"""Tests de l'export statique du site (mode Netlify) : API pré-générée en JSON.

Le site déployé doit fonctionner sans backend : replay, benchmarks et analyses
sont servis comme fichiers statiques ; live/duel tournent en navigateur via le
port JavaScript (web/engine.js, web/solver.js, web/interactif.js).
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(RACINE, "scripts", "export_site.py")


def exporter(vers: str) -> None:
    retour = subprocess.run(
        [sys.executable, SCRIPT, "--out", vers],
        capture_output=True, text=True, timeout=120, cwd=RACINE,
        env={**os.environ, "PYTHONPATH": os.path.join(RACINE, "src")},
    )
    if retour.returncode != 0:
        raise RuntimeError(f"export échoué: {retour.stderr}")


class TestExportStatique(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = tempfile.mkdtemp(prefix="site-")
        exporter(cls.dossier)

    def _json(self, chemin):
        with open(os.path.join(self.dossier, chemin), encoding="utf-8") as f:
            return json.load(f)

    def test_assets_web_copiés(self):
        for fichier in ("index.html", "style.css", "app.js",
                        "engine.js", "solver.js", "interactif.js"):
            chemin = os.path.join(self.dossier, fichier)
            self.assertTrue(os.path.isfile(chemin), f"{fichier} manquant")
            self.assertGreater(os.path.getsize(chemin), 100)

    def test_api_solvers(self):
        data = self._json("api/solvers.json")
        self.assertIn("classic", data["solvers"])

    def test_api_games_liste(self):
        data = self._json("api/games.json")
        ids = [g["id"] for g in data["games"]]
        self.assertIn("classic-seed42", ids)
        self.assertIn("rule-seed7", ids)
        for jeu in data["games"]:
            self.assertIn("seed", jeu)
            self.assertIn("solver", jeu)

    def test_api_game_detail(self):
        data = self._json("api/games/classic-seed42.json")
        self.assertEqual(data["header"]["id"], "classic-seed42")
        self.assertGreater(len(data["events"]), 5)
        self.assertIn(data["result"]["state"], ("won", "lost"))
        # les événements enchaînent les vues (B10)
        self.assertEqual(data["events"][1]["view_before"],
                         data["events"][0]["view_after"])

    def test_api_analyses_par_coup(self):
        # une analyse par coup, pré-calculée par le solveur Python (W08/W09)
        détail = self._json("api/games/classic-seed42.json")
        analyses = self._json("api/games/classic-seed42/analysis.json")
        self.assertEqual(analyses["kind"], "analysis")
        self.assertEqual(len(analyses["moves"]), len(détail["events"]))
        for coup in analyses["moves"]:
            self.assertIn("probabilities", coup)
            self.assertIn("constraints", coup)
            self.assertIn("safe", coup)
            self.assertIn("mines", coup)

    def test_api_benchmarks(self):
        data = self._json("api/benchmarks.json")
        difficultés = [b["difficulty"] for b in data["benchmarks"]]
        self.assertIn("beginner", difficultés)
        self.assertIn("expert", difficultés)

    def test_analyse_cohérente_avec_api_locale(self):
        # la première analyse du fichier statique = analyse du serveur local
        from demineur.artifacts import load_game
        from demineur.solvers.classic import analyze
        from demineur.view import view_from_json

        header, events, _ = load_game(
            os.path.join(RACINE, "games", "classic-seed42.jsonl"))
        attendu = analyze(view_from_json(events[0]["view_before"]))
        analyses = self._json("api/games/classic-seed42/analysis.json")
        coup = analyses["moves"][0]
        self.assertEqual(coup["probabilities"],
                         {f"{x},{y}": p for (x, y), p in attendu.probabilities.items()})


class TestSiteStatiqueServi(unittest.TestCase):
    """Le site exporté doit répondre tel quel, sans backend (conditions Netlify)."""

    @classmethod
    def setUpClass(cls):
        cls.dossier = tempfile.mkdtemp(prefix="site-serve-")
        exporter(cls.dossier)
        import http.server

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=cls.dossier, **kwargs)

            def log_message(self, *args):
                pass

        cls.serveur = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.serveur.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.serveur.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()
        cls.serveur.server_close()
        cls.thread.join(timeout=2)

    def _get(self, url):
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, json.loads(r.read().decode())

    def test_fonctionne_sans_backend(self):
        base = f"http://127.0.0.1:{self.port}"
        code, data = self._get(f"{base}/api/games.json")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(data["games"]), 3)
        code, data = self._get(f"{base}/api/benchmarks.json")
        self.assertEqual(code, 200)
        code, data = self._get(f"{base}/api/games/classic-seed42/analysis.json")
        self.assertEqual(code, 200)


if __name__ == "__main__":
    unittest.main()
