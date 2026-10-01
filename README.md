# demineur — Démineur local avec solveur classique

Projet du cours « conquering AI » (ENPC) : un démineur (Minesweeper) entièrement
**local**, avec un solveur classique déterministe, explicable et performant.
Aucune dépendance hors stdlib Python, aucun réseau : moteur, solveurs, tests,
CLI et site de visualisation tournent en local.

## Installation (F06)

```bash
# depuis la racine du dépôt
pip install -e .        # fournit la commande `demineur`

# ou, sans installation :
PYTHONPATH=src python3 -m demineur.cli --help
```

Python >= 3.10 requis. Aucune dépendance externe.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Utilisation (F01)

```bash
# nouvelle partie
demineur new --seed 42 --difficulty beginner

# jouer au clavier (r x y | f x y | u x y | q)  — A14
demineur play --seed 42 --w 9 --h 9 --mines 10

# faire résoudre une partie par le solveur classique, avec justifications — R15
demineur solve --seed 3 --difficulty beginner --method classic --explain

# benchmark des solveurs (random | rule | classic) — R14
demineur benchmark --difficulty beginner --seeds 50 --save docs/benchmarks.md

# duel : vous contre le solveur sur la même grille — F03
demineur duel --seed 7 --difficulty beginner

# rejouer une partie loggée — F04
demineur replay games/<id>.jsonl --delay 0.2

# site local de visualisation (127.0.0.1 uniquement) — W17
demineur serve --open
```

Difficultés : `beginner` (9x9, 10), `intermediate` (16x16, 40),
`expert` (30x16, 99), ou `--w/--h/--mines` pour du sur mesure.

## Architecture (G06)

```
src/demineur/
├── models.py          # Cell, CellState (A03)
├── board.py           # grille figée, seed, compteurs (A04-A06)
├── game.py            # moteur: révélation, cascade, drapeaux, fin (A07-A12)
├── view.py            # vue joueur — aucune fuite d'info (B01, INV1)
├── serialization.py   # JSON versionné état complet (A15)
├── presets.py         # difficultés standard (A16)
├── actions.py         # Reveal|Flag|Unflag|GiveUp + parsing strict (B02, B04)
├── runner.py          # GameRunner + événements unifiés (B09, B10)
├── solvers/           # contrat Solver (B01), étalons (B05, B06)
│   └── classic/       # phase R: contraintes, règles, CSP, probabilités
├── benchmark.py       # harnais déterministe partagé (R14)
├── artifacts.py       # parties loggées JSONL (B10 → W02)
├── cli.py             # new|play|solve|benchmark|duel|replay|serve (F01)
├── play.py / duel.py / replay.py / render.py
└── server.py          # serveur local + API JSON (W01, W02)
```

Flux de données : moteur (A15) → GameRunner (B10) → artefacts JSONL → API web
(W02) → frontend (`web/`).

## Solveurs

- `random` : étalon bas — révèle une case cachée au hasard.
- `rule` : single-point uniquement (R02).
- `classic` : règles R02-R04 + CSP exact (R05-R06) + probabilités combinatoires
  exactes (R07) + heuristique de devinette (R09) + comptage global.
  Chaque coup porte une justification courte (`--explain`, W07).

Détail des règles et preuves : `docs/classic_solver.md`. Résultats :
`docs/benchmarks.md`.

## Invariants du projet (INV)

- INV1 : un solveur ne voit jamais les mines réelles (vue joueur uniquement).
- INV2 : les tests sont la source de vérité.
- INV3 : chaque tâche terminée est journalisée dans `docs/PLAN.md`.
- INV4 : aucun secret n'est commité.
- INV5 : aucune écoute réseau autre que 127.0.0.1 (`demineur serve`).

Le plan complet (77 micro-tâches, graphe de dépendances) est dans `docs/PLAN.md`.
