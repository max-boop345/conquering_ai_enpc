/* Démineur local — application (JS pur, aucun bundler, aucune ressource distante).
 *
 * Structure : fonctions pures d'abord (testables sans DOM), puis initialisation
 * de l'interface sous garde `typeof document`. */

"use strict";

/* ============ fonctions pures (testables, W05) ============ */

/* Rendu d'une case depuis sa description JSON (état visible uniquement). */
function cellHtml(cell, x, y) {
  if (cell.state === "flagged") {
    return '<div class="case drapeau" data-x="' + x + '" data-y="' + y + '">F</div>';
  }
  if (cell.state === "revealed") {
    var n = cell.adjacent_mines;
    var classe = n === 0 ? "" : " n" + n;
    var texte = n === 0 ? "" : String(n);
    return '<div class="case révélée' + classe + '" data-x="' + x + '" data-y="' + y + '">' +
      texte + "</div>";
  }
  return '<div class="case cachée" data-x="' + x + '" data-y="' + y + '"></div>';
}

/* Rendu de la grille complète depuis une vue JSON (format A15/W03).
 * `mines` (optionnel) : liste [x,y] exposée uniquement sur une partie
 * terminée — rend les bombes visibles. */
function gridHtml(viewJson, mines) {
  var bombes = {};
  (mines || []).forEach(function (m) {
    bombes[m[0] + "," + m[1]] = true;
  });
  var lignes = [];
  for (var y = 0; y < viewJson.height; y++) {
    for (var x = 0; x < viewJson.width; x++) {
      if (bombes[x + "," + y]) {
        lignes.push('<div class="case minée" data-x="' + x + '" data-y="' + y +
          '">B</div>');
        continue;
      }
      lignes.push(cellHtml(viewJson.grid[y][x], x, y));
    }
  }
  return '<div class="grille" style="grid-template-columns: repeat(' +
    viewJson.width + ', 28px)">' + lignes.join("") + "</div>";
}

/* Bandeau de fin de partie posé sur une grille (W14).
 * "lost" → rouge, "won" → vert, "playing" → rien. */
function overlayBadge(state) {
  if (state === "lost") return '<div class="bandeau perdu">Perdu</div>';
  if (state === "won") return '<div class="bandeau gagné">Gagné</div>';
  return "";
}

/* Mines à afficher au coup final d'une partie terminée (replay) :
 * uniquement au dernier coup, uniquement si l'artefact les archive. */
function bombesFinDePartie(result, coup, total) {
  if (!result || coup < total - 1) return null;
  if (result.state !== "won" && result.state !== "lost") return null;
  return result.mines || null;
}

/* Couleur de heatmap (W08) : vert (probabilité nulle) → rouge (probabilité
 * forte). La teinte couvre [0, 0.5] pour bien distinguer les valeurs usuelles
 * (densité de mines ~0.12 en beginner, 50/50 = 0.5). */
function heatColor(p) {
  var t = Math.min(Math.max(p || 0, 0), 0.5) / 0.5;
  return "hsl(" + Math.round(120 * (1 - t)) + ", 75%, 45%)";
}

/* Texte de heatmap : pourcentage affiché dans la case (vide si ~0). */
function heatText(p) {
  if (p === null || p === undefined || p < 0.005) return "";
  return Math.round(p * 100) + "%";
}

/* Résumé d'un événement B10 pour le panneau de justification (W07). */
function eventSummary(event) {
  if (!event) return "—";
  var a = event.action;
  var cible = a.x !== undefined ? "(" + a.x + "," + a.y + ")" : (a.reason || "");
  return "#" + String(event.move).padStart(3, "0") + " " + a.kind + cible +
    " — " + (event.justification || "—") + " [" + event.result + "]";
}

/* Barre d'un graphique benchmark en SVG pur (W10). */
function benchmarkChart(results) {
  var noms = Object.keys(results);
  if (noms.length === 0) return "<p class='aide'>Aucun benchmark disponible. " +
    "Lancez : demineur benchmark --save docs/benchmarks.md --json games/benchmarks.json</p>";
  var largeur = 640, hauteur = 40 + noms.length * 44;
  var parts = ['<svg width="' + largeur + '" height="' + hauteur +
    '" xmlns="http://www.w3.org/2000/svg">'];
  noms.sort(function (a, b) { return results[b].win_rate - results[a].win_rate; })
    .forEach(function (nom, i) {
      var r = results[nom];
      var w = Math.round(r.win_rate * (largeur - 220));
      var y = 20 + i * 44;
      parts.push('<text x="10" y="' + (y + 16) + '" fill="#e8e6e3" font-size="14">' +
        nom + "</text>");
      parts.push('<rect x="120" y="' + y + '" width="' + (largeur - 220) +
        '" height="24" fill="#262b36" rx="3"/>');
      parts.push('<rect x="120" y="' + y + '" width="' + w +
        '" height="24" fill="#7aa2f7" rx="3"/>');
      parts.push('<text x="' + (128 + w) + '" y="' + (y + 17) +
        '" fill="#e8e6e3" font-size="13">' +
        (r.win_rate * 100).toFixed(1) + "%</text>");
    });
  parts.push("</svg>");
  return parts.join("");
}

