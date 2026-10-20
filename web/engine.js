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
  /* Comme game.py : 0 <= mines_count <= width*height à la construction ;
   * le contrôle "placement impossible" n'a lieu qu'au premier coup. */
  if (!(minesCount >= 0) || minesCount > width * height) {
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

/* GameRunner JS (port B09/B10) : applique une action {kind,x,y|reason},
 * journalise l'événement B10 (vues A15 avant/après), rejette les coups
 * illégaux (compteur + abandon après N rejets consécutifs). */
function RunnerJS(jeu, maxMoves, maxRejets) {
  this.jeu = jeu;
  this.maxMoves = maxMoves === undefined ? 10000 : maxMoves;
  this.maxRejets = maxRejets === undefined ? 5 : maxRejets;
  if (!(this.maxMoves > 0)) {
    throw new Error("max_moves doit être positif");
  }
  if (!(this.maxRejets > 0)) {
    throw new Error("max_rejections doit être positif");
  }
  this.events = [];
  this.abandon = false;
  this._rejets = 0;
}

RunnerJS.prototype.appliquer = function (action, justification) {
  var vueAvant = this.jeu.vue();
  var event = {
    move: this.events.length,
    view_before: vueAvant,
    action: { kind: action.kind, x: action.x, y: action.y, reason: action.reason },
    justification: typeof justification === "string" ? justification : null,
    view_after: vueAvant,
    result: "ok",
    detail: null,
  };
  if (action.kind === "giveup") {
    event.result = "gave_up";
    event.detail = action.reason || "";
    event.view_after = this.jeu.vue();
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
    event.view_after = this.jeu.vue();
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

if (typeof module !== "undefined" && module.exports) {
  module.exports = { Jeu: Jeu, mulberry32: mulberry32, voisins: voisins,
                     RunnerJS: RunnerJS };
}
