"""Solveur classique complet (R08→R12) : analyse, coup sûr, guess optimal, explicabilité.

Boucle de résolution complète (R10) : analyser → jouer → jusqu'à
victoire/défaite/limite de coups. Chaque décision porte une justification
textuelle courte (R11), affichable en CLI (R15) et dans le web (W07).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from demineur.actions import Action, Flag, GiveUp, Reveal
from demineur.game import GameState
from demineur.models import Pos
from demineur.solvers.base import Solver
from demineur.solvers.classic.analysis import Constraint, extract_constraints
from demineur.solvers.classic.csp import (
    DEFAULT_MAX_CELLS,
    ComponentTooLarge,
    ConfigurationImpossible,
    classify,
    components,
    enumerate_solutions,
)
from demineur.solvers.classic.probabilities import exact_probabilities, uniform_probabilities
from demineur.solvers.classic.rules import Deduction, deduce
from demineur.view import GameView


@dataclass
class Analysis:
    """Résultat d'analyse d'une vue — consommé par le solveur et le web (W08/W09)."""

    constraints: list[Constraint] = field(default_factory=list)
    safe: dict[Pos, str] = field(default_factory=dict)
    mines: dict[Pos, str] = field(default_factory=dict)
    probabilities: dict[Pos, float] = field(default_factory=dict)
    components: list[dict] = field(default_factory=list)
    exact: bool = True


def _réduis(contraintes: list[Constraint], connues: frozenset[Pos]) -> list[Constraint]:
    """Retranche les mines connues ; ignore les contraintes satisfaites."""
    réduites = []
    for c in contraintes:
        cells = c.cells - connues
        count = c.count - len(c.cells & connues)
        if cells and count > 0:
            réduites.append(Constraint(cells, count))
        elif cells and count < 0:
            raise ValueError(f"contrainte impossible: {count} mines pour {cells}")
    return réduites


def _clusters(groupe: list[Constraint], taille_max: int) -> list[list[Constraint]]:
    """Découpe une composante en sous-groupes de contraintes (repli R17).

    Les sous-groupes partagent potentiellement des cases : la classification
    qui en découle reste exacte (restriction d'une solution globale), seule
    l'indépendance nécessaire aux probabilités exactes est perdue.
    """
    clusters: list[list[Constraint]] = []
    courant: list[Constraint] = []
    cellules: set[Pos] = set()
    for c in groupe:
        if courant and len(cellules | c.cells) > taille_max:
            clusters.append(courant)
            courant, cellules = [], set()
        courant.append(c)
        cellules |= c.cells
    if courant:
        clusters.append(courant)
    return clusters


def analyze(view: GameView) -> Analysis:
    """Analyse complète d'une vue : règles, CSP, classification, probabilités.

    Lève ``ValueError`` (contrainte incohérente) ou ``ConfigurationImpossible``
    (CSP sans solution) — signal R12 exploité par le solveur.
    """
    contraintes = extract_constraints(view)
    déduction: Deduction = deduce(contraintes)
    return analyze_from(view, contraintes, déduction)


def analyze_from(
    view: GameView,
    contraintes: list[Constraint],
    déduction: Deduction,
) -> Analysis:
    """Prolonge une déduction par règles (R02-R04) jusqu'à l'analyse complète.

    ``ClassicSolver.decide`` n'appelle cette phase coûteuse (CSP R05-R07) que
    si les règles n'ont rien produit (R18 : budget de performance).
    """
    analyse = Analysis(
        constraints=contraintes,
        safe=dict(déduction.safe),
        mines=dict(déduction.mines),
    )
    connues = frozenset(analyse.mines)
    réduites = _réduis(contraintes, connues)

    comps_data: list[tuple[list[Pos], list[frozenset[Pos]]]] = []
    for groupe in components(réduites):
        cellules = sorted(set().union(*[c.cells for c in groupe]))
        analyse.components.append({
            "cells": cellules,
            "constraints": [
                {"cells": sorted(c.cells), "count": c.count} for c in groupe
            ],
        })
        try:
            solutions = enumerate_solutions(cellules, groupe)
        except ComponentTooLarge:
            # R17 : repli — sous-contraintes, à défaut règles + uniforme
            analyse.exact = False
            for sous_groupe in _clusters(groupe, DEFAULT_MAX_CELLS):
                sous_cellules = sorted(set().union(*[c.cells for c in sous_groupe]))
                try:
                    sous_sols = enumerate_solutions(sous_cellules, sous_groupe)
                except ComponentTooLarge:
                    continue  # plafond encore dépassé: règles R02-R04 seules
                toujours, jamais = classify(sous_cellules, sous_sols)
                for pos in jamais:
                    analyse.safe.setdefault(
                        pos, f"R17: sous-contrainte ({len(sous_sols)} solutions) → {pos} sûr"
                    )
                for pos in toujours:
                    analyse.mines.setdefault(
                        pos, f"R17: sous-contrainte ({len(sous_sols)} solutions) → {pos} mine"
                    )
            continue
        toujours, jamais = classify(cellules, solutions)
        for pos in jamais:
            analyse.safe.setdefault(
                pos, f"R06: jamais-mine ({len(solutions)} solutions) → {pos} sûr"
            )
        for pos in toujours:
            analyse.mines.setdefault(
                pos, f"R06: toujours-mine ({len(solutions)} solutions) → {pos} mine"
            )
        comps_data.append((cellules, solutions))

    if analyse.exact and comps_data is not None:
        try:
            analyse.probabilities = exact_probabilities(view, comps_data)
        except (ValueError, ZeroDivisionError):
            analyse.exact = False
    if not analyse.exact or not analyse.probabilities:
        analyse.probabilities = uniform_probabilities(view)
        analyse.exact = False
    return analyse


def _nb_voisins_révélés(view: GameView, pos: Pos) -> int:
    x, y = pos
    return sum(
        1
        for vx in range(max(0, x - 1), min(view.width, x + 2))
        for vy in range(max(0, y - 1), min(view.height, y + 2))
        if (vx, vy) != pos and view.is_revealed((vx, vy))
    )


def _nb_voisins_cachés(view: GameView, pos: Pos) -> int:
    x, y = pos
    return sum(
        1
        for vx in range(max(0, x - 1), min(view.width, x + 2))
        for vy in range(max(0, y - 1), min(view.height, y + 2))
        if (vx, vy) != pos and view.is_hidden((vx, vy))
    )


def _pénalité_bord(view: GameView, pos: Pos) -> int:
    """0 = intérieur, 1 = bord, 2 = coin (R09 : coin/bord en dernier recours)."""
    x, y = pos
    bord_x = x in (0, view.width - 1)
    bord_y = y in (0, view.height - 1)
    return int(bord_x) + int(bord_y)


class ClassicSolver(Solver):
    """Meilleur solveur classique : règles + CSP + probabilités exactes."""

    name = "classic"

    def __init__(self):
        self.last_justification: str | None = None

    def decide(self, view: GameView) -> Action:
        self.last_justification = None
        if view.state is not GameState.PLAYING:
            self.last_justification = "partie déjà terminée"
            return GiveUp("partie déjà terminée")
        cachées = [pos for pos in view.hidden_cells() if not view.is_flagged(pos)]
        if not cachées:
            self.last_justification = "aucune case cachée disponible"
            return GiveUp("aucune case cachée disponible")
        try:
            # R18 : phase règles d'abord (rapide) ; le CSP et les probabilités
            # exactes ne sont calculés que si les règles n'ont rien déduit.
            contraintes = extract_constraints(view)
            déduction: Deduction = deduce(contraintes)
            sûr = {p: j for p, j in déduction.safe.items() if not view.is_flagged(p)}
            mines = {p: j for p, j in déduction.mines.items() if not view.is_flagged(p)}
            if not sûr and not mines:
                a = analyze_from(view, contraintes, déduction)
                # comptage global (R07) : une case de probabilité nulle est sûre
                if a.exact:
                    for pos in cachées:
                        if pos not in a.safe and a.probabilities.get(pos, 1.0) < 1e-9:
                            a.safe[pos] = f"R07: comptage global p=0 → {pos} sûr"
                sûr = {p: j for p, j in a.safe.items() if not view.is_flagged(p)}
                mines = {p: j for p, j in a.mines.items() if not view.is_flagged(p)}
            else:
                a = None
        except (ValueError, ConfigurationImpossible) as err:
            # R12 : fail-fast explicite — bug moteur ou vue corrompue
            self.last_justification = f"R12: configuration impossible — {err}"
            return GiveUp(f"configuration impossible: {err}")

        # R08 : coup sûr en priorité — cascade potentielle maximale
        if sûr:
            pos = max(sûr, key=lambda p: (_nb_voisins_cachés(view, p), -p[1], -p[0]))
            self.last_justification = sûr[pos]
            return Reveal(*pos)
        # R08 : sinon drapeau utile sur une mine certaine
        if mines:
            pos = min(mines, key=lambda p: (p[1], p[0]))
            self.last_justification = mines[pos]
            return Flag(*pos)
        # R09 : devinette — probabilité minimale, voisins révélés, intérieur d'abord
        probabilités = a.probabilities if a is not None else uniform_probabilities(view)
        exact = a is not None and a.exact
        pos = min(
            cachées,
            key=lambda p: (
                round(probabilités.get(p, 1.0), 9),
                -_nb_voisins_révélés(view, p),
                _pénalité_bord(view, p),
                p[1],
                p[0],
            ),
        )
        p = probabilités.get(pos, 1.0)
        self.last_justification = (
            f"R07: guess p={p:.3f} → {pos}"
            if exact
            else f"R17: guess uniforme p={p:.3f} → {pos}"
        )
        return Reveal(*pos)
