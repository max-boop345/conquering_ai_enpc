# Protocole d'agent (G05)

Comment un agent (IA ou humain) choisit une tâche dans le graphe de dépendances
(§5 de `PLAN.md`) et la mène à bien.

## 1. Choisir une tâche

Prendre le **plus petit ID** dont toutes les arêtes `depends_on` pointent vers des
tâches `[x]`. Les arêtes `uses` indiquent les contrats à respecter, pas des
prérequis bloquants (sauf si la cible n'est pas encore `[x]`).

Les tâches `(annulé)` (W11, W12, G02, G04, F05) ne sont jamais choisies ; leurs
IDs restent pour la stabilité du graphe.

## 2. Respecter les invariants (§5, INV1–INV5)

- INV1 : le solveur ne voit jamais les mines réelles — passer uniquement
  `GameView` (B01).
- INV2 : les tests sont la source de vérité ; ne jamais modifier un test pour
  faire passer une fonctionnalité. Écrire le test d'abord (TDD), le voir
  échouer, implémenter, le voir passer.
- INV3 : chaque tâche terminée = une ligne dans le journal (§3) + `[x]` dans
  sa phase.
- INV4 : aucun secret dans le dépôt.
- INV5 : aucune écoute réseau autre que 127.0.0.1.

## 3. Exécuter

1. Écrire les tests (RED), vérifier l'échec, implémenter (GREEN), refactorer.
2. `PYTHONPATH=src python3 -m unittest discover -s tests` doit être vert.
3. Commit atomique : une tâche = un commit vérifiable, message référençant
   les IDs (`feat(classique): R01-R12 — ...`).

## 4. Mettre à jour le plan

- Passer la tâche à `[x]` dans sa phase (§2).
- Ajouter une ligne au journal d'avancement (§3) : date, ID, résumé.
- Ne jamais renuméroter les IDs ; les tâches annulées restent en place.

## 5. Ordre nominal (§6)

A → B → R → F → W → G, mais le protocole prime : une tâche est faisable dès
que ses dépendances sont `[x]`.
