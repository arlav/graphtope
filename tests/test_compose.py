"""M7 tests — modular composition: disjoint union + the inter-block BRIDGE (§7.6.3)."""

import networkx as nx

from graphtope import StateGraph, alphabet as A
from graphtope import serialize
from graphtope.compare import typed_isomorphic
from graphtope.compose import Bridge, disjoint_union, interface_nodes, mark_interface
from graphtope.engine import Derivation
from graphtope import grammar_dnf as dnf


def _components(sg):
    G = nx.DiGraph()
    G.add_nodes_from(sg.nodes())
    for e in sg.edges():
        G.add_edge(e["src"], e["tgt"])
    return nx.number_weakly_connected_components(G)


def _residential():
    g = StateGraph(); g.add_node(A.GENERIC, id="b1", block="residential")
    d = Derivation(g); dnf.derive_residential(d, "b1")
    return g


def _condenser():
    g = StateGraph(); g.add_node(A.GENERIC, id="b2", block="condenser")
    d = Derivation(g); dnf.derive_condenser(d, "b2")
    return g


# -- independently-derived blocks compose to the full DNF graph -----------
def test_separate_blocks_union_matches_full_derivation():
    combined, _, _ = disjoint_union(_residential(), _condenser())
    full, _ = dnf.derive_dnf()
    assert _components(combined) == 2
    assert typed_isomorphic(combined, full)        # modular == monolithic


def test_disjoint_union_prefixes_and_preserves():
    a = StateGraph(); a.add_node(A.GENERIC, id="x"); a.add_node(A.CORRIDOR, id="y")
    a.add_edge("x", "y", A.H)
    b = StateGraph(); b.add_node(A.STAIRCASE, id="x")     # same id as in a
    g, ma, mb = disjoint_union(a, b)
    assert g.order() == 3 and set(g.nodes()) == {"a_x", "a_y", "b_x"}
    assert g.has_edge("a_x", "a_y") or g.has_edge("a_y", "a_x")


# -- BRIDGE joins two completed blocks (reversible) -----------------------
def test_bridge_edge_connects_components_and_inverts():
    combined, ma, mb = disjoint_union(_residential(), _condenser())
    a_star, b_star = ma["b1"], mb["b2"]
    before = serialize.to_dict(combined)
    assert _components(combined) == 2
    inv = Bridge(a_star, b_star, connector="edge").apply(combined)
    assert _components(combined) == 1              # now a single building graph
    inv.apply(combined)
    assert serialize.to_dict(combined) == before


def test_bridge_corridor_inserts_passage_node():
    combined, ma, mb = disjoint_union(_residential(), _condenser())
    before = serialize.to_dict(combined)
    br = Bridge(ma["b1"], mb["b2"], connector="corridor")
    inv = br.apply(combined)
    assert combined.node_label(br.bridge_node) == A.CORRIDOR
    assert _components(combined) == 1
    inv.apply(combined)
    assert serialize.to_dict(combined) == before


def test_interface_marking():
    g = _residential()
    some = g.nodes()[0]
    mark_interface(g, some)
    assert interface_nodes(g) == [some]
