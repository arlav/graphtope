"""SG1 tests — the Σ_int registry and interior validity predicates.

Each predicate must reject a hand-built violation and accept every refined
unit the current sub-grammars produce (plan §SG1).
"""

import dataclasses

import pytest

from graphtope import StateGraph, alphabet as A
from graphtope import grammar_units as GU
from graphtope import interior, metrics
from graphtope.grammar_dnf import derive_dnf


def _refined_k_and_f():
    """The G3 fixture: a corridor serving two u_sections with the l_section
    interlocked below — then both grammar levels applied."""
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.U_SECTION, id="u1"); g.add_node(A.U_SECTION, id="u2")
    g.add_node(A.L_SECTION, id="l")
    g.add_edge("c", "u1", A.H); g.add_edge("c", "u2", A.H)
    g.add_edge("u1", "l", A.V); g.add_edge("u2", "l", A.V)
    GU.refine_k(g, "u1")
    GU.refine_f(g, "l")
    return g


def test_registry_is_frozen_and_the_single_source():
    # metrics derives its set from the registry — never restated
    assert set(metrics.INTERIOR_SUBTYPES) == set(interior.ROOM_SUBTYPES)
    # the previous hand-written metrics list is covered exactly
    assert {"living", "sleeping", "kitchen", "bath", "void",
            "entry", "room"} <= interior.ROOM_SUBTYPES
    # openings are registered kinds (§5.2 resolution) but are not rooms
    assert interior.DOOR in interior.SIGMA_INT
    assert interior.WINDOW in interior.SIGMA_INT
    assert interior.OPENING_SUBTYPES.isdisjoint(interior.ROOM_SUBTYPES)
    # wet / habitable flags drive the derived views
    assert interior.WET_SUBTYPES == {"kitchen", "bath", "wc"}
    assert interior.KITCHEN not in interior.HABITABLE_SUBTYPES
    # frozen: neither the mapping nor a kind can be mutated
    with pytest.raises(TypeError):
        interior.SIGMA_INT["door"] = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        interior.SIGMA_INT["living"].habitable = False
    # grammar_units re-exports the registry's names (single source)
    assert GU.LIVING == interior.LIVING and GU.ENTRY == interior.ENTRY


def test_current_refined_units_pass_every_interior_check():
    assert interior.violations(_refined_k_and_f()) == []


def test_refined_dnf_passes_every_interior_check():
    g, _ = derive_dnf()
    for u in [n for n in g.nodes() if g.node_label(n) == A.U_SECTION]:
        GU.refine_k(g, u)
    for l in [n for n in g.nodes() if g.node_label(n) == A.L_SECTION]:
        GU.refine_f(g, l)
    assert interior.violations(g) == []


def test_unreachable_room_is_rejected():
    g = StateGraph()
    g.add_node(A.GENERIC, id="s", subtype=GU.SLEEPING)
    g.add_node(A.GENERIC, id="lv", subtype=GU.LIVING)
    g.add_edge("s", "lv", A.V)                    # a sealed split-level
    vs = interior.violations(g, (interior.check_rooms_reach_circulation,))
    assert len(vs) == 2 and all("circulation" in v for v in vs)


def test_gallery_not_over_living_is_rejected():
    g = StateGraph()
    g.add_node(A.GENERIC, id="s", subtype=GU.SLEEPING)
    g.add_node(A.GENERIC, id="k", subtype=GU.KITCHEN)
    g.add_edge("s", "k", A.H)                     # a gallery beside a kitchen
    vs = interior.violations(g, (interior.check_gallery_sits_over_living,))
    assert len(vs) == 1 and "neither above nor beside" in vs[0]


def test_void_must_open_over_living_and_onto_a_room():
    g = StateGraph()
    g.add_node(A.GENERIC, id="vd", subtype=GU.VOID)
    g.add_node(A.GENERIC, id="sl", subtype=GU.SLEEPING)
    g.add_edge("vd", "sl", A.H)                   # onto the gallery, but…
    vs = interior.violations(g, (interior.check_void_adjoins_its_volume,))
    assert len(vs) == 1 and "over a living volume" in vs[0]
    g.add_node(A.GENERIC, id="lv", subtype=GU.LIVING)
    g.add_edge("vd", "lv", A.V)                   # …now it opens over living
    assert interior.violations(g, (interior.check_void_adjoins_its_volume,)) == []


def test_openings_valence_and_daylight():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.GENERIC, id="lv", subtype=GU.LIVING)
    g.add_node(A.GENERIC, id="kt", subtype=GU.KITCHEN)
    g.add_edge("c", "lv", A.H)
    g.add_node(A.GENERIC, id="d", subtype=interior.DOOR)
    g.add_edge("lv", "d", A.H); g.add_edge("d", "kt", A.H)   # door joins two
    g.add_node(A.GENERIC, id="w", subtype=interior.WINDOW)
    g.add_edge("w", "lv", A.H)                               # window on one
    assert interior.violations(g, (interior.check_openings_well_formed,)) == []
    assert interior.violations(g, (interior.check_habitable_rooms_lit,)) == []
    # a dangling door and an over-attached window are malformed
    g.add_node(A.GENERIC, id="d2", subtype=interior.DOOR)
    g.add_edge("d2", "kt", A.H)                   # joins only one space
    g.add_edge("w", "kt", A.H)                    # window claims two rooms
    vs = interior.violations(g, (interior.check_openings_well_formed,))
    assert len(vs) == 2
    # daylight armed by the window's presence: an unlit habitable room fails
    g.add_node(A.GENERIC, id="sl", subtype=GU.SLEEPING)
    g.add_edge("sl", "lv", A.V)
    vs = interior.violations(g, (interior.check_habitable_rooms_lit,))
    assert len(vs) == 1 and "no window" in vs[0]
