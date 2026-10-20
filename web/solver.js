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

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    posClé: posClé, parseClé: parseClé,
    extraireContraintes: extraireContraintes, déduire: déduire,
    composantes: composantes, énumérer: énumérer, classer: classer,
    MAX_CELLULES_CSP: MAX_CELLULES_CSP, MAX_SOLUTIONS_CSP: MAX_SOLUTIONS_CSP,
  };
}
