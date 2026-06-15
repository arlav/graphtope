"""M3 tests — core composite operations and reversibility (spec §5)."""

import networkx as nx
import pytest

from graphtope import StateGraph, alphabet as A
from graphtope import serialize
from graphtope.composite import (
    AttachPendant, Difference, Divide, Merge, Mirror, OpSequence, Split,
    Transform, Union,
)


def canon(sg):
    return serialize.to_dict(sg)


def _nx(sg):
    G = nx.DiGraph()
    for n in sg.nodes():
        G.add_node(n, label=sg.node_label(n), **sg.node_attrs(n))
    for e in sg.edges():
        G.add_edge(e["src"], e["tgt"], type=e["type"], orientation=e["orientation"],
                   bidirectional=e["bidirectional"], weight=e["weight"])
    return G


def iso(g1, g2):
    """Isomorphic up to node renaming, label/attr/edge-attr aware."""
    return nx.is_isomorphic(_nx(g1), _nx(g2),
                            node_match=lambda a, b: a == b,
                            edge_match=lambda a, b: a == b)


def _ctx_graph():
    """A node `m` with external context on both sides + a far neighbour."""
    g = StateGraph()
    g.add_node(A.GENERIC, id="m", area=10)
    g.add_node(A.CORRIDOR, id="L"); g.add_node(A.STAIRCASE, id="R")
    g.add_edge("L", "m", A.H, weight=2.0)   # incoming
    g.add_edge("m", "R", A.H, weight=3.0)   # outgoing
    return g


# -- SPLIT reversibility --------------------------------------------------
def test_split_inverse_is_identity_h():
    g = _ctx_graph(); before = canon(g)
    inv = Split("m", A.H).apply(g)           # default π: all context to child 1
    assert g.is_well_formed()
    assert g.order() == 4 and g.size() == 3  # m → 2 children + new inter-edge
    inv.apply(g)
    assert canon(g) == before


def test_split_inverse_is_identity_v_with_partition():
    g = _ctx_graph(); before = canon(g)
    # route the incoming L-edge to child 1, the outgoing R-edge to child 2
    part = lambda e: 1 if e["src"] == "L" else 2
    inv = Split("m", A.V, partition=part, upper=1).apply(g)
    assert g.is_well_formed()
    # the new inter-edge is vertical, one-way (above→below)
    v_edges = [e for e in g.edges() if e["orientation"] == A.V]
    assert len(v_edges) == 1 and v_edges[0]["bidirectional"] is False
    inv.apply(g)
    assert canon(g) == before


# -- MERGE reversibility + MERGE ∘ SPLIT ----------------------------------
def test_merge_inverse_is_identity():
    g = StateGraph()
    g.add_node(A.GENERIC, id="a"); g.add_node(A.GENERIC, id="b")
    g.add_node(A.CORRIDOR, id="x")
    g.add_edge("a", "b", A.H)               # the shared boundary
    g.add_edge("a", "x", A.H, weight=2.0)   # external on a
    before = canon(g)
    inv = Merge("a", "b").apply(g)
    assert g.is_well_formed()
    assert not g.has_node("a") and not g.has_node("b")
    inv.apply(g)                            # the recovered SPLIT
    assert canon(g) == before


def test_merge_after_split_recovers_original_exactly():
    g = _ctx_graph(); before = canon(g)
    sp = Split("m", A.H)
    sp.apply(g)
    c1, c2 = sp.children
    # MERGE the two children back into a node with the original id/label/attrs
    Merge(c1, c2, result_id="m", result_label=A.GENERIC, result_attrs={"area": 10}).apply(g)
    assert canon(g) == before


def test_merge_after_split_isomorphic_without_ids():
    g = _ctx_graph(); before = canon(g)
    sp = Split("m", A.H); sp.apply(g)
    c1, c2 = sp.children
    Merge(c1, c2).apply(g)                  # fresh id, but structurally identical
    assert iso(g, serialize.from_dict(before))


def test_merge_requires_adjacency():
    g = StateGraph()
    g.add_node(A.GENERIC, id="a"); g.add_node(A.GENERIC, id="b")
    with pytest.raises(ValueError):
        Merge("a", "b").apply(g)


