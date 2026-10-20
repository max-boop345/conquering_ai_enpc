# Mode interactif en ligne + bombes en fin de partie — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire fonctionner les modes Live et Duel sur le site Netlify (statique) en portant le moteur et le solveur classique en JavaScript côté navigateur, et afficher toutes les bombes à la fin de chaque partie dans tous les modes (replay, live, duel — gagné ou perdu).

**Architecture:** Port fidèle de `src/demineur` en trois fichiers JS chargés par `<script>` (pas de bundler, W19) : `web/engine.js` (moteur seedé, vue JSON A15, événements B10), `web/solver.js` (port du solveur classique R01-R12, ne consomme QUE la vue — INV1 respectée côté navigateur), `web/interactif.js` (contrôleurs LiveJS/DuelJS produisant les mêmes payloads que l'API Python). Le frontend détecte déjà le mode (local/statique) ; en mode statique, live/duel passent par ces contrôleurs JS au lieu de `fetch`. Les bombes de fin de partie exigent deux changements Python : `mines` ajouté à la ligne `result` des artefacts JSONL, et exposé dans les payloads dès que la partie est terminée (gagnée OU perdue). Le replay passe ces mines à `gridHtml` au coup final.

**Tech Stack:** Python 3.10+ (stdlib, unittest), JavaScript ES2015+ vanilla (Set/Map, pas de dépendance), Node (tests JS uniquement, skippés s'il manque), Netlify (build Python existant).

**Invariants du projet à respecter :** INV1 (le solveur JS ne voit jamais les mines réelles — `solver.js` n'importe pas `engine.js` et ne consomme que la vue JSON), INV2 (tests d'abord), INV3 (journal + statuts), INV5 (aucune écoute réseau).

## File Structure

```
web/
├── engine.js      # NOUVEAU — moteur de démineur JS (port de game.py/board.py) + RunnerJS (B10)
├── solver.js      # NOUVEAU — solveur classique JS (port de solvers/classic/, INV1)
├── interactif.js  # NOUVEAU — LiveJS/DuelJS : contrôleurs produisant les payloads API
├── app.js         # MODIFIÉ — live/duel branchent sur JS en mode statique ; replay bombes
└── index.html     # MODIFIÉ — <script> engine/solver/interactif ; footer

src/demineur/
├── artifacts.py   # MODIFIÉ — mines dans la ligne result des artefacts
└── server.py     # MODIFIÉ — payloads : mines dès que la partie est terminée

scripts/export_site.py  # MODIFIÉ — copie engine.js/solver.js/interactif.js
docs/web.md             # MODIFIÉ — modes interactifs en ligne
docs/PLAN.md            # MODIFIÉ — journal (INV3)

tests/
├── js_harness.py        # NOUVEAU — helper node réutilisable
├── test_frontend.py     # MODIFIÉ — utilise le harness ; test bombesFinDePartie
├── test_engine_js.py    # NOUVEAU — tests node du moteur JS
├── test_solver_js.py    # NOUVEAU — tests node du solveur JS
├── test_interactif_js.py # NOUVEAU — tests node des contrôleurs (sans DOM)
├── test_artifacts.py    # MODIFIÉ — mines dans le résultat
└── test_server.py       # MODIFIÉ — mines exposées sur partie gagnée
```

Convention commune aux fichiers JS : style ES5-ish (var, function) comme `app.js`, mais Set/Map autorisés ; identifiants en français comme le reste du repo ; positions internes = chaînes `"x,y"` ; à la fin de chaque fichier :

```js
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ... };
}
```

---

### Task 1: Harness node réutilisable

**Files:**
- Create: `tests/js_harness.py`
- Modify: `tests/test_frontend.py` (imports)

- [ ] **Step 1: Créer `tests/js_harness.py`**

```python
"""Harness node réutilisable : exécute du JS sous node pour les tests frontend.

Les fichiers JS de web/ marchent comme <script> navigateur (globals) ET comme
modules node (module.exports). Ce harness exploite le second.
"""

import json
import os
import shutil
import subprocess

NODE = shutil.which("node") if shutil.which else None
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def web_js(nom: str) -> str:
    """require() d'un fichier de web/ — ex. web_js("engine.js")."""
    chemin = os.path.join(RACINE, "web", nom)
    if not os.path.isfile(chemin):
        raise FileNotFoundError(chemin)
    return "require(" + json.dumps(chemin) + ")"


def node_exec(script: str, fixtures: dict | None = None) -> str:
    """Exécute `script` sous node ; `@fixture:<nom>` est remplacé par le
    littéral JSON du fixture (injection directe, pas de fichier temporaire)."""
    if NODE is None:
        raise RuntimeError("node non disponible")
    for nom, contenu in (fixtures or {}).items():
        script = script.replace("@fixture:" + nom, json.dumps(contenu))
    retour = subprocess.run([NODE, "-e", script], capture_output=True,
                            text=True, timeout=60, cwd=RACINE)
    if retour.returncode != 0:
        raise RuntimeError(f"node a échoué: {retour.stderr}")
    return retour.stdout
```

- [ ] **Step 2: Refactorer `tests/test_frontend.py` pour l'utiliser**

Remplacer l'en-tête du fichier par :

```python
import json
import os
import unittest

from demineur.game import Game
from tests.js_harness import NODE, RACINE, node_exec, web_js

APP_JS = os.path.join(RACINE, "web", "app.js")
_node_exec = node_exec  # compat avec le corps existant des tests
```

Puis adapter chaque appel `_node_exec(script, {"fixture.json": json.dumps(vue)})` : les fixtures deviennent des littéraux passés tels quels (`{"fixture.json": vue}`) et `"@fixture@"` devient `"@fixture:fixture.json"`. Vérifier avec `grep -n "fixture" tests/test_frontend.py` et corriger chaque occurrence.

- [ ] **Step 3: Lancer la suite concernée**

Run: `PYTHONPATH=src python3 -m unittest tests.test_frontend -v`
Expected: PASS (tous les tests existants, aucun comportement modifié)

- [ ] **Step 4: Commit**

```bash
git add tests/js_harness.py tests/test_frontend.py
git commit -m "test: harness node réutilisable pour les tests frontend JS"
```

---

### Task 2: engine.js — moteur (RNG, grille, placement, vue)

**Files:**
- Create: `web/engine.js`
- Test: `tests/test_engine_js.py`

- [ ] **Step 1: Écrire le test échouant `tests/test_engine_js.py`**

```python
"""Tests node du moteur JS (port de game.py/board.py) : A04-A06, vue A15."""

import json
import unittest

from tests.js_harness import NODE, node_exec, web_js

ENGINE = web_js("engine.js")


@unittest.skipUnless(NODE, "node non disponible")
class TestMoteurJS(unittest.TestCase):
    def script(self, corps):
        return "const E = " + ENGINE + ";\n" + corps

    def test_dimensions_et_vue(self):
        sortie = node_exec(self.script(
            "const jeu = new E.Jeu(5, 5, 3, 4);\n"
            "const vue = jeu.vue();\n"
            "console.log(JSON.stringify({w: vue.width, h: vue.height,"
            "m: vue.mines_count, state: vue.state, kind: vue.kind,"
            "cell00: vue.grid[0][0].state}));"
        ))
        d = json.loads(sortie)
        self.assertEqual((d["w"], d["h"], d["m"]), (5, 5, 3))
        self.assertEqual(d["state"], "playing")
        self.assertEqual(d["kind"], "view")
        self.assertEqual(d["cell00"], "hidden")

    def test_premier_coup_toujours_sur(self):
        sortie = node_exec(self.script(
            "let ok = true;\n"
            "for (let seed = 0; seed < 20; seed++) {\n"
            "  const jeu = new E.Jeu(6, 6, 4, seed);\n"
            "  jeu.révéler(2, 2);\n"
            "  const zone = [[2,2],[1,1],[2,1],[3,1],[1,2],[3,2],[1,3],[2,3],[3,3]];\n"
            "  zone.forEach(p => { if (jeu.estMine(p[0], p[1])) ok = false; });\n"
            "}\n"
            "console.log(ok);"
        ))
        self.assertIn("true", sortie)

    def test_determinisme_seed(self):
        sortie = node_exec(self.script(
            "const a = new E.Jeu(9, 9, 10, 7);\n"
            "const b = new E.Jeu(9, 9, 10, 7);\n"
            "a.révéler(0, 0); b.révéler(0, 0);\n"
            "const pa = a.positionsMines().map(m => m.join(',')).sort().join(';');\n"
            "const pb = b.positionsMines().map(m => m.join(',')).sort().join(';');\n"
            "console.log(pa === pb);"
        ))
        self.assertIn("true", sortie)

    def test_placement_impossible(self):
        sortie = node_exec(self.script(
            "const jeu = new E.Jeu(3, 3, 8, 0);\n"
            "try { jeu.révéler(0, 0); console.log('pas-derreur'); }\n"
            "catch (e) { console.log('erreur: ' + (e.message.indexOf('impossible') >= 0)); }"
        ))
        self.assertIn("erreur: true", sortie)

    def test_vue_sans_fuite(self):
        # la vue ne contient jamais les mines tant que la partie n'est pas finie
        sortie = node_exec(self.script(
            "const jeu = new E.Jeu(5, 5, 3, 4);\n"
            "jeu.révéler(0, 0);\n"
            "console.log(JSON.stringify(jeu.vue()).indexOf('is_mine') === -1);"
        ))
        self.assertIn("true", sortie)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Vérifier l'échec**

Run: `PYTHONPATH=src python3 -m unittest tests.test_engine_js -v`
Expected: ERROR — `FileNotFoundError` pour `web/engine.js`

- [ ] **Step 3: Créer `web/engine.js` — partie moteur (RunnerJS sera ajouté au Task 4)**

```js
/* Moteur de démineur en JavaScript — port fidèle de src/demineur (phase A).
 *
 * Mêmes règles que le moteur Python : placement différé des mines au premier
 * coup (zone sûre 3x3, A05), grille figée ensuite (A12), révélation en cascade,
 * drapeaux, victoire/défaite. La vue produite (méthode vue()) suit exactement
 * le format A15 du backend Python — le frontend ne fait pas la différence.
 *
 * INV1 côté navigateur : solver.js n'importe jamais ce fichier ; le solveur
 * ne reçoit que le JSON de vue().
 */

"use strict";

/* RNG déterministe (mulberry32) : même seed -> même grille, tous navigateurs. */
function mulberry32(seed) {
  var a = (seed >>> 0);
  return function () {
    a = (a + 0x6D2B79F5) | 0;
    var t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function voisins(width, height, x, y) {
  var out = [];
  for (var dy = -1; dy <= 1; dy++) {
    for (var dx = -1; dx <= 1; dx++) {
      if (dx === 0 && dy === 0) continue;
      var vx = x + dx, vy = y + dy;
      if (vx >= 0 && vx < width && vy >= 0 && vy < height) out.push([vx, vy]);
    }
  }
  return out;
}

function Jeu(width, height, minesCount, seed) {
  if (width <= 0 || height <= 0) {
    throw new Error("dimensions strictement positives requises");
  }
  if (!(minesCount > 0) || minesCount >= width * height) {
    throw new Error("nombre de mines invalide");
  }
  this.width = width;
  this.height = height;
  this.minesCount = minesCount;
  this.rng = mulberry32(seed === undefined ? 0 : seed);
  this.mines = null;          /* Set de "x,y" — null tant que le 1er coup n'a pas eu lieu */
  this.adjacent = null;       /* { "x,y": compteur } */
  this.révélées = new Set();
  this.drapeaux = new Set();
  this.state = "playing";
}

Jeu.prototype._placerMines = function (x, y) {
  var interdites = {};
  interdites[x + "," + y] = true;
  voisins(this.width, this.height, x, y).forEach(function (v) {
    interdites[v[0] + "," + v[1]] = true;
  });
  var libres = [];
  for (var yy = 0; yy < this.height; yy++) {
    for (var xx = 0; xx < this.width; xx++) {
      if (!interdites[xx + "," + yy]) libres.push([xx, yy]);
    }
  }
  if (this.minesCount >= libres.length) {
    throw new Error("placement impossible: " + this.minesCount +
                    " mines pour " + libres.length + " cases libres");
  }
  for (var i = libres.length - 1; i > 0; i--) {   /* Fisher-Yates seedé */
    var j = Math.floor(this.rng() * (i + 1));
    var tmp = libres[i]; libres[i] = libres[j]; libres[j] = tmp;
  }
  var self = this;
  this.mines = new Set();
  for (var k = 0; k < this.minesCount; k++) {
    this.mines.add(libres[k][0] + "," + libres[k][1]);
  }
  this.adjacent = {};
  for (var by = 0; by < this.height; by++) {
    for (var bx = 0; bx < this.width; bx++) {
      var n = 0;
      voisins(this.width, this.height, bx, by).forEach(function (v) {
        if (self.mines.has(v[0] + "," + v[1])) n++;
      });
      this.adjacent[bx + "," + by] = n;
    }
  }
};

Jeu.prototype.estMine = function (x, y) {
  return this.mines !== null && this.mines.has(x + "," + y);
};

Jeu.prototype.positionsMines = function () {
  if (this.mines === null) return [];
  var out = [];
  this.mines.forEach(function (clé) {
    var p = clé.split(",");
    out.push([parseInt(p[0], 10), parseInt(p[1], 10)]);
  });
  out.sort(function (a, b) { return (a[1] - b[1]) || (a[0] - b[0]); });
  return out;
};

Jeu.prototype.estDrapeau = function (x, y) {
  return this.drapeaux.has(x + "," + y);
};

Jeu.prototype.vue = function () {
  var grid = [];
  for (var y = 0; y < this.height; y++) {
    var ligne = [];
    for (var x = 0; x < this.width; x++) {
      var pos = x + "," + y;
      if (this.révélées.has(pos)) {
        ligne.push({ state: "revealed", adjacent_mines: this.adjacent[pos] });
      } else if (this.drapeaux.has(pos)) {
        ligne.push({ state: "flagged" });
      } else {
        ligne.push({ state: "hidden" });
      }
    }
    grid.push(ligne);
  }
  return {
    version: 1,
    kind: "view",
    width: this.width,
    height: this.height,
    mines_count: this.minesCount,
    state: this.state,
    grid: grid,
  };
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = { Jeu: Jeu, mulberry32: mulberry32, voisins: voisins };
}
```

- [ ] **Step 4: Vérifier que les tests passent**

Run: `PYTHONPATH=src python3 -m unittest tests.test_engine_js -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add web/engine.js tests/test_engine_js.py
git commit -m "feat(js): moteur de démineur navigateur — RNG seedé, placement zone sûre, vue A15 (port A04-A06)"
```

---

### Task 3: engine.js — révélation, cascade, drapeaux, fin de partie

**Files:**
- Modify: `web/engine.js`
- Modify: `tests/test_engine_js.py`

- [ ] **Step 1: Ajouter la classe de test `TestMoteurReveal`**

```python
@unittest.skipUnless(NODE, "node non disponible")
class TestMoteurReveal(unittest.TestCase):
    def _s(self, corps):
        return "const E = " + ENGINE + ";\n" + corps

    def test_cascade(self):
        # premier coup d'une 9x9 : zone sûre -> au moins 9 cases révélées
        sortie = node_exec(self._s(
            "const jeu = new E.Jeu(9, 9, 10, 42);\n"
            "const r = jeu.révéler(0, 0);\n"
            "console.log(r.length >= 9, jeu.state);"
        ))
        self.assertIn("true playing", sortie)

    def test_defaite_sur_mine(self):
        sortie = node_exec(self._s(
            "const jeu = new E.Jeu(5, 5, 3, 4);\n"
            "jeu.révéler(0, 0);\n"
            "const mine = jeu.positionsMines()[0];\n"
            "jeu.révéler(mine[0], mine[1]);\n"
            "console.log(jeu.state);"
        ))
        self.assertIn("lost", sortie)

    def test_victoire(self):
        sortie = node_exec(self._s(
            "const jeu = new E.Jeu(3, 3, 1, 0);\n"
            "jeu.révéler(0, 0);\n"
            "for (let y = 0; y < 3; y++) for (let x = 0; x < 3; x++) {\n"
            "  if (jeu.state !== 'playing') break;\n"
            "  if (!jeu.estMine(x, y)) { try { jeu.révéler(x, y); } catch (e) {} }\n"
            "}\n"
            "console.log(jeu.state);"
        ))
        self.assertIn("won", sortie)

    def test_coups_illegaux_refusés(self):
        sortie = node_exec(self._s(
            "const jeu = new E.Jeu(5, 5, 3, 4);\n"
            "jeu.révéler(0, 0);\n"
            "const erreurs = [];\n"
            "[[0,0], [9,9]].forEach(p => {\n"
            "  try { jeu.révéler(p[0], p[1]); } catch (e) { erreurs.push(e.message); }\n"
            "});\n"
            "jeu.drapeau(4, 4);\n"
            "try { jeu.révéler(4, 4); } catch (e) { erreurs.push(e.message); }\n"
            "console.log(erreurs.length, erreurs[0].indexOf('déjà révélée') >= 0,\n"
            "            erreurs[2].indexOf('drapeau') >= 0);"
        ))
        self.assertIn("3 true true", sortie)

    def test_drapeaux(self):
        sortie = node_exec(self._s(
            "const jeu = new E.Jeu(5, 5, 3, 4);\n"
            "jeu.drapeau(1, 1);\n"
            "const avant = jeu.estDrapeau(1, 1) + ' ' + jeu.vue().grid[1][1].state;\n"
            "jeu.retirerDrapeau(1, 1);\n"
            "console.log(avant, jeu.estDrapeau(1, 1));"
        ))
        self.assertIn("true flagged false", sortie)

    def test_aucune_action_apres_fin(self):
        sortie = node_exec(self._s(
            "const jeu = new E.Jeu(3, 3, 1, 0);\n"
            "jeu.révéler(0, 0);\n"
            "const mine = jeu.positionsMines()[0];\n"
            "jeu.révéler(mine[0], mine[1]);\n"
            "let erreur = false;\n"
            "try { jeu.révéler(2, 2); } catch (e) { erreur = true; }\n"
            "console.log(erreur, jeu.state);"
        ))
        self.assertIn("true lost", sortie)
```

- [ ] **Step 2: Vérifier l'échec**

Run: `PYTHONPATH=src python3 -m unittest tests.test_engine_js -v`
Expected: FAIL — `jeu.révéler is not a function`

- [ ] **Step 3: Ajouter les méthodes dans `web/engine.js` (avant le bloc module.exports)**

```js
Jeu.prototype.révéler = function (x, y) {
  if (this.state !== "playing") {
    throw new Error("partie terminée (" + this.state + ")");
  }
  if (x < 0 || x >= this.width || y < 0 || y >= this.height) {
    throw new Error("position hors grille: (" + x + "," + y + ")");
  }
  var pos = x + "," + y;
  if (this.révélées.has(pos)) {
    throw new Error("case déjà révélée: (" + x + "," + y + ")");
  }
  if (this.drapeaux.has(pos)) {
    throw new Error("case marquée d'un drapeau: (" + x + "," + y + ")");
  }
  if (this.mines === null) this._placerMines(x, y);
  if (this.mines.has(pos)) {
    this.révélées.add(pos);
    this.state = "lost";
    return [[x, y]];
  }
  var file = [[x, y]];
  var sorties = [];
  while (file.length > 0) {
    var p = file.pop();
    var clé = p[0] + "," + p[1];
    if (this.révélées.has(clé) || this.drapeaux.has(clé)) continue;
    this.révélées.add(clé);
    sorties.push(p);
    if (this.adjacent[clé] === 0) {
      voisins(this.width, this.height, p[0], p[1]).forEach(function (v) {
        file.push(v);
      });
    }
  }
  if (this.révélées.size === this.width * this.height - this.minesCount) {
    this.state = "won";
  }
  return sorties;
};

Jeu.prototype.drapeau = function (x, y) {
  if (this.state !== "playing") throw new Error("partie terminée (" + this.state + ")");
  if (x < 0 || x >= this.width || y < 0 || y >= this.height) {
    throw new Error("position hors grille: (" + x + "," + y + ")");
  }
  var pos = x + "," + y;
  if (this.révélées.has(pos)) {
    throw new Error("case déjà révélée: (" + x + "," + y + ")");
  }
  if (this.drapeaux.has(pos)) {
    throw new Error("drapeau déjà posé: (" + x + "," + y + ")");
  }
  this.drapeaux.add(pos);
};

Jeu.prototype.retirerDrapeau = function (x, y) {
  if (this.state !== "playing") throw new Error("partie terminée (" + this.state + ")");
  var pos = x + "," + y;
  if (!this.drapeaux.has(pos)) {
    throw new Error("pas de drapeau en (" + x + "," + y + ")");
  }
  this.drapeaux.delete(pos);
};
```

- [ ] **Step 4: Vérifier que tout passe**

Run: `PYTHONPATH=src python3 -m unittest tests.test_engine_js -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add web/engine.js tests/test_engine_js.py
git commit -m "feat(js): révélation en cascade, drapeaux, victoire/défaite (port A07-A12)"
```

---

### Task 4: engine.js — RunnerJS (événements B10)

**Files:**
- Modify: `web/engine.js`
- Modify: `tests/test_engine_js.py`

- [ ] **Step 1: Ajouter la classe de test `TestRunnerJS`**

```python
@unittest.skipUnless(NODE, "node non disponible")
class TestRunnerJS(unittest.TestCase):
    def _s(self, corps):
        return "const E = " + ENGINE + ";\n" + corps

    def test_format_evenement_b10(self):
        sortie = node_exec(self._s(
            "const runner = new E.RunnerJS(new E.Jeu(5, 5, 3, 4));\n"
            "const e = runner.appliquer({kind: 'reveal', x: 0, y: 0}, 'R07: test');\n"
            "console.log(e.move, e.action.kind, e.result,"
            "            e.view_after.width, e.justification);"
        ))
        self.assertIn("0 reveal ok 5 R07: test", sortie)

    def test_illegal_comptée(self):
        sortie = node_exec(self._s(
            "const runner = new E.RunnerJS(new E.Jeu(5, 5, 3, 4));\n"
            "runner.appliquer({kind: 'reveal', x: 0, y: 0}, null);\n"
            "const e = runner.appliquer({kind: 'reveal', x: 0, y: 0}, null);\n"
            "console.log(e.result, e.detail !== null, runner.events.length);"
        ))
        self.assertIn("illegal true 2", sortie)

    def test_abandon_apres_rejets(self):
        sortie = node_exec(self._s(
            "const runner = new E.RunnerJS(new E.Jeu(5, 5, 3, 4), 10000, 3);\n"
            "for (let i = 0; i < 4; i++) {\n"
            "  runner.appliquer({kind: 'reveal', x: 9, y: 9}, null);\n"
            "}\n"
            "const dernier = runner.events[runner.events.length - 1];\n"
            "console.log(runner.abandon, dernier.result, dernier.action.kind);"
        ))
        self.assertIn("true gave_up giveup", sortie)

    def test_give_up_direct(self):
        sortie = node_exec(self._s(
            "const runner = new E.RunnerJS(new E.Jeu(5, 5, 3, 4));\n"
            "const e = runner.appliquer({kind: 'giveup', reason: 'test'}, null);\n"
            "console.log(e.result, e.detail, runner.abandon);"
        ))
        self.assertIn("gave_up test true", sortie)
```

- [ ] **Step 2: Vérifier l'échec** — Run: `PYTHONPATH=src python3 -m unittest tests.test_engine_js -v`. Expected: `E.RunnerJS is not a constructor`.

- [ ] **Step 3: Ajouter `RunnerJS` dans `web/engine.js` et exporter**

```js
/* GameRunner JS (port B09/B10) : applique une action {kind,x,y|reason},
 * journalise l'événement B10 (vues A15 avant/après), rejette les coups
 * illégaux (compteur + abandon après N rejets consécutifs). */
function RunnerJS(jeu, maxMoves, maxRejets) {
  this.jeu = jeu;
  this.maxMoves = maxMoves === undefined ? 10000 : maxMoves;
  this.maxRejets = maxRejets === undefined ? 5 : maxRejets;
  this.events = [];
  this.abandon = false;
  this._rejets = 0;
}

RunnerJS.prototype.appliquer = function (action, justification) {
  var vueAvant = this.jeu.vue();
  var event = {
    move: this.events.length,
    view_before: vueAvant,
    action: action,
    justification: justification || null,
    view_after: vueAvant,
    result: "ok",
    detail: null,
  };
  if (action.kind === "giveup") {
    event.result = "gave_up";
    event.detail = action.reason || "";
    this.abandon = true;
    this.events.push(event);
    return event;
  }
  try {
    if (action.kind === "reveal") this.jeu.révéler(action.x, action.y);
    else if (action.kind === "flag") this.jeu.drapeau(action.x, action.y);
    else if (action.kind === "unflag") this.jeu.retirerDrapeau(action.x, action.y);
    else throw new Error("kind inconnu: " + action.kind);
    this._rejets = 0;
    event.view_after = this.jeu.vue();
    this.events.push(event);
    return event;
  } catch (err) {
    this._rejets++;
    event.result = "illegal";
    event.detail = String(err.message || err);
    this.events.push(event);
    if (this._rejets >= this.maxRejets) {
      this.abandon = true;
      this.events.push({
        move: this.events.length,
        view_before: this.jeu.vue(),
        action: { kind: "giveup", reason: "trop d'actions illégales" },
        justification: null,
        view_after: this.jeu.vue(),
        result: "gave_up",
        detail: this._rejets + " rejets consécutifs",
      });
    }
    return event;
  }
};

RunnerJS.prototype.plein = function () {
  return this.events.length >= this.maxMoves;
};
```

Export : `module.exports = { Jeu, mulberry32, voisins, RunnerJS };`

- [ ] **Step 4: Vérifier** — Run: `PYTHONPATH=src python3 -m unittest tests.test_engine_js -v`. Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add web/engine.js tests/test_engine_js.py
git commit -m "feat(js): RunnerJS — événements B10 au format identique au backend (port B09/B10)"
```

---

### Task 5: solver.js — contraintes et règles R02-R04

**Files:**
- Create: `web/solver.js`
- Create: `tests/test_solver_js.py`

- [ ] **Step 1: Écrire le test échouant `tests/test_solver_js.py`**

```python
"""Tests node du solveur classique JS (port de solvers/classic/) — INV1 :
solver.js ne consomme que le JSON de vue, jamais le plateau réel."""

import json
import unittest

from tests.js_harness import NODE, node_exec, web_js

SOLVER = web_js("solver.js")


def vue_fixture(numbers, flags=(), width=4, height=2, mines=2):
    grid = [[{"state": "hidden"} for _ in range(width)] for _ in range(height)]
    for (x, y), n in numbers.items():
        grid[y][x] = {"state": "revealed", "adjacent_mines": n}
    for (x, y) in flags:
        grid[y][x] = {"state": "flagged"}
    return {"version": 1, "kind": "view", "width": width, "height": height,
            "mines_count": mines, "state": "playing", "grid": grid}


@unittest.skipUnless(NODE, "node non disponible")
class TestContraintesJS(unittest.TestCase):
    def test_extraction(self):
        fixture = vue_fixture({(1, 0): 1})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = S.extraireContraintes(@fixture:vue);\n"
            "console.log(c.length, c[0].count);",
            {"vue": fixture},
        )
        self.assertIn("1 1", sortie)

    def test_exclusion_drapeaux(self):
        fixture = vue_fixture({(1, 0): 2}, flags={(0, 0)})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = S.extraireContraintes(@fixture:vue);\n"
            "console.log(c[0].count, Array.from(c[0].cells).indexOf('0,0') === -1);",
            {"vue": fixture},
        )
        self.assertIn("1 true", sortie)


@unittest.skipUnless(NODE, "node non disponible")
class TestReglesJS(unittest.TestCase):
    def test_r02_satisfaite(self):
        fixture = vue_fixture({(1, 0): 1}, flags={(0, 0)})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "console.log(Object.keys(d.safe).join(','),"
            "            (d.safe['2,0'] || '').indexOf('R02') === 0);",
            {"vue": fixture},
        )
        self.assertIn("2,0 true", sortie)

    def test_r02_saturée(self):
        fixture = vue_fixture({(1, 0): 2}, width=3, height=1, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "console.log(Object.keys(d.mines).sort().join(','));",
            {"vue": fixture},
        )
        self.assertEqual(sortie.strip(), "0,0,2,0")

    def test_r03_motif_1_2_1(self):
        fixture = vue_fixture({(0, 0): 1, (1, 0): 2, (2, 0): 1},
                              width=3, height=2, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "console.log(JSON.stringify({mines: Object.keys(d.mines).sort(),"
            "safe: Object.keys(d.safe).sort(),"
            "just: d.mines['0,1'] || ''}));",
            {"vue": fixture},
        )
        d = json.loads(sortie)
        self.assertEqual(d["mines"], ["0,1", "2,1"])
        self.assertEqual(d["safe"], ["1,1"])
        self.assertIn("R03", d["just"])

    def test_aucune_deduction(self):
        fixture = vue_fixture({(1, 0): 1})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = S.déduire(S.extraireContraintes(@fixture:vue));\n"
            "console.log(Object.keys(d.safe).length +"
            "            Object.keys(d.mines).length);",
            {"vue": fixture},
        )
        self.assertIn("0", sortie)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Vérifier l'échec** — Run: `PYTHONPATH=src python3 -m unittest tests.test_solver_js -v`. Expected: ERROR `FileNotFoundError` pour `web/solver.js`.

- [ ] **Step 3: Créer `web/solver.js` — contraintes + règles**

```js
/* Solveur classique en JavaScript — port fidèle de src/demineur/solvers/classic/
 * (phase R). INV1 respecté : ce fichier ne connaît jamais le plateau réel,
 * il ne consomme que le JSON de vue A15 (mêmes données que le backend Python).
 *
 * Représentation interne : positions = chaînes "x,y" ; contrainte =
 * { cells: Set<"x,y">, count: int }.
 */

"use strict";

function posClé(x, y) { return x + "," + y; }
function parseClé(clé) {
  var p = clé.split(",");
  return [parseInt(p[0], 10), parseInt(p[1], 10)];
}

function voisinsVue(vue, x, y) {
  var out = [];
  for (var dy = -1; dy <= 1; dy++) {
    for (var dx = -1; dx <= 1; dx++) {
      if (dx === 0 && dy === 0) continue;
      var vx = x + dx, vy = y + dy;
      if (vx >= 0 && vx < vue.width && vy >= 0 && vy < vue.height) out.push([vx, vy]);
    }
  }
  return out;
}

/* R01 : contraintes (cases frontière, nombre de mines). */
function extraireContraintes(vue) {
  var contraintes = [];
  for (var y = 0; y < vue.height; y++) {
    for (var x = 0; x < vue.width; x++) {
      var cell = vue.grid[y][x];
      if (cell.state !== "revealed") continue;
      var cachées = new Set();
      var drapeaux = 0;
      voisinsVue(vue, x, y).forEach(function (v) {
        var c = vue.grid[v[1]][v[0]];
        if (c.state === "hidden") cachées.add(posClé(v[0], v[1]));
        else if (c.state === "flagged") drapeaux++;
      });
      if (cachées.size === 0) continue;
      var count = cell.adjacent_mines - drapeaux;
      if (count < 0 || count > cachées.size) {
        throw new Error("contrainte impossible: " + count + "/" + cachées.size);
      }
      contraintes.push({ cells: cachées, count: count });
    }
  }
  return contraintes;
}

/* ---- helpers ensembles ---- */
function cléContrainte(cells, count) {
  return Array.from(cells).sort().join("|") + ":" + count;
}
function sousEnsemble(a, b) {  /* a sous-ensemble strict de b */
  if (a.size >= b.size) return false;
  var ok = true;
  a.forEach(function (p) { if (!b.has(p)) ok = false; });
  return ok;
}
function différence(b, a) {
  var out = new Set();
  b.forEach(function (p) { if (!a.has(p)) out.add(p); });
  return out;
}
function tailleIntersection(a, b) {
  var n = 0;
  a.forEach(function (p) { if (b.has(p)) n++; });
  return n;
}

/* R02/R03/R04 jusqu'au point fixe, avec provenance des justifications (R11). */
function déduire(contraintes) {
  var safe = {};
  var mines = {};
  var minesConnues = new Set();
  var travail = {};
  var parClé = {};
  contraintes.forEach(function (c) {
    var k = cléContrainte(c.cells, c.count);
    if (!(k in travail)) {
      travail[k] = "R01: contrainte initiale";
      parClé[k] = { cells: new Set(c.cells), count: c.count };
    }
  });
  var bornes = Object.keys(travail).length * (Object.keys(travail).length + 1) + 1;
  for (var tour = 0; tour <= bornes; tour++) {
    var nouvelles = false;
    /* R04 : réduction par les mines connues */
    Object.keys(parClé).forEach(function (k) {
      var c = parClé[k];
      var réduites = différence(c.cells, minesConnues);
      var réduit = c.count - tailleIntersection(c.cells, minesConnues);
      if (réduites.size > 0) {
        var k2 = cléContrainte(réduites, réduit);
        if (!(k2 in travail)) {
          travail[k2] = "R04: mines connues retranchées [" + travail[k] + "]";
          parClé[k2] = { cells: réduites, count: réduit };
          nouvelles = true;
        }
      }
    });
    /* R02 : single-point (les contraintes dérivées de R03 gardent leur règle) */
    Object.keys(parClé).forEach(function (k) {
      var c = parClé[k];
      var règle = travail[k].indexOf("R03") === 0 ? "R03" : "R02";
      if (c.count === 0) {
        c.cells.forEach(function (p) {
          if (!(p in safe) && !minesConnues.has(p)) {
            var xy = parseClé(p);
            safe[p] = règle + ": → (" + xy[0] + ", " + xy[1] + ") sûr";
            nouvelles = true;
          }
        });
      } else if (c.count === c.cells.size) {
        c.cells.forEach(function (p) {
          if (!minesConnues.has(p)) {
            var xy = parseClé(p);
            mines[p] = règle + ": → (" + xy[0] + ", " + xy[1] + ") mine";
            minesConnues.add(p);
            nouvelles = true;
          }
        });
      }
    });
    /* R03 : subset — C1 sous-ensemble de C2 -> C2-C1 hérite de count2-count1 */
    var clés = Object.keys(parClé);
    clés.forEach(function (k1) {
      clés.forEach(function (k2) {
        if (k1 === k2) return;
        var c1 = parClé[k1], c2 = parClé[k2];
        if (!sousEnsemble(c1.cells, c2.cells)) return;
        var dérivée = différence(c2.cells, c1.cells);
        if (dérivée.size === 0) return;
        var k3 = cléContrainte(dérivée, c2.count - c1.count);
        if (!(k3 in travail)) {
          travail[k3] = "R03: subset";
          parClé[k3] = { cells: dérivée, count: c2.count - c1.count };
          nouvelles = true;
        }
      });
    });
    if (!nouvelles) break;
  }
  return { safe: safe, mines: mines };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    posClé: posClé, parseClé: parseClé,
    extraireContraintes: extraireContraintes, déduire: déduire,
  };
}
```

- [ ] **Step 4: Vérifier** — Run: `PYTHONPATH=src python3 -m unittest tests.test_solver_js -v`. Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add web/solver.js tests/test_solver_js.py
git commit -m "feat(js): contraintes et règles R02-R04 jusqu'au point fixe (port R01-R04, INV1)"
```

---

### Task 6: solver.js — CSP (composantes, énumération, classification)

**Files:**
- Modify: `web/solver.js`
- Modify: `tests/test_solver_js.py`

- [ ] **Step 1: Ajouter la classe de test `TestCspJS`**

```python
@unittest.skipUnless(NODE, "node non disponible")
class TestCspJS(unittest.TestCase):
    def test_composantes(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c1 = {cells: new Set(['0,0','0,1']), count: 1};\n"
            "const c2 = {cells: new Set(['0,1','0,2']), count: 1};\n"
            "const c3 = {cells: new Set(['5,5','6,5']), count: 1};\n"
            "console.log(S.composantes([c1, c2, c3]).length);"
        )
        self.assertIn("2", sortie)

    def test_énumération_2_solutions(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = [{cells: new Set(['0,0','1,0']), count: 1}];\n"
            "console.log(S.énumérer(['0,0','1,0'], c).length);"
        )
        self.assertIn("2", sortie)

    def test_classification(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const r = S.classer(['0,0','1,0'], [new Set(['0,0'])]);\n"
            "console.log(Array.from(r.toujours).join(','),"
            "            Array.from(r.jamais).join(','));"
        )
        self.assertIn("0,0 1,0", sortie)

    def test_plafond_cellules(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const cellules = [];\n"
            "for (let i = 0; i < 40; i++) cellules.push(i + ',0');\n"
            "const c = [{cells: new Set(cellules), count: 20}];\n"
            "try { S.énumérer(cellules, c); console.log('pas-derreur'); }\n"
            "catch (e) { console.log(e.name); }"
        )
        self.assertIn("ComponentTooLarge", sortie)

    def test_configuration_impossible(self):
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const c = [{cells: new Set(['0,0','1,0']), count: 2},\n"
            "           {cells: new Set(['0,0','1,0']), count: 1}];\n"
            "try { S.énumérer(['0,0','1,0'], c); console.log('pas-derreur'); }\n"
            "catch (e) { console.log(e.name); }"
        )
        self.assertIn("ConfigurationImpossible", sortie)
```

- [ ] **Step 2: Vérifier l'échec** — `S.composantes is not a function`.

- [ ] **Step 3: Ajouter le CSP dans `web/solver.js` (avant le bloc exports)**

```js
/* Plafonds R17/R18 (identiques au backend Python). */
var MAX_CELLULES_CSP = 30;
var MAX_SOLUTIONS_CSP = 100000;

function ComponentTooLarge(message) {
  var e = new Error(message);
  e.name = "ComponentTooLarge";
  return e;
}
function ConfigurationImpossible(message) {
  var e = new Error(message);
  e.name = "ConfigurationImpossible";
  return e;
}

/* R05 : composantes connexes (cases partagées). */
function composantes(contraintes) {
  var comps = [];
  var restantes = contraintes.slice();
  while (restantes.length > 0) {
    var graine = restantes.shift();
    var groupe = [graine];
    var cellules = new Set(graine.cells);
    var croissance = true;
    while (croissance) {
      croissance = false;
      for (var i = restantes.length - 1; i >= 0; i--) {
        var c = restantes[i];
        var partage = false;
        cellules.forEach(function (p) { if (c.cells.has(p)) partage = true; });
        if (partage) {
          c.cells.forEach(function (p) { cellules.add(p); });
          groupe.push(c);
          restantes.splice(i, 1);
          croissance = true;
        }
      }
    }
    comps.push(groupe);
  }
  return comps;
}

/* R05 : énumération exacte par DFS avec élagage ; lève ComponentTooLarge
 * (repli R17) ou ConfigurationImpossible (R12). */
function énumérer(cellules, contraintes, maxCells, maxSolutions) {
  maxCells = maxCells === undefined ? MAX_CELLULES_CSP : maxCells;
  maxSolutions = maxSolutions === undefined ? MAX_SOLUTIONS_CSP : maxSolutions;
  if (cellules.length > maxCells) {
    throw ComponentTooLarge("composante de " + cellules.length +
                            " cases > plafond " + maxCells);
  }
  var index = {};
  cellules.forEach(function (clé) { index[clé] = []; });
  contraintes.forEach(function (c, i) {
    c.cells.forEach(function (clé) { index[clé].push(i); });
  });
  var minesPosées = contraintes.map(function () { return 0; });
  var restantesDans = contraintes.map(function (c) { return c.cells.size; });
  var solutions = [];
  var minesCourantes = [];

  function poserPossible(clé) {
    for (var t = 0; t < index[clé].length; t++) {
      var i = index[clé][t];
      var posées = minesPosées[i] + 1;
      var restantes = restantesDans[i] - 1;
      if (posées > contraintes[i].count ||
          contraintes[i].count - posées > restantes) return false;
    }
    return true;
  }
  function laisserPossible(clé) {
    for (var t = 0; t < index[clé].length; t++) {
      var i = index[clé][t];
      if (contraintes[i].count - minesPosées[i] > restantesDans[i] - 1) {
        return false;
      }
    }
    return true;
  }
  function explorer(i) {
    if (solutions.length > maxSolutions) {
      throw ComponentTooLarge("plus de " + maxSolutions + " solutions");
    }
    if (i === cellules.length) {
      solutions.push(new Set(minesCourantes));
      return;
    }
    var clé = cellules[i];
    if (poserPossible(clé)) {
      minesCourantes.push(clé);
      index[clé].forEach(function (j) { minesPosées[j]++; restantesDans[j]--; });
      explorer(i + 1);
      minesCourantes.pop();
      index[clé].forEach(function (j) { minesPosées[j]--; restantesDans[j]++; });
    }
    if (laisserPossible(clé)) {
      index[clé].forEach(function (j) { restantesDans[j]--; });
      explorer(i + 1);
      index[clé].forEach(function (j) { restantesDans[j]++; });
    }
  }
  explorer(0);
  if (solutions.length === 0) {
    throw ConfigurationImpossible("aucune solution au CSP de la composante");
  }
  return solutions;
}

/* R06 : classification toujours-mine / jamais-mine. */
function classer(cellules, solutions) {
  var toujours = new Set(cellules);
  var jamais = new Set(cellules);
  solutions.forEach(function (sol) {
    cellules.forEach(function (p) {
      if (!sol.has(p)) toujours.delete(p);
      if (sol.has(p)) jamais.delete(p);
    });
  });
  return { toujours: toujours, jamais: jamais };
}
```

Mettre à jour l'export : ajouter `composantes, énumérer, classer, MAX_CELLULES_CSP, MAX_SOLUTIONS_CSP`.

- [ ] **Step 4: Vérifier** — Run: `PYTHONPATH=src python3 -m unittest tests.test_solver_js -v`. Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add web/solver.js tests/test_solver_js.py
git commit -m "feat(js): CSP — composantes, énumération DFS plafonnée, classification (port R05/R06/R12/R17)"
```

---

### Task 7: solver.js — probabilités exactes et analyse complète

**Files:**
- Modify: `web/solver.js`
- Modify: `tests/test_solver_js.py`

- [ ] **Step 1: Ajouter la classe `TestProbabilitésJS`**

```python
@unittest.skipUnless(NODE, "node non disponible")
class TestProbabilitésJS(unittest.TestCase):
    def test_cinquante_cinquante(self):
        fixture = vue_fixture({(1, 0): 1}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(a.probabilities['0,0'].toFixed(2),"
            "            a.probabilities['2,0'].toFixed(2), a.exact);",
            {"vue": fixture},
        )
        self.assertIn("0.50 0.50 true", sortie)

    def test_hors_frontière_déduite(self):
        fixture = vue_fixture({(1, 0): 1}, width=4, height=1, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(a.probabilities['0,0'].toFixed(2),"
            "            a.probabilities['3,0'].toFixed(2));",
            {"vue": fixture},
        )
        self.assertIn("0.50 1.00", sortie)

    def test_somme_égale_mines_restantes(self):
        specs = [({}, 3, 1, 1), ({(1, 0): 1}, 4, 1, 2), ({(1, 0): 1, (2, 0): 1}, 5, 1, 2)]
        for numbers, w, mines in specs:
            fixture = vue_fixture(numbers, width=w, height=1, mines=mines)
            sortie = node_exec(
                "const S = " + SOLVER + ";\n"
                "const a = S.analyser(@fixture:vue);\n"
                "let somme = 0;\n"
                "Object.keys(a.probabilities).forEach(k => { somme += a.probabilities[k]; });\n"
                "console.log(somme.toFixed(6));",
                {"vue": fixture},
            )
            self.assertAlmostEqual(float(sortie.strip()), mines, places=5,
                                   msg=str(numbers))

    def test_aucune_contrainte_uniforme(self):
        fixture = vue_fixture({}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = S.analyser(@fixture:vue);\n"
            "console.log(a.probabilities['1,0'].toFixed(4), a.exact);",
            {"vue": fixture},
        )
        self.assertIn("0.3333 true", sortie)
```

- [ ] **Step 2: Vérifier l'échec** — `S.analyser is not a function`.

- [ ] **Step 3: Ajouter probabilités + analyser dans `web/solver.js`**

```js
/* C(n, k) exact (0 hors domaine). */
function comb(n, k) {
  if (k < 0 || k > n) return 0;
  var r = 1;
  for (var i = 1; i <= k; i++) r = r * (n - k + i) / i;
  return Math.round(r);
}
function convolue(a, b) {
  var out = {};
  Object.keys(a).forEach(function (ja) {
    Object.keys(b).forEach(function (jb) {
      var j = parseInt(ja, 10) + parseInt(jb, 10);
      out[j] = (out[j] || 0) + a[ja] * b[jb];
    });
  });
  return out;
}

function compterDrapeaux(vue) {
  var n = 0;
  for (var y = 0; y < vue.height; y++) {
    for (var x = 0; x < vue.width; x++) {
      if (vue.grid[y][x].state === "flagged") n++;
    }
  }
  return n;
}
function casesCachées(vue) {
  var out = [];
  for (var y = 0; y < vue.height; y++) {
    for (var x = 0; x < vue.width; x++) {
      if (vue.grid[y][x].state === "hidden") out.push(posClé(x, y));
    }
  }
  return out;
}
function uniformiser(vue) {
  var cachées = casesCachées(vue);
  var p = cachées.length > 0 ? (vue.mines_count - compterDrapeaux(vue)) /
                                cachées.length : 0;
  var out = {};
  cachées.forEach(function (c) { out[c] = p; });
  return out;
}

/* R07 : probabilité exacte d'être une mine pour chaque case cachée. */
function probabilitésExactes(vue, comps) {
  var m = vue.mines_count - compterDrapeaux(vue);
  var cachées = casesCachées(vue);
  if (cachées.length === 0) return {};
  if (m < 0) return uniformiser(vue);
  var frontier = new Set();
  comps.forEach(function (comp) {
    comp.cells.forEach(function (p) { frontier.add(p); });
  });
  var dehors = cachées.filter(function (p) { return !frontier.has(p); });
  var nDehors = dehors.length;
  var fs = [], gs = [];
  comps.forEach(function (comp) {
    var f = {}, g = {};
    comp.cells.forEach(function (p) { g[p] = {}; });
    comp.solutions.forEach(function (sol) {
      var j = sol.size;
      f[j] = (f[j] || 0) + 1;
      sol.forEach(function (p) { g[p][j] = (g[p][j] || 0) + 1; });
    });
    fs.push(f);
    gs.push(g);
  });
  var W = { 0: 1 };
  fs.forEach(function (f) { W = convolue(W, f); });
  var N = 0;
  Object.keys(W).forEach(function (J) {
    N += W[J] * comb(nDehors, m - parseInt(J, 10));
  });
  if (N === 0) return uniformiser(vue);
  var probas = {};
  comps.forEach(function (comp, i) {
    var Wmoins = { 0: 1 };
    fs.forEach(function (f, j) { if (j !== i) Wmoins = convolue(Wmoins, f); });
    comp.cells.forEach(function (p) {
      var num = 0;
      Object.keys(gs[i][p]).forEach(function (js) {
        Object.keys(Wmoins).forEach(function (Jp) {
          num += gs[i][p][js] * Wmoins[Jp] *
                 comb(nDehors, m - parseInt(js, 10) - parseInt(Jp, 10));
        });
      });
      probas[p] = num / N;
    });
  });
  dehors.forEach(function (p) {
    var num = 0;
    Object.keys(W).forEach(function (J) {
      num += W[J] * comb(nDehors - 1, m - parseInt(J, 10) - 1);
    });
    probas[p] = num / N;
  });
  return probas;
}

/* Analyse complète (équivalent Python analyze). Sortie :
 * { safe, mines, probabilities, components, constraints, exact }. */
function analyser(vue) {
  var contraintes = extraireContraintes(vue);
  var d = déduire(contraintes);
  var résultat = {
    safe: d.safe,
    mines: d.mines,
    probabilities: {},
    components: [],
    constraints: contraintes.map(function (c) {
      return { cells: Array.from(c.cells).map(parseClé), count: c.count };
    }),
    exact: true,
  };
  var minesConnues = new Set(Object.keys(d.mines));
  var réduites = [];
  contraintes.forEach(function (c) {
    var cells = différence(c.cells, minesConnues);
    var count = c.count - tailleIntersection(c.cells, minesConnues);
    if (cells.size > 0 && count > 0) réduites.push({ cells: cells, count: count });
  });
  var compsData = [];
  composantes(réduites).forEach(function (groupe) {
    var cellules = [];
    var vu = new Set();
    groupe.forEach(function (c) {
      c.cells.forEach(function (p) {
        if (!vu.has(p)) { vu.add(p); cellules.push(p); }
      });
    });
    cellules.sort();
    résultat.components.push({
      cells: cellules.map(parseClé),
      constraints: groupe.map(function (c) {
        return { cells: Array.from(c.cells).map(parseClé), count: c.count };
      }),
    });
    try {
      var sols = énumérer(cellules, groupe);
      var classe = classer(cellules, sols);
      classe.jamais.forEach(function (p) {
        if (!(p in résultat.safe)) {
          var xy = parseClé(p);
          résultat.safe[p] = "R06: jamais-mine (" + sols.length +
                             " solutions) → (" + xy[0] + ", " + xy[1] + ") sûr";
        }
      });
      classe.toujours.forEach(function (p) {
        if (!(p in résultat.mines)) {
          var xy = parseClé(p);
          résultat.mines[p] = "R06: toujours-mine (" + sols.length +
                              " solutions) → (" + xy[0] + ", " + xy[1] + ") mine";
        }
      });
      compsData.push({ cells: cellules, solutions: sols });
    } catch (e) {
      if (e.name === "ComponentTooLarge") {
        /* R17 : repli — sous-contraintes (classification exacte), uniforme sinon */
        résultat.exact = false;
        découper(groupe, MAX_CELLULES_CSP).forEach(function (sous) {
          var sc = [];
          var vu2 = new Set();
          sous.forEach(function (c) {
            c.cells.forEach(function (p) {
              if (!vu2.has(p)) { vu2.add(p); sc.push(p); }
            });
          });
          sc.sort();
          try {
            var ss = énumérer(sc, sous);
            var cl = classer(sc, ss);
            cl.jamais.forEach(function (p) {
              if (!(p in résultat.safe)) {
                var xy = parseClé(p);
                résultat.safe[p] = "R17: sous-contrainte (" + ss.length +
                                   " solutions) → (" + xy[0] + ", " + xy[1] + ") sûr";
              }
            });
            cl.toujours.forEach(function (p) {
              if (!(p in résultat.mines)) {
                var xy = parseClé(p);
                résultat.mines[p] = "R17: sous-contrainte (" + ss.length +
                                    " solutions) → (" + xy[0] + ", " + xy[1] + ") mine";
              }
            });
          } catch (e2) { /* plafond encore dépassé : règles R02-R04 seules */ }
        });
      } else if (e.name === "ConfigurationImpossible") {
        throw e; /* R12 : propagé, traité par décider() */
      } else {
        throw e;
      }
    }
  });
  if (résultat.exact) {
    résultat.probabilities = probabilitésExactes(vue, compsData);
  }
  if (!résultat.exact || Object.keys(résultat.probabilities).length === 0) {
    résultat.probabilities = uniformiser(vue);
  }
  return résultat;
}

/* Découpe une composante trop grande en sous-groupes (repli R17). */
function découper(groupe, tailleMax) {
  var clusters = [];
  var courant = [];
  var cellules = new Set();
  groupe.forEach(function (c) {
    if (courant.length > 0 && cellules.size + c.cells.size > tailleMax) {
      clusters.push(courant);
      courant = [];
      cellules = new Set();
    }
    courant.push(c);
    c.cells.forEach(function (p) { cellules.add(p); });
  });
  if (courant.length > 0) clusters.push(courant);
  return clusters;
}
```

Mettre à jour l'export : ajouter `analyser, probabilitésExactes, uniformiser, comb, casesCachées`.

- [ ] **Step 4: Vérifier** — Run: `PYTHONPATH=src python3 -m unittest tests.test_solver_js -v`. Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add web/solver.js tests/test_solver_js.py
git commit -m "feat(js): probabilités exactes par combinatoire + analyse complète (port R07/R17)"
```

---

### Task 8: solver.js — SolveurClassique.décider

**Files:**
- Modify: `web/solver.js`
- Modify: `tests/test_solver_js.py`

- [ ] **Step 1: Ajouter la classe `TestDéciderJS`**

```python
@unittest.skipUnless(NODE, "node non disponible")
class TestDéciderJS(unittest.TestCase):
    def test_premier_coup(self):
        fixture = vue_fixture({}, width=9, height=9, mines=10)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind, d.justification.indexOf('guess') >= 0);",
            {"vue": fixture},
        )
        self.assertIn("reveal true", sortie)

    def test_coup_sûr_avant_guess(self):
        fixture = vue_fixture({(1, 0): 1}, flags={(0, 0)})
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind, d.action.x, d.action.y,"
            "            d.justification.indexOf('R02') === 0);",
            {"vue": fixture},
        )
        self.assertIn("reveal 2 0 true", sortie)

    def test_drapeau_sur_toujours_mine(self):
        fixture = vue_fixture({(1, 0): 2}, width=3, height=1, mines=2)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind);",
            {"vue": fixture},
        )
        self.assertIn("flag", sortie)

    def test_comptage_global_p0(self):
        fixture = vue_fixture({(1, 0): 1}, width=4, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.x, d.action.y,"
            "            d.justification.indexOf('R07') === 0);",
            {"vue": fixture},
        )
        self.assertIn("3 0 true", sortie)

    def test_guess_justifié(self):
        fixture = vue_fixture({(1, 0): 1}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const d = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(d.action.kind, d.justification.indexOf('guess') >= 0,"
            "            d.justification.indexOf('p=0.500') >= 0);",
            {"vue": fixture},
        )
        self.assertIn("reveal true true", sortie)

    def test_partie_experte_complète(self):
        # moteur + solveur JS, une partie experte entière, zéro coup illégal
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const E = " + web_js("engine.js") + ";\n"
            "const t0 = Date.now();\n"
            "const jeu = new E.Jeu(30, 16, 99, 1);\n"
            "const runner = new E.RunnerJS(jeu);\n"
            "const s = new S.SolveurClassique();\n"
            "let illégaux = 0;\n"
            "while (jeu.state === 'playing' && !runner.abandon && !runner.plein()) {\n"
            "  const d = s.décider(jeu.vue());\n"
            "  const e = runner.appliquer(d.action, d.justification);\n"
            "  if (e.result === 'illegal') illégaux++;\n"
            "}\n"
            "console.log(jeu.state, illégaux, Date.now() - t0 < 10000);"
        )
        self.assertIn("won 0 true", sortie)

    def test_déterminisme(self):
        fixture = vue_fixture({(1, 0): 1}, width=3, height=1, mines=1)
        sortie = node_exec(
            "const S = " + SOLVER + ";\n"
            "const a = new S.SolveurClassique().décider(@fixture:vue);\n"
            "const b = new S.SolveurClassique().décider(@fixture:vue);\n"
            "console.log(JSON.stringify(a) === JSON.stringify(b));",
            {"vue": fixture},
        )
        self.assertIn("true", sortie)
```

- [ ] **Step 2: Vérifier l'échec** — `S.SolveurClassique is not a constructor`.

- [ ] **Step 3: Ajouter la classe dans `web/solver.js`**

```js
function nbVoisinsÉtat(vue, x, y, état) {
  var n = 0;
  voisinsVue(vue, x, y).forEach(function (v) {
    if (vue.grid[v[1]][v[0]].state === état) n++;
  });
  return n;
}
function pénalitéBord(vue, x, y) {
  return ((x === 0 || x === vue.width - 1) ? 1 : 0) +
         ((y === 0 || y === vue.height - 1) ? 1 : 0);
}

/* Port de ClassicSolver (R08-R12) : coup sûr en priorité (cascade potentielle
 * maximale), sinon drapeau sur une mine certaine, sinon guess — probabilité
 * minimale, voisins révélés, intérieur d'abord, (y,x). */
function SolveurClassique() {}

SolveurClassique.prototype.décider = function (vue) {
  if (vue.state !== "playing") {
    return { action: { kind: "giveup", reason: "partie déjà terminée" },
             justification: "partie déjà terminée" };
  }
  var cachées = casesCachées(vue);
  if (cachées.length === 0) {
    return { action: { kind: "giveup", reason: "aucune case cachée" },
             justification: "aucune case cachée disponible" };
  }
  var d = null;
  var a = null;
  try {
    var contraintes = extraireContraintes(vue);
    d = déduire(contraintes);
    var sûrs = Object.keys(d.safe);
    var minés = Object.keys(d.mines);
    if (sûrs.length === 0 && minés.length === 0) {
      a = analyser(vue);
      if (a.exact) {
        cachées.forEach(function (p) {
          if (!(p in a.safe) && a.probabilities[p] < 1e-9) {
            var xy = parseClé(p);
            a.safe[p] = "R07: comptage global p=0 → (" + xy[0] + ", " + xy[1] + ") sûr";
          }
        });
      }
      sûrs = Object.keys(a.safe);
      minés = Object.keys(a.mines);
    }
  } catch (e) {
    if (e.name === "ConfigurationImpossible" ||
        String(e.message).indexOf("contrainte impossible") >= 0) {
      return { action: { kind: "giveup",
                         reason: "configuration impossible: " + e.message },
               justification: "R12: configuration impossible — " + e.message };
    }
    throw e;
  }
  var source = a !== null ? a : d;
  if (Object.keys(source.safe).length > 0) {
    var pos = Object.keys(source.safe).reduce(function (meilleur, p) {
      if (meilleur === null) return p;
      var xy = parseClé(p), mxy = parseClé(meilleur);
      var score = nbVoisinsÉtat(vue, xy[0], xy[1], "hidden");
      var mscore = nbVoisinsÉtat(vue, mxy[0], mxy[1], "hidden");
      if (score !== mscore) return score > mscore ? p : meilleur;
      if (xy[1] !== mxy[1]) return xy[1] > mxy[1] ? p : meilleur;
      return xy[0] > mxy[0] ? p : meilleur;
    }, null);
    var px = parseClé(pos);
    return { action: { kind: "reveal", x: px[0], y: px[1] },
             justification: source.safe[pos] };
  }
  if (Object.keys(source.mines).length > 0) {
    var posM = Object.keys(source.mines).sort(function (p, q) {
      var a2 = parseClé(p), b2 = parseClé(q);
      return (a2[1] - b2[1]) || (a2[0] - b2[0]);
    })[0];
    var mx = parseClé(posM);
    return { action: { kind: "flag", x: mx[0], y: mx[1] },
             justification: source.mines[posM] };
  }
  /* R09 : guess — probabilité minimale, voisins révélés, intérieur, (y,x) */
  var probas = a !== null ? a.probabilities : uniformiser(vue);
  var exact = a !== null && a.exact;
  var posG = cachées.reduce(function (meilleur, p) {
    if (meilleur === null) return p;
    var xy = parseClé(p), myx = parseClé(meilleur);
    var clé = function (pos, xy2) {
      return [Math.round((probas[pos] === undefined ? 1 : probas[pos]) * 1e9),
              -nbVoisinsÉtat(vue, xy2[0], xy2[1], "revealed"),
              pénalitéBord(vue, xy2[0], xy2[1]), xy2[1], xy2[0]];
    };
    var ca = clé(p, xy), cb = clé(meilleur, myx);
    for (var i = 0; i < ca.length; i++) {
      if (ca[i] !== cb[i]) return ca[i] < cb[i] ? p : meilleur;
    }
    return meilleur;
  }, null);
  var gx = parseClé(posG);
  var pValue = probas[posG] === undefined ? 1 : probas[posG];
  var just = exact
    ? "R07: guess p=" + pValue.toFixed(3) + " → (" + gx[0] + ", " + gx[1] + ")"
    : "R17: guess uniforme p=" + pValue.toFixed(3) + " → (" + gx[0] + ", " + gx[1] + ")";
  return { action: { kind: "reveal", x: gx[0], y: gx[1] }, justification: just };
};
```

Mettre à jour l'export : ajouter `SolveurClassique`.

- [ ] **Step 4: Vérifier** — Run: `PYTHONPATH=src python3 -m unittest tests.test_solver_js -v`. Expected: PASS (22 tests). Si `test_partie_experte_complète` dépasse 10s : réduire les allocations dans `énumérer` (passer des tableaux d'indices pré-construits) avant de toucher aux plafonds.

- [ ] **Step 5: Commit**

```bash
git add web/solver.js tests/test_solver_js.py
git commit -m "feat(js): SolveurClassique.décider — coup sûr, comptage global, guess optimal (port R08-R12)"
```

---

### Task 9: interactif.js — LiveJS et DuelJS

**Files:**
- Create: `web/interactif.js`
- Create: `tests/test_interactif_js.py`

- [ ] **Step 1: Écrire le test échouant `tests/test_interactif_js.py`**

```python
"""Tests node des contrôleurs interactifs JS — payloads identiques à l'API."""

import unittest

from tests.js_harness import NODE, node_exec, web_js

INTERACTIF = web_js("interactif.js")


@unittest.skipUnless(NODE, "node non disponible")
class TestLiveJS(unittest.TestCase):
    def test_partie_complete(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const live = new I.LiveJS(1, 5, 5, 3);\n"
            "for (let i = 0; i < 60; i++) {\n"
            "  live.étape();\n"
            "  if (live.payload().state !== 'playing') break;\n"
            "}\n"
            "const p = live.payload();\n"
            "console.log(p.state, p.view.kind, p.moves > 0,"
            "            p.event !== null, p.event.justification !== null,"
            "            (p.mines || []).length >= 2);"
        )
        self.assertIn("true true true", sortie)

    def test_payload_initial(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const p = new I.LiveJS(1, 5, 5, 3).payload();\n"
            "console.log(p.state, p.moves, p.view.width, p.event === null);"
        )
        self.assertIn("playing 0 5 true", sortie)


@unittest.skipUnless(NODE, "node non disponible")
class TestDuelJS(unittest.TestCase):
    def test_humain_perd_solveur_continue(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const duel = new I.DuelJS(5, 5, 5, 3);\n"
            "const p0 = duel.coupHumain({kind: 'reveal', x: 0, y: 0});\n"
            "console.log('coup1:', p0.human_state, p0.solver_state,"
            "            p0.human_mines === undefined);\n"
            "const mine = duel.humain.positionsMines()[0];\n"
            "const p1 = duel.coupHumain({kind: 'reveal', x: mine[0], y: mine[1]});\n"
            "console.log('fin:', p1.human_state, p1.solver_state,"
            "            Array.isArray(p1.human_mines));"
        )
        self.assertIn("coup1: playing playing true", sortie)
        self.assertIn("fin: lost", sortie)

    def test_coup_illégal_rejeté(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const duel = new I.DuelJS(5, 5, 5, 3);\n"
            "duel.coupHumain({kind: 'reveal', x: 0, y: 0});\n"
            "try { duel.coupHumain({kind: 'reveal', x: 0, y: 0});\n"
            "     console.log('pas-derreur'); }\n"
            "catch (e) { console.log('erreur: ' + (e.message.length > 0)); }"
        )
        self.assertIn("erreur: true", sortie)

    def test_mines_exposées_aux_deux_camps_finis(self):
        sortie = node_exec(
            "const I = " + INTERACTIF + ";\n"
            "const duel = new I.DuelJS(5, 5, 5, 3);\n"
            "duel.coupHumain({kind: 'reveal', x: 0, y: 0});\n"
            "const mine = duel.humain.positionsMines()[0];\n"
            "const p = duel.coupHumain({kind: 'reveal', x: mine[0], y: mine[1]});\n"
            "console.log(Array.isArray(p.human_mines),"
            "            p.solver_state !== 'playing' ?"
            "              Array.isArray(p.solver_mines) : true);"
        )
        self.assertIn("true true", sortie)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Vérifier l'échec** — `FileNotFoundError` pour `web/interactif.js`.

- [ ] **Step 3: Créer `web/interactif.js`**

```js
/* Contrôleurs interactifs côté navigateur — produisent les MÊMES payloads que
 * l'API Python (/api/live/*, /api/duel/*) : la couche app.js ne fait pas la
 * différence. Dépendances : engine.js (Jeu, RunnerJS), solver.js
 * (SolveurClassique). En navigateur, globals ; sous node (tests), require. */

"use strict";

var Jeu_ = (typeof Jeu !== "undefined") ? Jeu : require("./engine.js").Jeu;
var RunnerJS_ = (typeof RunnerJS !== "undefined") ?
  RunnerJS : require("./engine.js").RunnerJS;
var SolveurClassique_ = (typeof SolveurClassique !== "undefined") ?
  SolveurClassique : require("./solver.js").SolveurClassique;

/* Équivalent JS de LiveState (W13). Mines exposées dès que la partie est
 * terminée — gagnée OU perdue (aucune fuite tant qu'on joue : INV1). */
function LiveJS(seed, width, height, mines) {
  this.jeu = new Jeu_(width, height, mines, seed);
  this.runner = new RunnerJS_(this.jeu);
  this.solver = new SolveurClassique_();
  this.seed = seed;
}

LiveJS.prototype.étape = function () {
  if (this.jeu.state !== "playing" || this.runner.abandon) return null;
  var vue = this.jeu.vue();
  var d = this.solver.décider(vue);
  return this.runner.appliquer(d.action, d.justification);
};

LiveJS.prototype.payload = function () {
  var dernier = this.runner.events.length > 0 ?
    this.runner.events[this.runner.events.length - 1] : null;
  var p = {
    state: this.jeu.state,
    view: this.jeu.vue(),
    moves: this.runner.events.length,
    event: dernier,
  };
  if (this.jeu.state !== "playing") p.mines = this.jeu.positionsMines();
  return p;
};

/* Équivalent JS de DuelState (W14) : l'humain joue, le solveur répond ; si la
 * partie de l'humain est finie, le solveur continue seul jusqu'au bout. */
function DuelJS(seed, width, height, mines) {
  this.humain = new Jeu_(width, height, mines, seed);
  this.solveurJeu = new Jeu_(width, height, mines, seed);
  this.humainRunner = new RunnerJS_(this.humain);
  this.solveurRunner = new RunnerJS_(this.solveurJeu);
  this.solver = new SolveurClassique_();
  this.seed = seed;
}

DuelJS.prototype.coupHumain = function (action) {
  var event = this.humainRunner.appliquer(action, null);
  if (event.result !== "ok") {
    throw new Error(event.detail || "coup illégal");
  }
  if (this.humain.state === "playing") {
    this.étapeSolveur();
  } else {
    var garde = 0;
    while (this.solveurJeu.state === "playing" &&
           !this.solveurRunner.abandon && garde < 10000) {
      this.étapeSolveur();
      garde++;
    }
  }
  return this.payload();
};

DuelJS.prototype.étapeSolveur = function () {
  if (this.solveurJeu.state !== "playing" || this.solveurRunner.abandon) return;
  var d = this.solver.décider(this.solveurJeu.vue());
  this.solveurRunner.appliquer(d.action, d.justification);
};

DuelJS.prototype.payload = function () {
  var p = {
    human: this.humain.vue(),
    solver: this.solveurJeu.vue(),
    human_state: this.humain.state,
    solver_state: this.solveurJeu.state,
  };
  if (this.humain.state !== "playing") {
    p.human_mines = this.humain.positionsMines();
  }
  if (this.solveurJeu.state !== "playing") {
    p.solver_mines = this.solveurJeu.positionsMines();
  }
  return p;
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = { LiveJS: LiveJS, DuelJS: DuelJS };
}
```

- [ ] **Step 4: Vérifier** — Run: `PYTHONPATH=src python3 -m unittest tests.test_interactif_js -v`. Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add web/interactif.js tests/test_interactif_js.py
git commit -m "feat(js): contrôleurs LiveJS/DuelJS — payloads identiques à l'API, solveur continue seul"
```

---

### Task 10: Python — mines dans les artefacts et les payloads de fin de partie

**Files:**
- Modify: `src/demineur/artifacts.py`
- Modify: `src/demineur/server.py`
- Modify: `tests/test_artifacts.py`, `tests/test_server.py`

- [ ] **Step 1: Tests échouants**

Dans `tests/test_artifacts.py` (classe `TestArtefacts`) :

```python
    def test_mines_dans_le_resultat(self):
        # fin de partie : toutes les mines sont archivées, cliquées ou non
        import tempfile as _tf

        from demineur.game import Game
        from demineur.runner import GameRunner
        from demineur.solvers.classic import ClassicSolver

        with _tf.TemporaryDirectory() as d:
            runner = GameRunner(Game(5, 5, 3, seed=4))
            runner.run(ClassicSolver())
            chemin = save_game(d, runner, meta={"seed": 4, "solver": "classic"})
            _, _, result = load_game(chemin)
            self.assertIn("mines", result)
            self.assertEqual(len(result["mines"]), 3)
            self.assertTrue(all(len(m) == 2 for m in result["mines"]))
```

Dans `tests/test_server.py` (classe `TestServeurLocal`) :

```python
    def test_live_gagne_mines_exposees(self):
        # partie gagnée: les mines sont aussi exposées (fin de partie)
        from demineur.server import LiveState

        live = LiveState(seed=3, width=5, height=5, mines=2)
        for _ in range(60):
            live.step()
            if live.game.state.value != "playing":
                break
        data = live.payload()
        self.assertEqual(data["state"], "won")
        self.assertIn("mines", data)
        self.assertEqual(len(data["mines"]), 2)

    def test_duel_humain_gagne_mines_exposees(self):
        from demineur.game import GameState
        from demineur.server import DuelState

        état = DuelState(seed=5, width=5, height=5, mines=3)
        data = état.human_play({"kind": "reveal", "x": 0, "y": 0})
        while état.human.state is GameState.PLAYING:
            vue = état.human.view()
            sûres = [p for p in vue.hidden_cells()
                     if not vue.is_flagged(p) and not état.human.board.is_mine(p)]
            if not sûres:
                break
            data = état.human_play({"kind": "reveal", "x": sûres[0][0],
                                    "y": sûres[0][1]})
        self.assertEqual(data["human_state"], "won")
        self.assertIn("human_mines", data)
        self.assertEqual(len(data["human_mines"]), 3)
```

- [ ] **Step 2: Vérifier l'échec**

Run: `PYTHONPATH=src python3 -m unittest tests.test_artifacts tests.test_server -v`
Expected: FAIL sur les 3 nouveaux tests

- [ ] **Step 3: Implémenter**

`src/demineur/artifacts.py` — dans `save_game`, la ligne résultat devient :

```python
        résultat = {
            "kind": "result",
            "state": runner.game.state.value,
            "won": runner.game.state.value == "won",
            "moves": len(runner.events),
        }
        # fin de partie : toutes les mines archivées (replay), cliquées ou non
        if runner.game.board is not None:
            résultat["mines"] = [list(m) for m in sorted(runner.game.board.mines)]
```

`src/demineur/server.py` — `LiveState.payload` :

```python
        if self.game.state is not GameState.PLAYING and self.game.board is not None:
            data["mines"] = [list(m) for m in sorted(self.game.board.mines)]
```

(remplace la condition `is GameState.LOST`)

`DuelState.payload` — même remplacement pour les deux camps :

```python
        if self.human.state is not GameState.PLAYING and self.human.board is not None:
            data["human_mines"] = [list(m) for m in sorted(self.human.board.mines)]
        if self.solver_game.state is not GameState.PLAYING and self.solver_game.board is not None:
            data["solver_mines"] = [list(m) for m in sorted(self.solver_game.board.mines)]
```

- [ ] **Step 4: Vérifier** — Run: `PYTHONPATH=src python3 -m unittest discover -s tests 2>&1 | tail -3`. Expected: OK (les tests existants perdu ⊂ terminé restent valides).

- [ ] **Step 5: Commit**

```bash
git add src/demineur/artifacts.py src/demineur/server.py tests/
git commit -m "feat: mines exposées à toute fin de partie (gagnée ou perdue) — artefacts et payloads"
```

---

### Task 11: app.js — replay : bombes au coup final

**Files:**
- Modify: `web/app.js`
- Modify: `tests/test_frontend.py`

- [ ] **Step 1: Test échouant — fonction pure `bombesFinDePartie`**

Ajouter dans `tests/test_frontend.py` (classe `TestFonctionsPures`) :

```python
    def test_bombes_fin_de_partie(self):
        result_gagné = {"state": "won", "mines": [[1, 1], [2, 2]]}
        result_perdu = {"state": "lost", "mines": [[0, 0]]}
        result_sans = {"state": "won"}
        script = (
            "const app = require(" + json.dumps(APP_JS) + ");"
            "console.log(app.bombesFinDePartie(" + json.dumps(result_gagné) + ", 3, 4) + '|'"
            " + app.bombesFinDePartie(" + json.dumps(result_perdu) + ", 4, 4) + '|'"
            " + app.bombesFinDePartie(" + json.dumps(result_gagné) + ", 1, 4) + '|'"
            " + app.bombesFinDePartie(" + json.dumps(result_sans) + ", 4, 4));"
        )
        g, p, pas_dernier, sans = _node_exec(script, {}).strip().split("|")
        self.assertEqual(json.loads(g), [[1, 1], [2, 2]])
        self.assertEqual(json.loads(p), [[0, 0]])
        self.assertEqual(pas_dernier, "null")
        self.assertEqual(sans, "null")
```

- [ ] **Step 2: Vérifier l'échec** — `app.bombesFinDePartie is not a function`.

- [ ] **Step 3: Implémenter dans `web/app.js` (fonctions pures) et brancher `aller`**

```js
/* Mines à afficher au coup final d'une partie terminée (replay) :
 * uniquement au dernier coup, uniquement si l'artefact les archive. */
function bombesFinDePartie(result, coup, total) {
  if (!result || coup !== total - 1) return null;
  if (result.state !== "won" && result.state !== "lost") return null;
  return result.mines || null;
}
```

`afficherVue` gagne un paramètre mines (passé à `gridHtml`) :

```js
  function afficherVue(vueJson, event, mines) {
    var zone = document.getElementById("grille-replay");
    zone.innerHTML = gridHtml(vueJson, mines || []);
```

et `aller` calcule les mines de fin :

```js
  function aller(coup) {
    if (!état.partie) return;
    var n = état.partie.events.length;
    coup = Math.max(0, Math.min(n - 1, coup));
    état.coup = coup;
    var event = état.partie.events[coup];
    var bombes = bombesFinDePartie(état.partie.result, coup, n);
    afficherVue(event.view_after, event, bombes);
  }
```

Exporter `bombesFinDePartie` dans `module.exports`.

- [ ] **Step 4: Vérifier** — Run: `PYTHONPATH=src python3 -m unittest tests.test_frontend -v`. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/app.js tests/test_frontend.py
git commit -m "feat(web): replay — toutes les bombes affichées au coup final d'une partie terminée"
```

---

### Task 12: app.js + index.html — live/duel interactifs en mode statique

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`

- [ ] **Step 1: `web/index.html` — charger les modules**

Remplacer la ligne `<script src="app.js"></script>` par :

```html
<script src="engine.js"></script>
<script src="solver.js"></script>
<script src="interactif.js"></script>
<script src="app.js"></script>
```

- [ ] **Step 2: `web/app.js` — brancher les contrôleurs en mode statique**

Dans `initUI(statique)` :

a) Déclarer `var liveJS = null; var duelJS = null;` avec les autres variables.

b) Remplacer le bloc d'adaptation statique (celui qui masquait les panneaux live/duel et affichait la note) par la seule mise à jour du pied de page :

```js
  if (statique) {
    var notePied = document.getElementById("note-locale");
    if (notePied) {
      notePied.textContent = "Version en ligne — modes interactifs 100% navigateur " +
        "(moteur + solveur en JavaScript). Les parties jouées ici ne sont pas " +
        "archivées : lancez demineur serve en local pour les retrouver dans le Replay.";
    }
  }
```

c) Boutons live — chaque handler teste `statique` en premier :

```js
  document.getElementById("btn-live-new").addEventListener("click", function () {
    if (statique) {
      liveJS = new LiveJS(parseInt(document.getElementById("live-seed").value, 10) || 0,
                          parseInt(document.getElementById("live-w").value, 10) || 9,
                          parseInt(document.getElementById("live-h").value, 10) || 9,
                          parseInt(document.getElementById("live-mines").value, 10) || 10);
      liveMAJ(liveJS.payload());
      return;
    }
    var q = "?seed=" + document.getElementById("live-seed").value +
      "&w=" + document.getElementById("live-w").value +
      "&h=" + document.getElementById("live-h").value +
      "&mines=" + document.getElementById("live-mines").value;
    api("/api/live/new" + q).then(liveMAJ)
      .catch(erreur("live-etat", "nouvelle partie impossible"));
  });
  document.getElementById("btn-live-step").addEventListener("click", function () {
    if (statique) {
      if (liveJS) { liveJS.étape(); liveMAJ(liveJS.payload()); }
      return;
    }
    api("/api/live/step").then(liveMAJ)
      .catch(erreur("live-etat", "aucune partie en cours"));
  });
```

La boucle auto (« lecture auto ») : si `statique`, dans le setInterval → `liveJS.étape(); liveMAJ(liveJS.payload());` et arrêt quand `liveJS.payload().state !== "playing"`.

d) Duel :

```js
  document.getElementById("btn-duel-new").addEventListener("click", function () {
    if (statique) {
      duelJS = new DuelJS(parseInt(document.getElementById("duel-seed").value, 10) || 0,
                          parseInt(document.getElementById("duel-w").value, 10) || 9,
                          parseInt(document.getElementById("duel-h").value, 10) || 9,
                          parseInt(document.getElementById("duel-mines").value, 10) || 10);
      duelMAJ(duelJS.payload());
      return;
    }
    /* code existant api /api/duel/new inchangé */
  });
```

Les handlers de clic sur `#grille-duel-humain` (et `contextmenu`) insèrent en tête :

```js
    if (statique) {
      if (!duelJS) return;
      try {
        duelMAJ(duelJS.coupHumain({ kind: "reveal", x: parseInt(el.dataset.x, 10),
                                    y: parseInt(el.dataset.y, 10) }));
      } catch (err) {
        document.getElementById("duel-etat").textContent = err.message;
      }
      return;
    }
```

- [ ] **Step 3: Vérifier syntaxe et suite**

Run: `node --check web/app.js && PYTHONPATH=src python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: syntaxe OK, tous les tests PASS.

- [ ] **Step 4: Vérification intégrée (mode statique complet, sans DOM)**

```bash
PYTHONPATH=src python3 scripts/export_site.py --out /tmp/site-check && \
node -e "
const I = require('/tmp/site-check/interactif.js');
const duel = new I.DuelJS(5, 5, 5, 3);
duel.coupHumain({kind: 'reveal', x: 0, y: 0});
const mine = duel.humain.positionsMines()[0];
const p = duel.coupHumain({kind: 'reveal', x: mine[0], y: mine[1]});
if (p.human_state !== 'lost' || !Array.isArray(p.human_mines)) process.exit(1);
console.log('OK: duel perdu, mines exposées:', p.human_mines.length,
            '| solveur:', p.solver_state);
"
```

Expected: `OK: duel perdu, mines exposées: 3 | solveur: won` (ou lost).

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat(web): live et duel interactifs en mode en ligne — moteur et solveur JS côté navigateur"
```

---

### Task 13: export, docs, suite complète

**Files:**
- Modify: `scripts/export_site.py`
- Modify: `docs/web.md`, `docs/PLAN.md`, `README.md`

- [ ] **Step 1: `scripts/export_site.py`** — liste des assets :

```python
ASSETS = ("index.html", "style.css", "app.js", "engine.js", "solver.js", "interactif.js")
```

- [ ] **Step 2: `docs/web.md`** — remplacer le paragraphe « Le frontend détecte le mode... Live et Duel ... affichent une note explicative » par :

```markdown
Le frontend détecte le mode au chargement : serveur local (``/api/...``) ou
site statique (``api/*.json``). En mode statique, les onglets Live et Duel
tournent intégralement dans le navigateur : le moteur de jeu et le solveur
classique sont portés en JavaScript (``web/engine.js``, ``web/solver.js``,
``web/interactif.js``) et produisent les mêmes formats (vue A15, événements
B10, payloads). INV1 y est respecté : ``solver.js`` ne reçoit jamais le plateau
réel. Limites du mode en ligne : pas d'archivage des parties jouées (utiliser
``demineur serve`` en local pour les retrouver dans le Replay).
```

- [ ] **Step 3: Journal `docs/PLAN.md`** (INV3) — ajouter une ligne session 6 : port JS du moteur et du solveur (A/R), contrôleurs LiveJS/DuelJS, mines de fin de partie dans tous les modes, N tests verts.

- [ ] **Step 4: Suite complète**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: OK — noter le nombre total dans le commit.

- [ ] **Step 5: Commit**

```bash
git add scripts/export_site.py docs/ README.md
git commit -m "docs+export: modes interactifs en ligne documentés, assets JS exportés"
```

---

### Task 14: Push et vérification Netlify

- [ ] **Step 1: Pousser**

```bash
git push origin main
```

- [ ] **Step 2: Attendre le build puis vérifier la disponibilité**

```bash
sleep 60
curl -s -o /dev/null -w "engine.js: %{http_code}\n" https://conquering-ai-enpc.netlify.app/engine.js
curl -s -o /dev/null -w "solver.js: %{http_code}\n" https://conquering-ai-enpc.netlify.app/solver.js
curl -s -o /dev/null -w "interactif.js: %{http_code}\n" https://conquering-ai-enpc.netlify.app/interactif.js
```

Expected: `200` x3.

- [ ] **Step 3: Simulation client contre le site déployé**

```bash
node - <<'EOF'
const https = require("https");
function get(url) {
  return new Promise((ok, ko) => {
    https.get(url, r => {
      if (r.statusCode !== 200) return ko(new Error(url + " -> " + r.statusCode));
      let b = ""; r.on("data", c => b += c); r.on("end", () => ok(b));
    }).on("error", ko);
  });
}
(async () => {
  const base = "https://conquering-ai-enpc.netlify.app";
  const E = await get(base + "/engine.js");
  const S = await get(base + "/solver.js");
  const I = await get(base + "/interactif.js");
  /* ordre de chargement navigateur : engine, solver, interactif en globals */
  const source = E + "\n" + S + "\n" + I + "\nmodule.exports = { LiveJS, DuelJS };";
  const module = { exports: {} };
  new Function("module", "exports", source)(module, module.exports);
  const live = new module.exports.LiveJS(1, 5, 5, 3);
  let p;
  for (let i = 0; i < 60; i++) { live.étape(); p = live.payload(); if (p.state !== "playing") break; }
  if (!["won", "lost"].includes(p.state)) throw new Error("partie non terminée");
  console.log("partie live en ligne:", p.state, "| mines exposées:", (p.mines || []).length);
  console.log("NETLIFY OK");
})().catch(e => { console.error("ÉCHEC:", e.message); process.exit(1); });
EOF
```

Expected: `partie live en ligne: won|lost | mines exposées: 2-3` puis `NETLIFY OK`.

- [ ] **Step 4: Vérification manuelle finale par l'utilisateur** sur https://conquering-ai-enpc.netlify.app : onglets Live et Duel jouables dans le navigateur, bombes visibles à toute fin de partie, replay avec bombes au coup final. (Demander à l'utilisateur de confirmer.)

---

## Self-Review

**Spec coverage :**
- « Mode interactif en ligne » → Tasks 2-9 (moteur + solveur + contrôleurs JS), Task 12 (branchement UI), Tasks 13-14 (export + déploiement). Couvert.
- « Bombes à la fin de la partie, cliquées ou non » → Task 10 (backend : artefacts + payloads, gagné OU perdu), Task 11 (replay), Task 9 (payloads JS identiques), Task 12 (UI existante déjà câblée sur `data.mines`). Couvert.
- INV1 → `solver.js` ne référence jamais `engine.js` ; test `test_vue_sans_fuite` (Task 2) ; mines exposées uniquement après fin (Tasks 9-10). Couvert.

**Placeholder scan :** aucun TODO/TBD ; chaque étape contient le code exact ou la commande avec résultat attendu.

**Type consistency :** positions internes JS = `"x,y"` partout ; payloads LiveJS `{state, view, moves, event, mines?}` et DuelJS `{human, solver, human_state, solver_state, human_mines?, solver_mines?}` conformes aux consommateurs existants `liveMAJ`/`duelMAJ` ; `bombesFinDePartie(result, coup, total)` identique entre test et implémentation ; `Engine`/`SOLVER`/`INTERACTIF` noms de constantes de test cohérents.
