"""Tier-0 atomic operations A1–A7, each with its inverse (spec §4).

    A1 add-node      A2 del-node      A3 add-edge     A4 del-edge
    A5 relabel       A6 reweight      A7 reverse-edge

Each operation is a small dataclass. ``op.apply(sg)`` checks the precondition,
performs the effect, and **returns the concrete inverse op** (capturing the
pre-state it needs — old label, old weight, removed-edge attributes, the
generated id …). Reversibility is therefore operation-level and exact:

    inv = op.apply(sg)     # mutates sg, hands back its undo
    inv.apply(sg)          # restores sg

This "command returns its undo" shape is also what the derivation engine (M6)
records to replay and invert traces (§10.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import alphabet as A
from .model import StateGraph


class AtomicOp:
    """Base class: ``apply`` mutates the graph and returns the inverse op."""

    def apply(self, sg: StateGraph) -> "AtomicOp":  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class AddNode(AtomicOp):
    """A1 — new isolated node with label ``λ`` and attrs ``α``. Inverse: A2."""

    label: str = A.DEFAULT_NODE_LABEL
    attrs: dict = field(default_factory=dict)
    id: str | None = None  # if None, one is generated and recorded on apply

    def apply(self, sg: StateGraph) -> "DelNode":
        self.id = sg.add_node(self.label, id=self.id, **self.attrs)
        return DelNode(self.id)


@dataclass
class DelNode(AtomicOp):
    """A2 — remove an isolated node. Precondition ``deg(n)=0``. Inverse: A1."""

    id: str

    def apply(self, sg: StateGraph) -> AddNode:
        if sg.degree(self.id) != 0:
            raise ValueError(f"A2 precondition: node {self.id!r} must be isolated (deg=0)")
        label = sg.node_label(self.id)
        attrs = dict(sg.node_attrs(self.id))
        sg.remove_node(self.id)
        return AddNode(label, attrs, id=self.id)


@dataclass
class AddEdge(AtomicOp):
    """A3 — new directed edge ``a→b``. Precondition: endpoints present, edge
    absent. Inverse: A4."""

    src: str
    tgt: str
    orientation: str
    bidirectional: bool | None = None
    weight: float = A.DEFAULT_WEIGHT
    type: str = A.DEFAULT_EDGE_TYPE
    attrs: dict = field(default_factory=dict)

    def apply(self, sg: StateGraph) -> "DelEdge":
        if sg.has_edge(self.src, self.tgt):
            raise ValueError(f"A3 precondition: edge {self.src!r}→{self.tgt!r} already present")
        sg.add_edge(self.src, self.tgt, self.orientation,
                    bidirectional=self.bidirectional, weight=self.weight,
                    type=self.type, **self.attrs)
        return DelEdge(self.src, self.tgt)


@dataclass
class DelEdge(AtomicOp):
    """A4 — remove an edge. Precondition: edge present. Inverse: A3."""

    src: str
    tgt: str

    def apply(self, sg: StateGraph) -> AddEdge:
        e = sg.edge(self.src, self.tgt)
        if e is None:
            raise ValueError(f"A4 precondition: edge {self.src!r}→{self.tgt!r} absent")
        sg.remove_edge(self.src, self.tgt)
        return AddEdge(self.src, self.tgt, e["orientation"],
                       bidirectional=e["bidirectional"], weight=e["weight"],
                       type=e["type"], attrs=dict(e["attrs"]))


@dataclass
class Relabel(AtomicOp):
    """A5 — set ``λN(n) = λ′``. Inverse: relabel back to the old label."""

    id: str
    new_label: str

    def apply(self, sg: StateGraph) -> "Relabel":
        old = sg.node_label(self.id)
        sg.set_node_label(self.id, self.new_label)
        return Relabel(self.id, old)


@dataclass
class Reweight(AtomicOp):
    """A6 — set ``ω(e) = w′``. Inverse: reweight back to the old weight."""

    src: str
    tgt: str
    new_weight: float

    def apply(self, sg: StateGraph) -> "Reweight":
        e = sg.edge(self.src, self.tgt)
        if e is None:
            raise ValueError(f"A6 precondition: edge {self.src!r}→{self.tgt!r} absent")
        old = e["weight"]
        sg.set_edge_weight(self.src, self.tgt, self.new_weight)
        return Reweight(self.src, self.tgt, old)


@dataclass
class ReverseEdge(AtomicOp):
    """A7 — swap ``src(e), tgt(e)``. Self-inverse (reverse the reversed edge)."""

    src: str
    tgt: str

    def apply(self, sg: StateGraph) -> "ReverseEdge":
        e = sg.edge(self.src, self.tgt)
        if e is None:
            raise ValueError(f"A7 precondition: edge {self.src!r}→{self.tgt!r} absent")
        sg.remove_edge(self.src, self.tgt)
        sg.add_edge(self.tgt, self.src, e["orientation"],
                    bidirectional=e["bidirectional"], weight=e["weight"],
                    type=e["type"], **e["attrs"])
        return ReverseEdge(self.tgt, self.src)
