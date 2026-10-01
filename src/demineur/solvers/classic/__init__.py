"""Solveur classique déterministe complet (phase R)."""

from demineur.solvers.classic.analysis import Constraint, extract_constraints
from demineur.solvers.classic.classic_solver import Analysis, ClassicSolver, analyze
from demineur.solvers.classic.csp import (
    ComponentTooLarge,
    ConfigurationImpossible,
    classify,
    components,
    enumerate_solutions,
)
from demineur.solvers.classic.probabilities import exact_probabilities, uniform_probabilities
from demineur.solvers.classic.rules import Deduction, deduce

__all__ = [
    "Analysis", "ClassicSolver", "analyze",
    "Constraint", "extract_constraints",
    "ComponentTooLarge", "ConfigurationImpossible",
    "classify", "components", "enumerate_solutions",
    "exact_probabilities", "uniform_probabilities",
    "Deduction", "deduce",
]
