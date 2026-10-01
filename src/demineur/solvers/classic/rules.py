"""Règles déterministes (R02, R03, R04) appliquées jusqu'au point fixe.

- R02 single-point : contrainte satisfaite → ses cases sont sûres ;
  contrainte saturée → toutes ses cases sont des mines.
- R03 subset : C1 ⊆ C2 → C2−C1 hérite de ``mines(C2)−mines(C1)`` (motifs 1-2-1,
  1-2-2-1) ; les contraintes dérivées rejoignent le système.
- R04 intersection croisée : les mines déjà connues (drapeaux ou déductions)
  sont retranchées des contraintes, ce qui propage les révélations sûres.

Chaque déduction porte sa justification (R11) : règle d'origine + case ciblée.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from demineur.models import Pos
from demineur.solvers.classic.analysis import Constraint


@dataclass
class Deduction:
    """Cases sûres et mines identifiées, avec justification par case (R11)."""

    safe: dict[Pos, str] = field(default_factory=dict)
    mines: dict[Pos, str] = field(default_factory=dict)
    derived: list[Constraint] = field(default_factory=list)


def deduce(contraintes: list[Constraint]) -> Deduction:
    """Applique R04→R02→R03 en boucle jusqu'à stabilisation.

    Point fixe garanti : chaque tour ajoute au moins une case identifiée ou une
    contrainte dérivée, en nombre borné par les cases et paires de contraintes.
    """
    déduction = Deduction()
    mines_connues: set[Pos] = set()
    # provenance[(cells, count)] = justification d'origine de la contrainte
    travail: dict[tuple[frozenset, int], str] = {}
    for c in contraintes:
        travail.setdefault((c.cells, c.count), "R01: contrainte initiale")

    for _ in range(len(travail) * (len(travail) + 1) + 1):
        nouvelles = False
        # R04 : réduction par les mines connues
        for (cells, count), origine in list(travail.items()):
            réduites = cells - mines_connues
            réduit = count - len(cells & mines_connues)
            if réduites and (réduites, réduit) not in travail:
                prov = "R04: mines connues retranchées"
                travail[(réduites, réduit)] = f"{prov} [de {origine}]"
                nouvelles = True
        # R02 : single-point sur toutes les contraintes (réduites incluses)
        for (cells, count), origine in travail.items():
            if count == 0:
                for pos in cells:
                    if pos not in déduction.safe and pos not in mines_connues:
                        règle = "R03" if origine.startswith("R03") else "R02"
                        déduction.safe[pos] = f"{règle}: → {pos} sûr"
                        nouvelles = True
            elif count == len(cells):
                for pos in cells:
                    if pos not in mines_connues:
                        règle = "R03" if origine.startswith("R03") else "R02"
                        déduction.mines[pos] = f"{règle}: → {pos} mine"
                        mines_connues.add(pos)
                        nouvelles = True
        # R03 : subset — C1 ⊂ C2 → contrainte dérivée
        clés = list(travail.items())
        for (cells1, count1), _ in clés:
            for (cells2, count2), _ in clés:
                if cells1 < cells2:
                    dérivée = (cells2 - cells1, count2 - count1)
                    if dérivée not in travail and dérivée[0]:
                        travail[dérivée] = "R03: subset"
                        déduction.derived.append(Constraint(*dérivée))
                        nouvelles = True
        if not nouvelles:
            break
    return déduction
