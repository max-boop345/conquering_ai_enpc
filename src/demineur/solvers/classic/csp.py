"""Résolution CSP (R05, R06, R12, R17).

- partition des contraintes en composantes connexes indépendantes (R05) ;
- énumération exacte des solutions par composante, avec plafonds de taille et
  de nombre de solutions (préparation du repli R17) ;
- classification toujours-mine / jamais-mine (R06) ;
- détection de configuration impossible (R12, fail-fast).
"""

from __future__ import annotations

from demineur.models import Pos
from demineur.solvers.classic.analysis import Constraint

# Plafonds par défaut (R17/R18) — au-delà, repli documenté
DEFAULT_MAX_CELLS = 30
DEFAULT_MAX_SOLUTIONS = 100_000


class ComponentTooLarge(Exception):
    """La composante dépasse le plafond d'énumération (repli R17)."""


class ConfigurationImpossible(Exception):
    """Le CSP n'a aucune solution : bug moteur ou vue corrompue (R12)."""


def components(contraintes: list[Constraint]) -> list[list[Constraint]]:
    """Partitionne les contraintes en composantes connexes (cases partagées)."""
    restantes = list(contraintes)
    comps: list[list[Constraint]] = []
    while restantes:
        graine = restantes.pop(0)
        groupe = [graine]
        cellules = set(graine.cells)
        croissance = True
        while croissance:
            croissance = False
            for c in list(restantes):
                if c.cells & cellules:
                    restantes.remove(c)
                    groupe.append(c)
                    cellules |= c.cells
                    croissance = True
        comps.append(groupe)
    return comps


def enumerate_solutions(
    cells: list[Pos],
    contraintes: list[Constraint],
    max_cells: int = DEFAULT_MAX_CELLS,
    max_solutions: int = DEFAULT_MAX_SOLUTIONS,
) -> list[frozenset[Pos]]:
    """Énumère toutes les affectations valides de ``cells`` (R05).

    Retourne la liste des ensembles de mines. Lève ``ComponentTooLarge`` si un
    plafond est dépassé (jamais d'échec silencieux, repli en amont, R17) et
    ``ConfigurationImpossible`` si aucune solution n'existe (R12).
    """
    if len(cells) > max_cells:
        raise ComponentTooLarge(
            f"composante de {len(cells)} cases > plafond {max_cells}"
        )
    index: dict[Pos, list[int]] = {cell: [] for cell in cells}
    for i, c in enumerate(contraintes):
        for cell in c.cells:
            index[cell].append(i)

    # pour la propagion: état par contrainte (mines posées, cases restantes)
    mines_posées = [0] * len(contraintes)
    restantes_dans = [len(c.cells) for c in contraintes]

    solutions: list[frozenset[Pos]] = []
    mines_courantes: list[Pos] = []

    def candidate(cell: Pos) -> bool:
        """Poser une mine en ``cell`` reste-t-il faisable pour chaque contrainte ?"""
        for i in index[cell]:
            k = contraintes[i]
            posées = mines_posées[i] + 1
            restantes = restantes_dans[i] - 1
            if posées > k.count or k.count - posées > restantes:
                return False
        return True

    def explore(prochaine: int) -> None:
        if len(solutions) > max_solutions:
            raise ComponentTooLarge(f"plus de {max_solutions} solutions")
        if prochaine == len(cells):
            solutions.append(frozenset(mines_courantes))
            return
        cell = cells[prochaine]
        # branche mine
        if candidate(cell):
            for i in index[cell]:
                mines_posées[i] += 1
                restantes_dans[i] -= 1
            mines_courantes.append(cell)
            explore(prochaine + 1)
            mines_courantes.pop()
            for i in index[cell]:
                mines_posées[i] -= 1
                restantes_dans[i] += 1
        # branche sûre
        feasable = True
        for i in index[cell]:
            k = contraintes[i]
            if k.count - mines_posées[i] > restantes_dans[i] - 1:
                feasable = False
                break
        if feasable:
            for i in index[cell]:
                restantes_dans[i] -= 1
            explore(prochaine + 1)
            for i in index[cell]:
                restantes_dans[i] += 1

    explore(0)
    if not solutions:
        raise ConfigurationImpossible("aucune solution au CSP de la composante")
    return solutions


def classify(cells: list[Pos], solutions: list[frozenset[Pos]]) -> tuple[set, set]:
    """R06 : cases toujours-mine et jamais-mine à partir des solutions."""
    toujours: set[Pos] = set(cells)
    jamais: set[Pos] = set(cells)
    for sol in solutions:
        toujours &= sol
        jamais -= sol
    return toujours, jamais
