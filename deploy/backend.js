/* Backend navigateur pour la version Netlify (aucun serveur Python en ligne).
 *
 * Intercepte fetch("/api/...") avant app.js :
 * - routes en lecture seule (parties, analyses, benchmarks) → JSON statiques
 *   figés au build par deploy/build_site.py ;
 * - routes live/duel → moteur Python exécuté dans le navigateur via Pyodide
 *   (chargé à la première partie, puis gardé en mémoire de l'onglet).
 */
(function () {
  "use strict";
  var fetchOrigine = window.fetch.bind(window);
  var DYNAMIQUE = /^\/api\/(live|duel)(\/|$)/;
  var moteur = null;

  function réponse(code, corps) {
    return new Response(corps, {
      status: code,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }

  function annoncer(texte) {
    ["live-etat", "duel-etat"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.textContent = texte;
    });
  }

  function chargerScript(src) {
    return new Promise(function (ok, ko) {
      var s = document.createElement("script");
      s.src = src;
      s.onload = ok;
      s.onerror = function () { ko(new Error("chargement de " + src + " impossible")); };
      document.head.appendChild(s);
    });
  }

  function chargerMoteur() {
    if (moteur) return moteur;
    annoncer("chargement du moteur Python (quelques secondes)…");
    moteur = chargerScript("/pyodide/pyodide.js").then(function () {
      return Promise.all([
        window.loadPyodide({ indexURL: "/pyodide/" }),
        fetchOrigine("/demineur.zip").then(function (r) {
          if (!r.ok) throw new Error("demineur.zip: HTTP " + r.status);
          return r.arrayBuffer();
        }),
      ]);
    }).then(function (res) {
      var py = res[0];
      py.unpackArchive(res[1], "zip", { extractDir: "/home/pyodide/app" });
      py.runPython("import sys; sys.path.insert(0, '/home/pyodide/app')");
      return py.pyimport("demineur_bridge");
    }).catch(function (err) {
      moteur = null; // nouvel essai possible au prochain clic
      throw err;
    });
    return moteur;
  }

  function appelMoteur(chemin, url, init) {
    var méthode = ((init && init.method) || "GET").toUpperCase();
    return chargerMoteur().then(function (pont) {
      var résultat;
      if (méthode === "POST") {
        résultat = pont.post(chemin, (init && init.body) || "{}");
      } else {
        var params = {};
        url.searchParams.forEach(function (v, k) { params[k] = v; });
        résultat = pont.get(chemin, JSON.stringify(params));
      }
      var paire = résultat.toJs();
      résultat.destroy();
      return réponse(paire[0], paire[1]);
    });
  }

  window.fetch = function (entrée, init) {
    var brut = typeof entrée === "string" ? entrée : entrée.url;
    var url = new URL(brut, window.location.href);
    if (url.origin !== window.location.origin || url.pathname.indexOf("/api/") !== 0) {
      return fetchOrigine(entrée, init);
    }
    var chemin = url.pathname.replace(/\/+$/, "");
    if (DYNAMIQUE.test(chemin)) return appelMoteur(chemin, url, init);
    return fetchOrigine(chemin + ".json", { cache: "no-cache" });
  };
})();
