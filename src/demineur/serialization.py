"""Sérialisation JSON versionnée du plateau (A15).

Deux formats, même numéro de version :
- ``kind: "game"``  : état complet du moteur (mines incluses) — tests, replay, debug ;
- ``kind: "view"`` : vue joueur sans les mines — cf. ``demineur.view``.

Rétro-compatibilité : le champ ``version`` est vérifié strictement, toute version
supérieure à la version courante est refusée.
"""

from __future__ import annotations

from demineur.board import Board
from demineur.game import Game, GameState
from demineur.models import Pos

FORMAT_VERSION = 1


def _positions(data: list) -> list[Pos]:
    paires = []
    for p in data:
        if not (isinstance(p, (list, tuple)) and len(p) == 2):
            raise ValueError(f"position invalide: {p!r}")
        x, y = int(p[0]), int(p[1])
        paires.append((x, y))
    return paires


def game_to_json(game: Game) -> dict:
    """État complet du moteur, source unique pour les fixtures et le web (W03)."""
    mines = sorted(game.board.mines) if game.board is not None else []
    return {
        "version": FORMAT_VERSION,
        "kind": "game",
        "width": game.width,
        "height": game.height,
        "mines_count": game.mines_count,
        "state": game.state.value,
        "mines": [list(p) for p in mines],
        "revealed": [list(p) for p in sorted(game.revealed)],
        "flags": [list(p) for p in sorted(game.flags)],
    }


def game_from_json(data: dict) -> Game:
    """Reconstruit une partie depuis son JSON complet (validation stricte)."""
    if not isinstance(data, dict):
        raise ValueError("partie: objet JSON attendu")
    if data.get("version") != FORMAT_VERSION:
        raise ValueError(f"version de format non supportée: {data.get('version')!r}")
    if data.get("kind") not in (None, "game"):
        raise ValueError(f"kind inattendu: {data.get('kind')!r}")
    for champ in ("width", "height", "mines_count", "state", "mines", "revealed", "flags"):
        if champ not in data:
            raise ValueError(f"partie: champ manquant '{champ}'")
    width, height, mines_count = int(data["width"]), int(data["height"]), int(data["mines_count"])
    game = Game(width, height, mines_count, seed=None)
    mines = _positions(data["mines"])
    if mines:
        board = Board(width, height, frozenset(mines))
        if len(board.mines) != mines_count:
            raise ValueError("mines déclarées et mines_count incohérents")
        game._board = board
    for pos in _positions(data["revealed"]):
        if not (0 <= pos[0] < width and 0 <= pos[1] < height):
            raise ValueError(f"case révélée hors grille: {pos}")
        game._revealed.add(pos)
    for pos in _positions(data["flags"]):
        if pos in game._revealed:
            raise ValueError(f"drapeau sur une case révélée: {pos}")
        game._flags.add(pos)
    if game.board is not None and GameState(data["state"]) is not GameState.LOST:
        # invariant: une case révélée minée n'est valide qu'en état LOST
        if any(pos in game.board.mines for pos in game._revealed):
            raise ValueError("case minée révélée hors d'une partie perdue")
    game.state = GameState(data["state"])
    return game
