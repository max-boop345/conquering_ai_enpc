"""Construit la version statique du site pour Netlify (dossier ``dist/``).

Netlify n'exécute pas de serveur Python : on démarre donc le serveur local
(``demineur.server``) le temps du build et on enregistre ses réponses en
fichiers JSON statiques pour les routes en lecture seule (parties, analyses,
benchmarks). Les modes live et duel, qui ont besoin du moteur, tournent dans
le navigateur via Pyodide (``backend.js`` + ``bridge.py``), avec exactement le
même code Python que le site local.

Usage : ``python3 deploy/build_site.py`` depuis la racine du dépôt.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import urllib.request
import zipfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "src"))

from demineur.server import make_server  # noqa: E402

DIST = os.path.join(RACINE, "dist")
ICI = os.path.dirname(os.path.abspath(__file__))
PYODIDE = os.path.join(RACINE, "node_modules", "pyodide")
FICHIERS_PYODIDE = ["pyodide.js", "pyodide.asm.mjs", "pyodide.asm.wasm",
                    "python_stdlib.zip", "pyodide-lock.json"]


def _écrire(chemin_api: str, données) -> None:
    """``/api/games/x`` → ``dist/api/games/x.json``."""
    chemin = os.path.join(DIST, chemin_api.lstrip("/") + ".json")
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(données, f, ensure_ascii=False)


def _figer_api() -> int:
    serveur = make_server(games_dir=os.path.join(RACINE, "games"), port=0)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % serveur.server_address[1]

    def get(chemin):
        with urllib.request.urlopen(base + chemin) as r:
            return json.load(r)

    total = 0
    try:
        for chemin in ("/api/solvers", "/api/benchmarks", "/api/games"):
            _écrire(chemin, get(chemin))
            total += 1
        for partie in get("/api/games")["games"]:
            détail = get(f"/api/games/{partie['id']}")
            _écrire(f"/api/games/{partie['id']}", détail)
            total += 1
            for n in range(len(détail["events"])):
                chemin = f"/api/games/{partie['id']}/analysis/{n}"
                analyse = get(chemin)
                # deux parties identiques (ex. classic/live seed 42) donnent des
                # analyses identiques : l'id rend chaque fichier unique, sinon
                # l'upload Netlify (dédupliqué par hash) échoue en 422
                analyse["game"] = partie["id"]
                _écrire(chemin, analyse)
                total += 1
    finally:
        serveur.shutdown()
        serveur.server_close()
    return total


def _paquet_python() -> None:
    """``src/demineur`` zippé, décompressé par Pyodide dans le navigateur."""
    source = os.path.join(RACINE, "src")
    with zipfile.ZipFile(os.path.join(DIST, "demineur.zip"), "w",
                         zipfile.ZIP_DEFLATED) as z:
        for dossier, _, fichiers in os.walk(os.path.join(source, "demineur")):
            for nom in fichiers:
                if nom.endswith(".py") or nom == "py.typed":
                    chemin = os.path.join(dossier, nom)
                    z.write(chemin, os.path.relpath(chemin, source))
        z.write(os.path.join(ICI, "bridge.py"), "demineur_bridge.py")


def _pyodide() -> None:
    if not os.path.isdir(PYODIDE):
        raise SystemExit("pyodide absent : lancez `npm ci` avant le build")
    cible = os.path.join(DIST, "pyodide")
    os.makedirs(cible)
    for nom in FICHIERS_PYODIDE:
        shutil.copy2(os.path.join(PYODIDE, nom), cible)


def _frontend() -> None:
    shutil.copytree(os.path.join(RACINE, "web"), DIST)
    shutil.copy2(os.path.join(ICI, "backend.js"), DIST)
    index = os.path.join(DIST, "index.html")
    with open(index, encoding="utf-8") as f:
        html = f.read()
    balise = '<script src="app.js"></script>'
    if balise not in html:
        raise SystemExit("index.html : balise app.js introuvable")
    # backend.js doit intercepter fetch avant que app.js ne l'utilise
    html = html.replace(balise, '<script src="backend.js"></script>\n' + balise)
    with open(index, "w", encoding="utf-8") as f:
        f.write(html)


def main() -> int:
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    _frontend()
    _pyodide()
    _paquet_python()
    total = _figer_api()
    print(f"dist/ prêt : {total} réponses API figées, live/duel via Pyodide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
