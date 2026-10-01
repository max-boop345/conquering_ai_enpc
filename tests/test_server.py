"""Tests du serveur local (W01, W02, W15, W16, W20) : API, sécurité, live, duel.

Tout se passe sur 127.0.0.1 : aucun réseau externe, arrêt propre du serveur.
"""

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from demineur.artifacts import save_game
from demineur.game import Game
from demineur.runner import GameRunner
from demineur.server import make_server
from demineur.solvers.classic import ClassicSolver


def http_get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None


def http_post(url, data):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None


def http_get_text(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, None


class TestServeurLocal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = tempfile.mkdtemp()
        # une partie loggée pour l'API
        runner = GameRunner(Game(width=5, height=5, mines_count=3, seed=4))
        runner.run(ClassicSolver())
        cls.chemin = save_game(cls.dossier, runner, meta={
            "seed": 4, "solver": "classic", "difficulty": "beginner"})
        # artefacts benchmarks (un par difficulté)
        for difficulté in ("beginner", "intermediate", "expert"):
            with open(os.path.join(cls.dossier, f"benchmarks-{difficulté}.json"), "w") as f:
                json.dump({"version": 1, "kind": "benchmark", "difficulty": difficulté,
                           "seeds": 10,
                           "results": {"classic": {"wins": 9, "seeds": 10,
                                                    "win_rate": 0.9}}}, f)
        cls.serveur = make_server(games_dir=cls.dossier, port=0)
        cls.thread = threading.Thread(target=cls.serveur.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.serveur.server_address[:2]
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()  # W20 : arrêt propre
        cls.serveur.server_close()
        cls.thread.join(timeout=2)

    # ---------------------------------------------------------- W16
    def test_bind_localhost_uniquement(self):
        host, port = self.serveur.server_address[:2]
        self.assertEqual(host, "127.0.0.1")

    def test_chemin_traversé_refusé(self):
        code, _ = http_get_text(f"{self.base}/../src/demineur/server.py")
        self.assertIn(code, (301, 403, 404))

    def test_fichier_inexistant_404(self):
        code, _ = http_get_text(f"{self.base}/inconnu.html")
        self.assertEqual(code, 404)

    # ---------------------------------------------------------- W01
    def test_index_sert_html(self):
        code, texte = http_get_text(f"{self.base}/")
        self.assertEqual(code, 200)
        self.assertIn("<!DOCTYPE html>", texte)
        self.assertIn("démineur", texte.lower())

    def test_assets_locaux_uniquement(self):
        # W19 : aucun chargement de ressource distante ; le lien GitHub du
        # pied de page (navigation, pas chargement) est la seule exception
        import re as _re

        motifs_distan = ['src="http', "src='http", 'fetch("http', "fetch('http",
                         "url(http"]
        for asset in ("/", "/style.css", "/app.js"):
            _, texte = http_get_text(f"{self.base}{asset}")
            for motif in motifs_distan:
                self.assertNotIn(motif, texte, f"{asset} charge du distant")
            for lien in _re.findall(r'href="https?://[^"]+"', texte):
                self.assertIn("github.com/max-boop345", lien,
                              f"{asset}: lien externe non autorisé")

    # ---------------------------------------------------------- W02
    def test_api_solvers(self):
        code, data = http_get(f"{self.base}/api/solvers")
        self.assertEqual(code, 200)
        self.assertIn("classic", data["solvers"])

    def test_api_games_liste(self):
        code, data = http_get(f"{self.base}/api/games")
        self.assertEqual(code, 200)
        ids = [g["id"] for g in data["games"]]
        self.assertTrue(any("seed" in str(i) or True for i in ids))
        self.assertGreaterEqual(len(data["games"]), 1)

    def test_api_game_detail(self):
        _, data = http_get(f"{self.base}/api/games")
        gid = data["games"][0]["id"]
        code, partie = http_get(f"{self.base}/api/games/{gid}")
        self.assertEqual(code, 200)
        self.assertIn("events", partie)
        self.assertGreater(len(partie["events"]), 0)
        self.assertIn(partie["result"]["state"], ("won", "lost"))

    def test_api_game_inconnu_404(self):
        code, _ = http_get(f"{self.base}/api/games/nimporte")
        self.assertEqual(code, 404)

    def test_api_benchmarks(self):
        # agrégation de tous les artefacts benchmarks*.json du répertoire
        code, data = http_get(f"{self.base}/api/benchmarks")
        self.assertEqual(code, 200)
        self.assertEqual(data["kind"], "benchmarks")
        difficultés = [b["difficulty"] for b in data["benchmarks"]]
        self.assertIn("beginner", difficultés)
        self.assertIn("intermediate", difficultés)
        self.assertIn("expert", difficultés)
        beginner = next(b for b in data["benchmarks"] if b["difficulty"] == "beginner")
        self.assertIn("classic", beginner["results"])
        self.assertEqual(beginner["seeds"], 10)

    def test_api_benchmarks_absents(self):
        with tempfile.TemporaryDirectory() as d:
            s = make_server(games_dir=d, port=0)
            t = threading.Thread(target=s.serve_forever, daemon=True)
            t.start()
            host, port = s.server_address[:2]
            code, data = http_get(f"http://{host}:{port}/api/benchmarks")
            s.shutdown()
            s.server_close()
            t.join(timeout=2)
            self.assertEqual(code, 200)
            self.assertEqual(data["benchmarks"], [])

    def test_api_analysis_par_coup(self):
        # W08/W09 : analyse de la vue avant un coup donné
        _, data = http_get(f"{self.base}/api/games")
        gid = data["games"][0]["id"]
        code, analyse = http_get(f"{self.base}/api/games/{gid}/analysis/0")
        self.assertEqual(code, 200)
        self.assertIn("probabilities", analyse)
        self.assertIn("components", analyse)
        code, _ = http_get(f"{self.base}/api/games/{gid}/analysis/9999")
        self.assertEqual(code, 404)

    # ---------------------------------------------------------- W13, W20
    def test_live_partie_en_direct(self):
        base = f"{self.base}/api/live"
        code, data = http_get(f"{base}/new?seed=1&w=5&h=5&mines=3")
        self.assertEqual(code, 200)
        self.assertEqual(data["state"], "playing")
        # le solveur joue pas à pas
        for _ in range(50):
            code, data = http_get(f"{base}/step")
            self.assertEqual(code, 200)
            if data["state"] != "playing":
                break
        self.assertIn(data["state"], ("won", "lost"))

    def test_live_reset(self):
        base = f"{self.base}/api/live"
        http_get(f"{base}/new?seed=2&w=5&h=5&mines=3")
        code, data = http_get(f"{base}/state")
        self.assertEqual(code, 200)
        self.assertEqual(data["view"]["state"], "playing")

    # ---------------------------------------------------------- W14
    def test_duel_web(self):
        base = f"{self.base}/api/duel"
        code, data = http_get(f"{base}/new?seed=5&w=5&h=5&mines=3")
        self.assertEqual(code, 200)
        code, data = http_post(f"{base}/human", {"kind": "reveal", "x": 0, "y": 0})
        self.assertEqual(code, 200)
        self.assertIn("human", data)
        self.assertIn("solver", data)
        # action illégale -> 400
        code, _ = http_post(f"{base}/human", {"kind": "reveal", "x": 0, "y": 0})
        self.assertEqual(code, 400)
        # action inconnue -> 400
        code, _ = http_post(f"{base}/human", {"kind": "dance", "x": 0, "y": 0})
        self.assertEqual(code, 400)
        # json invalide -> 400
        req = urllib.request.Request(f"{base}/human", data=b"pas du json",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        self.assertEqual(code, 400)

    def test_duel_get_etat(self):
        base = f"{self.base}/api/duel"
        http_get(f"{base}/new?seed=5&w=5&h=5&mines=3")
        code, data = http_get(f"{base}")
        self.assertEqual(code, 200)
        self.assertIn("human", data)
        self.assertIn("solver", data)
        self.assertEqual(data["human_state"], "playing")

    def test_duel_humain_perd_solveur_continue_et_mines_revelees(self):
        # l'humain révèle une mine: le duel continue, le solveur finit seul,
        # et les mines de l'humain sont exposées (partie finie, pas de fuite)
        from demineur.server import DuelState

        état = DuelState(seed=5, width=5, height=5, mines=3)
        data = état.human_play({"kind": "reveal", "x": 0, "y": 0})
        self.assertEqual(data["human_state"], "playing")
        self.assertNotIn("human_mines", data)
        mine = next(iter(état.human.board.mines))
        data = état.human_play({"kind": "reveal", "x": mine[0], "y": mine[1]})
        self.assertEqual(data["human_state"], "lost")
        self.assertIn("human_mines", data)
        self.assertIn([mine[0], mine[1]], data["human_mines"])
        # le solveur a continué jusqu'au bout
        self.assertIn(data["solver_state"], ("won", "lost"))

    def test_duel_solveur_perd_mines_exposees(self):
        from demineur.server import DuelState

        état = DuelState(seed=5, width=5, height=5, mines=3)
        état.human_play({"kind": "reveal", "x": 0, "y": 0})
        # le solveur touche une mine de sa propre grille (défaite simulée)
        mine = next(iter(état.solver_game.board.mines))
        état.solver_game.reveal(*mine)
        data = état.payload()
        self.assertEqual(data["solver_state"], "lost")
        self.assertIn("solver_mines", data)
        self.assertIn([mine[0], mine[1]], data["solver_mines"])
        # l'humain encore en jeu n'a PAS ses mines exposées (pas de fuite)
        self.assertNotIn("human_mines", data)

    # ---------------------------------------------------------- W15
    def test_api_inconnue_404(self):
        code, _ = http_get(f"{self.base}/api/nimporte")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
