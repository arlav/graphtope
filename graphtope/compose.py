"""Modular composition of completed block graphs — the inter-block bridge (§7.6.3).

Each block is developed by its own grammar to a complete graph; the blocks are
joined only afterwards. ``disjoint_union`` places two completed block graphs in
one graph (id-prefixed, no collisions); ``Bridge`` introduces the connector ``κ``
between designated interface nodes — a single adjacency edge, or a corridor/bridge
node for an enclosed passage. ``Bridge`` is reversible like every operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .alphabet import CORRIDOR, DEFAULT_WEIGHT, H
from .atomic import AddEdge, AddNode, AtomicOp
from .composite import OpSequence, _Recorder
from .model import StateGraph


def disjoint_union(ga: StateGraph, gb: StateGraph,
                   prefix_a: str = "a_", prefix_b: str = "b_") -> tuple:
    """Combine two block graphs into one (ids prefixed). Returns (graph, ma, mb)."""
    g = StateGraph()
    ma: dict[str, str] = {}
    mb: dict[str, str] = {}
    for src, pre, m in ((ga, prefix_a, ma), (gb, prefix_b, mb)):
        for n in src.nodes():
            nid = pre + n
            g.add_node(src.node_label(n), id=nid, **src.node_attrs(n))
            m[n] = nid
    for src, m in ((ga, ma), (gb, mb)):
        for e in src.edges():
            g.add_edge(m[e["src"]], m[e["tgt"]], e["orientation"],
                       bidirectional=e["bidirectional"], weight=e["weight"],
                       type=e["type"], **e["attrs"])
    return g, ma, mb


def mark_interface(sg: StateGraph, *ids: str) -> None:
    """Tag nodes as block interface points (αN["interface"] = True, §7.6.3)."""
    from ._topo import set_value
    for i in ids:
        set_value(sg._vertex_obj(i), "interface", True)


def interface_nodes(sg: StateGraph) -> list[str]:
    # bool is stored as int in topologic dicts (1/0) — test truthiness, not `is True`
    return [n for n in sg.nodes() if sg.node_attrs(n).get("interface")]


@dataclass
class Bridge(AtomicOp):
    """BRIDGE(a* , b* , κ) — connect two interface nodes across blocks.

    ``connector='edge'`` adds a single adjacency edge; ``connector='corridor'``
    inserts a corridor/bridge node ``a* — κ:corridor — b*`` (an enclosed passage).
    """

    a: str
    b: str
    connector: str = "edge"
    orientation: str = H
    weight: float = DEFAULT_WEIGHT
    bridge_node: str | None = field(default=None, init=False)

    def apply(self, sg: StateGraph) -> OpSequence:
        rec = _Recorder(sg)
        if self.connector == "edge":
            rec.do(AddEdge(self.a, self.b, self.orientation, weight=self.weight))
        elif self.connector == "corridor":
            self.bridge_node = rec.do(AddNode(CORRIDOR, {"subtype": "bridge"})).id
            rec.do(AddEdge(self.a, self.bridge_node, self.orientation, weight=self.weight))
            rec.do(AddEdge(self.bridge_node, self.b, self.orientation, weight=self.weight))
        else:
            raise ValueError(f"BRIDGE: unknown connector {self.connector!r}")
        return rec.inverse()
