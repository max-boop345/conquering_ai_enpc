"""Harness node réutilisable : exécute du JS sous node pour les tests frontend.

Les fichiers JS de web/ marchent comme <script> navigateur (globals) ET comme
modules node (module.exports). Ce harness exploite le second.
"""

import json
import os
import shutil
import subprocess

NODE = shutil.which("node") if shutil.which else None
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def web_js(nom: str) -> str:
    """require() d'un fichier de web/ — ex. web_js("engine.js")."""
    chemin = os.path.join(RACINE, "web", nom)
    if not os.path.isfile(chemin):
        raise FileNotFoundError(chemin)
    return "require(" + json.dumps(chemin) + ")"


def node_exec(script: str, fixtures: dict | None = None) -> str:
    """Exécute `script` sous node ; `@fixture:<nom>` est remplacé par le
    littéral JSON du fixture (injection directe, pas de fichier temporaire)."""
    if NODE is None:
        raise RuntimeError("node non disponible")
    for nom, contenu in (fixtures or {}).items():
        script = script.replace("@fixture:" + nom, json.dumps(contenu))
    retour = subprocess.run([NODE, "-e", script], capture_output=True,
                            text=True, timeout=60, cwd=RACINE)
    if retour.returncode != 0:
        raise RuntimeError(f"node a échoué: {retour.stderr}")
    return retour.stdout
