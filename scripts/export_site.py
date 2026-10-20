"""Export du site statique (déploiement Netlify et hébergements sans backend).

Génère un répertoire autonome :
- les assets de ``web/`` (index.html, style.css, app.js) ;
- l'API pré-générée en JSON : ``api/solvers.json``, ``api/benchmarks.json``,
  ``api/games.json``, ``api/games/<id>.json`` et ``api/games/<id>/analysis.json``
  (une analyse par coup, calculée par le solveur Python — heatmap W08 et
  frontières W09 fonctionnent donc aussi en ligne).

Les modes interactifs (live, duel) restent locaux : ils nécessitent le serveur
``demineur serve`` (INV5) et le site en ligne l'explique à leur place.

Usage : ``python3 scripts/export_site.py [--games-dir games] [--web-dir web] [--out site]``
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from demineur.artifacts import list_games, load_game  # noqa: E402
from demineur.solvers.classic import analyze  # noqa: E402
from demineur.view import view_from_json  # noqa: E402

ASSETS = ("index.html", "style.css", "app.js")


def _dump(chemin: str, data) -> None:
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def analyse_partie(events: list[dict]) -> list[dict]:
    """Une analyse par coup (sur la vue avant le coup), pré-calculée."""
    coups = []
    for event in events:
        coup = {
            "move": event["move"],
            "probabilities": {}, "safe": [], "mines": [],
            "components": [], "constraints": [], "exact": False,
        }
        try:
            vue = view_from_json(event["view_before"])
            a = analyze(vue)
            coup["probabilities"] = {
                f"{x},{y}": p for (x, y), p in a.probabilities.items()
            }
            coup["safe"] = sorted(a.safe)
            coup["mines"] = sorted(a.mines)
            coup["components"] = a.components
            coup["constraints"] = [
                {"cells": sorted(c.cells), "count": c.count} for c in a.constraints
            ]
            coup["exact"] = a.exact
        except Exception as err:  # vue incohérente: coup sans analyse, jamais bloquant
            coup["erreur"] = str(err)
        coups.append(coup)
    return coups


def exporter(games_dir: str, web_dir: str, out_dir: str) -> int:
    """Génère le site statique complet dans ``out_dir``."""
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    # 1. assets web
    for asset in ASSETS:
        source = os.path.join(web_dir, asset)
        if not os.path.isfile(source):
            raise SystemExit(f"asset manquant: {source}")
        shutil.copy2(source, os.path.join(out_dir, asset))

    # 2. solvers
    _dump(os.path.join(out_dir, "api", "solvers.json"),
          {"solvers": ["random", "rule", "classic"]})

    # 3. benchmarks agrégés (mêmes règles que le serveur local)
    documents = []
    ordre = {"beginner": 0, "intermediate": 1, "expert": 2}
    if os.path.isdir(games_dir):
        for nom in os.listdir(games_dir):
            if not (nom.startswith("benchmarks") and nom.endswith(".json")):
                continue
            try:
                with open(os.path.join(games_dir, nom), encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and "results" in data:
                documents.append(data)
    documents.sort(key=lambda d: ordre.get(d.get("difficulty", "?"), 9))
    _dump(os.path.join(out_dir, "api", "benchmarks.json"),
          {"version": 1, "kind": "benchmarks", "benchmarks": documents})

    # 4. parties + analyses
    parties = list_games(games_dir)
    résumés = []
    for partie in parties:
        header, events, result = load_game(partie["path"])
        identifiant = partie["id"]
        résumés.append({
            "id": identifiant,
            "seed": header.get("seed"),
            "solver": header.get("solver"),
            "difficulty": header.get("difficulty"),
            "width": header.get("width"),
            "height": header.get("height"),
            "mines": header.get("mines"),
            "moves": header.get("moves", len(events)),
        })
        _dump(os.path.join(out_dir, "api", "games", f"{identifiant}.json"),
              {"header": header, "events": events, "result": result})
        _dump(os.path.join(out_dir, "api", "games", identifiant, "analysis.json"),
              {"version": 1, "kind": "analysis", "id": identifiant,
               "moves": analyse_partie(events)})
    _dump(os.path.join(out_dir, "api", "games.json"), {"games": résumés})
    print(f"site statique exporté dans {out_dir} "
          f"({len(résumés)} parties, {len(documents)} benchmarks)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="export_site", description="Exporte le site statique (Netlify)")
    parser.add_argument("--games-dir", default="games")
    parser.add_argument("--web-dir", default="web")
    parser.add_argument("--out", default="site")
    args = parser.parse_args(argv)
    return exporter(args.games_dir, args.web_dir, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
