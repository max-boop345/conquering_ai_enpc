# Architecture (G06)

## Schéma des modules

```
┌──────────────────────────────────────────────────────────────┐
│                          src/demineur/                        │
│                                                               │
│  models.py ── Cell, CellState (A03)                           │
│      │                                                        │
│  board.py ──── grille figée, seed, compteurs (A04-A06)        │
│      │                                                        │
│  game.py ──── moteur : révélation, cascade, drapeaux,        │
│      │        victoire/défaite, anti-triche (A07-A12)         │
│      │                                                        │
│  view.py ──── GameView : vue joueur, zéro fuite (B01, INV1)   │
│      │                                                        │
│  ┌───┴────────────┐        ┌──────────────────────────────┐   │
│  │ runner.py      │        │ solvers/                     │   │
│  │ GameRunner     │◄───────│ base.py (contrat B01)         │   │
│  │ (B09) +        │ decide │ random_solver.py (B05)        │   │
│  │ MoveEvent (B10)│  Action │ rule_solver.py (B06)         │   │
│  └───┬────────────┘        │ classic/ (R01-R12, R17)       │   │
│      │                     │   analysis.py (R01)           │   │
│      │                     │   rules.py (R02-R04)         │   │
│      │                     │   csp.py (R05, R06, R12)      │   │
│      │                     │   probabilities.py (R07)      │   │
│      │                     │   classic_solver.py (R08-R12) │   │
│      │                     └──────────────────────────────┘   │
│      │                                                        │
│  artifacts.py ── JSONL B10 → games/*.jsonl                    │
│  benchmark.py ── harnais R14 → games/benchmarks.json          │
│  serialization.py (A15) · presets.py (A16) · actions.py (B02/B04) │
│  play.py (A14) · duel.py (F03) · replay.py (F04) · render.py (F02) │
│  cli.py (F01) · server.py (W01/W02)                            │
└──────────────────────────────────────────────────────────────┘
```

## Flux de données

```
Game (A15) ──► GameRunner (B09)
                 │  MoveEvent (B10) :
                 │  (n° coup, vue avant, action, justification,
                 │   vue après, résultat)
                 ▼
          artifacts.save_game ──► games/<id>.jsonl
                 │
                 ▼
          server (W02) : /api/games/{id}  /api/games/{id}/analysis/{n}
                 │                              │
                 ▼                              ▼
        web/ replay interactif (W06)    heatmap (W08) + CSP (W09)
                                        + justifications (W07)
```

- La sérialisation A15 (vue joueur JSON, versionnée) est l'unique format
  échangé entre CLI, API et frontend (W03).
- L'événement B10 est l'unique source du replay, des justifications et des
  benchmarks.
- Le mode live (W13) et le duel web (W14) tiennent leur état en mémoire du
  serveur local, sur les mêmes contrats (GameView + Action).

## Choix structurants

| Choix | Raison |
|---|---|
| stdlib uniquement | local-first, aucune dépendance à installer |
| `GameView` passé aux solveurs | INV1 anti-fuite, mesurable honnêtement |
| mines placées au premier coup | A05/A12 : parties toujours jouables, reproductibles |
| GameRunner unique | une seule politique de rejet/détection de fin (B09) |
| analyse par coup côté serveur | le replay n'a jamais besoin des mines réelles |
| bind 127.0.0.1 forcé | INV5, testé (W16) |
