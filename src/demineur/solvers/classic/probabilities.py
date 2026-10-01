"""Probabilités exactes par combinatoire (R07).

Pour chaque composante CSP on connaît toutes ses solutions ; on combine les
composantes entre elles et avec les cases inconnues hors frontière pour
obtenir la probabilité exacte d'être une mine pour chaque case cachée.

Notations : ``m`` = mines restantes, ``O`` = cases hors frontière,
``f_i(j)`` = nombre de solutions de la composante ``i`` avec ``j`` mines,
``g_i(c, j)`` = celles où ``c`` est une mine.
"""

from __future__ import annotations

from collections import Counter

from demineur.models import Pos
from demineur.view import GameView


def _comb(n: int, k: int) -> int:
    """C(n, k) avec convention 0 hors domaine."""
    if k < 0 or k > n:
        return 0
    from math import comb
    return comb(n, k)


def _convolue(a: Counter, b: Counter) -> Counter:
    out: Counter = Counter()
    for ja, na in a.items():
        for jb, nb in b.items():
            out[ja + jb] += na * nb
    return out


def exact_probabilities(
    view: GameView,
    comps: list[tuple[list[Pos], list[frozenset[Pos]]]],
) -> dict[Pos, float]:
    """Probabilité exacte d'être une mine pour chaque case cachée non drapeautée.

    ``comps`` fournit, par composante, ses cases et ses solutions énumérées (R05).
    Les cases cachées absentes des composantes sont traitées comme hors
    frontière (répartition uniforme conditionnée au nombre de mines).
    """
    m = view.mines_count - len(view.flags)
    cachées = [pos for pos in view.hidden_cells() if not view.is_flagged(pos)]
    if m < 0:
        # plus de drapeaux que de mines: information incohérente, uniforme
        p = m / len(cachées) if cachées else 0.0
        return {pos: p for pos in cachées}

    frontier: set[Pos] = set()
    for cellules, _ in comps:
        frontier |= set(cellules)
    dehors = [pos for pos in cachées if pos not in frontier]
    n_dehors = len(dehors)

    # f_i et g_i par composante
    fs: list[Counter] = []
    gs: list[dict[Pos, Counter]] = []
    for cellules, solutions in comps:
        f: Counter = Counter()
        g: dict[Pos, Counter] = {c: Counter() for c in cellules}
        for sol in solutions:
            j = len(sol)
            f[j] += 1
            for c in sol:
                g[c][j] += 1
        fs.append(f)
        gs.append(g)

    # W = convolution des f_i ; W_minus[i] = convolution sans la composante i
    W: Counter = Counter({0: 1})
    for f in fs:
        W = _convolue(W, f)
    W_minus: list[Counter] = []
    for i in range(len(fs)):
        acc: Counter = Counter({0: 1})
        for j, f in enumerate(fs):
            if j != i:
                acc = _convolue(acc, f)
        W_minus.append(acc)

    # N = nombre total de configurations compatibles
    N = sum(w * _comb(n_dehors, m - J) for J, w in W.items())
    if N == 0:
        # ne devrait jamais survenir si la vue est cohérente (cf. R12)
        p = m / len(cachées) if cachées else 0.0
        return {pos: p for pos in cachées}

    probas: dict[Pos, float] = {}
    for i, (cellules, _) in enumerate(comps):
        for c in cellules:
            numérateur = 0
            for j, nj in gs[i][c].items():
                for Jp, wp in W_minus[i].items():
                    numérateur += nj * wp * _comb(n_dehors, m - j - Jp)
            probas[c] = numérateur / N
    for pos in dehors:
        probas[pos] = (
            sum(w * _comb(n_dehors - 1, m - J - 1) for J, w in W.items()) / N
        )
    return probas


def uniform_probabilities(view: GameView) -> dict[Pos, float]:
    """Repli R17 : probabilité uniforme quand l'énumération exacte est impossible."""
    m = view.mines_count - len(view.flags)
    cachées = [pos for pos in view.hidden_cells() if not view.is_flagged(pos)]
    p = m / len(cachées) if cachées else 0.0
    return {pos: p for pos in cachées}
