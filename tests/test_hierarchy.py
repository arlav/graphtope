"""M7 tests — sub-grammar refinement REFINE / ABSTRACT (spec §7.6.2)."""

from graphtope import StateGraph, alphabet as A
from graphtope import serialize
from graphtope.hierarchy import Refine, l_section_unit, u_section_unit


def _corridor_with_u():
    """A corridor serving one u_section node (the P6 situation)."""
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.U_SECTION, id="u")
    g.add_edge("c", "u", A.H)
    return g


def test_refine_u_section_expands_unit_and_preserves_interface():
    g = _corridor_with_u()
    before = serialize.to_dict(g)
    r = Refine("u", u_section_unit())
    inv = r.apply(g)

    assert g.is_well_formed()
    assert not g.has_node("u")                      # the non-terminal is gone
    # the unit's interior appeared (lower, upper, internal stair)
    subs = {g.node_attrs(n).get("subtype") for n in g.nodes()}
    assert {"u_lower", "u_upper", "internal"} <= subs
    # the corridor's edge was re-attached to the anchor (lower), not dropped
    assert g.has_edge("c", r.anchor_id) or g.has_edge(r.anchor_id, "c")
    # ABSTRACT (the returned inverse) collapses it back exactly
    inv.apply(g)
    assert serialize.to_dict(g) == before


def test_refine_l_section_round_trips():
    g = StateGraph()
    g.add_node(A.U_SECTION, id="u"); g.add_node(A.L_SECTION, id="l")
    g.add_edge("u", "l", A.V)
    before = serialize.to_dict(g)
    inv = Refine("l", l_section_unit()).apply(g)
    assert g.is_well_formed() and not g.has_node("l")
    inv.apply(g)
    assert serialize.to_dict(g) == before


def test_refining_all_non_terminals_makes_graph_fully_refined():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.U_SECTION, id="u1"); g.add_node(A.U_SECTION, id="u2")
    g.add_node(A.L_SECTION, id="l")
    g.add_edge("c", "u1", A.H); g.add_edge("c", "u2", A.H)
    g.add_edge("u1", "l", A.V); g.add_edge("u2", "l", A.V)
    assert not g.is_fully_refined()
    Refine("u1", u_section_unit()).apply(g)
    Refine("u2", u_section_unit()).apply(g)
    Refine("l", l_section_unit()).apply(g)
    assert g.is_fully_refined()                     # only terminals remain
    assert g.is_well_formed()
