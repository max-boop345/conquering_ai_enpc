"""Serveur web local (W01, W02, W13, W14, W16, W17).

- écoute sur 127.0.0.1 uniquement (W16, INV5) — jamais 0.0.0.0 ;
- sert les fichiers statiques de ``web/`` (W04) sans échapper au répertoire ;
- API JSON locale (W02) alimentée par les artefacts (JSONL B10, benchmarks R14) ;
- mode live (W13) et mode duel (W14) en mémoire, polling local uniquement.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from demineur.artifacts import list_games, load_game
from demineur.game import Game, GameState
from demineur.runner import GameRunner
from demineur.solvers.classic import ClassicSolver
from demineur.view import view_from_json

_HOST = "127.0.0.1"  # W16 : localhost uniquement, non configurable (INV5)
_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


class LiveState:
    """Une partie en direct pilotée par le solveur classique (W13).

    Une fois terminée, la partie est archivée dans ``games_dir`` (si fourni)
    et apparaît dans l'onglet Replay du site.
    """

    def __init__(self, seed, width, height, mines, games_dir: str | None = None):
        self.game = Game(width, height, mines, seed=seed)
        self.runner = GameRunner(self.game)
        self.solver = ClassicSolver()
        self.seed = seed
        self.games_dir = games_dir
        self.last_event = None
        self._sauvegardée = False

    def _archive(self) -> None:
        if self.games_dir is None or self._sauvegardée:
            return
        self._sauvegardée = True
        from demineur.artifacts import save_game
        save_game(self.games_dir, self.runner, meta={
            "id": f"live-seed{self.seed}", "seed": self.seed,
            "solver": "classic", "origin": "live",
        })
        print(f"[live seed={self.seed}] partie archivée dans {self.games_dir}",
              flush=True)

    def step(self):
        """Le solveur joue un coup ; retourne le dernier événement."""
        if self.game.state is not GameState.PLAYING or self.runner.gave_up:
            self._archive()
            return self.last_event
        vue = self.game.view()
        action = self.solver.decide(vue)
        event = self.runner.apply(action, self.solver.last_justification)
        self.last_event = event
        if self.game.state is not GameState.PLAYING or self.runner.gave_up:
            self._archive()
        return event


class DuelState:
    """Humain vs solveur sur la même grille seedée (W14).

    Chaque camp est enregistré séparément (événements B10) ; à la fin de sa
    partie, chaque camp est archivé dans ``games_dir`` (onglet Replay).
    """

    def __init__(self, seed, width, height, mines, games_dir: str | None = None):
        self.human = Game(width, height, mines, seed=seed)
        self.solver_game = Game(width, height, mines, seed=seed)
        self.solver = ClassicSolver()
        self.seed = seed
        self.games_dir = games_dir
        self.human_runner = GameRunner(self.human)
        self.solver_runner = GameRunner(self.solver_game)
        self._sauvés = set()

    def _archive(self, camp: str) -> None:
        if self.games_dir is None or camp in self._sauvés:
            return
        self._sauvés.add(camp)
        from demineur.artifacts import save_events
        jeu = self.human if camp == "humain" else self.solver_game
        runner = self.human_runner if camp == "humain" else self.solver_runner
        save_events(self.games_dir, jeu, list(runner.events), meta={
            "id": f"duel-seed{self.seed}-{camp}", "seed": self.seed,
            "solver": "humain" if camp == "humain" else "classic",
            "origin": f"duel-{camp}",
        })
        print(f"[duel seed={self.seed}] partie {camp} archivée", flush=True)

    def payload(self) -> dict:
        """État complet du duel ; les mines ne sont exposées que pour les
        grilles terminées (perdues) — jamais pour une partie en cours (INV1)."""
        data = {
            "human": self.human.view().to_json(),
            "solver": self.solver_game.view().to_json(),
            "human_state": self.human.state.value,
            "solver_state": self.solver_game.state.value,
        }
        if self.human.state is GameState.LOST and self.human.board is not None:
            data["human_mines"] = [list(m) for m in sorted(self.human.board.mines)]
        if self.solver_game.state is GameState.LOST and self.solver_game.board is not None:
            data["solver_mines"] = [list(m) for m in sorted(self.solver_game.board.mines)]
        return data

    def human_play(self, action: dict):
        """Applique le coup humain, puis un coup du solveur.

        Si la partie de l'humain est terminée, le solveur continue seul
        jusqu'au bout (le duel reste intéressant jusqu'à la fin). Chaque camp
        est archivé à la fin de sa partie.
        """
        from demineur.actions import Flag, Reveal, Unflag

        kind = action.get("kind")
        if kind == "reveal":
            coup = Reveal
        elif kind == "flag":
            coup = Flag
        elif kind == "unflag":
            coup = Unflag
        else:
            raise ValueError(f"kind inconnu: {kind!r}")
        try:
            event = self.human_runner.apply(coup(int(action["x"]), int(action["y"])))
        except (ValueError, KeyError, TypeError) as err:
            raise ValueError(str(err)) from err
        if event.result != "ok":
            raise ValueError(event.detail or "coup illégal")
        print(f"[duel seed={self.seed}] humain {kind} "
              f"({action.get('x')},{action.get('y')}) → {self.human.state.value}",
              flush=True)
        if self.human.state is GameState.PLAYING:
            self._solver_step()
        else:
            self._archive("humain")
            self._solver_jusqu_au_bout()
        return self.payload()

    def _solver_jusqu_au_bout(self) -> None:
        """Le solveur finit sa partie seul (l'humain a terminé la sienne)."""
        garde = 0
        while self.solver_game.state is GameState.PLAYING and garde < 10_000:
            self._solver_step()
            garde += 1
        if self.solver_game.state is not GameState.PLAYING:
            self._archive("solveur")

    def _solver_step(self):
        if self.solver_game.state is not GameState.PLAYING:
            return
        if self.solver_runner.gave_up:
            return
        action = self.solver.decide(self.solver_game.view())
        event = self.solver_runner.apply(action, self.solver.last_justification)
        if event.result == "ok":
            print(f"[duel seed={self.seed}] solveur {action} → "
                  f"{self.solver_game.state.value}", flush=True)
            if self.solver_game.state is not GameState.PLAYING:
                self._archive("solveur")
        else:
            print(f"[duel seed={self.seed}] coup solveur refusé: {event.detail}",
                  flush=True)


def make_handler(games_dir: str, web_dir: str):
    état = {"live": None, "duel": None}

    class Handler(BaseHTTPRequestHandler):
        server_version = "DemineurLocal/1.0"

        def log_message(self, *args):  # silence en usage normal
            pass

        # ---------------------------------------------------- utilitaires
        def _json(self, data, code=200):
            corps = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def _fichier(self, chemin_rel: str):
            """Sert un fichier statique de web/ (aucune traversée possible, W16)."""
            chemin_rel = posixpath.normpath(urllib.parse.unquote(chemin_rel))
            if chemin_rel.startswith("/") :
                chemin_rel = chemin_rel[1:]
            if ".." in chemin_rel.split("/"):
                self._json({"error": "chemin refusé"}, 403)
                return
            if chemin_rel in ("", "."):
                chemin_rel = "index.html"
            chemin = os.path.join(web_dir, chemin_rel)
            if not os.path.isfile(chemin):
                self._json({"error": "introuvable"}, 404)
                return
            with open(chemin, "rb") as f:
                corps = f.read()
            ext = os.path.splitext(chemin)[1]
            self.send_response(200)
            self.send_header("Content-Type", _TYPES.get(ext, "application/octet-stream"))
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def _paramètres(self, query: str) -> dict:
            return {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}

        # ---------------------------------------------------- GET
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            chemin, query = parsed.path, parsed.query
            p = self._paramètres(query)
            try:
                if chemin.startswith("/api/"):
                    return self._api_get(chemin, p)
                return self._fichier(chemin)
            except Exception as err:  # jamais de crash serveur
                self._json({"error": str(err)}, 500)

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            try:
                longueur = int(self.headers.get("Content-Length", 0))
                corps = self.rfile.read(longueur) if longueur else b"{}"
                data = json.loads(corps)
                if not isinstance(data, dict):
                    raise ValueError("objet JSON attendu")
            except (ValueError, json.JSONDecodeError):
                return self._json({"error": "JSON invalide"}, 400)
            if parsed.path == "/api/duel/human":
                duel = état["duel"]
                if duel is None:
                    return self._json({"error": "aucun duel en cours"}, 400)
                try:
                    résultat = duel.human_play(data)
                except ValueError as err:
                    return self._json({"error": str(err)}, 400)
                return self._json(résultat)
            return self._json({"error": "route inconnue"}, 404)

        # ---------------------------------------------------- API
        def _api_get(self, chemin: str, p: dict):
            if chemin == "/api/solvers":
                return self._json({"solvers": ["random", "rule", "classic"]})

            if chemin == "/api/games":
                parties = [
                    {
                        "id": g["id"],
                        "seed": g["header"].get("seed"),
                        "solver": g["header"].get("solver"),
                        "difficulty": g["header"].get("difficulty"),
                        "width": g["header"].get("width"),
                        "height": g["header"].get("height"),
                        "mines": g["header"].get("mines"),
                        "moves": g["header"].get("moves", 0),
                    }
                    for g in list_games(games_dir)
                ]
                return self._json({"games": parties})

            m = re.fullmatch(r"/api/games/([^/]+)", chemin)
            if m:
                return self._partie(m.group(1))

            m = re.fullmatch(r"/api/games/([^/]+)/analysis/(\d+)", chemin)
            if m:
                return self._analyse(m.group(1), int(m.group(2)))

            if chemin == "/api/benchmarks":
                return self._json(self._benchmarks())

            if chemin == "/api/live/new":
                état["live"] = LiveState(
                    seed=int(p.get("seed", 0)),
                    width=int(p.get("w", 9)), height=int(p.get("h", 9)),
                    mines=int(p.get("mines", 10)), games_dir=games_dir)
                live = état["live"]
                return self._json({"state": live.game.state.value,
                                   "view": live.game.view().to_json()})

            if chemin == "/api/live/state":
                live = état["live"]
                if live is None:
                    return self._json({"error": "aucune partie live"}, 404)
                return self._json({"state": live.game.state.value,
                                   "view": live.game.view().to_json(),
                                   "moves": len(live.runner.events)})

            if chemin == "/api/live/step":
                live = état["live"]
                if live is None:
                    return self._json({"error": "aucune partie live"}, 404)
                event = live.step()
                view = live.game.view().to_json()
                return self._json({
                    "state": live.game.state.value,
                    "view": view,
                    "moves": len(live.runner.events),
                    "event": event.to_json() if event else None,
                })

            if chemin == "/api/duel/new":
                état["duel"] = DuelState(
                    seed=int(p.get("seed", 0)),
                    width=int(p.get("w", 9)), height=int(p.get("h", 9)),
                    mines=int(p.get("mines", 10)), games_dir=games_dir)
                duel = état["duel"]
                return self._json(duel.payload())

            if chemin == "/api/duel":
                duel = état["duel"]
                if duel is None:
                    return self._json({"error": "aucun duel en cours"}, 404)
                return self._json(duel.payload())

            return self._json({"error": "route inconnue"}, 404)

        def _benchmarks(self) -> dict:
            """Agrège tous les artefacts ``benchmarks*.json`` du répertoire."""
            ordre = {"beginner": 0, "intermediate": 1, "expert": 2}
            documents = []
            if os.path.isdir(games_dir):
                for nom in os.listdir(games_dir):
                    if not (nom.startswith("benchmarks") and nom.endswith(".json")):
                        continue
                    try:
                        with open(os.path.join(games_dir, nom), encoding="utf-8") as f:
                            data = json.load(f)
                    except (OSError, json.JSONDecodeError):
                        continue  # artefact illisible: ignoré, jamais bloquant
                    if not isinstance(data, dict) or "results" not in data:
                        continue
                    documents.append(data)
            documents.sort(key=lambda d: ordre.get(d.get("difficulty", "?"), 9))
            return {"version": 1, "kind": "benchmarks", "benchmarks": documents}

        def _partie(self, identifiant: str):
            for g in list_games(games_dir):
                if g["id"] == identifiant:
                    header, events, result = load_game(g["path"])
                    return self._json({
                        "header": header, "events": events, "result": result})
            return self._json({"error": "partie inconnue"}, 404)

        def _analyse(self, identifiant: str, coup: int):
            from demineur.solvers.classic import analyze

            for g in list_games(games_dir):
                if g["id"] == identifiant:
                    _, events, _ = load_game(g["path"])
                    if not 0 <= coup < len(events):
                        return self._json({"error": "coup hors bornes"}, 404)
                    vue = view_from_json(events[coup]["view_before"])
                    a = analyze(vue)
                    return self._json({
                        "move": coup,
                        "probabilities": {f"{x},{y}": p
                                         for (x, y), p in a.probabilities.items()},
                        "safe": sorted(a.safe),
                        "mines": sorted(a.mines),
                        "components": a.components,
                        # contraintes R01 complètes : la frontière active,
                        # même quand les règles l'ont déjà résolue
                        "constraints": [
                            {"cells": sorted(c.cells), "count": c.count}
                            for c in a.constraints
                        ],
                        "exact": a.exact,
                    })
            return self._json({"error": "partie inconnue"}, 404)

    return Handler


def défaut_games_dir() -> str:
    """Répertoire d'artefacts par défaut : ``./games`` s'il existe, sinon
    celui du dépôt (le site fonctionne même lancé depuis un autre dossier)."""
    if os.path.isdir("games"):
        return "games"
    racine = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    candidat = os.path.join(racine, "games")
    return candidat if os.path.isdir(candidat) else "games"


def make_server(games_dir: str, port: int = 8765,
                web_dir: str | None = None) -> ThreadingHTTPServer:
    """Crée le serveur (W01). Bind 127.0.0.1 forcé (W16, INV5)."""
    if web_dir is None:
        web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "..", "web")
        web_dir = os.path.normpath(web_dir)
    handler = make_handler(games_dir, web_dir)
    serveur = ThreadingHTTPServer((_HOST, port), handler)
    serveur.daemon_threads = True
    return serveur


def main(argv=None) -> int:
    """``demineur serve [--port] [--open] [--games-dir]`` (W17)."""
    import argparse

    parser = argparse.ArgumentParser(prog="demineur serve",
                                     description="Site local de visualisation")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--games-dir", default=None,
                        help="répertoire des artefacts (défaut: ./games ou celui du dépôt)")
    if argv is not None and hasattr(argv, "port"):
        args = argv  # déjà un Namespace (appel depuis demineur.cli)
    else:
        args = parser.parse_args(argv if isinstance(argv, list) else None)
    games_dir = args.games_dir or défaut_games_dir()
    serveur = make_server(games_dir=games_dir, port=args.port)
    host, port = serveur.server_address[:2]
    url = f"http://{host}:{port}/"
    print(f"serveur local: {url} (CTRL+C pour arrêter)")
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("arrêt du serveur")
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