/* Table benchmark (W10). */
function benchmarkTable(results) {
  var noms = Object.keys(results);
  if (noms.length === 0) return "<p class='aide'>Aucun résultat.</p>";
  var html = "<tr><th>solveur</th><th>win-rate</th><th>victoires</th>" +
    "<th>défaites</th><th>abandons</th><th>coups moyens</th></tr>";
  noms.sort(function (a, b) { return results[b].win_rate - results[a].win_rate; })
    .forEach(function (nom) {
      var r = results[nom];
      html += "<tr><td>" + nom + "</td><td>" + (r.win_rate * 100).toFixed(1) +
        "%</td><td>" + (r.wins || 0) + "</td><td>" + (r.losses || 0) +
        "</td><td>" + (r.gave_ups || 0) + "</td><td>" + (r.avg_moves || "—") + "</td></tr>";
    });
  return html;
}

/* Section complète d'une difficulté : titre + table + graphique. */
function benchmarkSection(doc) {
  var g = doc.grid ? " — " + doc.grid.width + "x" + doc.grid.height +
    ", " + doc.grid.mines + " mines" : "";
  return "<h3>" + (doc.difficulty || "custom") + g +
    " (" + (doc.seeds || 0) + " seeds)</h3>" +
    "<table>" + benchmarkTable(doc.results || {}) + "</table>" +
    benchmarkChart(doc.results || {});
}

/* Toutes les difficultés de /api/benchmarks (W10). */
function benchmarksSections(data) {
  var docs = (data && data.benchmarks) || [];
  if (docs.length === 0) {
    return "<p class='aide'>Aucun benchmark disponible. Lancez : " +
      "<code>demineur benchmark --difficulty beginner --seeds 30 " +
      "--solvers random,rule,classic --json games/benchmarks.json</code></p>";
  }
  return docs.map(benchmarkSection).join("");
}

/* ============ interface (DOM) ============ */

/* Mapping endpoint local -> fichier statique pré-généré (mode Netlify).
 * Retourne null pour tout ce qui nécessite le backend (live, duel). */
function staticUrl(chemin) {
  var m;
  if (chemin === "/api/games") return "api/games.json";
  if (chemin === "/api/solvers") return "api/solvers.json";
  if (chemin === "/api/benchmarks") return "api/benchmarks.json";
  m = chemin.match(/^\/api\/games\/([^/]+)\/analysis\/\d+$/);
  if (m) return "api/games/" + m[1] + "/analysis.json";
  m = chemin.match(/^\/api\/games\/([^/]+)$/);
  if (m) return "api/games/" + m[1] + ".json";
  return null;
}

function initApp() {
  /* détection du mode: serveur local (Python) ou site statique pré-généré */
  fetch("/api/solvers").then(function (r) {
    if (r.ok) { initUI(false); return; }
    throw new Error("pas local");
  }).catch(function () {
    fetch("api/solvers.json").then(function (r) {
      if (r.ok) { initUI(true); return; }
      throw new Error("pas statique");
    }).catch(function () {
      initUI(true);
      document.getElementById("bannière-serveur").classList.remove("cache");
    });
  });
}

