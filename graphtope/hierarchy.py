"""Terminals/non-terminals and sub-grammar refinement (spec §7.6.1–§7.6.2).

``Refine(n, unit)`` is a REPLACE whose left side is the single non-terminal node
``n`` and whose right side is the start graph of its section sub-grammar; ``n``'s
incident edges are the interface ``K`` and are **routed** to the unit's interior
nodes (SG0): ``UnitSpec.interface`` maps an edge class — ``(orientation,
neighbour-label)``, ``(V, "above"/"below")``, or ``(orientation, "*")`` — to the
local node that receives it, falling back to the ``anchor`` (so a spec with no
router behaves exactly as before). The edge multiset is preserved either way.
Its inverse — returned as an ``OpSequence`` — is ``ABSTRACT(S → n)``, collapsing
the refined unit back to the non-terminal (exact when the derivation trace is
kept, §5.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .alphabet import GENERIC, H, STAIRCASE, V
from .atomic import AddEdge, AddNode, AtomicOp, DelEdge, DelNode
from .composite import OpSequence, _Recorder
from .model import StateGraph


@dataclass
class UnitSpec:
    """The start graph of a section sub-grammar.

    ``nodes``: list of ``(localname, label, attrs)``;
    ``edges``: list of ``(src, tgt, orientation, bidirectional)``;
    ``anchor``: the local node that inherits any interface edge the router
    does not claim (a spec with no ``interface`` behaves as before: every
    incident edge lands on the anchor);
    ``interface``: the SG0 router — ``{(orientation, selector): localname}``
    where ``selector`` is a neighbour label (e.g. ``"corridor"``), ``"above"``
    / ``"below"`` for V edges, or ``"*"``. Most-specific key wins:
    neighbour label, then above/below, then ``"*"``, then ``anchor``.
    """

    nodes: list
    edges: list
    anchor: str
    interface: dict | None = None


def _route(unit: UnitSpec, sg: StateGraph, node: str, e: dict) -> str:
    """The local node that receives interface edge ``e`` (SG0 routing)."""
    if not unit.interface:
        return unit.anchor
    other = e["tgt"] if e["src"] == node else e["src"]
    o = e["orientation"]
    keys = [(o, sg.node_label(other))]
    if o == V:                       # V is directed: src is the upper space
        keys.append((o, "above" if e["tgt"] == node else "below"))
    keys.append((o, "*"))
    for k in keys:
        if k in unit.interface:
            return unit.interface[k]
    return unit.anchor


def u_section_unit() -> UnitSpec:
    """A U-section duplex: lower + upper joined by a V adjacency and a stair (§7.6.2)."""
    return UnitSpec(
        nodes=[("lower", GENERIC, {"subtype": "u_lower"}),
               ("upper", GENERIC, {"subtype": "u_upper"}),
               ("stair", STAIRCASE, {"subtype": "internal"})],
        edges=[("upper", "lower", V, False),     # upper directly above lower
               ("lower", "stair", H, True),
               ("upper", "stair", H, True)],
        anchor="lower",
    )


def l_section_unit() -> UnitSpec:
    """An L-section interlock: a lower + upper joined by a V adjacency."""
    return UnitSpec(
        nodes=[("lower", GENERIC, {"subtype": "l_lower"}),
               ("upper", GENERIC, {"subtype": "l_upper"})],
        edges=[("upper", "lower", V, False)],
        anchor="lower",
    )


@dataclass
class Refine(AtomicOp):
    """REFINE(n, unit) — replace a non-terminal with its sub-grammar start graph."""

    node: str
    unit: UnitSpec
    produced: dict | None = field(default=None, init=False)
    anchor_id: str | None = field(default=None, init=False)

    def apply(self, sg: StateGraph) -> OpSequence:
        incident = sg.incident_edges(self.node)
        rec = _Recorder(sg)

        idmap: dict[str, str] = {}
        for ln, label, attrs in self.unit.nodes:
            idmap[ln] = rec.do(AddNode(label, dict(attrs))).id
        for s, t, o, b in self.unit.edges:
            rec.do(AddEdge(idmap[s], idmap[t], o, bidirectional=b))

        anchor = idmap[self.unit.anchor]
        for e in incident:                # route each interface edge (SG0)
            target = idmap[_route(self.unit, sg, self.node, e)]
            rec.do(DelEdge(e["src"], e["tgt"]))
            if e["src"] == self.node:
                rec.do(AddEdge(target, e["tgt"], e["orientation"],
                               bidirectional=e["bidirectional"], weight=e["weight"],
                               type=e["type"], attrs=dict(e["attrs"])))
            else:
                rec.do(AddEdge(e["src"], target, e["orientation"],
                               bidirectional=e["bidirectional"], weight=e["weight"],
                               type=e["type"], attrs=dict(e["attrs"])))

        rec.do(DelNode(self.node))
        self.produced, self.anchor_id = dict(idmap), anchor
        return rec.inverse()                        # this is ABSTRACT(S → n)
