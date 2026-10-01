"""CLI complète (F01) — intègre R15 (solve) et W17 (serve).

Commandes : ``new`` | ``play`` | ``solve`` | ``benchmark`` | ``serve``.
"""

from __future__ import annotations

import argparse
import sys

from demineur.game import Game
from demineur.render import render_view
from demineur.solvers.classic import ClassicSolver


def _résous_jeu(argv: argparse.Namespace) -> Game:
    """Construit la partie selon --difficulty ou --w/--h/--mines."""
    if argv.difficulty:
        from demineur.presets import get_preset
        p = get_preset(argv.difficulty)
        return Game(p.width, p.height, p.mines, seed=argv.seed)
    return Game(argv.w, argv.h, argv.mines, seed=argv.seed)


def _fabrique_solver(méthode: str):
    if méthode == "classic":
        return ClassicSolver()
    if méthode == "random":
        from demineur.solvers.random_solver import RandomSolver
        return RandomSolver()
    if méthode == "rule":
        from demineur.solvers.rule_solver import RuleSolver
        return RuleSolver()
    raise SystemExit(f"méthode inconnue: {méthode!r} (classic | random | rule)")


def cmd_new(argv) -> int:
    jeu = _résous_jeu(argv)
    print(f"nouvelle partie {jeu.width}x{jeu.height} — {jeu.mines_count} mines — seed={argv.seed}")
    print(render_view(jeu.view()))
    return 0


def cmd_play(argv) -> int:
    from demineur.play import main as play_main
    return play_main([
        "--seed", str(argv.seed), "--w", str(argv.w),
        "--h", str(argv.h), "--mines", str(argv.mines),
    ])


def cmd_solve(argv) -> int:
    from demineur.runner import GameRunner

    jeu = _résous_jeu(argv)
    solver = _fabrique_solver(argv.method)
    runner = GameRunner(jeu)
    difficulté = f" [{argv.difficulty}]" if argv.difficulty else ""
    print(f"solveur: {solver.name} — grille {jeu.width}x{jeu.height} "
          f"({jeu.mines_count} mines){difficulté} — seed={argv.seed}")
    résultat = runner.run(solver)
    if argv.explain:
        for event in runner.events:
            coup = event.action
            just = event.justification or "—"
            print(f"#{event.move:03d} {coup['kind']}({coup.get('x', '')}"
                  f"{',' + str(coup['y']) if 'y' in coup else ''}) — {just}")
    état = {"won": "gagné", "lost": "perdu", "playing": "abandonné"}[résultat.state.value]
    print(f"résultat: {état} en {résultat.moves} coups")
    return 0 if résultat.won else 1


def cmd_benchmark(argv) -> int:
    from demineur.benchmark import benchmark_to_json, format_table, run_benchmark

    classes = {}
    for nom in argv.solvers.split(","):
        nom = nom.strip()
        if nom == "random":
            from demineur.solvers.random_solver import RandomSolver
            classes[nom] = RandomSolver
        elif nom == "rule":
            from demineur.solvers.rule_solver import RuleSolver
            classes[nom] = RuleSolver
        elif nom == "classic":
            classes[nom] = ClassicSolver
        else:
            raise SystemExit(f"solveur inconnu: {nom!r}")
    difficulté = argv.difficulty or "beginner"
    résultats = run_benchmark(classes, difficulté, list(range(argv.seeds)))
    table = format_table(résultats)
    print(table)
    if argv.save:
        with open(argv.save, "w", encoding="utf-8") as f:
            f.write(table)
        print(f"résultats sauvegardés dans {argv.save}")
    return 0


def cmd_serve(argv) -> int:
    from demineur.server import main as serve_main
    return serve_main(argv)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demineur",
        description="Démineur local : moteur, solveurs classiques et visualisation",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def grille_args(p):
        p.add_argument("--seed", type=int, default=None)
        p.add_argument("--difficulty", default=None,
                       help="beginner | intermediate | expert (prioritaire sur --w/--h/--mines)")
        p.add_argument("--w", type=int, default=9)
        p.add_argument("--h", type=int, default=9)
        p.add_argument("--mines", type=int, default=10)

    p_new = sub.add_parser("new", help="nouvelle partie (affiche la grille de départ)")
    grille_args(p_new)
    p_new.set_defaults(fn=cmd_new)

    p_play = sub.add_parser("play", help="jouer au clavier")
    grille_args(p_play)
    p_play.set_defaults(fn=cmd_play)

    p_solve = sub.add_parser("solve", help="résoudre une partie avec un solveur")
    grille_args(p_solve)
    p_solve.add_argument("--method", default="classic", choices=["classic", "random", "rule"])
    p_solve.add_argument("--explain", action="store_true",
                         help="afficher la justification de chaque coup (R11)")
    p_solve.set_defaults(fn=cmd_solve)

    p_bench = sub.add_parser("benchmark", help="win-rate par solveur sur N seeds")
    p_bench.add_argument("--difficulty", default="beginner",
                         help="beginner | intermediate | expert")
    p_bench.add_argument("--seeds", type=int, default=50)
    p_bench.add_argument("--solvers", default="random,rule,classic")
    p_bench.add_argument("--save", default=None, help="sauvegarder la table Markdown")
    p_bench.set_defaults(fn=cmd_benchmark)

    p_serve = sub.add_parser("serve", help="lancer le site local de visualisation (W17)")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.add_argument("--open", action="store_true", help="ouvrir le navigateur local")
    p_serve.add_argument("--games-dir", default="games",
                         help="répertoire des artefacts de parties (JSONL)")
    p_serve.set_defaults(fn=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    argv = argv if argv is not None else sys.argv[1:]
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
