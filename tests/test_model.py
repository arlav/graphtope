"""M1 tests — carrier + invariants (spec §2, §3)."""

import pytest

from graphtope import StateGraph, alphabet as A
from graphtope import serialize


# -- axiom ----------------------------------------------------------------
def test_axiom_is_two_isolated_generic_blocks():
    g = StateGraph.axiom()
    assert g.order() == 2
    assert g.size() == 0
    assert set(g.nodes()) == {"b1", "b2"}
    assert g.node_label("b1") == A.GENERIC
    assert g.node_attrs("b1") == {"block": "residential"}
    assert g.is_well_formed()


# -- construction + well-formedness ---------------------------------------
def test_build_small_graph_well_formed():
    g = StateGraph()
    g.add_node(A.GENERIC, id="g1")
    g.add_node(A.CORRIDOR, id="c1", level=1)
    g.add_node(A.STAIRCASE, id="s1")
    g.add_edge("g1", "c1", A.H)
    g.add_edge("c1", "s1", A.V)
    assert g.order() == 3 and g.size() == 2
    assert g.is_well_formed()
    assert g.well_formedness_errors() == []


def test_edge_orientation_defaults_match_spec():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b"); g.add_node(id="c")
    g.add_edge("a", "b", A.H)          # H -> bidirectional True
    g.add_edge("a", "c", A.V)          # V -> bidirectional False (above->below)
    assert g.edge("a", "b")["bidirectional"] is True
    assert g.edge("a", "c")["bidirectional"] is False


def test_edge_attributes_persist():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b")
    g.add_edge("a", "b", A.H, weight=2.5)
    e = g.edge("a", "b")
    assert e["weight"] == 2.5
    assert e["type"] == A.ADJACENCY
    assert e["orientation"] == A.H


def test_directed_degrees():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b")
    g.add_edge("a", "b", A.V)          # a above b
    assert g.out_degree("a") == 1 and g.in_degree("a") == 0
    assert g.in_degree("b") == 1 and g.out_degree("b") == 0
    assert g.degree("a") == 1 and g.degree("b") == 1


# -- guards ---------------------------------------------------------------
def test_unknown_label_rejected():
    g = StateGraph()
    with pytest.raises(ValueError):
        g.add_node("not_a_label", id="x")


def test_self_loop_rejected():
    g = StateGraph()
    g.add_node(id="a")
    with pytest.raises(ValueError):
        g.add_edge("a", "a", A.H)


def test_bad_orientation_rejected():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b")
    with pytest.raises(ValueError):
        g.add_edge("a", "b", "diagonal")


def test_duplicate_id_rejected():
    g = StateGraph()
    g.add_node(id="a")
    with pytest.raises(ValueError):
        g.add_node(id="a")


def test_edge_to_missing_node_rejected():
    g = StateGraph()
    g.add_node(id="a")
    with pytest.raises(ValueError):
        g.add_edge("a", "ghost", A.H)


# -- refinement predicate -------------------------------------------------
def test_is_fully_refined():
    g = StateGraph()
    g.add_node(A.GENERIC, id="g")
    assert g.is_fully_refined()
    g.add_node(A.U_SECTION, id="u")
    assert not g.is_fully_refined()


# -- JSON round-trip ------------------------------------------------------
def test_json_round_trip():
    g = StateGraph()
    g.add_node(A.GENERIC, id="g1", block="residential")
    g.add_node(A.CORRIDOR, id="c1", level=1)
    g.add_edge("g1", "c1", A.H, weight=1.5)

    data = serialize.to_dict(g)
    g2 = serialize.from_dict(data)

    assert set(g2.nodes()) == set(g.nodes())
    assert g2.node_attrs("g1") == g.node_attrs("g1")
    assert g2.edge("g1", "c1") == g.edge("g1", "c1")
    assert serialize.to_dict(g2) == data
