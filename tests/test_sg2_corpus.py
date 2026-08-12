"""SG2 tests — the level-2 production corpus (plan §SG2).

Five families (G_U, G_L, G_B, G_D, G_R) + the §5.2 opening productions.
Collectively these tests apply every production in the corpus and verify the
SG2 contract: every derivable interior passes SG1's predicates, and every
refinement inverts to the exact starting graph.
"""

import pytest

from graphtope import StateGraph, alphabet as A
from graphtope import bridge, interior, serialize
from graphtope import grammar_units as GU
from graphtope import narkomfin as nf


def _corridor_with_units():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.U_SECTION, id="u1"); g.add_node(A.U_SECTION, id="u2")
    g.add_node(A.L_SECTION, id="l")
    g.add_edge("c", "u1", A.H); g.add_edge("c", "u2", A.H)
    g.add_edge("u1", "l", A.V); g.add_edge("u2", "l", A.V)
    return g


def test_corpus_scale_and_family_coverage():
    assert len(GU.CORPUS) >= 20                  # the plan's deliverable
    assert len(GU.U_PRODUCTIONS) == 10
    assert len(GU.L_PRODUCTIONS) == 6
    assert GU.B_PRODUCTIONS and GU.R_PRODUCTIONS
    doors = [p for p in GU.OPENING_PRODUCTIONS.values()
             if any(n.subtype == GU.DOOR for n in p.rhs.nodes)]
    windows = [p for p in GU.OPENING_PRODUCTIONS.values()
               if any(n.subtype == GU.WINDOW for n in p.rhs.nodes)]
    assert len(doors) == 9 and len(windows) == 3
    # names are unique across the whole corpus
    assert len(GU.CORPUS) == (len(GU.U_PRODUCTIONS) + len(GU.L_PRODUCTIONS)
                              + len(GU.B_PRODUCTIONS) + len(GU.R_PRODUCTIONS)
                              + len(GU.OPENING_PRODUCTIONS))


def test_full_k_interior_is_valid_and_reversible():
    g = _corridor_with_units()
    before = serialize.to_dict(g)
    inv, ids = GU.refine_k(g, "u1", kitchen_form="room", bath_level="gallery",
                           wc=True, loggia=True, storage=True,
                           split_gallery=True, doors=True, windows=True,
                           front_door=True)
    subs = [g.node_attrs(n).get("subtype") for n in g.nodes()]
    for s in (GU.VOID, GU.KITCHEN, GU.BATH, GU.WC, GU.LOGGIA, GU.STORAGE,
              GU.DOOR, GU.WINDOW):
        assert s in subs
    assert subs.count(GU.SLEEPING) == 2          # the subdivided gallery
    assert subs.count(GU.DOOR) == 4              # kitchen, bath, wc + front
    assert subs.count(GU.WINDOW) == 3            # living + both galleries
    # alternates stay exclusive: no second kitchen of either form
    assert not [m for m in GU.GU_KITCHEN.matches(g)
                if m["host"] == ids["living"]]
    assert interior.violations(g) == []
    # the other unit takes the *other* alternates: full void, bath at entry
    # (windows too — once the graph carries any window, the SG1 daylight
    # check is armed for the whole building, so mixing is a real violation)
    inv2, ids2 = GU.refine_k(g, "u2", void_extent="full", bath_level="entry",
                             doors=True, windows=True)
    assert g.node_attrs(ids2["void"])["extent"] == "full"
    assert g.node_attrs(ids["void"])["extent"] == "partial"
    assert interior.violations(g) == []
    inv2.apply(g)
    inv.apply(g)
    assert serialize.to_dict(g) == before        # exact round-trip (§4)


def test_full_f_interior_is_valid_and_reversible():
    g = _corridor_with_units()
    g.add_edge("c", "l", A.H)                    # hosted on the corridor
    before = serialize.to_dict(g)
    inv, ids = GU.refine_f(g, "l", sleeping=True, wc=True, loggia=True,
                           storage=True, doors=True, windows=True,
                           front_door=True)
    subs = [g.node_attrs(n).get("subtype") for n in g.nodes()]
    for s in (GU.ENTRY, GU.SLEEPING, GU.KITCHEN, GU.BATH, GU.WC, GU.LOGGIA,
              GU.STORAGE, GU.DOOR, GU.WINDOW):
        assert s in subs
    # the bedroom sits beside the dropped living, windows on both
    assert g.has_edge(ids["living"], ids["sleeping"]) or \
        g.has_edge(ids["sleeping"], ids["living"])
    assert interior.violations(g) == []
    inv.apply(g)
    assert serialize.to_dict(g) == before


def test_b_and_r_bays_develop_and_reverse():
    g = nf.derive_slab_from_patterns(["BR"])
    before = serialize.to_dict(g)
    # R before B — the host door matches the apartment while it still is one
    inv_r, ids_r = GU.refine_r(g, "room_0_1", storage=True, doors=True,
                               windows=True)
    inv_b1, _ = GU.refine_b(g, "box_0_1", doors=True, windows=True,
                            front_door=True)
    inv_b0, _ = GU.refine_b(g, "box_0_0", doors=True, windows=True,
                            front_door=True)
    subs = [g.node_attrs(n).get("subtype") for n in g.nodes()]
    assert "apartment" not in subs               # every B developed
    for s in (GU.ENTRY, GU.LIVING, GU.KITCHEN, GU.BATH, GU.ROOM, GU.STORAGE,
              GU.DOOR, GU.WINDOW):
        assert s in subs
    assert interior.violations(g) == []
    inv_b0.apply(g); inv_b1.apply(g); inv_r.apply(g)
    assert serialize.to_dict(g) == before


def test_d_pair_refines_with_the_cross_unit_constraint():
    g = nf.derive_slab_from_patterns(["D"])
    before = serialize.to_dict(g)
    # §5.1: the K's void and the F behind cannot claim the same bay volume
    with pytest.raises(ValueError):
        GU.refine_pair(g, "K_0_0", "F_0_0", void_extent="full")
    assert serialize.to_dict(g) == before        # the refusal touched nothing
    inv, ids = GU.refine_pair(g, "K_0_0", "F_0_0",
                              k_opts={"windows": True, "front_door": True},
                              f_opts={"sleeping": True, "windows": True,
                                      "front_door": True})
    voids = [n for n in g.nodes()
             if g.node_attrs(n).get("subtype") == GU.VOID]
    assert [g.node_attrs(v)["extent"] for v in voids] == ["partial"]
    assert interior.violations(g) == []
    inv.apply(g)
    assert serialize.to_dict(g) == before


def test_refine_units_develops_every_bay_type():
    slab = nf.derive_slab_from_patterns(["KFDBR"])
    refined, inv = bridge.refine_units(
        slab, all_bays=True,
        k_opts={"wc": True, "doors": True, "windows": True,
                "front_door": True},
        f_opts={"sleeping": True, "windows": True, "front_door": True},
        b_opts={"doors": True, "windows": True, "front_door": True},
        r_opts={"storage": True, "doors": True, "windows": True})
    assert refined.is_fully_refined()
    subs = {refined.node_attrs(n).get("subtype") for n in refined.nodes()}
    assert "apartment" not in subs               # every bay type develops
    assert {GU.DOOR, GU.WINDOW} <= subs          # openings are nodes (§5.2)
    assert interior.violations(refined) == []
    inv.apply(refined)
    assert serialize.to_dict(refined) == serialize.to_dict(slab)
