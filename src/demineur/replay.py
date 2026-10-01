"""Mode spectateur (F04) : rejouer une partie loggée dans le terminal.

Version texte minimale — le replay interactif complet est le web (W06),
pas de duplication : ce module ne fait qu'afficher.
"""

from __future__ import annotations

from demineur.render import render_view
from demineur.view import view_from_json


def format_event(event: dict) -> str:
    """Une ligne résumant un coup : numéro, action, justification, résultat."""
    action = event["action"]
    cible = (f"({action.get('x')},{action.get('y')})"
             if "x" in action else action.get("reason", ""))
    justification = event.get("justification") or "—"
    return f"#{event['move']:03d} {action['kind']}{cible} — {justification} [{event['result']}]"


def replay_text(header: dict, events: list[dict], result: dict, output_stream,
                delay: float = 0.0) -> None:
    """Affiche une partie loggée coup par coup (grille + ligne de coup)."""
    print(
        f"replay — seed={header.get('seed')} — grille "
        f"{header.get('width')}x{header.get('height')} — "
        f"{header.get('mines')} mines — solveur={header.get('solver')}",
        file=output_stream,
    )
    for event in events:
        vue = view_from_json(event["view_after"])
        print(format_event(event), file=output_stream)
        print(render_view(vue), file=output_stream)
        if delay:
            import time
            time.sleep(delay)
    print(f"résultat: {result['state']} en {result['moves']} coups", file=output_stream)
