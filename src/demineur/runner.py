"""GameRunner centralisé (B09, B07) et format d'événement unifié (B10).

Un seul ``GameRunner`` pour humain comme solveur : applique une ``Action``,
refuse les actions illégales (compteur + abandon après N rejets), enregistre
un événement par coup, détecte la fin de partie. L'événement B10 —
``(numéro de coup, vue avant [A15], action, justification, vue après, résultat)`` —
est le contrat unique consommé par le web (W02, W06, W07) et les benchmarks (R14).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from demineur.actions import Action, Flag, GiveUp, Reveal, Unflag, action_to_json
from demineur.game import Game, GameState
from demineur.solvers.base import Solver

RESULT_OK = "ok"
RESULT_ILLEGAL = "illegal"
RESULT_GAVE_UP = "gave_up"


@dataclass(frozen=True)
class MoveEvent:
    """Événement de coup au format unifié B10."""

    move: int
    view_before: dict
    action: dict
    justification: str | None
    view_after: dict
    result: str
    detail: str | None = None

    def to_json(self) -> dict:
        return {
            "move": self.move,
            "view_before": self.view_before,
            "action": self.action,
            "justification": self.justification,
            "view_after": self.view_after,
            "result": self.result,
            "detail": self.detail,
        }


@dataclass
class RunResult:
    """Résultat d'une partie pilotée par un solveur."""

    state: GameState
    won: bool
    moves: int
    events: list[MoveEvent] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "state": self.state.value,
            "won": self.won,
            "moves": self.moves,
            "events": [e.to_json() for e in self.events],
        }


class GameRunner:
    """Applique des actions sur une partie avec politique de rejet explicite (B09)."""

    def __init__(self, game: Game, max_moves: int = 10_000, max_rejections: int = 5):
        if max_moves <= 0:
            raise ValueError("max_moves doit être positif")
        if max_rejections <= 0:
            raise ValueError("max_rejections doit être positif")
        self.game = game
        self.max_moves = max_moves
        self.max_rejections = max_rejections
        self.events: list[MoveEvent] = []
        self._rejets = 0
        self._abandonné = False

    @property
    def gave_up(self) -> bool:
        return self._abandonné

    def _enregistre(self, action: Action, view_before: dict, view_after: dict,
                    justification, result: str, detail: str | None = None) -> MoveEvent:
        event = MoveEvent(
            move=len(self.events),
            view_before=view_before,
            action=action_to_json(action),
            justification=justification if isinstance(justification, str) else None,
            view_after=view_after,
            result=result,
            detail=detail,
        )
        self.events.append(event)
        return event

    def apply(self, action: Action, justification: str | None = None) -> MoveEvent:
        """Applique une action ; retourne l'événement B10 correspondant.

        Politique illégalité : le coup est rejeté (état inchangé), compté ;
        au-delà de ``max_rejections`` rejets consécutifs la partie est abandonnée.
        """
        if not isinstance(action, Action):
            raise TypeError(f"Action attendue, reçu: {action!r}")
        vue_avant = self.game.view().to_json()
        if isinstance(action, GiveUp):
            self._abandonné = True
            return self._enregistre(action, vue_avant, vue_avant, justification,
                                     RESULT_GAVE_UP, detail=action.reason)
        try:
            if isinstance(action, Reveal):
                self.game.reveal(action.x, action.y)
            elif isinstance(action, Flag):
                self.game.flag(action.x, action.y)
            elif isinstance(action, Unflag):
                self.game.unflag(action.x, action.y)
            else:
                raise ValueError(f"action non supportée par le moteur: {action!r}")
        except ValueError as err:
            self._rejets += 1
            vue_après = self.game.view().to_json()
            event = self._enregistre(action, vue_avant, vue_après, justification,
                                     RESULT_ILLEGAL, detail=str(err))
            if self._rejets >= self.max_rejections:
                self._abandonné = True
                self._enregistre(GiveUp("trop d'actions illégales"), vue_après, vue_après,
                                None, RESULT_GAVE_UP,
                                detail=f"{self._rejets} rejets consécutifs")
            return event
        self._rejets = 0
        return self._enregistre(action, vue_avant, self.game.view().to_json(),
                                justification, RESULT_OK)

    def run(self, solver: Solver) -> RunResult:
        """Boucle de jeu pilotée par un solveur (B07 : jamais de blocage)."""
        while (
            self.game.state is GameState.PLAYING
            and not self._abandonné
            and len(self.events) < self.max_moves
        ):
            vue = self.game.view()
            action = solver.decide(vue)
            justification = getattr(solver, "last_justification", None)
            if not isinstance(action, Action):
                self.apply(GiveUp(f"action invalide: {action!r}"))
                break
            self.apply(action, justification)
            if self._abandonné:
                break
        return RunResult(
            state=self.game.state,
            won=self.game.state is GameState.WON,
            moves=len(self.events),
            events=list(self.events),
        )
