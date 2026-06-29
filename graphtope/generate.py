"""Generative derivation — exploring the grammar's *space* of derivations (G0).

Stage 1's ``grammar_dnf.derive`` is one scripted path ``A₀ →* G_DNF``. Here the
derivation driver is pluggable: a ``Strategy`` chooses the next
``(production, match)`` at each step, and ``generate`` runs it to a budget. Many
sequences yield the same graph (confluence), so ``catalogue`` dedups a population
by typed isomorphism. Every variant is a recorded ``Derivation`` — still
replayable and invertible (``engine``).

This is the enabler for the "diverse catalogue" goal; validity filtering (G1),
parameterised productions (G2), sub-grammars (G3) and metrics (G4) build on it.
See ``docs/Generative_Variation_Research_Plan.md``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import alphabet as A
from .compare import typed_isomorphic
from .engine import Derivation
from .grammar_dnf import PRODUCTIONS
from .model import StateGraph

#: a reasonable default bias — grow spaces & circulation before the special units
DEFAULT_WEIGHTS = {"P1": 3.0, "P2": 1.0, "P3": 2.0, "P4": 1.5,
                   "P5": 1.0, "P6": 1.5, "P7": 1.0, "P8": 1.0}


def _sorted_matches(matches: list[dict]) -> list[dict]:
    """Deterministic match order (the carrier's node order is not stable)."""
    return sorted(matches, key=lambda m: tuple(sorted(m.items())))


class Strategy:
    """Chooses the next derivation step, or ``None`` to stop."""

    def next(self, sg: StateGraph, history: list):  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class RandomStrategy(Strategy):
    """Pick a (weighted) applicable production and a random valid match, up to a
    step budget. Seeded for reproducibility."""

    productions: dict = field(default_factory=lambda: dict(PRODUCTIONS))
    weights: dict | None = None
    max_steps: int = 12
    seed: int = 0

    def __post_init__(self):
        self.rng = random.Random(self.seed)

    def next(self, sg, history):
        if len(history) >= self.max_steps:
            return None
        # weights restrict *and* bias: a production absent from `weights` (or ≤ 0)
        # is excluded, so its matches aren't even computed.
        applicable = []
        for p in self.productions.values():
            w = 1.0 if self.weights is None else self.weights.get(p.name, 0.0)
            if w <= 0:
                continue
            ms = p.matches(sg)
            if ms:
                applicable.append((p, _sorted_matches(ms), w))
        if not applicable:
            return None
        p, ms, _ = self.rng.choices(applicable, weights=[a[2] for a in applicable], k=1)[0]
        return p, self.rng.choice(ms)


def single_block_axiom() -> StateGraph:
    """A one-node axiom (a single block) → generation yields one connected building."""
    g = StateGraph()
    g.add_node(A.GENERIC, id="b", block="residential")
    return g


def generate(strategy: Strategy, axiom: StateGraph | None = None) -> Derivation:
    """Run ``strategy`` from the axiom to its stop condition; return the trace."""
    d = Derivation(axiom if axiom is not None else StateGraph.axiom())
    while True:
        step = strategy.next(d.sg, d.steps)
        if step is None:
            break
        d.apply(*step)
    return d


def catalogue(n: int, *, strategy_factory=None, axiom_factory=None,
              dedup: bool = True, keep=None, max_attempts: int | None = None) -> list:
    """Generate up to ``n`` distinct variants. ``keep(sg) -> bool`` filters (e.g.
    ``validity.is_valid``); dedup is by typed isomorphism. Generation continues
    (varying the seed) until ``n`` are collected or ``max_attempts`` is reached.

    Returns a list of ``Derivation`` objects."""
    strategy_factory = strategy_factory or (lambda i: RandomStrategy(seed=i, weights=DEFAULT_WEIGHTS))
    axiom_factory = axiom_factory or StateGraph.axiom
    max_attempts = max_attempts if max_attempts is not None else n * 12
    out: list = []
    i = 0
    while len(out) < n and i < max_attempts:
        d = generate(strategy_factory(i), axiom_factory())
        i += 1
        if keep is not None and not keep(d.sg):
            continue
        if dedup and any(typed_isomorphic(d.sg, prev.sg) for prev in out):
            continue
        out.append(d)
    return out
