"""Presets de difficulté (A16), utilisés par la CLI, les solveurs et les benchmarks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    """Format standard de difficulté."""

    name: str
    width: int
    height: int
    mines: int

    @property
    def shape(self) -> tuple[int, int, int]:
        return (self.width, self.height, self.mines)


PRESETS: dict[str, Preset] = {
    "beginner": Preset("beginner", 9, 9, 10),
    "intermediate": Preset("intermediate", 16, 16, 40),
    "expert": Preset("expert", 30, 16, 99),
}


def list_presets() -> tuple[str, ...]:
    """Noms des presets disponibles, ordre de difficulté croissante."""
    return ("beginner", "intermediate", "expert")


def get_preset(name: str) -> Preset:
    """Preset par nom (insensible à la casse) ; ``ValueError`` si inconnu."""
    clé = name.lower()
    if clé not in PRESETS:
        raise ValueError(f"preset inconnu: {name!r} (disponibles: {', '.join(list_presets())})")
    return PRESETS[clé]


def custom_preset(width: int, height: int, mines: int) -> Preset:
    """Difficulté personnalisée validée."""
    if width <= 0 or height <= 0:
        raise ValueError("dimensions strictement positives requises")
    if not 0 < mines < width * height:
        raise ValueError("nombre de mines invalide")
    return Preset("custom", width, height, mines)
