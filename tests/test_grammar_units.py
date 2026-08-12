"""G3 tests — U/L section sub-grammars via REFINE (spec §7.6.2)."""

import os

import pytest

import graphtope
from graphtope import StateGraph, alphabet as A
from graphtope import exchange, serialize, validity
from graphtope import grammar_units as GU
from graphtope.compare import typed_isomorphic
from graphtope.grammar_dnf import derive_dnf

MODEL = os.path.join(os.path.dirname(graphtope.__file__), "models",
                     "U_units_realised.obj")
have_model = pytest.mark.skipif(not os.path.exists(MODEL),
                                reason="U units OBJ not present")


def _corridor_with_units():
    """A corridor serving two u_sections with the l_section interlocked below
    (the P6+P7 situation)."""
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.U_SECTION, id="u1"); g.add_node(A.U_SECTION, id="u2")
    g.add_node(A.L_SECTION, id="l")
    g.add_edge("c", "u1", A.H); g.add_edge("c", "u2", A.H)
    g.add_edge("u1", "l", A.V); g.add_edge("u2", "l", A.V)
    return g


def test_refine_k_expands_interior_and_preserves_interface():
    g = _corridor_with_units()
    inv, ids = GU.refine_k(g, "u1")
    assert g.is_well_formed()
    assert not g.has_node("u1")                     # the non-terminal is gone
    # the K interior appeared: split-level living/sleeping, internal stair,
    # double-height void, kitchen, bath
    subs = {g.node_attrs(n).get("subtype") for n in g.nodes()}
    assert {GU.LIVING, GU.SLEEPING, GU.INTERNAL, GU.VOID,
            GU.KITCHEN, GU.BATH} <= subs
    # split level: sleeping directly above living, stair connects both levels
    assert g.edge(ids["sleeping"], ids["living"])["orientation"] == A.V
    assert g.has_edge(ids["living"], ids["stair"])
    assert g.has_edge(ids["sleeping"], ids["stair"])
    # the void sits over living and opens onto the sleeping gallery
    assert g.edge(ids["void"], ids["living"])["orientation"] == A.V
    assert g.has_edge(ids["void"], ids["sleeping"])
    # anchor interface: the corridor's H edge survived, re-attached to living
    e = g.edge("c", ids["living"])
    assert e is not None and e["orientation"] == A.H and e["bidirectional"]
    # ...and so did the interlock V edge to the (still non-terminal) l_section
    assert g.has_edge(ids["living"], "l")


def test_refine_f_enters_at_corridor_level_and_drops_a_floor():
    g = _corridor_with_units()
    inv, ids = GU.refine_f(g, "l")
    assert g.is_well_formed()
    assert not g.has_node("l")
    subs = {g.node_attrs(n).get("subtype") for n in g.nodes()}
    assert {GU.ENTRY, GU.LIVING, GU.INTERNAL, GU.KITCHEN, GU.BATH} <= subs
    # living drops a floor below the corridor-level entry; internal stair down
    assert g.edge(ids["entry"], ids["living"])["orientation"] == A.V
    assert g.has_edge(ids["entry"], ids["stair"])
    assert g.has_edge(ids["living"], ids["stair"])
    # anchor interface: the u_sections' V interlock edges land on the entry
    assert g.edge("u1", ids["entry"])["orientation"] == A.V
    assert g.edge("u2", ids["entry"])["orientation"] == A.V


def test_refine_then_abstract_is_identity():
    g = _corridor_with_units()
    before = serialize.to_dict(g)
    inv_k, _ = GU.refine_k(g, "u1")
    inv_f, _ = GU.refine_f(g, "l")
    inv_f.apply(g)                                  # ABSTRACT in reverse order
    inv_k.apply(g)
    assert serialize.to_dict(g) == before           # exact round-trip (§4)
    assert typed_isomorphic(g, _corridor_with_units())


def test_void_is_optional_and_nac_blocks_a_second_void():
    g = _corridor_with_units()
    _, ids = GU.refine_k(g, "u1", void=False, kitchen=False, bath=False)
    subs = {g.node_attrs(n).get("subtype") for n in g.nodes()}
    assert GU.VOID not in subs                      # start graph only
    # the void production matches the bare split-level...
    pins = [m for m in GU.GU_VOID.matches(g) if m["lv"] == ids["living"]]
    assert pins
    GU.GU_VOID.apply(g, pins[0])
    # ...but its NAC blocks a second void over the same living space
    assert not [m for m in GU.GU_VOID.matches(g) if m["lv"] == ids["living"]]


