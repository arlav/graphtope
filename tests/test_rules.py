"""M4 tests — DPO productions, the typed directed matcher, and NACs (spec §6)."""

import pytest

from graphtope import StateGraph, alphabet as A
from graphtope import serialize
from graphtope.rules import (
    Pattern, PEdge, PNode, Production, add_node_production, match_pattern,
)


def canon(sg):
    return serialize.to_dict(sg)


# -- matcher: node labels -------------------------------------------------
def test_match_respects_node_label():
    g = StateGraph()
    g.add_node(A.GENERIC, id="g1"); g.add_node(A.CORRIDOR, id="c1")
    g.add_node(A.GENERIC, id="g2")
    ms = match_pattern(Pattern([PNode("x", label=A.GENERIC)]), g)
    assert {m["x"] for m in ms} == {"g1", "g2"}        # corridor excluded


def test_match_respects_subtype():
    g = StateGraph()
    g.add_node(A.GENERIC, id="t", subtype="toilet")
    g.add_node(A.GENERIC, id="r")
    ms = match_pattern(Pattern([PNode("x", label=A.GENERIC, subtype="toilet")]), g)
    assert [m["x"] for m in ms] == ["t"]


# -- matcher: orientation + direction -------------------------------------
def test_match_respects_orientation():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b"); g.add_node(id="c")
    g.add_edge("a", "b", A.H)
    g.add_edge("a", "c", A.V)        # a above c
    pat = Pattern([PNode("s"), PNode("t")], [PEdge("s", "t", orientation=A.V)])
    ms = match_pattern(pat, g)
    assert [(m["s"], m["t"]) for m in ms] == [("a", "c")]   # only the V edge


def test_match_respects_direction_for_oneway():
    # distinct labels pin the endpoints so direction is the only thing tested
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="a"); g.add_node(A.GENERIC, id="b")
    g.add_edge("a", "b", A.V)        # one-way: corridor a above generic b
    fwd = Pattern([PNode("s", label=A.CORRIDOR), PNode("t", label=A.GENERIC)],
                  [PEdge("s", "t", orientation=A.V)])
    rev = Pattern([PNode("s", label=A.CORRIDOR), PNode("t", label=A.GENERIC)],
                  [PEdge("t", "s", orientation=A.V)])   # asks generic above corridor
    assert len(match_pattern(fwd, g)) == 1
    assert match_pattern(rev, g) == []     # direction is strict for one-way edges


def test_bidirectional_h_matches_either_direction():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b")
    g.add_edge("a", "b", A.H)        # stored a→b, bidirectional True
    # pattern asks for b→a; symmetric adjacency should still match
    pat = Pattern([PNode("s"), PNode("t")], [PEdge("s", "t", orientation=A.H)])
    pairs = {(m["s"], m["t"]) for m in match_pattern(pat, g)}
    assert ("a", "b") in pairs and ("b", "a") in pairs


def test_match_is_injective():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b"); g.add_edge("a", "b", A.H)
    pat = Pattern([PNode("x"), PNode("y")], [PEdge("x", "y", orientation=A.H)])
    for m in match_pattern(pat, g):
        assert m["x"] != m["y"]


# -- NAC ------------------------------------------------------------------
def _entrance_production():
    """P5-like: add an entrance one-way into a corridor, at most one per block."""
    x = PNode("x", label=A.CORRIDOR)
    e = PNode("e", label=A.ENTRANCE)
    nac = Pattern([PNode("x"), PNode("en", label=A.ENTRANCE)],
                  [PEdge("en", "x", orientation=A.H)])
    return Production(
        name="P5", lhs=Pattern([x]), interface={"x"},
        rhs=Pattern([x, e], [PEdge("e", "x", orientation=A.H, bidirectional=False)]),
        nacs=[nac], instantiates="+N(entrance)+UNION(one-way)",
    )


def test_nac_blocks_second_entrance():
    p = _entrance_production()
    g = StateGraph(); g.add_node(A.CORRIDOR, id="c")
    assert len(p.matches(g)) == 1                 # no entrance yet → allowed
    # add an entrance, now the NAC must block
    g.add_node(A.ENTRANCE, id="e1"); g.add_edge("e1", "c", A.H, bidirectional=False)
    assert p.matches(g) == []


# -- application: additive production (reversible) ------------------------
def test_apply_additive_and_invert():
    p = add_node_production("P-add-corridor", A.CORRIDOR, host_label=A.GENERIC)
    g = StateGraph(); g.add_node(A.GENERIC, id="g")
    before = canon(g)
    inv, m = p.apply_first(g)
    assert g.order() == 2 and g.size() == 1
    new = [n for n in g.nodes() if n != "g"][0]
    assert g.node_label(new) == A.CORRIDOR and g.has_edge("g", new)
    assert g.is_well_formed()
    inv.apply(g)
    assert canon(g) == before                     # rule application is reversible


def test_apply_entrance_oneway_edge():
    p = _entrance_production()
    g = StateGraph(); g.add_node(A.CORRIDOR, id="c")
    inv, m = p.apply_first(g)
    e = [n for n in g.nodes() if g.node_label(n) == A.ENTRANCE][0]
    edge = g.edge(e, "c")
    assert edge["bidirectional"] is False and edge["orientation"] == A.H
    inv.apply(g); assert g.order() == 1


# -- application: deletion (general REPLACE) + dangling condition ---------
def test_replace_with_deletion_and_invert():
    """L: g → x(corridor)  ⇒  R: g (delete the corridor and the edge). K = {g}.

    Distinct labels make the match unique, so the deletion is deterministic."""
    g_n, x_n = PNode("g", label=A.GENERIC), PNode("x", label=A.CORRIDOR)
    p = Production(
        name="REPLACE-del-x",
        lhs=Pattern([g_n, x_n], [PEdge("g", "x", orientation=A.H)]),
        interface={"g"},
        rhs=Pattern([g_n]),
    )
    g = StateGraph()
    g.add_node(A.GENERIC, id="g"); g.add_node(A.CORRIDOR, id="x")
    g.add_edge("g", "x", A.H)
    before = canon(g)
    inv, m = p.apply_first(g)
    assert not g.has_node("x") and g.order() == 1
    inv.apply(g)
    assert canon(g) == before


def test_dangling_condition_raises():
    """Deleting a node that still has host edges outside the pattern is illegal."""
    g_n, x_n = PNode("g", label=A.GENERIC), PNode("x", label=A.CORRIDOR)
    p = Production(
        name="bad-del", lhs=Pattern([g_n, x_n], [PEdge("g", "x", orientation=A.H)]),
        interface={"g"}, rhs=Pattern([g_n]),
    )
    g = StateGraph()
    g.add_node(A.GENERIC, id="g"); g.add_node(A.CORRIDOR, id="x")
    g.add_node(A.STAIRCASE, id="extra")
    g.add_edge("g", "x", A.H)
    g.add_edge("x", "extra", A.H)        # x has an edge outside the pattern
    with pytest.raises(ValueError):
        p.apply(g, {"g": "g", "x": "x"})