def test_merge_requires_label_policy_when_labels_differ():
    g = StateGraph()
    g.add_node(A.GENERIC, id="a"); g.add_node(A.CORRIDOR, id="b")
    g.add_edge("a", "b", A.H)
    with pytest.raises(ValueError):
        Merge("a", "b").apply(g)            # no result_label given


def test_merge_coalesces_shared_neighbour_and_inverts():
    """a and b both connect to x; MERGE coalesces under ξ=max, and inverts."""
    g = StateGraph()
    g.add_node(A.GENERIC, id="a"); g.add_node(A.GENERIC, id="b")
    g.add_node(A.CORRIDOR, id="x")
    g.add_edge("a", "b", A.H)
    g.add_edge("a", "x", A.H, weight=2.0)
    g.add_edge("b", "x", A.H, weight=5.0)
    before = canon(g)
    inv = Merge("a", "b", result_id="ab").apply(g)
    assert g.is_well_formed()
    assert g.edge("ab", "x")["weight"] == 5.0   # max(2,5)
    assert g.size() == 1                         # the two a/b→x edges coalesced to one
    inv.apply(g)
    assert canon(g) == before                    # un-coalesced exactly


# -- DIVIDE = (k-1) splits ------------------------------------------------
@pytest.mark.parametrize("k", [2, 3, 5])
def test_divide_yields_k_cells_in_a_path(k):
    g = StateGraph(); g.add_node(A.GENERIC, id="blk")
    before = canon(g)
    d = Divide("blk", k, A.H)
    inv = d.apply(g)
    assert g.is_well_formed()
    assert len(d.children) == k
    assert g.order() == k
    assert g.size() == k - 1                       # a path has k-1 edges
    # connectivity is a single path over the k cells: degree sequence 1,2,…,2,1
    u = _nx(g).to_undirected()
    assert nx.is_connected(u)
    assert sorted(d_ for _, d_ in u.degree()) == [1, 1] + [2] * (k - 2)
    inv.apply(g)
    assert canon(g) == before


# -- UNION / DIFFERENCE / MIRROR / TRANSFORM / OTHER ----------------------
def test_union_adjacency_and_inverse():
    g = StateGraph(); g.add_node(id="a"); g.add_node(id="b")
    before = canon(g)
    inv = Union("a", "b", mode="adjacency", orientation=A.H).apply(g)
    assert g.has_edge("a", "b")
    inv.apply(g); assert canon(g) == before


def test_union_merge_mode_delegates():
    g = StateGraph()
    g.add_node(A.GENERIC, id="a"); g.add_node(A.GENERIC, id="b")
    g.add_edge("a", "b", A.H)
    before = canon(g)
    inv = Union("a", "b", mode="merge").apply(g)
    assert g.order() == 1
    inv.apply(g); assert iso(g, serialize.from_dict(before))


def test_difference_carve_room_and_inverse():
    g = StateGraph(); g.add_node(A.GENERIC, id="a")
    before = canon(g)
    d = Difference("a", mode="carve_room")
    inv = d.apply(g)
    assert g.node_attrs(d.void)["subtype"] == "void"
    assert g.has_edge("a", d.void)
    inv.apply(g); assert canon(g) == before


def test_difference_reshape_is_noop():
    g = _ctx_graph(); before = canon(g)
    Difference("m", mode="reshape").apply(g)
    assert canon(g) == before


def test_mirror_and_inverse():
    # a small 2-node wing  c — g , mirror across the seam node c
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c"); g.add_node(A.GENERIC, id="g")
    g.add_edge("c", "g", A.H)
    before = canon(g)
    m = Mirror(["c", "g"], seam=["c"])
    inv = m.apply(g)
    assert g.is_well_formed()
    assert g.order() == 4                       # two copies added
    assert g.has_edge("c", m.copies["c"])       # seam stitch
    inv.apply(g); assert canon(g) == before


def test_transform_rigid_is_identity():
    g = _ctx_graph(); before = canon(g)
    inv = Transform(kind="rigid").apply(g)
    assert canon(g) == before
    inv.apply(g); assert canon(g) == before


def test_attach_pendant_and_inverse():
    g = StateGraph(); g.add_node(A.GENERIC, id="room")
    before = canon(g)
    p = AttachPendant("room", label=A.GENERIC, subtype="balcony")
    inv = p.apply(g)
    assert g.node_attrs(p.pendant)["subtype"] == "balcony"
    assert g.has_edge("room", p.pendant)
    inv.apply(g); assert canon(g) == before
