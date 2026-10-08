# Le site web local (W18)

## Architecture

- **Serveur** : `src/demineur/server.py` — stdlib `http.server`
  (`ThreadingHTTPServer`), bind **127.0.0.1 uniquement** (W16, INV5,
  non configurable).
- **Frontend** : `web/` — HTML/CSS/JS statiques, aucun bundler, aucune
  ressource distante (W19, testé).
- **Artefacts** : le serveur lit, sans jamais écrire :
  - `games/<id>.jsonl` — parties loggées (format B10) ;
  - `games/benchmarks.json` — benchmarks (format R14).

## Endpoints (W02)

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/` et `web/*` | fichiers statiques (traversée refusée) |
| GET | `/api/games` | liste des parties loggées |
| GET | `/api/games/{id}` | entête + événements + résultat |
| GET | `/api/games/{id}/analysis/{n}` | analyse de la vue avant le coup `n` : probabilités (W08), composantes CSP, sûres/mines (W09) |
| GET | `/api/solvers` | solveurs disponibles |
| GET | `/api/benchmarks` | agrégation de tous les artefacts `games/benchmarks*.json` : `{"benchmarks": [{difficulty, grid, seeds, results}, ...]}` classés beginner → expert |
| GET | `/api/live/new?seed&w&h&mines` | nouvelle partie live (W13) |
| GET | `/api/live/state` | état courant (vue + coups) |
| GET | `/api/live/step` | le solveur joue un coup |
| GET | `/api/duel/new?seed&w&h&mines` | nouveau duel humain vs solveur (W14) |
| POST | `/api/duel/human` | coup humain `{"kind","x","y"}` → 200, illégal → 400 |

Codes d'erreur : 400 (requête invalide), 404 (route/partie/coup inconnu),
403 (chemin refusé), 500 (jamais de crash serveur).

## Format de replay

Le frontend recharge les événements B10 via `/api/games/{id}` et rend
`view_after` de l'événement courant ; la justification du coup est affichée à
côté (W07). La heatmap et le surlignage CSP interrogent `/analysis/{n}` —
l'analyse est recalculée à la demande, à partir de la seule vue joueur.

## Limites

- Le serveur Python reste local (127.0.0.1) ; la version en ligne n'en a pas
  besoin (voir « Version en ligne (Netlify) »).
- Le mode live/duel vit en mémoire du serveur : perdu à l'arrêt (voulu).
- Un seul utilisateur (pas d'authentification) — acceptable sur 127.0.0.1.

## Lancement

```bash
demineur serve --open            # ouvre le navigateur local
# équivalent : PYTHONPATH=src python3 -m demineur.cli serve
```

## Version en ligne (Netlify)

Netlify n'exécute pas de serveur Python : `deploy/build_site.py` (commande de
build de `netlify.toml`) produit un site statique dans `dist/` :

- les routes en lecture seule (`/api/solvers`, `/api/games`, parties,
  analyses de chaque coup, `/api/benchmarks`) sont figées en JSON en
  interrogeant le serveur local pendant le build ;
- les modes live et duel tournent dans le navigateur grâce à Pyodide
  (servi depuis le site, aucune ressource distante) : `deploy/backend.js`
  intercepte `fetch("/api/...")` et `deploy/bridge.py` réutilise `LiveState`
  et `DuelState` de `server.py` — même moteur, mêmes seeds qu'en local ;
- en ligne, les parties live/duel ne sont pas archivées dans `games/`.

Pour ajouter une partie au Replay en ligne, commitez son fichier `games/*.jsonl`.
