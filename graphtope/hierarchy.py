"""Terminals/non-terminals and sub-grammar refinement (spec §7.6.1–§7.6.2).

``Refine(n, unit)`` is a REPLACE whose left side is the single non-terminal node
``n`` and whose right side is the start graph of its section sub-grammar; ``n``'s
incident edges are the interface ``K`` and are re-attached to the unit's
``anchor`` node, so they are preserved. Its inverse — returned as an
``OpSequence`` — is ``ABSTRACT(S → n)``, collapsing the refined unit back to the
non-terminal (exact when the derivation trace is kept, §5.1).
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
    ``anchor``: the local node that inherits the non-terminal's incident edges.
    """

    nodes: list
    edges: list
    anchor: str


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
        for e in incident:                          # re-attach the interface K to anchor
            rec.do(DelEdge(e["src"], e["tgt"]))
            if e["src"] == self.node:
                rec.do(AddEdge(anchor, e["tgt"], e["orientation"],
                               bidirectional=e["bidirectional"], weight=e["weight"],
                               type=e["type"], attrs=dict(e["attrs"])))
            else:
                rec.do(AddEdge(e["src"], anchor, e["orientation"],
                               bidirectional=e["bidirectional"], weight=e["weight"],
                               type=e["type"], attrs=dict(e["attrs"])))

        rec.do(DelNode(self.node))
        self.produced, self.anchor_id = dict(idmap), anchor
        return rec.inverse()                        # this is ABSTRACT(S → n)
