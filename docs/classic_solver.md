# Le solveur classique — règles, preuves, cas limites (R16)

Ce document décrit chaque technique du solveur `classic` (phase R), sa preuve
de correction et ses cas limites. Toutes les techniques sont déterministes et
testées (`tests/test_rules.py`, `tests/test_csp.py`, `tests/test_probabilities.py`,
`tests/test_classic_solver.py`, `tests/test_regressions.py`).

## Vue d'ensemble

```
vue joueur (B01)
   │
   ├─ R01 extraction des contraintes
   ├─ R02/R03/R04 règles locales → point fixe (sûr / mines, avec justification)
   ├─ R05 CSP par composante connexe (énumération exacte, plafonnée)
   │    ├─ R06 classification toujours-mine / jamais-mine
   │    └─ R12 échec = configuration impossible (fail-fast)
   ├─ R07 probabilités exactes (combinatoire composantes + hors frontière)
   └─ R08/R09 choix du coup : sûr d'abord, sinon probabilité minimale
```

## R01 — Extraction des contraintes

Pour chaque case révélée de nombre `n`, ses voisines cachées (non drapeautées)
forment une contrainte `(S, k)` : « exactement `k = n − drapeaux_voisins` mines
dans `S` ».

**Preuve** : c'est la définition même du nombre affiché par le moteur.

**Cas limites** : une case sans voisine cachée ne produit rien ; `k < 0` ou
`k > |S|` lève immédiatement (vue incohérente, cf. R12).

## R02 — Single-point

Contrainte `(S, k)` :
- `k = 0` → toutes les cases de `S` sont sûres ;
- `k = |S|` → toutes les cases de `S` sont des mines.

**Preuve** : il y a exactement `k` mines dans `S` ; si `k = 0` aucune case
n'est minée, si `k = |S|` toutes le sont.

**Motifs classiques** : couvre les déductions de base du joueur humain.

## R03 — Subset

Si `C1 ⊆ C2` alors `C2 − C1` contient exactement `k2 − k1` mines. La contrainte
dérivée rejoint le système ; le single-point s'y applique ensuite.

**Preuve** : les mines de `C1` comptent dans `k2`, donc les `k2 − k1` mines
restantes de `C2` sont dans `C2 − C1` (disjoint de `C1`).

**Motifs classiques** : 1-2-1 et 1-2-2-1 (`tests/test_rules.py::test_r03_motif_1_2_1`,
`tests/test_regressions.py::test_motif_1_2_2_1`).

## R04 — Intersection croisée (propagation)

Les mines identifiées (drapeaux ou déductions) sont retranchées de chaque
contrainte : `(S, k) → (S − M, k − |S ∩ M|)`. Une contrainte ainsi réduite peut
devenir triviale (R02) et révéler des cases sûres « ailleurs ».

**Preuve** : les mines de `M ∩ S` sont déjà comptées dans `k`.

Les trois règles bouclent jusqu'au point fixe (chaque tour ajoute au moins une
information, en nombre borné).

## R05 — CSP par composante

Les contraintes sont partitionnées en composantes connexes (cases partagées).
Chaque composante est résolue par énumération exacte (DFS avec élagage par
contrainte). Plafonds : 30 cases et 100 000 solutions par composante.

**Preuve** : l'énumération visite toutes les affectations valides.

## R06 — Classification

Une case est **toujours-mine** si elle est minée dans toutes les solutions de sa
composante, **jamais-mine** dans aucune.

**Preuve** : l'ensemble des solutions est exhaustif (R05).

## R07 — Probabilités exactes

Soit `m` les mines restantes, `O` les cases cachées hors frontière. Pour chaque
composante `i`, `f_i(j)` = nombre de solutions à `j` mines, `g_i(c, j)` = celles
où `c` est minée. Le nombre total de configurations est :

```
N = Σ_J  W(J) · C(|O|, m − J)      avec W = f_1 ⊛ f_2 ⊛ ... (convolution)
```

Probabilité d'une case `c` de la composante `i` :

```
P(c) = Σ_j  g_i(c, j) · W₋ᵢ(J') · C(|O|, m − j − J')  /  N
```

Probabilité d'une case hors frontière :

```
P(hors) = Σ_J  W(J) · C(|O|−1, m − J − 1)  /  N
```

**Invariant** (testé) : la somme des probabilités sur toutes les cases cachées
est exactement `m`.

**Cas limite — comptage global** : une case de probabilité `0` (par exemple
toutes les mines sont contraintes ailleurs) est un coup sûr, même hors frontière.

## R08 — Choix du coup sûr

Révéler en priorité une case jamais-mine (R06) — celle avec le plus de voisines
cachées (potentiel de cascade maximal) ; sinon poser un drapeau sur une
toujours-mine.

## R09 — Heuristique de devinette

En incertitude totale : minimiser `P(mine)` (R07), départager par nombre de
voisins révélés, puis pénaliser bords et coins (en dernier recours), puis ordre
`(y, x)` — entièrement déterministe.

**Preuve d'optimalité locale** : révéler la case de probabilité minimale
maximise la probabilité de survie du coup courant.

## R12 — Configuration impossible

Un CSP sans solution signifie un bug moteur ou une vue corrompue : le solveur
abandonne avec un message explicite (`R12: configuration impossible`), jamais de
boucle infinie ni d'échec silencieux.

## R17 — Repli d'énumération

Si une composante dépasse un plafond : découpage en sous-groupes de contraintes
(la classification qui en résulte reste **exacte** — toute restriction d'une
solution globale est solution du sous-groupe) ; à défaut, règles R02-R04 seules
et probabilité **uniforme**. Le repli est signalé (`exact: false`,
justification `R17`), jamais silencieux.

## R18 — Budget de performance

Plafond documenté et testé : **1,0 s maximum par coup** sur grille expert
(30×16, 99) dans le pire cas observé
(`tests/test_regressions.py::test_partie_expert_par_coup`). Les plafonds R05
bornent le pire cas d'énumération ; une partie experte complète se joue en
moins de 10 s.
