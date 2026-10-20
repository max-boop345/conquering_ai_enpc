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
