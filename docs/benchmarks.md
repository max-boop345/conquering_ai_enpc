# Benchmarks — beginner (9x9, 10 mines, 30 seeds)

| solveur | win-rate | victoires | défaites | abandons | coups moyens |
|---------|----------|-----------|----------|----------|--------------|
| classic | 96.7% | 29 | 1 | 0 | 20.3 |
| rule | 83.3% | 25 | 5 | 0 | 24.4 |
| random | 0.0% | 0 | 30 | 0 | 3.5 |
# Benchmarks — intermediate (16x16, 40 mines, 20 seeds)

| solveur | win-rate | victoires | défaites | abandons | coups moyens |
|---------|----------|-----------|----------|----------|--------------|
| classic | 85.0% | 17 | 3 | 0 | 95.0 |
| rule | 40.0% | 8 | 12 | 0 | 87.7 |
| random | 0.0% | 0 | 20 | 0 | 3.1 |

# Benchmarks — expert (30x16, 99 mines, 20 seeds)

| solveur | win-rate | victoires | défaites | abandons | coups moyens |
|---------|----------|-----------|----------|----------|--------------|
| classic | 45.0% | 9 | 11 | 0 | 239.8 |
| random | 0.0% | 0 | 20 | 0 | 4.0 |
| rule | 0.0% | 0 | 20 | 0 | 97.0 |


## Note sur le solveur `rule` (étalon single-point)

`rule` n'a pas de guess probabiliste : en expert son win-rate est 0% (comportement attendu — il sert d'étalon bas, `classic` est le solveur complet). Depuis cette session, son fallback aléatoire est seedé par la partie : les benchmarks sont strictement déterministes (C13) — deux exécutions sur les mêmes seeds donnent des tables identiques.
