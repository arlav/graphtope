"""DPO productions and the typed-attributed directed matcher (spec §6).

A production is a span ``L ⊇ K ⊆ R`` (§6.1). Applying it at a match ``m: L → G``
deletes ``m(L∖K)``, keeps ``m(K)``, and glues in ``R∖K``. Matching is an
injective, typed, attributed, **directed** subgraph monomorphism (§6.2)
preserving node label/subtype, edge type + orientation, and direction;
bidirectional H-adjacency — stored one-way but semantically symmetric — is
matched in *either* direction, while one-way edges (V, `entrance`) stay strict.
Negative application conditions (§6.3) block over-generating matches.

Patterns are tiny and the host is small, so the matcher is a direct
backtracking search. (Per the carrier briefing gap C3, ``Graph.SubGraphMatches``
matches only vertices, so the edge/direction/attribute-aware matcher lives here.)
Rule application is built from atomics, so it is reversible like everything else.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import alphabet as A
from .atomic import AddEdge, AddNode, DelEdge, DelNode
from .composite import OpSequence, _Recorder
from .model import StateGraph


# === pattern graphs =======================================================
@dataclass
class PNode:
    """A pattern node. In L/NAC the fields are *match constraints*; in R they
    are the *spec to create* (``label``/``subtype``/``attrs``). ``label=None``
    is a wildcard; ``labels`` (non-empty) matches any label in the set —
    e.g. ``x ∈ {generic, corridor}`` (§7.2)."""

    name: str
    label: str | None = None
    labels: tuple = ()
    subtype: str | None = None
    attrs: dict = field(default_factory=dict)


@dataclass
class PEdge:
    """A pattern edge ``src → tgt``. ``orientation``/``bidirectional`` are
    constraints when ``None`` means 'unconstrained'; weight is matched only when
    ``match_weight`` is set, and is otherwise just the value to create in R."""

    src: str
    tgt: str
    orientation: str | None = None
    type: str = A.ADJACENCY
    bidirectional: bool | None = None
    weight: float = A.DEFAULT_WEIGHT
    match_weight: bool = False


@dataclass
class Pattern:
    nodes: list
    edges: list = field(default_factory=list)

    def names(self) -> list[str]:
        return [n.name for n in self.nodes]

    def node(self, name: str) -> PNode:
        return next(n for n in self.nodes if n.name == name)


# === matcher ==============================================================
def _node_ok(pn: PNode, sg: StateGraph, hid: str) -> bool:
    if pn.labels:
        if sg.node_label(hid) not in pn.labels:
            return False
    elif pn.label is not None and sg.node_label(hid) != pn.label:
        return False
    if pn.subtype is not None and sg.node_attrs(hid).get("subtype") != pn.subtype:
        return False
    return True


def _edge_ok(pe: PEdge, sg: StateGraph, assign: dict) -> bool:
    hs, ht = assign[pe.src], assign[pe.tgt]
    e = sg.edge(hs, ht)
    if e is None:                                   # try the symmetric reading
        rev = sg.edge(ht, hs)
        if rev is not None and rev["bidirectional"]:
            e = rev
        else:
            return False
    if e["type"] != pe.type:
        return False
    if pe.orientation is not None and e["orientation"] != pe.orientation:
        return False
    if pe.bidirectional is not None and e["bidirectional"] != pe.bidirectional:
        return False
    if pe.match_weight and e["weight"] != pe.weight:
        return False
    return True


def match_pattern(pattern: Pattern, sg: StateGraph, fixed: dict | None = None,
                  node_matcher=None) -> list[dict]:
    """All injective matches of ``pattern`` into ``sg`` extending ``fixed``.

    ``node_matcher(pnode, sg, host_id) -> bool`` overrides the default label/
    subtype node test — this is the seam where Stage 2 swaps in the *geometric*
    predicate (§9) without touching edge matching or the rule structure."""
    ok = node_matcher or _node_ok
    fixed = dict(fixed or {})
    free = [pn for pn in pattern.nodes if pn.name not in fixed]
    cand = {pn.name: [h for h in sg.nodes() if ok(pn, sg, h)] for pn in free}
    names = [pn.name for pn in free]

    def edges_ok(assign: dict) -> bool:
        return all(_edge_ok(pe, sg, assign) for pe in pattern.edges
                   if pe.src in assign and pe.tgt in assign)

    if not edges_ok(fixed):
        return []

    results: list[dict] = []

    def bt(i: int, assign: dict, used: set) -> None:
        if i == len(names):
            results.append(dict(assign))
            return
        name = names[i]
        for h in cand[name]:
            if h in used:
                continue
            assign[name] = h
            if edges_ok(assign):
                bt(i + 1, assign, used | {h})
            del assign[name]

    bt(0, dict(fixed), set(fixed.values()))
    return results


# === productions ==========================================================
@dataclass
class Production:
    """A DPO production ``L ⊇ K ⊆ R`` with negative application conditions.

    ``interface`` is the set of K node names (shared by L and R, preserved).
    Each NAC is a ``Pattern`` extending L (its L-names are bound by the match;
    if the extension matches, the production is blocked).
    """

    name: str
    lhs: Pattern
    interface: set
    rhs: Pattern
    nacs: list = field(default_factory=list)
    instantiates: str = ""        # which Tier-1 op this names (doc only, §6.4)

    # -- matching ----------------------------------------------------------
    def matches(self, sg: StateGraph, node_matcher=None) -> list[dict]:
        """Valid matches of L into ``sg`` that survive every NAC. Pass
        ``node_matcher`` (e.g. ``realise.shape_matcher(sg)``) to match by
        geometry rather than label — the §9 Stage-2 swap."""
        return [m for m in match_pattern(self.lhs, sg, node_matcher=node_matcher)
                if not any(match_pattern(nac, sg, fixed=m, node_matcher=node_matcher)
                           for nac in self.nacs)]

    def _preserved(self) -> set:
        lset = {(e.src, e.tgt, e.type) for e in self.lhs.edges}
        return {(e.src, e.tgt, e.type) for e in self.rhs.edges
                if (e.src, e.tgt, e.type) in lset}

    # -- application -------------------------------------------------------
    def apply(self, sg: StateGraph, match: dict) -> OpSequence:
        """Apply at ``match`` (deletes L∖K, keeps K, glues R∖K). Reversible."""
        return self.apply_at(sg, match).inverse

    def apply_at(self, sg: StateGraph, match: dict) -> "Application":
        """Apply at ``match``; return the inverse + the produced node ids."""
        iface = set(self.interface)
        preserved = self._preserved()
        rec = _Recorder(sg)

        # 1. delete L-edges not preserved by K (use the actually-stored
        #    direction — a symmetric H-edge may have matched either way)
        for e in self.lhs.edges:
            if (e.src, e.tgt, e.type) in preserved:
                continue
            hs, ht = match[e.src], match[e.tgt]
            if sg.edge(hs, ht) is not None:
                rec.do(DelEdge(hs, ht))
            elif sg.edge(ht, hs) is not None:
                rec.do(DelEdge(ht, hs))
            else:
                raise ValueError(f"{self.name}: matched L-edge {e.src!r}→{e.tgt!r} not in host")

        # 2. delete L∖K nodes (DPO dangling condition: must be isolated)
        for pn in self.lhs.nodes:
            if pn.name in iface:
                continue
            hid = match[pn.name]
            if sg.degree(hid) != 0:
                raise ValueError(
                    f"{self.name}: dangling condition — deleting {pn.name!r} would leave dangling edges")
            rec.do(DelNode(hid))

        # 3. create R∖K nodes; build name → host-id map
        idmap = {nm: match[nm] for nm in iface}
        for pn in self.rhs.nodes:
            if pn.name in iface:
                continue
            attrs = dict(pn.attrs)
            if pn.subtype is not None:
                attrs["subtype"] = pn.subtype
            op = AddNode(pn.label or A.DEFAULT_NODE_LABEL, attrs)
            rec.do(op)
            idmap[pn.name] = op.id

        # 4. glue R∖K edges
        for e in self.rhs.edges:
            if (e.src, e.tgt, e.type) in preserved:
                continue
            o = e.orientation or A.H
            bidir = (e.bidirectional if e.bidirectional is not None
                     else A.default_bidirectional(o))
            rec.do(AddEdge(idmap[e.src], idmap[e.tgt], o,
                           bidirectional=bidir, weight=e.weight, type=e.type))

        produced = {pn.name: idmap[pn.name] for pn in self.rhs.nodes
                    if pn.name not in iface}
        return Application(rec.inverse(), match, produced)

    def apply_first(self, sg: StateGraph, node_matcher=None) -> tuple[OpSequence, dict]:
        """Apply at the first valid match; returns (inverse, match)."""
        ms = self.matches(sg, node_matcher=node_matcher)
        if not ms:
            raise ValueError(f"{self.name}: no valid match")
        return self.apply(sg, ms[0]), ms[0]


@dataclass
class Application:
    """The result of applying a production: its inverse + produced node ids."""

    inverse: OpSequence
    match: dict
    produced: dict


# convenience builders for atomic/core productions (§6.4) ------------------
def add_node_production(name: str, label: str, *, host_label: str | None = None,
                        orientation: str = A.H) -> Production:
    """A core production that attaches a fresh ``label`` node to a matched host."""
    host = PNode("h", label=host_label)
    new = PNode("n", label=label)
    return Production(
        name=name,
        lhs=Pattern([host]),
        interface={"h"},
        rhs=Pattern([host, new], [PEdge("h", "n", orientation=orientation)]),
    )
