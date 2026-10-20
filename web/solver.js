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

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    posClé: posClé, parseClé: parseClé,
    extraireContraintes: extraireContraintes, déduire: déduire,
    composantes: composantes, énumérer: énumérer, classer: classer,
    MAX_CELLULES_CSP: MAX_CELLULES_CSP, MAX_SOLUTIONS_CSP: MAX_SOLUTIONS_CSP,
    analyser: analyser, probabilitésExactes: probabilitésExactes,
    uniformiser: uniformiser, comb: comb, casesCachées: casesCachées,
  };
}
