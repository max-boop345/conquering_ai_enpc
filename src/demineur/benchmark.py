"""Harnais de benchmark (R14) — unique, partagé entre CLI et tests de non-régression.

Déterminisme strict : mêmes seeds -> mêmes résultats (moteur et solveurs
seedés). Les résultats alimentent ``docs/benchmarks.md`` (G03) et la vue web
(W10).
"""

from __future__ import annotations

from dataclasses import dataclass

from demineur.game import Game
from demineur.presets import Preset, get_preset
from demineur.runner import GameRunner
from demineur.solvers.base import Solver


@dataclass
class BenchmarkResult:
    """Résultats d'un solveur sur une difficulté, N seeds."""

    solver: str
    difficulty: str
    width: int
    height: int
    mines: int
    seeds: int
    wins: int
    losses: int
    gave_ups: int
    avg_moves: float

    @property
    def win_rate(self) -> float:
        return self.wins / self.seeds if self.seeds else 0.0

    def to_json(self) -> dict:
        return {
            "solver": self.solver,
            "difficulty": self.difficulty,
            "width": self.width,
            "height": self.height,
            "mines": self.mines,
            "seeds": self.seeds,
            "wins": self.wins,
            "losses": self.losses,
            "gave_ups": self.gave_ups,
            "avg_moves": round(self.avg_moves, 2),
            "win_rate": round(self.win_rate, 4),
        }


def run_benchmark(
    solvers: dict[str, type[Solver]],
    difficulty: str | Preset,
    seeds: range | list[int],
) -> dict[str, BenchmarkResult]:
    """Exécute chaque solveur sur chaque seed ; retourne les résultats par solveur.

    Chaque solveur rejoue exactement les mêmes grilles (mêmes seeds).
    """
    preset = difficulty if isinstance(difficulty, Preset) else get_preset(difficulty)
    if not seeds:
        raise ValueError("aucune seed fournie")
    résultats: dict[str, BenchmarkResult] = {}
    for nom, classe in solvers.items():
        victoires = défaites = abandons = 0
        coups_total = 0
        for seed in seeds:
            jeu = Game(preset.width, preset.height, preset.mines, seed=seed)
            runner = GameRunner(jeu)
            # random et rule ont un fallback aléatoire: seedé par la partie
            # pour un benchmark strictement déterministe (C13)
            solver = classe(seed=seed) if nom in ("random", "rule") else classe()
            résultat = runner.run(solver)
            coups_total += résultat.moves
            if résultat.won:
                victoires += 1
            elif résultat.state.value == "lost":
                défaites += 1
            else:
                abandons += 1
        résultats[nom] = BenchmarkResult(
            solver=nom,
            difficulty=preset.name,
            width=preset.width,
            height=preset.height,
            mines=preset.mines,
            seeds=len(list(seeds)),
            wins=victoires,
            losses=défaites,
            gave_ups=abandons,
            avg_moves=coups_total / len(list(seeds)),
        )
    return résultats


def benchmark_to_json(résultats: dict[str, BenchmarkResult]) -> dict:
    """Format JSON stable consommé par la CLI, les tests et le web (W10)."""
    premier = next(iter(résultats.values()))
    return {
        "version": 1,
        "kind": "benchmark",
        "difficulty": premier.difficulty,
        "grid": {"width": premier.width, "height": premier.height, "mines": premier.mines},
        "seeds": premier.seeds,
        "results": {nom: r.to_json() for nom, r in résultats.items()},
    }


def format_table(résultats: dict[str, BenchmarkResult]) -> str:
    """Table Markdown prête pour ``docs/benchmarks.md``."""
    premier = next(iter(résultats.values()))
    lignes = [
        f"# Benchmarks — {premier.difficulty} "
        f"({premier.width}x{premier.height}, {premier.mines} mines, "
        f"{premier.seeds} seeds)",
        "",
        "| solveur | win-rate | victoires | défaites | abandons | coups moyens |",
        "|---------|----------|-----------|----------|----------|--------------|",
    ]
    for nom, r in sorted(résultats.items(), key=lambda kv: -kv[1].win_rate):
        lignes.append(
            f"| {nom} | {r.win_rate:.1%} | {r.wins} | {r.losses} | "
            f"{r.gave_ups} | {r.avg_moves:.1f} |"
        )
    return "\n".join(lignes) + "\n"
