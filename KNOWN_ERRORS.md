# Known errors

Erreurs et limitations connues. Bilan initial constaté lors de la vérification
finale (Python 3.13, Linux, VM partagée), puis **corrections apportées en
session 3** — état de chaque point ci-dessous. Environnement de référence :
`PYTHONPATH=src python3 -m unittest discover -s tests` = 177 tests verts,
`ruff check src tests` = 0 erreur.

## 1. Budget de performance expert — CORRIGÉ (session 3)

Cause identifiée : le solveur calculait le CSP et les probabilités exactes à
chaque coup, même quand les règles simples (R02-R04) suffisaient. Le calcul
coûteux n'est plus déclenché que lorsque les règles ne déduisent rien
(évaluation paresseuse dans `ClassicSolver.decide`, `analyze_from`).

Mesures après correction (Mac M-series, Python 3.14) :

```
expert seed=1: gagnée, total 4.8s,  pire coup 0.094s
expert seed=2: gagnée, total 2.5s,  pire coup 0.054s
expert seed=3: gagnée, total 13.2s, pire coup 0.137s
```

Le plafond R18 (1.0 s/coup) garde une marge ×7 environ. Win-rates inchangés
(classic 96.7 % / 85 % / 45 % en beginner / intermediate / expert). Les deux
tests concernés passent désormais avec ~30 % de marge sur la machine de
référence ; sur un hôte nettement plus lent, la marge reste la principale
protection — les plafonds du test sont conservés volontairement serrés.

## 2. Lint ruff — CORRIGÉ (session 3)

31 avertissements corrigés : 14 auto-fixables (imports, uplift) + 17 manuels
(E501 lignes longues, E741 variables ambiguës, F401/F841 imports et variables
inutilisés, B017 exceptions trop aveugles → `AttributeError`, B904 chaînage
d'exceptions, B007 boucle morte remplacée par une validation réelle dans
`serialization.py`). `ruff check src tests` : **All checks passed**.

## 3. CLI solve sans --save — CORRIGÉ (session 3)

`demineur solve --save <répertoire>` écrit l'artefact JSONL (via
`artifacts.save_game`), relisible par `demineur replay` et servi par
`demineur serve`. Testé (`tests/test_cli.py::test_solve_sauvegarde_artefact`).

## 4. Noms d'options CLI — clarifié (pas un bug)

Les noms réels et cohérents avec `--help` : `solve --method {classic,random,rule}`
et `benchmark --seeds N --solvers liste`. Aucun document du dépôt n'utilise de
nom obsolète (vérifié). Les supports de formation externes doivent se fier à
`demineur <cmd> --help`.

## 5. Benchmark rule à 0% en expert — comportement attendu, documenté

`rule` (single-point uniquement, sans guess probabiliste) perd en expert :
c'est le rôle d'un étalon bas. Documenté dans `docs/benchmarks.md`.
Corrigé au passage : le fallback aléatoire de `rule` est désormais **seedé
par la partie** dans le harnais — les benchmarks `rule` sont strictement
déterministes (deux exécutions sur les mêmes seeds = tables identiques).
Nouvelle référence : rule 83.3 % / 40 % / 0 % (beginner / intermediate / expert).

## Amélioration associée (constatée en corrigeant le point 1)

`serialization.game_from_json` validate désormais qu'une case minée révélée
n'apparaît que dans une partie perdue (invariant moteur, fail-fast plutôt que
boucle silencieuse).

## Vérifications passées (inchangées, aucune action requise)

- `demineur new`, `solve` (classic/rule/random, `--explain`), `benchmark`
  (tables Markdown + artefact `--json`), `play`, `duel`, `replay`, `serve` ;
- tests frontend + serveur (`test_frontend.py`, `test_server.py`) ;
- `pip install -e .` : point d'entrée `demineur` fonctionnel.
