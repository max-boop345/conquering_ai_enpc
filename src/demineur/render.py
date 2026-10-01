"""Rendu texte du plateau (A14, F02) : ASCII pur ou couleurs ANSI."""

from __future__ import annotations

from demineur.view import GameView

# codes ANSI (F02) — activés uniquement si demandés, aucune dépendance
_COULEURS = {
    "1": "\033[94m", "2": "\033[92m", "3": "\033[91m",
    "4": "\033[93m", "5": "\033[95m", "6": "\033[96m",
    "7": "\033[97m", "8": "\033[90m",
}
_RESET = "\033[0m"
_FANION = "\033[91m"
_GRIS = "\033[90m"


def render_view(view: GameView, ansi: bool = False) -> str:
    """Grille une ligne par rangée : '.' cachée, 'F' drapeau, chiffre révélée.

    Le rendu n'expose jamais les mines cachées.
    """
    lignes: list[str] = []
    for y in range(view.height):
        morceaux = []
        for x in range(view.width):
            pos = (x, y)
            if view.is_flagged(pos):
                morceaux.append(f"{_FANION}F{_RESET}" if ansi else "F")
            elif view.is_revealed(pos):
                n = view.number(pos)
                if ansi and str(n) in _COULEURS:
                    morceaux.append(f"{_COULEURS[str(n)]}{n}{_RESET}")
                else:
                    morceaux.append(str(n))
            else:
                morceaux.append(f"{_GRIS}.{_RESET}" if ansi else ".")
        lignes.append("".join(morceaux))
    return "\n".join(lignes)


def render_header(view: GameView) -> str:
    return f"grille {view.width}x{view.height} — mines restantes: {view.mines_count - len(view.flags)}"
