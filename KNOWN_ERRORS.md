# Known errors

Erreurs et limitations connues, constatées lors de la vérification finale des
fonctionnalités (environnement de test : Python 3.13, Linux, machine virtuelle
partagée — les mesures de performance peuvent varier selon la charge).

## 1. Budget de performance dépassé en difficulté expert (2 tests en échec)

La résolution d'une grille experte (30x16, 99 mines) avec `ClassicSolver`
dépasse les plafonds fixés par le plan :

- `tests/test_regressions.py::TestBudgetPerformance::test_partie_expert_par_coup`
  — échec : pire coup observé ~1.14s, plafond R18 de 1.0s/coup dépassé.
- `tests/test_classic_solver.py::TestBoucleComplete::test_expert_termine_rapidement`
  — échec : partie experte seed=1 résolue en ~18.3s, plafond de 10s dépassé.

Commandes de reproduction :

```bash
python -m pytest tests/test_regressions.py::TestBudgetPerformance tests/test_classic_solver.py::TestBoucleComplete -q
```

Les 176 autres tests passent (174 passed + 2 failed ci-dessus). En difficulté
beginner/intermediate, aucun dépassement n'a été observé. Cause probable :
coût du calcul exact de probabilités par combinatoire sur les grandes
composantes CSP en fin de partie experte. Piste d'optimisation : plafonner
le travail combinatoire ou mettre en cache les dénombrements par composante.

Note : la performance dépend de la machine ; ces seuils peuvent repasser en
dessous des plafonds sur un hôte plus rapide. Ce n'est pas un défaut de
correction — le solveur gagne bien les parties expertes (ex. seed=1 gagnée
en 295 coups), il est seulement trop lent par rapport aux plafonds choisis.

## 2. Lint : 31 avertissements ruff sur `src` et `tests`

`ruff check src tests` (config du dépôt, line-length 100) rapporte 31
erreurs, dont 15 auto-fixables. Principales catégories :

- `E501` lignes trop longues (ex. `src/demineur/artifacts.py:21`) ;
- `E741` nom de variable ambigu `l` (`src/demineur/artifacts.py:70`) ;
- `F401` imports inutilisés (ex. `demineur.actions.Action` dans
  `src/demineur/duel.py:11`) ;
- le reste : tri d'imports (`I`), uplift syntaxique (`UP`), etc.

Commande :

```bash
ruff check src tests
```

## 3. CLI solve : pas d'option `--save` pour les artefacts JSONL

`demineur solve` ne propose pas d'option d'écriture d'artefact
(`--save`/`--out`). Le replay (`demineur replay <fichier>.jsonl`) ne peut
donc lire que les artefacts déjà présents dans `games/` (produits par les
tests/benchmarks). Replay lui-même fonctionne (vérifié sur
`games/game-1790855092351-9x9.jsonl`).

## 4. CLI : noms d'options source de confusion (pas un bug bloquant)

Le solveur se choisit via `--method {classic,random,rule}` (et non
`--solver`), et le benchmark prend `--seeds N` / `--solvers liste` (et non
`--n`/`--method`). Ces noms sont cohérents avec l'aide (`--help`) mais
diffèrent de ceux utilisés dans certains documents du dépôt ; toute
formation les utilisant tels quels produit une erreur argparse « unrecognized
arguments ». Vérifier systématiquement `demineur <cmd> --help`.

## 5. Benchmark expert : win-rate du solveur `rule` à 0% sur 3 seeds

Sur `demineur benchmark --difficulty expert --seeds 3`, le solveur `rule`
(single-point uniquement, sans guess probabiliste) perd ses 3 parties
(40 coups moyens). C'est un comportement attendu — le solveur `rule` ne
devine pas de manière optimale et n'a pas été conçu pour gagner en expert —
mais le win-rate à 0% est à garder en tête si on l'utilise hors beginner.

## Vérifications passées (aucune action requise)

- `demineur new` (beginner/intermediate/expert, seeds, dimensions custom) ;
- `demineur solve` classic/rule/random avec `--explain` ;
- `demineur benchmark` beginner + expert, sortie table Markdown et artefact
  JSON (`--json`) consommé par `demineur serve` ;
- `demineur play` et `demineur duel` (abandon propre via `q`) ;
- `demineur replay` sur artefact JSONL existant ;
- `demineur serve` : serveur local 127.0.0.1 (stdlib), page `/` et API
  `/api/games`, `/api/benchmarks` répondent 200 ;
- tests frontend + serveur (`test_frontend.py`, `test_server.py`) : 23 passed.
