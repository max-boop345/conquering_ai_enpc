"""Pont Pyodide : routes live/duel du serveur local, exécutées dans le navigateur.

Réutilise ``LiveState`` et ``DuelState`` de ``demineur.server`` (même moteur,
même solveur, mêmes seeds que le site local). Rien n'est archivé : la partie
vit dans l'onglet du navigateur. Chaque fonction renvoie ``(code, json)``.
"""

import json

from demineur.server import DuelState, LiveState

_état = {"live": None, "duel": None}


def _réponse(données, code=200):
    return code, json.dumps(données, ensure_ascii=False)


def _nouvelle(p):
    return dict(seed=int(p.get("seed", 0)), width=int(p.get("w", 9)),
                height=int(p.get("h", 9)), mines=int(p.get("mines", 10)))


def get(chemin, params_json):
    p = json.loads(params_json)
    try:
        if chemin == "/api/live/new":
            _état["live"] = LiveState(**_nouvelle(p))
            return _réponse(_état["live"].payload())
        if chemin in ("/api/live/state", "/api/live/step"):
            live = _état["live"]
            if live is None:
                return _réponse({"error": "aucune partie live"}, 404)
            if chemin == "/api/live/step":
                live.step()
            return _réponse(live.payload())
        if chemin == "/api/duel/new":
            _état["duel"] = DuelState(**_nouvelle(p))
            return _réponse(_état["duel"].payload())
        if chemin == "/api/duel":
            duel = _état["duel"]
            if duel is None:
                return _réponse({"error": "aucun duel en cours"}, 404)
            return _réponse(duel.payload())
    except ValueError as err:
        return _réponse({"error": str(err)}, 400)
    return _réponse({"error": "route inconnue"}, 404)


def post(chemin, corps_json):
    try:
        data = json.loads(corps_json or "{}")
        if not isinstance(data, dict):
            raise ValueError("objet JSON attendu")
    except ValueError:
        return _réponse({"error": "JSON invalide"}, 400)
    if chemin == "/api/duel/human":
        duel = _état["duel"]
        if duel is None:
            return _réponse({"error": "aucun duel en cours"}, 400)
        try:
            return _réponse(duel.human_play(data))
        except ValueError as err:
            return _réponse({"error": str(err)}, 400)
    return _réponse({"error": "route inconnue"}, 404)
