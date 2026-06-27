"""Derivation engine: apply / invert (spec §8, §10.2).

A ``Derivation`` applies a sequence of (production, match) steps to a state
graph, recording each step's reversible inverse and the ids it produced. The
derivation can be inverted to walk the graph back to its axiom — the grammar
runs both ways (§8). Full JSON trace replay/invert is M6; this is the M5 core.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .composite import OpSequence
from .model import StateGraph
from .rules import Production


@dataclass
class Step:
    rule: str
    match: dict
    produced: dict
    inverse: OpSequence


class Derivation:
    """Records an ordered, invertible sequence of production applications."""

    def __init__(self, sg: StateGraph, on_apply=None):
        self.sg = sg
        self.steps: list[Step] = []
        #: optional callback ``(step, sg)`` fired after each apply — e.g. to
        #: snapshot the graph for step-by-step visualisation.
        self.on_apply = on_apply

    def apply(self, production: Production, match: dict | None = None) -> dict:
        """Apply ``production`` (at ``match``, or the first valid match);
        return the produced node-id map."""
        if match is None:
            ms = production.matches(self.sg)
            if not ms:
                raise ValueError(f"{production.name}: no valid match")
            match = ms[0]
        app = production.apply_at(self.sg, match)
        step = Step(production.name, match, app.produced, app.inverse)
        self.steps.append(step)
        if self.on_apply is not None:
            self.on_apply(step, self.sg)
        return app.produced

    def invert(self) -> None:
        """Undo every step in reverse order — walks the graph back to the axiom."""
        while self.steps:
            self.steps.pop().inverse.apply(self.sg)

    def trace(self) -> list[dict]:
        """The ordered derivation trace (replayable; §10.2)."""
        return [{"rule": s.rule, "match": dict(s.match), "produced": dict(s.produced)}
                for s in self.steps]


def replay(trace: list[dict], productions: dict, axiom: StateGraph | None = None) -> "Derivation":
    """Replay a recorded trace on a fresh axiom (deterministic ids).

    Returns a rebuilt ``Derivation`` (with live inverses), so ``.invert()`` walks
    it back. Raises if replay diverges from the recorded ``produced`` ids.
    """
    d = Derivation(axiom if axiom is not None else StateGraph.axiom())
    for entry in trace:
        produced = d.apply(productions[entry["rule"]], dict(entry["match"]))
        expected = entry.get("produced")
        if expected is not None and produced != expected:
            raise ValueError(
                f"replay diverged at {entry['rule']}: {produced} != {expected}")
    return d
