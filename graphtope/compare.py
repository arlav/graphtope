"""Graph comparison helpers (used by the recovery / composition tests).

``typed_isomorphic`` is the right notion for "reproduces the figure-5 graph":
it compares node label + subtype and edge orientation/type, treating
bidirectional H-adjacency as undirected and one-way edges (V, entrance) as
directed — the typed adjacency graph, ignoring ids, weights and free attrs.
``isomorphic`` is the stricter attribute-aware version.
"""

from __future__ import annotations

import networkx as nx


def _typed_nx(sg):
    G = nx.DiGraph()
    for n in sg.nodes():
        G.add_node(n, label=sg.node_label(n), subtype=sg.node_attrs(n).get("subtype"))
    for e in sg.edges():
        a = {"orientation": e["orientation"], "type": e["type"]}
        G.add_edge(e["src"], e["tgt"], **a)
        if e["bidirectional"]:
            G.add_edge(e["tgt"], e["src"], **a)
    return G


def _attr_nx(sg):
    G = nx.DiGraph()
    for n in sg.nodes():
        G.add_node(n, label=sg.node_label(n), **sg.node_attrs(n))
    for e in sg.edges():
        G.add_edge(e["src"], e["tgt"], type=e["type"], orientation=e["orientation"],
                   bidirectional=e["bidirectional"], weight=e["weight"])
    return G


def typed_isomorphic(g1, g2) -> bool:
    """Typed isomorphism: label+subtype, oriented, bidirectional-H undirected."""
    return nx.is_isomorphic(_typed_nx(g1), _typed_nx(g2),
                            node_match=lambda a, b: a == b,
                            edge_match=lambda a, b: a == b)


def isomorphic(g1, g2) -> bool:
    """Strict isomorphism: full node attrs + edge attrs, directed."""
    return nx.is_isomorphic(_attr_nx(g1), _attr_nx(g2),
                            node_match=lambda a, b: a == b,
                            edge_match=lambda a, b: a == b)
