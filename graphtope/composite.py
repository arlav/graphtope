"""Tier-1 core composite operations (spec §5) — the six generic verbs.

Each composite is a recipe over the Tier-0 atomics (§4). Because every atomic
``apply`` returns its exact inverse, a composite records the inverses of the
atomics it runs and hands back their **reversed sequence** as ``OpSequence`` —
so ``inverse(op) ∘ op == id`` holds exactly, and the engine (M6) can replay or
invert by storing the sequence (the "merge record" / recovered π of §5.1).

    SPLIT / MERGE   the reversible pair at the heart of D-I (§5.1)
    DIVIDE          k-cell partition = (k−1) chained SPLITs (§5.2)
    UNION           merge OR add-adjacency, by dispatch (§5.2)
    DIFFERENCE      carve-room / disconnect / reshape, by dispatch (§5.2)
    MIRROR          Transform-by-reflection (§5.3)
    TRANSFORM       rigid → identity on the graph; reflection → MIRROR (§5.2)
    OTHER           relabel (A5) / attach a pendant node (§5.2)
    REPLACE         general DPO — deferred to M4 (§6)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import alphabet as A
from .atomic import (
    AddEdge, AddNode, AtomicOp, DelEdge, DelNode, Relabel, Reweight,
)
from .model import StateGraph


@dataclass
class OpSequence(AtomicOp):
    """An ordered programme of ops; its inverse is the reverse of the inverses."""

    ops: list

    def apply(self, sg: StateGraph) -> "OpSequence":
        inverses = [op.apply(sg) for op in self.ops]
        inverses.reverse()
        return OpSequence(inverses)


class _Recorder:
    """Applies ops one at a time so generated ids are visible between steps."""

    def __init__(self, sg: StateGraph):
        self.sg = sg
        self._inv: list = []

    def do(self, op: AtomicOp) -> AtomicOp:
        self._inv.append(op.apply(self.sg))
        return op  # op carries any id it generated (AddNode.id, …)

    def inverse(self) -> OpSequence:
        return OpSequence(list(reversed(self._inv)))


# === SPLIT / MERGE (§5.1) =================================================
@dataclass
class Split(AtomicOp):
    """SPLIT(n, o, π) — divide one space into two adjacent spaces.

    ``partition(edge_record) -> 1 | 2`` routes each of ``n``'s incident edges to
    a child (default: all to child 1). For ``o = V``, ``upper`` (1 or 2) fixes
    which child is above. Children inherit ``n``'s label and attributes.
    """

    n: str
    orientation: str = A.H
    partition: Callable[[dict], int] | None = None
    upper: int = 1
    children: tuple | None = field(default=None, init=False)

    def apply(self, sg: StateGraph) -> OpSequence:
        if not A.is_orientation(self.orientation):
            raise ValueError(f"SPLIT: bad orientation {self.orientation!r}")
        label = sg.node_label(self.n)
        attrs = dict(sg.node_attrs(self.n))
        incident = sg.incident_edges(self.n)
        rec = _Recorder(sg)

        c1 = rec.do(AddNode(label, dict(attrs))).id      # child 1
        c2 = rec.do(AddNode(label, dict(attrs))).id      # child 2

        for e in incident:
            side = self.partition(e) if self.partition else 1
            child = c1 if side == 1 else c2
            rec.do(DelEdge(e["src"], e["tgt"]))
            if e["src"] == self.n:                        # outgoing n → other
                rec.do(AddEdge(child, e["tgt"], e["orientation"],
                               bidirectional=e["bidirectional"], weight=e["weight"],
                               type=e["type"], attrs=dict(e["attrs"])))
            else:                                         # incoming other → n
                rec.do(AddEdge(e["src"], child, e["orientation"],
                               bidirectional=e["bidirectional"], weight=e["weight"],
                               type=e["type"], attrs=dict(e["attrs"])))

        if self.orientation == A.V:
            upper, lower = (c1, c2) if self.upper == 1 else (c2, c1)
            rec.do(AddEdge(upper, lower, A.V, bidirectional=False))
        else:
            rec.do(AddEdge(c1, c2, A.H, bidirectional=True))

        rec.do(DelNode(self.n))                           # original now isolated
        self.children = (c1, c2)
        return rec.inverse()


@dataclass
class Merge(AtomicOp):
    """MERGE(n1, n2) — fuse two adjacent spaces into one (inverse of SPLIT).

    ``ζ`` (label policy): keep the shared label, else require ``result_label``.
    ``ξ`` (weight policy for coalesced parallel edges): default ``max``.
    """

    n1: str
    n2: str
    result_label: str | None = None
    result_id: str | None = None
    result_attrs: dict | None = None
    xi: Callable[[float, float], float] = max
    result: str | None = field(default=None, init=False)

    def apply(self, sg: StateGraph) -> OpSequence:
        inter = sg.edge(self.n1, self.n2) or sg.edge(self.n2, self.n1)
        if inter is None:
            raise ValueError(f"MERGE precondition: {self.n1!r}, {self.n2!r} not adjacent")

        l1, l2 = sg.node_label(self.n1), sg.node_label(self.n2)
        if self.result_label is not None:
            rlabel = self.result_label
        elif l1 == l2:
            rlabel = l1
        else:
            raise ValueError("MERGE (ζ): labels differ — provide result_label")
        rattrs = (self.result_attrs if self.result_attrs is not None
                  else {**sg.node_attrs(self.n1), **sg.node_attrs(self.n2)})

        pair = (self.n1, self.n2)
        externals = [e for e in sg.edges()
                     if (e["src"] in pair) ^ (e["tgt"] in pair)]  # exactly one end in pair

        rec = _Recorder(sg)
        m = rec.do(AddNode(rlabel, dict(rattrs), id=self.result_id)).id
        self.result = m

        for e in externals:
            rec.do(DelEdge(e["src"], e["tgt"]))
            if e["src"] in pair:                          # child → other  ⇒  m → other
                other = e["tgt"]
                if sg.has_edge(m, other):                 # coalesce under ξ
                    rec.do(Reweight(m, other, self.xi(sg.edge(m, other)["weight"], e["weight"])))
                else:
                    rec.do(AddEdge(m, other, e["orientation"], bidirectional=e["bidirectional"],
                                   weight=e["weight"], type=e["type"], attrs=dict(e["attrs"])))
            else:                                         # other → child  ⇒  other → m
                other = e["src"]
                if sg.has_edge(other, m):
                    rec.do(Reweight(other, m, self.xi(sg.edge(other, m)["weight"], e["weight"])))
                else:
                    rec.do(AddEdge(other, m, e["orientation"], bidirectional=e["bidirectional"],
                                   weight=e["weight"], type=e["type"], attrs=dict(e["attrs"])))

        rec.do(DelEdge(inter["src"], inter["tgt"]))
        rec.do(DelNode(self.n1))
        rec.do(DelNode(self.n2))
        return rec.inverse()


# === DIVIDE (§5.2) ========================================================
@dataclass
class Divide(AtomicOp):
    """DIVIDE(n → c₁…cₖ) — partition into k cells via (k−1) chained SPLITs."""

    n: str
    k: int
    orientation: str = A.H
    children: list | None = field(default=None, init=False)

    def apply(self, sg: StateGraph) -> OpSequence:
        if self.k < 2:
            raise ValueError("DIVIDE: k must be ≥ 2")
        rec = _Recorder(sg)
        produced: list[str] = []
        current = self.n
        for _ in range(self.k - 1):
            sp = Split(current, self.orientation)
            rec.do(sp)                                    # records sp's OpSequence inverse
            left, right = sp.children
            produced.append(left)
            current = right
        produced.append(current)
        self.children = produced
        return rec.inverse()


# === UNION (§5.2) =========================================================
@dataclass
class Union(AtomicOp):
    """UNION(a ⊕ b) — dispatch: ``mode='merge'`` fuses; ``mode='adjacency'``
    records a new shared boundary (default)."""

    a: str
    b: str
    mode: str = "adjacency"
    orientation: str = A.H
    weight: float = A.DEFAULT_WEIGHT
    bidirectional: bool | None = None

    def apply(self, sg: StateGraph) -> OpSequence:
        if self.mode == "merge":
            return Merge(self.a, self.b).apply(sg)
        if self.mode != "adjacency":
            raise ValueError(f"UNION: unknown mode {self.mode!r}")
        rec = _Recorder(sg)
        rec.do(AddEdge(self.a, self.b, self.orientation,
                       bidirectional=self.bidirectional, weight=self.weight))
        return rec.inverse()


# === DIFFERENCE (§5.2) ====================================================
@dataclass
class Difference(AtomicOp):
    """DIFFERENCE(a ⊖ b) — dispatch: ``carve_room`` adds a void room adjacent to
    ``a``; ``disconnect`` SPLITs ``a``; ``reshape`` is a no-op on the graph."""

    a: str
    mode: str = "carve_room"
    void_label: str = A.GENERIC
    void_subtype: str = "void"
    orientation: str = A.H
    partition: Callable[[dict], int] | None = None
    void: str | None = field(default=None, init=False)

    def apply(self, sg: StateGraph) -> OpSequence:
        if self.mode == "reshape":
            return OpSequence([])                         # geometry only (Stage 2)
        if self.mode == "disconnect":
            sp = Split(self.a, self.orientation, self.partition)
            return sp.apply(sg)
        if self.mode != "carve_room":
            raise ValueError(f"DIFFERENCE: unknown mode {self.mode!r}")
        rec = _Recorder(sg)
        self.void = rec.do(AddNode(self.void_label, {"subtype": self.void_subtype})).id
        rec.do(AddEdge(self.a, self.void, self.orientation))
        return rec.inverse()


# === MIRROR (§5.3) ========================================================
@dataclass
class Mirror(AtomicOp):
    """MIRROR(S, seam) — reflect a subgraph and stitch it to the original.

    Copies every node in ``nodes``; copies internal edges (H access reflected,
    i.e. direction reversed; V kept); stitches each ``seam`` node to its copy.
    """

    nodes: list
    seam: list
    seam_orientation: str = A.H
    seam_weight: float = A.DEFAULT_WEIGHT
    copies: dict | None = field(default=None, init=False)

    def apply(self, sg: StateGraph) -> OpSequence:
        S = set(self.nodes)
        internal = [e for e in sg.edges() if e["src"] in S and e["tgt"] in S]
        rec = _Recorder(sg)
        copy: dict[str, str] = {}
        for v in self.nodes:
            copy[v] = rec.do(AddNode(sg.node_label(v), dict(sg.node_attrs(v)))).id
        for e in internal:
            u, w = copy[e["src"]], copy[e["tgt"]]
            if e["orientation"] == A.H:                   # reflect access direction
                rec.do(AddEdge(w, u, A.H, bidirectional=e["bidirectional"],
                               weight=e["weight"], type=e["type"], attrs=dict(e["attrs"])))
            else:
                rec.do(AddEdge(u, w, e["orientation"], bidirectional=e["bidirectional"],
                               weight=e["weight"], type=e["type"], attrs=dict(e["attrs"])))
        for v in self.seam:
            rec.do(AddEdge(v, copy[v], self.seam_orientation, weight=self.seam_weight))
        self.copies = copy
        return rec.inverse()


# === TRANSFORM / OTHER (§5.2) ============================================
@dataclass
class Transform(AtomicOp):
    """TRANSFORM(τ) — rigid motion is identity on the graph; reflection ⇒ MIRROR."""

    kind: str = "rigid"
    nodes: list | None = None
    seam: list | None = None
    seam_orientation: str = A.H

    def apply(self, sg: StateGraph) -> OpSequence:
        if self.kind == "rigid":
            return OpSequence([])
        if self.kind == "reflection":
            return Mirror(self.nodes or [], self.seam or [], self.seam_orientation).apply(sg)
        raise ValueError(f"TRANSFORM: unknown kind {self.kind!r}")


@dataclass
class AttachPendant(AtomicOp):
    """OTHER — attach a pendant node (aperture/content) to a host (+N ; +E)."""

    host: str
    label: str = A.GENERIC
    orientation: str = A.H
    weight: float = A.DEFAULT_WEIGHT
    subtype: str | None = None
    from_host: bool = True                                # host → pendant, else reverse
    pendant: str | None = field(default=None, init=False)

    def apply(self, sg: StateGraph) -> OpSequence:
        rec = _Recorder(sg)
        attrs = {} if self.subtype is None else {"subtype": self.subtype}
        self.pendant = rec.do(AddNode(self.label, attrs)).id
        if self.from_host:
            rec.do(AddEdge(self.host, self.pendant, self.orientation, weight=self.weight))
        else:
            rec.do(AddEdge(self.pendant, self.host, self.orientation, weight=self.weight))
        return rec.inverse()


# Relabel (A5) is re-exported as the OTHER "assign semantics" operation.
__all__ = [
    "OpSequence", "Split", "Merge", "Divide", "Union", "Difference",
    "Mirror", "Transform", "AttachPendant", "Relabel",
]