function initUI(statique) {
  var okJson = function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  };
  var analysesCache = {};
  function analyseStatique(id, coup) {
    if (!analysesCache[id]) {
      analysesCache[id] = fetch("api/games/" + id + "/analysis.json").then(okJson);
    }
    return analysesCache[id].then(function (data) {
      var c = data.moves[coup];
      if (!c) throw new Error("coup hors bornes");
      return c;
    });
  }
  var api = function (chemin) {
    if (statique) {
      var m = chemin.match(/^\/api\/games\/([^/]+)\/analysis\/(\d+)$/);
      if (m) return analyseStatique(m[1], parseInt(m[2], 10));
      var url = staticUrl(chemin);
      if (!url) return Promise.reject(new Error("indisponible en ligne"));
      return fetch(url).then(okJson);
    }
    return fetch(chemin).then(okJson);
  };
  var apiPost = function (chemin, data) {
    if (statique) return Promise.reject(new Error("mode en ligne"));
    return fetch(chemin, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  };
  var erreur = function (zone, préfixe) {
    return function (err) {
      var cible = document.getElementById(zone);
      if (cible) cible.textContent = préfixe + " — " + err.message;
    };
  };

  /* ---------- onglets ---------- */
  var onglets = document.querySelectorAll(".tab");
  onglets.forEach(function (btn) {
    btn.addEventListener("click", function () {
      onglets.forEach(function (b) { b.classList.remove("actif"); });
      btn.classList.add("actif");
      document.querySelectorAll(".panneau").forEach(function (p) {
        p.classList.remove("actif");
      });
      document.getElementById(btn.dataset.tab).classList.add("actif");
      /* les parties jouées (live, duel) apparaissent sans recharger */
      if (btn.dataset.tab === "replay") partiesListe();
    });
  });

  /* ---------- replay (W06, W07, W08, W09) ---------- */
  var état = { partie: null, coup: -1, auto: null, heatmap: false, csp: false };

  function partiesListe() {
    api("/api/games").then(function (data) {
      var ul = document.getElementById("liste-parties");
      ul.innerHTML = "";
      data.games.forEach(function (g) {
        var li = document.createElement("li");
        li.textContent = g.solver + " · seed " + g.seed + " · " + g.width + "x" +
          g.height + " · " + g.moves + " coups";
        li.addEventListener("click", function () { chargerPartie(g.id, li); });
        ul.appendChild(li);
      });
      if (data.games.length === 0) {
        ul.innerHTML = "<li class='aide'>Aucune partie loggée dans games/.</li>";
      }
    }).catch(erreur("liste-parties", "serveur injoignable"));
  }

  function chargerPartie(id, li) {
    document.querySelectorAll("#liste-parties li").forEach(function (l) {
      l.classList.remove("sélectionné");
    });
    if (li) li.classList.add("sélectionné");
    api("/api/games/" + id).then(function (data) {
      état.partie = data;
      état.coup = -1;
      document.getElementById("replay-controles").classList.remove("cache");
      document.getElementById("replay-options").classList.remove("cache");
      aller(0);
    });
  }

  function afficherVue(vueJson, event, mines) {
    var zone = document.getElementById("grille-replay");
    zone.innerHTML = gridHtml(vueJson, mines || []);
    document.getElementById("justification").textContent = eventSummary(event);
    document.getElementById("compteur-coups").textContent =
      "coup " + (état.coup + 1) + " / " + état.partie.events.length;
    var options = document.getElementById("opt-heatmap").checked ||
      document.getElementById("opt-csp").checked;
    if (options) appliquerAnalyse();
  }

  function appliquerAnalyse() {
    if (!état.partie) return;
    var id = état.partie.header.id;
    api("/api/games/" + id + "/analysis/" + état.coup).then(function (a) {
      document.querySelectorAll("#grille-replay .case").forEach(function (el) {
        el.classList.remove("chauffe", "csp", "mine-déduite", "frontière", "sure");
        el.style.removeProperty("background");
        if (el.classList.contains("cachée")) el.innerHTML = "";
      });
      if (document.getElementById("opt-heatmap").checked) {
        Object.keys(a.probabilities).forEach(function (clé) {
          var p = a.probabilities[clé];
          var el = document.querySelector(
            '#grille-replay .case[data-x="' + clé.split(",")[0] +
            '"][data-y="' + clé.split(",")[1] + '"]');
          if (el && el.classList.contains("cachée")) {
            el.style.background = heatColor(p);
            el.innerHTML = '<span class="p">' + heatText(p) + "</span>";
          }
        });
      }
      if (document.getElementById("opt-csp").checked) {
        /* la frontière active : toutes les contraintes R01 (W09) */
        (a.constraints || []).forEach(function (contrainte) {
          contrainte.cells.forEach(function (pos) {
            var el = document.querySelector(
              '#grille-replay .case[data-x="' + pos[0] + '"][data-y="' + pos[1] + '"]');
            if (el) el.classList.add("frontière");
          });
        });
        /* les déductions : coups sûrs (vert) et mines certaines (rouge) */
        a.safe.forEach(function (pos) {
          var el = document.querySelector(
            '#grille-replay .case[data-x="' + pos[0] + '"][data-y="' + pos[1] + '"]');
          if (el) el.classList.add("sure");
        });
        a.mines.forEach(function (pos) {
          var el = document.querySelector(
            '#grille-replay .case[data-x="' + pos[0] + '"][data-y="' + pos[1] + '"]');
          if (el) el.classList.add("mine-déduite");
        });
      }
    }).catch(function () { /* coup sans analyse: silencieux */ });
  }

  function aller(coup) {
    if (!état.partie) return;
    var n = état.partie.events.length;
    coup = Math.max(0, Math.min(n - 1, coup));
    état.coup = coup;
    var event = état.partie.events[coup];
    var bombes = bombesFinDePartie(état.partie.result, coup, n);
    afficherVue(event.view_after, event, bombes);
  }

  function vitesse() {
    return 1.4 - (parseInt(document.getElementById("vitesse").value, 10) * 0.12);
  }

  function toggleAuto() {
    if (état.auto) {
      clearInterval(état.auto);
      état.auto = null;
      document.getElementById("btn-auto").textContent = "lecture auto";
      return;
    }
    état.auto = setInterval(function () {
      if (!état.partie) return;
      if (état.coup >= état.partie.events.length - 1) {
        toggleAuto();
        return;
      }
      aller(état.coup + 1);
    }, vitesse() * 1000);
    document.getElementById("btn-auto").textContent = "pause";
  }

  document.getElementById("btn-premier").addEventListener("click", function () { aller(0); });
  document.getElementById("btn-prec").addEventListener("click", function () { aller(état.coup - 1); });
  document.getElementById("btn-suiv").addEventListener("click", function () { aller(état.coup + 1); });
  document.getElementById("btn-dernier").addEventListener("click", function () {
    aller(état.partie.events.length - 1);
  });
  document.getElementById("btn-fatal").addEventListener("click", function () {
    var events = état.partie.events;
    for (var i = 0; i < events.length; i++) {
      if (events[i].result === "ok" && events[i].view_after.state === "lost") {
        aller(i);
        return;
      }
    }
    aller(events.length - 1);
  });
  document.getElementById("btn-auto").addEventListener("click", toggleAuto);
  document.getElementById("opt-heatmap").addEventListener("change", appliquerAnalyse);
  document.getElementById("opt-csp").addEventListener("change", appliquerAnalyse);

  /* ---------- benchmarks (W10) ---------- */
  function chargerBenchmarks() {
    api("/api/benchmarks").then(function (data) {
      document.getElementById("benchmarks-contenu").innerHTML =
        benchmarksSections(data);
    }).catch(function () {
      document.getElementById("benchmarks-contenu").innerHTML =
        "<p class='aide'>Serveur injoignable — lancez <code>demineur serve</code>.</p>";
    });
  }

  /* ---------- live (W13) ---------- */
  var liveAuto = null;
  var liveJS = null;

  /* Arrête la lecture auto (statique ou locale) et réinitialise le bouton. */
  function stopperLiveAuto() {
    clearInterval(liveAuto);
    liveAuto = null;
    document.getElementById("btn-live-auto").textContent = "lecture auto";
  }

  /* Paramètres d'une nouvelle partie (live/duel) : `query` pour l'API locale
   * (chaînes brutes), `jeu` pour les contrôleurs JS (entiers coercés). */
  function lireParams(préfixe) {
    var champ = function (nom) {
      return document.getElementById(préfixe + "-" + nom).value;
    };
    return {
      query: { seed: champ("seed"), w: champ("w"), h: champ("h"), mines: champ("mines") },
      jeu: { seed: parseInt(champ("seed"), 10) || 0, w: parseInt(champ("w"), 10) || 9,
             h: parseInt(champ("h"), 10) || 9, mines: parseInt(champ("mines"), 10) || 10 },
    };
  }

  function liveMAJ(data) {
    document.getElementById("grille-live").innerHTML =
      overlayBadge(data.state) + gridHtml(data.view, data.mines);
    document.getElementById("live-etat").textContent =
      data.state + " · " + data.moves + " coups";
    document.getElementById("live-justification").textContent =
      data.event ? eventSummary(data.event) : "—";
  }

  document.getElementById("btn-live-new").addEventListener("click", function () {
    var p = lireParams("live");
    if (statique) {
      try {
        liveJS = new LiveJS(p.jeu.seed, p.jeu.w, p.jeu.h, p.jeu.mines);
        liveMAJ(liveJS.payload());
      } catch (err) {
        document.getElementById("live-etat").textContent = err.message;
      }
      return;
    }
    api("/api/live/new?seed=" + p.query.seed + "&w=" + p.query.w +
      "&h=" + p.query.h + "&mines=" + p.query.mines).then(liveMAJ)
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
  document.getElementById("btn-live-auto").addEventListener("click", function () {
    if (liveAuto) {
      stopperLiveAuto();
      return;
    }
    if (statique) {
      if (!liveJS) {
        document.getElementById("live-etat").textContent = "aucune partie en cours";
        return;
      }
      liveAuto = setInterval(function () {
        liveJS.étape();
        var p = liveJS.payload();
        liveMAJ(p);
        if (p.state !== "playing") stopperLiveAuto();
      }, 350);
      this.textContent = "pause";
      return;
    }
    api("/api/live/step").then(function (data) {
      if (data.state === "playing") {
        liveAuto = setInterval(function () {
          api("/api/live/step").then(function (data) {
            liveMAJ(data);
            if (data.state !== "playing") stopperLiveAuto();
          }).catch(function () {
            clearInterval(liveAuto);
            liveAuto = null;
          });
        }, 350);
        document.getElementById("btn-live-auto").textContent = "pause";
      }
      liveMAJ(data);
    }).catch(erreur("live-etat", "aucune partie en cours"));
  });

  /* ---------- duel (W14) ---------- */
  var duelActif = null;
  var duelJS = null;

  function duelMAJ(data) {
    document.getElementById("grille-duel-humain").innerHTML =
      overlayBadge(data.human_state) +
      gridHtml(data.human, data.human_mines);
    document.getElementById("grille-duel-solveur").innerHTML =
      overlayBadge(data.solver_state) +
      gridHtml(data.solver, data.solver_mines);
    var message = "vous: " + data.human_state + " · solveur: " + data.solver_state;
    if (data.human_state === "lost") {
      message = "Vous avez perdu — le solveur continue sa partie.";
    } else if (data.human_state === "won") {
      message = "Vous avez gagné !";
    }
    document.getElementById("duel-etat").textContent = message;
  }

  document.getElementById("btn-duel-new").addEventListener("click", function () {
    var p = lireParams("duel");
    if (statique) {
      try {
        duelJS = new DuelJS(p.jeu.seed, p.jeu.w, p.jeu.h, p.jeu.mines);
        duelMAJ(duelJS.payload());
      } catch (err) {
        document.getElementById("duel-etat").textContent = err.message;
      }
      return;
    }
    var q = "?seed=" + p.query.seed + "&w=" + p.query.w +
      "&h=" + p.query.h + "&mines=" + p.query.mines;
    api("/api/duel/new" + q).then(function (data) {
      duelActif = data;
      duelMAJ(data);
    }).catch(erreur("duel-etat", "nouveau duel impossible"));
  });

  /* Clic humain sur la grille duel (reveal/flag) : statique → DuelJS (erreur
   * affichée), local → apiPost (flag refusé ignoré en silence, comme avant). */
  function coupDuel(kind, e) {
    var el = e.target.closest(".case");
    if (!el) return;
    if (statique) {
      if (!duelJS) return;
      try {
        duelMAJ(duelJS.coupHumain({ kind: kind, x: parseInt(el.dataset.x, 10),
                                    y: parseInt(el.dataset.y, 10) }));
      } catch (err) {
        document.getElementById("duel-etat").textContent = err.message;
      }
      return;
    }
    if (!duelActif) return;
    apiPost("/api/duel/human", {
      kind: kind, x: parseInt(el.dataset.x, 10), y: parseInt(el.dataset.y, 10),
    }).then(duelMAJ).catch(function (err) {
      if (kind === "flag") return; /* drapeau déjà posé */
      document.getElementById("duel-etat").textContent = "coup refusé: " + err.message;
    });
  }

  document.getElementById("grille-duel-humain").addEventListener("click", function (e) {
    coupDuel("reveal", e);
  });
  document.getElementById("grille-duel-humain").addEventListener("contextmenu", function (e) {
    e.preventDefault();
    coupDuel("flag", e);
  });

  /* ---------- adaptation au mode en ligne (statique) ---------- */
  if (statique) {
    var notePied = document.getElementById("note-locale");
    if (notePied) {
      notePied.textContent = "Version en ligne — modes interactifs 100% navigateur " +
        "(moteur + solveur en JavaScript). Les parties jouées ici ne sont pas " +
        "archivées : lancez demineur serve en local pour les retrouver dans le Replay.";
    }
  }

  /* ---------- démarrage ---------- */
  partiesListe();
  chargerBenchmarks();
}

if (typeof document !== "undefined" && typeof fetch !== "undefined") {
  document.addEventListener("DOMContentLoaded", initApp);
}

/* export pour les tests (node) */
if (typeof module !== "undefined" && module.exports) {
  module.exports = { gridHtml, cellHtml, heatColor, heatText, eventSummary,
                     bombesFinDePartie,
                     benchmarkChart, benchmarkTable, benchmarkSection,
                     benchmarksSections, overlayBadge, staticUrl };
}