def test_refining_units_inside_the_derived_dnf_keeps_validity():
    g, _ = derive_dnf()
    us = [n for n in g.nodes() if g.node_label(n) == A.U_SECTION]
    ls = [n for n in g.nodes() if g.node_label(n) == A.L_SECTION]
    assert len(us) == 2 and len(ls) == 1
    before = serialize.to_dict(g)
    inverses = [GU.refine_k(g, u)[0] for u in us]
    inverses.append(GU.refine_f(g, ls[0])[0])
    assert g.is_well_formed()
    assert g.is_fully_refined()                     # only terminals remain
    assert validity.is_valid(g)                     # still a building
    assert validity.is_valid(g, validity.STRICT_CHECKS)
    for inv in reversed(inverses):                  # ABSTRACT all the way back
        inv.apply(g)
    assert serialize.to_dict(g) == before


@have_model
def test_vocabulary_grounded_against_the_real_k_units():
    """The OBJ grounds structure/metrics, not names (see module docstring)."""
    g, _ = exchange.graph_from_model(MODEL)
    assert g.is_well_formed() and g.order() >= 30
    # no room-type names in the model → vocabulary is spec-grounded
    assert {g.node_attrs(n).get("subtype") for n in g.nodes()} == {"apartment"}
    dims = [g.node_attrs(n) for n in g.nodes()]
    # unit envelopes: one bay wide (≈3.66 m module), ~8.4 m deep, multi-storey
    envelopes = [a for a in dims
                 if 3.4 < a["width"] < 4.0 and a["depth"] > 8 and a["height"] > 6]
    assert envelopes                                # split-level duplex is real
    # partial-width mezzanine strips — the sleeping gallery, leaving a
    # double-height void over the rest of the living volume
    assert [a for a in dims
            if a["width"] < 2.5 and a["depth"] > 8 and a["height"] <= 2.5]
    # V-stacked interior pieces: the split level shows in the adjacency
    assert any(e["orientation"] == A.V for e in g.edges())


def test_sg0_interface_edges_route_to_declared_interior_nodes():
    """SG0: a multi-face K routes each interface edge class to its declared
    interior node — corridor and below to living, stacked-above to the
    sleeping gallery (which sits over the corridor, plan §5.3) — and
    ABSTRACT still restores the host exactly."""
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.U_SECTION, id="u")
    g.add_node(A.U_SECTION, id="above")             # a unit stacked above
    g.add_node(A.L_SECTION, id="below")             # the interlock below
    g.add_node(A.GENERIC, id="side", subtype="apartment")
    g.add_edge("c", "u", A.H)
    g.add_edge("above", "u", A.V)                   # src is the upper space
    g.add_edge("u", "below", A.V)
    g.add_edge("u", "side", A.H)
    before = serialize.to_dict(g)
    inv, ids = GU.refine_k(g, "u", void=False, kitchen=False, bath=False)
    assert g.edge("c", ids["living"]) is not None        # (H, corridor)
    assert g.edge("above", ids["sleeping"]) is not None  # (V, above) → gallery
    assert g.edge(ids["living"], "below") is not None    # (V, below)
    assert g.edge(ids["living"], "side") is not None     # default → anchor
    inv.apply(g)
    assert serialize.to_dict(g) == before


def test_sg0_interface_multiset_preserved_on_random_hosts():
    """Property (SG0): for random hosts, REFINE preserves the multiset of
    interface edges (neighbour, orientation, direction), and ABSTRACT is
    exact — the routing changes *where* edges land, never *what* survives."""
    import random
    for seed in range(6):
        rng = random.Random(seed)
        g = StateGraph()
        g.add_node(A.U_SECTION, id="u")
        expected = []
        for i in range(rng.randint(1, 6)):
            nid = f"nb{i}"
            g.add_node(rng.choice([A.CORRIDOR, A.GENERIC,
                                   A.U_SECTION, A.L_SECTION]), id=nid)
            o = rng.choice([A.H, A.V])
            if rng.random() < 0.5:
                g.add_edge(nid, "u", o)
                expected.append((nid, o, "in"))
            else:
                g.add_edge("u", nid, o)
                expected.append((nid, o, "out"))
        before = serialize.to_dict(g)
        inv, ids = GU.refine_k(g, "u")
        interior = set(ids.values())
        got = []
        for e in g.edges():
            if e["src"] in interior and e["tgt"] not in interior:
                got.append((e["tgt"], e["orientation"], "out"))
            elif e["tgt"] in interior and e["src"] not in interior:
                got.append((e["src"], e["orientation"], "in"))
        assert sorted(got) == sorted(expected)
        inv.apply(g)
        assert serialize.to_dict(g) == before
