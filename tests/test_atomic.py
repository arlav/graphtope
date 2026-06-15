"""M2 tests — atomic basis A1–A7 and reversibility (spec §4)."""

import random

import pytest

from graphtope import StateGraph, alphabet as A
from graphtope import serialize
from graphtope.atomic import (
    AddEdge, AddNode, DelEdge, DelNode, Relabel, Reweight, ReverseEdge,
)


def canon(sg):
    return serialize.to_dict(sg)


def roundtrip(sg, op):
    """Apply op, then its returned inverse; return (snapshot, after-inverse)."""
    before = canon(sg)
    inv = op.apply(sg)
    after_apply = canon(sg)
    inv.apply(sg)
    return before, after_apply, canon(sg)


# -- per-operation effect + reversibility ---------------------------------
def test_a1_add_node_and_inverse():
    g = StateGraph()
    before, after, restored = roundtrip(g, AddNode(A.CORRIDOR, {"level": 1}))
    assert len(after["nodes"]) == 1 and after["nodes"][0]["label"] == A.CORRIDOR
    assert restored == before


def test_a2_del_node_requires_isolated():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b"); g.add_edge("a", "b", A.H)
    with pytest.raises(ValueError):
        DelNode("a").apply(g)


def test_a2_del_node_and_inverse():
    g = StateGraph()
    g.add_node(A.STAIRCASE, id="s", level=2)
    before, after, restored = roundtrip(g, DelNode("s"))
    assert after["nodes"] == []
    assert restored == before  # node re-created with same id/label/attrs


def test_a3_add_edge_and_inverse():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b")
    before, after, restored = roundtrip(g, AddEdge("a", "b", A.V))
    assert len(after["edges"]) == 1 and after["edges"][0]["orientation"] == A.V
    assert restored == before


def test_a3_add_edge_rejects_duplicate():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b"); g.add_edge("a", "b", A.H)
    with pytest.raises(ValueError):
        AddEdge("a", "b", A.H).apply(g)


def test_a4_del_edge_and_inverse_preserves_attributes():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b")
    g.add_edge("a", "b", A.H, weight=3.0)
    before, after, restored = roundtrip(g, DelEdge("a", "b"))
    assert after["edges"] == []
    assert restored == before  # weight/orientation/bidirectional all restored


def test_a5_relabel_and_inverse():
    g = StateGraph()
    g.add_node(A.GENERIC, id="n")
    before, after, restored = roundtrip(g, Relabel("n", A.CORRIDOR))
    assert after["nodes"][0]["label"] == A.CORRIDOR
    assert restored == before


def test_a6_reweight_and_inverse():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b"); g.add_edge("a", "b", A.H, weight=1.0)
    before, after, restored = roundtrip(g, Reweight("a", "b", 5.0))
    assert after["edges"][0]["weight"] == 5.0
    assert restored == before


def test_a7_reverse_edge_and_inverse():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b")
    g.add_edge("a", "b", A.V, weight=2.0)
    before = canon(g)
    inv = ReverseEdge("a", "b").apply(g)
    assert g.has_edge("b", "a") and not g.has_edge("a", "b")
    assert g.edge("b", "a")["weight"] == 2.0  # attrs carried across the swap
    inv.apply(g)
    assert canon(g) == before


def test_a7_is_self_inverse_shape():
    # inverse of ReverseEdge(a,b) is ReverseEdge(b,a)
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b"); g.add_edge("a", "b", A.H)
    inv = ReverseEdge("a", "b").apply(g)
    assert isinstance(inv, ReverseEdge) and (inv.src, inv.tgt) == ("b", "a")


# -- randomized property test: inverse(op) ∘ op == id ----------------------
def _random_graph(rng, n=6):
    g = StateGraph()
    labels = list(A.NODE_LABELS)
    ids = [f"n{i}" for i in range(n)]
    for i, nid in enumerate(ids):
        g.add_node(rng.choice(labels), id=nid, level=rng.randint(0, 2))
    # add a handful of distinct, non-self, non-duplicate edges
    added = set()
    for _ in range(n):
        a, b = rng.sample(ids, 2)
        if (a, b) in added or (b, a) in added:
            continue
        o = rng.choice([A.H, A.V])
        g.add_edge(a, b, o, weight=round(rng.uniform(0.5, 3.0), 2))
        added.add((a, b))
    assert g.is_well_formed()
    return g, ids, list(added)


def _random_op(rng, g, ids, edges):
    """Pick a valid atomic op for the current graph state."""
    choices = ["addnode", "relabel"]
    isolated = [i for i in ids if g.degree(i) == 0]
    if isolated:
        choices.append("delnode")
    unconnected = [(a, b) for a in ids for b in ids
                   if a != b and not g.has_edge(a, b) and not g.has_edge(b, a)]
    if unconnected:
        choices.append("addedge")
    if edges:
        choices += ["deledge", "reweight", "reverse"]

    kind = rng.choice(choices)
    if kind == "addnode":
        return AddNode(rng.choice(list(A.NODE_LABELS)), {"k": rng.randint(0, 9)})
    if kind == "delnode":
        return DelNode(rng.choice(isolated))
    if kind == "relabel":
        return Relabel(rng.choice(ids), rng.choice(list(A.NODE_LABELS)))
    if kind == "addedge":
        a, b = rng.choice(unconnected)
        return AddEdge(a, b, rng.choice([A.H, A.V]), weight=round(rng.uniform(0.5, 3), 2))
    a, b = rng.choice(edges)
    if kind == "deledge":
        return DelEdge(a, b)
    if kind == "reweight":
        return Reweight(a, b, round(rng.uniform(0.5, 3), 2))
    return ReverseEdge(a, b)


@pytest.mark.parametrize("seed", range(25))
def test_reversibility_property(seed):
    rng = random.Random(seed)
    g, ids, edges = _random_graph(rng)
    op = _random_op(rng, g, ids, edges)

    before = canon(g)
    inv = op.apply(g)
    assert g.is_well_formed(), f"{op} broke well-formedness"
    inv.apply(g)
    assert canon(g) == before, f"inverse(op) ∘ op != id for {op}"
    assert g.is_well_formed()
