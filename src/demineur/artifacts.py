"""Artefacts de parties (B10 → W02/W06) : fichiers JSONL versionnés.

Format d'un fichier ``games/<id>.jsonl`` :
- ligne 1  : entête ``{"version":1,"kind":"game_header",...}`` ;
- lignes n : événements B10 ``{"kind":"event",...}`` ;
- dernière  : résultat ``{"kind":"result",...}``.
"""

from __future__ import annotations

import json
import os
import time

FORMAT_VERSION = 1


def save_game(directory: str, runner, meta: dict) -> str:
    """Écrit la partie complète (entête + événements + résultat) en JSONL."""
    os.makedirs(directory, exist_ok=True)
    identifiant = meta.get("id") or f"game-{int(time.time() * 1000)}-{runner.game.width}x{runner.game.height}"
    header = {
        "version": FORMAT_VERSION,
        "kind": "game_header",
        "id": identifiant,
        "width": runner.game.width,
        "height": runner.game.height,
        "mines": runner.game.mines_count,
        "moves": len(runner.events),
    }
    header.update({k: v for k, v in meta.items() if k != "id"})
    chemin = os.path.join(directory, f"{identifiant}.jsonl")
    suffixe = 1
    while os.path.exists(chemin):  # id unique même si sauvegardes rapprochées
        suffixe += 1
        chemin = os.path.join(directory, f"{identifiant}-{suffixe}.jsonl")
        header["id"] = f"{identifiant}-{suffixe}"
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
        for event in runner.events:
            ligne = {"kind": "event"}
            ligne.update(event.to_json())
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
        résultat = {
            "kind": "result",
            "state": runner.game.state.value,
            "won": runner.game.state.value == "won",
            "moves": len(runner.events),
        }
        f.write(json.dumps(résultat, ensure_ascii=False) + "\n")
    return chemin


def _parse_ligne(numéro: int, texte: str) -> dict:
    try:
        data = json.loads(texte)
    except json.JSONDecodeError as err:
        raise ValueError(f"ligne {numéro} invalide: {err}") from err
    if not isinstance(data, dict):
        raise ValueError(f"ligne {numéro}: objet JSON attendu")
    return data


def load_game(path: str) -> tuple[dict, list[dict], dict]:
    """Charge une partie ; retourne (entête, événements, résultat).

    Lève ``ValueError`` sur fichier corrompu, version inconnue ou ordre invalide.
    """
    with open(path, encoding="utf-8") as f:
        lignes = [l.strip() for l in f if l.strip()]
    if not lignes:
        raise ValueError("fichier vide")
    header = _parse_ligne(1, lignes[0])
    if header.get("kind") != "game_header":
        raise ValueError("première ligne: entête game_header attendue")
    if header.get("version") != FORMAT_VERSION:
        raise ValueError(f"version non supportée: {header.get('version')!r}")
    events: list[dict] = []
    résultat: dict | None = None
    for i, ligne in enumerate(lignes[1:], start=2):
        data = _parse_ligne(i, ligne)
        if data.get("kind") == "event":
            if résultat is not None:
                raise ValueError(f"événement après le résultat (ligne {i})")
            for champ in ("move", "view_before", "action", "view_after", "result"):
                if champ not in data:
                    raise ValueError(f"événement ligne {i}: champ manquant '{champ}'")
            events.append(data)
        elif data.get("kind") == "result":
            résultat = data
        else:
            raise ValueError(f"ligne {i}: kind inconnu {data.get('kind')!r}")
    if résultat is None:
        raise ValueError("pas de ligne résultat")
    return header, events, résultat


def list_games(directory: str) -> list[dict]:
    """Toutes les parties d'un répertoire : [{"id","path","header"}...]."""
    if not os.path.isdir(directory):
        return []
    parties = []
    for nom in sorted(os.listdir(directory)):
        if not nom.endswith(".jsonl"):
            continue
        chemin = os.path.join(directory, nom)
        try:
            header, _, _ = load_game(chemin)
        except ValueError:
            continue  # fichier illisible: ignoré, jamais d'échec bloquant
        parties.append({"id": header.get("id", nom[:-6]), "path": chemin, "header": header})
    return parties
