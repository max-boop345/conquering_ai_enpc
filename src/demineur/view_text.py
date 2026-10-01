"""Export texte de la vue joueur (B03) : grille ASCII + historique des coups.

Format compact destiné aux logs, à l'explicabilité et au web — jamais de donnée
sur les mines cachées (INV1).
"""

from __future__ import annotations

from demineur.render import render_view
from demineur.view import GameView


def view_to_text(view: GameView, historique: list | None = None) -> str:
    """Vue compacte : entête, grille ASCII, puis historique un coup par ligne."""
    lignes = [
        f"grille {view.width}x{view.height} mines:{view.mines_count} "
        f"drapeaux:{len(view.flags)} etat:{view.state.value}",
        render_view(view),
    ]
    if historique:
        lignes.append("historique:")
        for coup in historique:
            if isinstance(coup, (list, tuple)):
                lignes.append(" ".join(str(p) for p in coup))
            else:
                lignes.append(str(coup))
    return "\n".join(lignes)
