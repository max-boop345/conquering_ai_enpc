"""Type Action (B02) et parsing strict (B04).

Formes sérialisées :
- texte compact : ``reveal 3 4`` | ``flag 0 0`` | ``unflag 1 2`` | ``giveup <raison>`` ;
- JSON : ``{"kind": "reveal", "x": 3, "y": 4}`` (validation stricte, aucun champ superflu).
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    """Action de jeu proposée par un solveur ou un joueur."""

    def to_text(self) -> str:
        return action_to_text(self)

    def to_json(self) -> dict:
        return action_to_json(self)


@dataclass(frozen=True)
class Reveal(Action):
    x: int
    y: int


@dataclass(frozen=True)
class Flag(Action):
    x: int
    y: int


@dataclass(frozen=True)
class Unflag(Action):
    x: int
    y: int


@dataclass(frozen=True)
class GiveUp(Action):
    reason: str


_KINDS = {"reveal": Reveal, "flag": Flag, "unflag": Unflag}


def action_to_text(action: Action) -> str:
    if isinstance(action, (Reveal, Flag, Unflag)):
        kind = {Reveal: "reveal", Flag: "flag", Unflag: "unflag"}[type(action)]
        return f"{kind} {action.x} {action.y}"
    if isinstance(action, GiveUp):
        return f"giveup {action.reason}"
    raise TypeError(f"action inconnue: {action!r}")


def action_to_json(action: Action) -> dict:
    if isinstance(action, (Reveal, Flag, Unflag)):
        kind = {Reveal: "reveal", Flag: "flag", Unflag: "unflag"}[type(action)]
        return {"kind": kind, "x": action.x, "y": action.y}
    if isinstance(action, GiveUp):
        return {"kind": "giveup", "reason": action.reason}
    raise TypeError(f"action inconnue: {action!r}")


def _entier(valeur) -> int:
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ValueError(f"entier attendu: {valeur!r}")
    return valeur


def action_from_text(texte: str) -> Action:
    """Parse une action texte ; ``ValueError`` si le format est invalide (B04)."""
    if not isinstance(texte, str):
        raise ValueError("chaîne attendue")
    morceaux = texte.split()
    if not morceaux:
        raise ValueError("action vide")
    kind = morceaux[0]
    if kind == "giveup":
        if len(morceaux) < 2:
            raise ValueError("giveup exige une raison")
        return GiveUp(" ".join(morceaux[1:]))
    if kind not in _KINDS:
        raise ValueError(f"kind inconnu: {kind!r}")
    if len(morceaux) != 3:
        raise ValueError(f"action '{kind}' exige exactement 2 coordonnées")
    try:
        x, y = int(morceaux[1]), int(morceaux[2])
    except ValueError as err:
        raise ValueError(f"coordonnées invalides: {err}") from err
    return _KINDS[kind](x, y)


def action_from_json(data) -> Action:
    """Parse une action JSON ; validation stricte (champs exacts, types exacts)."""
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as err:
            raise ValueError(f"JSON invalide: {err}") from err
    if not isinstance(data, dict):
        raise ValueError("objet JSON attendu")
    kind = data.get("kind")
    if kind == "giveup":
        if set(data) != {"kind", "reason"} or not isinstance(data["reason"], str):
            raise ValueError("giveup mal formé")
        return GiveUp(data["reason"])
    if kind not in _KINDS:
        raise ValueError(f"kind inconnu: {kind!r}")
    if set(data) != {"kind", "x", "y"}:
        raise ValueError("champs exacts attendus: kind, x, y")
    return _KINDS[kind](_entier(data["x"]), _entier(data["y"]))
