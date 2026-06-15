"""``StateGraph`` — the state graph object (spec §2), carried by TopologicPy.

A *state graph* is a typed, directed, weighted, attributed (multi)graph
``G = (N, E, src, tgt, λN, λE, ω, αN, αE)`` (§2.1). The canonical store is a
single ``topologicpy.Graph`` mutated in place; nodes are addressed by a stable
``id`` held in each vertex's dictionary (never by coordinates — Stage-1
coordinates are arbitrary layout only).

This module provides construction + inspection + the well-formedness invariants
(§2.2). The reversible operation basis (A1–A7) is layered on top in
``atomic.py`` (M2).
"""

from __future__ import annotations

from topologicpy.Graph import Graph
from topologicpy.Vertex import Vertex
from topologicpy.Edge import Edge

from . import alphabet as A
from ._topo import (
    clean,
    empty_graph,
    id_of,
    py_dict,
    set_dict,
    set_value,
    vertex_at,
)

#: structural keys that are not free attributes αN / αE
_NODE_STRUCTURAL = {"id", "label"}
_EDGE_STRUCTURAL = {"type", "orientation", "bidirectional", "weight"}


class StateGraph:
    """A well-formed state graph over the alphabets Σ (§3.1) and Θ (§3.2)."""

    def __init__(self):
        self._g = empty_graph()
        self._auto = 0          # auto node-id counter
        self._x = 0.0           # monotonic layout x (keeps coordinates unique)

    # -- construction ------------------------------------------------------
    @classmethod
    def axiom(cls) -> "StateGraph":
        """Axiom A₀ (§7.0): two isolated generic blocks, no edges."""
        g = cls()
        g.add_node(A.GENERIC, id="b1", block="residential")
        g.add_node(A.GENERIC, id="b2", block="condenser")
        return g

    def add_node(self, label: str = A.DEFAULT_NODE_LABEL, *, id: str | None = None,
                 level: int | None = None, subtype: str | None = None,
                 **attrs) -> str:
        """Create a node with ``label`` and attributes; return its id."""
        if not A.is_node_label(label):
            raise ValueError(f"unknown node label {label!r}; Σ={sorted(A.NODE_LABELS)}")
        existing = set(self.nodes())
        if id is None:
            while f"n{self._auto}" in existing:   # skip ids taken by explicit names
                self._auto += 1
            id = f"n{self._auto}"
            self._auto += 1
        if id in existing:
            raise ValueError(f"duplicate node id {id!r}")

        d = {"id": id, "label": label}
        if level is not None:
            d["level"] = level
        if subtype is not None:
            d["subtype"] = subtype
        d.update(attrs)

        y = float(level) if level is not None else 0.0
        v = set_dict(Vertex.ByCoordinates(self._x, y, 0.0), d)
        self._x += 1.0
        self._g = Graph.AddVertex(self._g, v, silent=True)
        return id

    def add_edge(self, src: str, tgt: str, orientation: str, *,
                 bidirectional: bool | None = None,
                 weight: float = A.DEFAULT_WEIGHT,
                 type: str = A.DEFAULT_EDGE_TYPE, **attrs) -> None:
        """Add a directed ``src → tgt`` edge (§3.2)."""
        if not self.has_node(src) or not self.has_node(tgt):
            raise ValueError(f"edge endpoint not in graph: {src!r} → {tgt!r}")
        if src == tgt:
            raise ValueError("self-loops are not allowed (§2.2 inv-4)")
        if not A.is_orientation(orientation):
            raise ValueError(f"bad orientation {orientation!r}; Θ-orient={sorted(A.ORIENTATIONS)}")
        if not A.is_edge_type(type):
            raise ValueError(f"unknown edge type {type!r}; Θ={sorted(A.EDGE_TYPES)}")
        if weight < 0:
            raise ValueError("edge weight ω must be ≥ 0 (§2.2 inv-3)")
        if bidirectional is None:
            bidirectional = A.default_bidirectional(orientation)

        d = {"type": type, "orientation": orientation,
             "bidirectional": bool(bidirectional), "weight": float(weight)}
        d.update(attrs)
        e = set_dict(Edge.ByStartVertexEndVertex(vertex_at(self._g, src),
                                                 vertex_at(self._g, tgt)), d)
        # transferEdgeDictionaries=True is mandatory or the dict is dropped (0.9.43)
        self._g = Graph.AddEdge(self._g, e, transferEdgeDictionaries=True, silent=True)

    # -- inspection: nodes -------------------------------------------------
    def nodes(self) -> list[str]:
        return [id_of(v) for v in (Graph.Vertices(self._g) or [])]

    def has_node(self, id: str) -> bool:
        return id in set(self.nodes())

    def node_dict(self, id: str) -> dict:
        v = vertex_at(self._g, id)
        if v is None:
            raise KeyError(f"no node {id!r}")
        return clean(py_dict(v))

    def node_label(self, id: str) -> str:
        return self.node_dict(id).get("label", A.DEFAULT_NODE_LABEL)

    def node_attrs(self, id: str) -> dict:
        return {k: v for k, v in self.node_dict(id).items()
                if k not in _NODE_STRUCTURAL}

    # -- inspection: edges -------------------------------------------------
    def edges(self) -> list[dict]:
        """List edges as records ``{src, tgt, type, orientation,
        bidirectional, weight, attrs}``."""
        out = []
        for e in (Graph.Edges(self._g) or []):
            d = clean(py_dict(e))
            rec = {
                "src": id_of(Edge.StartVertex(e)),
                "tgt": id_of(Edge.EndVertex(e)),
                "type": d.get("type", A.DEFAULT_EDGE_TYPE),
                "orientation": d.get("orientation"),
                "bidirectional": bool(d.get("bidirectional", False)),
                "weight": float(d.get("weight", A.DEFAULT_WEIGHT)),
                "attrs": {k: v for k, v in d.items() if k not in _EDGE_STRUCTURAL},
            }
            out.append(rec)
        return out

    def edge(self, src: str, tgt: str) -> dict | None:
        for e in self.edges():
            if e["src"] == src and e["tgt"] == tgt:
                return e
        return None

    def has_edge(self, src: str, tgt: str) -> bool:
        return self.edge(src, tgt) is not None

    def incident_edges(self, id: str) -> list[dict]:
        """All edge records touching ``id`` (as source or target)."""
        return [e for e in self.edges() if e["src"] == id or e["tgt"] == id]

    def neighbors(self, id: str) -> set[str]:
        return {e["tgt"] if e["src"] == id else e["src"]
                for e in self.incident_edges(id)}

    # -- carrier mutators (used by the atomic basis, §4) ------------------
    def _vertex_obj(self, id: str):
        v = vertex_at(self._g, id)
        if v is None:
            raise KeyError(f"no node {id!r}")
        return v

    def _edge_obj(self, src: str, tgt: str):
        for e in (Graph.Edges(self._g) or []):
            if id_of(Edge.StartVertex(e)) == src and id_of(Edge.EndVertex(e)) == tgt:
                return e
        return None

    def remove_node(self, id: str) -> None:
        """Remove an (isolated) node. Caller guarantees no incident edges."""
        self._g = Graph.RemoveVertex(self._g, self._vertex_obj(id), silent=True)

    def remove_edge(self, src: str, tgt: str) -> None:
        e = self._edge_obj(src, tgt)
        if e is None:
            raise KeyError(f"no edge {src!r}→{tgt!r}")
        self._g = Graph.RemoveEdge(self._g, e, silent=True)

    def set_node_label(self, id: str, label: str) -> None:
        if not A.is_node_label(label):
            raise ValueError(f"unknown node label {label!r}")
        set_value(self._vertex_obj(id), "label", label)

    def set_edge_weight(self, src: str, tgt: str, weight: float) -> None:
        if weight < 0:
            raise ValueError("edge weight ω must be ≥ 0 (§2.2 inv-3)")
        e = self._edge_obj(src, tgt)
        if e is None:
            raise KeyError(f"no edge {src!r}→{tgt!r}")
        set_value(e, "weight", float(weight))

    # -- degrees (always direction-aware; topologic defaults to undirected) -
    def out_degree(self, id: str) -> int:
        return len(Graph.OutgoingEdges(self._g, vertex_at(self._g, id),
                                       directed=True) or [])

    def in_degree(self, id: str) -> int:
        return len(Graph.IncomingEdges(self._g, vertex_at(self._g, id),
                                       directed=True) or [])

    def degree(self, id: str) -> int:
        return self.out_degree(id) + self.in_degree(id)

    def order(self) -> int:
        return Graph.Order(self._g)

    def size(self) -> int:
        return Graph.Size(self._g)

    # -- well-formedness (§2.2) -------------------------------------------
    def well_formedness_errors(self) -> list[str]:
        errs: list[str] = []
        ids = set(self.nodes())
        for nid in ids:
            lbl = self.node_label(nid)
            if not A.is_node_label(lbl):                       # inv-2
                errs.append(f"node {nid!r} has unknown label {lbl!r}")
        for e in self.edges():
            if e["src"] not in ids or e["tgt"] not in ids:    # inv-1
                errs.append(f"dangling edge {e['src']!r}→{e['tgt']!r}")
            if e["src"] == e["tgt"]:                           # inv-4
                errs.append(f"self-loop on {e['src']!r}")
            if not A.is_edge_type(e["type"]):                  # inv-3
                errs.append(f"edge {e['src']!r}→{e['tgt']!r} has unknown type {e['type']!r}")
            if e["weight"] < 0:                                # inv-3
                errs.append(f"edge {e['src']!r}→{e['tgt']!r} has negative weight")
            if not A.is_orientation(e["orientation"]):         # inv-5
                errs.append(f"edge {e['src']!r}→{e['tgt']!r} has bad orientation {e['orientation']!r}")
        return errs

    def is_well_formed(self) -> bool:
        return not self.well_formedness_errors()

    # -- refinement predicate (§3.1) --------------------------------------
    def is_fully_refined(self) -> bool:
        """True when no non-terminal (`u_section`/`l_section`) remains (§3.1)."""
        return all(A.is_terminal(self.node_label(n)) for n in self.nodes())

    # -- interop -----------------------------------------------------------
    @property
    def topologic_graph(self):
        """The underlying ``topologicpy.Graph`` (for viz / Stage 2)."""
        return self._g

    def to_networkx(self):
        """Escape hatch: a networkx view (e.g. for matching). Not the carrier."""
        return Graph.NetworkXGraph(self._g)

    def show(self, **kwargs):
        from .topoview import show
        return show(self, **kwargs)

    def __repr__(self) -> str:
        return f"<StateGraph |N|={self.order()} |E|={self.size()} well_formed={self.is_well_formed()}>"
