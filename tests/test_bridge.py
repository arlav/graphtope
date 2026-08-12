"""The graph→shape bridge — the graph grammar proposes, the shape grammar builds."""

from graphtope import alphabet as A
from graphtope import bridge, narkomfin as nf, validity
from graphtope.compare import typed_isomorphic
from graphtope.model import StateGraph
from graphtope.realise import _faces_touch
from graphtope.serialize import from_dict, to_dict


def _abstract_proposal() -> StateGraph:
    """A hand-built abstract proposal: two corridors; c2 serves two U's with an
    L interlocked below (P6+P7 shape), c1 serves two plain rooms; a P1 chain off
    r1 — one room deep (bankable behind r1's bay) then one deeper (must be
    *skipped*, not faked: the slab section is one room deep behind the front)."""
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c1"); g.add_node(A.CORRIDOR, id="c2")
    g.add_node(A.GENERIC, id="r1"); g.add_node(A.GENERIC, id="r2")
    g.add_edge("c1", "r1", A.H); g.add_edge("c1", "r2", A.H)
    g.add_node(A.U_SECTION, id="u1"); g.add_node(A.U_SECTION, id="u2")
    g.add_node(A.L_SECTION, id="l1")
    g.add_edge("c2", "u1", A.H); g.add_edge("c2", "u2", A.H)
    g.add_edge("u1", "l1", A.V, bidirectional=False)
    g.add_edge("u2", "l1", A.V, bidirectional=False)
    g.add_node(A.GENERIC, id="far")
    g.add_edge("r1", "far", A.H)          # one room deep — banked behind r1
    g.add_node(A.GENERIC, id="far2")
    g.add_edge("far", "far2", A.H)        # two rooms deep — beyond the section
    return g


def test_spec_reads_bands_units_interlock_and_banking():
    spec = bridge.spec_from_graph(_abstract_proposal())
    assert len(spec.band_patterns) == 2                       # corridor per band
    assert sorted(spec.band_patterns[0]) == ["B", "R"]        # r1 banks `far` behind it
    assert sorted(spec.band_patterns[1]) == ["D", "K"]        # P7 L pairs into a D bay
    assert spec.skipped == ("far2",)                          # reported, not faked


def test_one_banked_room_per_host_extras_skipped():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c1")
    g.add_node(A.GENERIC, id="r1")
    g.add_edge("c1", "r1", A.H)
    g.add_node(A.GENERIC, id="pa"); g.add_node(A.GENERIC, id="pb")
    g.add_edge("r1", "pa", A.H); g.add_edge("r1", "pb", A.H)   # two P1 rooms, one host
    spec = bridge.spec_from_graph(g)
    assert spec.band_patterns == ("R",)                        # r1 banks exactly one
    assert spec.skipped == ("pb",)                             # the other: honest skip


def test_no_corridor_means_no_slab():
    g = StateGraph()
    g.add_node(A.GENERIC, id="a")
    assert bridge.spec_from_graph(g) is None


def test_realised_spec_is_a_real_building():
    spec = bridge.spec_from_graph(_abstract_proposal())
    slab = bridge.realise_spec(spec)
    assert slab.is_well_formed() and validity.is_valid(slab)
    boxes = nf.boxes_of(slab)
    # every edge is a real shared face — graph and geometry are one
    assert all(_faces_touch(boxes[e["src"]], boxes[e["tgt"]]) for e in slab.edges())
    rep = bridge.report(_abstract_proposal(), spec, slab)
    assert rep["units_realised"] == rep["units_proposed"] == 6
    assert rep["units_docked"] == 5                           # entered off a corridor
    assert rep["rooms_banked"] == 1                           # `far`, behind r1's bay
    assert rep["units_docked"] + rep["rooms_banked"] == rep["units_realised"]
    assert rep["interlocks_reinterpreted"] == 2               # the two u→l V edges


def test_ragged_and_empty_bands():
    slab = nf.derive_slab_from_patterns(["KFK", "", "B"])
    assert validity.is_valid(slab)
    boxes = nf.boxes_of(slab)
    assert all(_faces_touch(boxes[e["src"]], boxes[e["tgt"]]) for e in slab.edges())
    # the empty band still gets its corridor, spanning the widest band
    assert boxes["corridor_1"][3] == boxes["corridor_0"][3]
    # the west stair core reaches every band's corridor
    assert all(_faces_touch(boxes["stair_W"], boxes[f"corridor_{b}"]) for b in range(3))


def test_derive_slab_delegates_unchanged():
    a = nf.derive_slab(bands=2, n_bays=5, pattern="KFKFK")
    b = nf.derive_slab_from_patterns(["KFKFK", "KFKFK"])
    assert typed_isomorphic(a, b)


def test_refine_units_drives_the_second_level_reversibly():
    slab = nf.derive_slab_from_patterns(["KFK"])
    n_units = sum(1 for n in slab.nodes()
                  if slab.node_label(n) in (A.U_SECTION, A.L_SECTION))
    assert n_units == 3
    refined, inverse = bridge.refine_units(slab)
    # level 2: every non-terminal interior expanded, graph still a building
    assert refined.is_well_formed() and refined.is_fully_refined()
    assert validity.is_valid(refined)
    assert refined.order() > slab.order()                    # interiors added rooms
    # the slab was not mutated (refine works on a copy)
    assert any(slab.node_label(n) in (A.U_SECTION, A.L_SECTION) for n in slab.nodes())
    # the interface survives: every corridor↔unit face is still present as a face
    # onto some interior anchor (connectivity preserved through refinement)
    assert validity.is_valid(refined)
    # reversible: applying the inverse collapses every interior back to the slab
    back = from_dict(to_dict(refined))
    inverse.apply(back)
    assert typed_isomorphic(back, slab)
    assert to_dict(back) == to_dict(slab)                    # exact, not just iso


def test_catalogue_refine_flag_carries_two_levels():
    cat = bridge.grammar_catalogue(2, seed=0, max_steps=8, refine=True)
    assert len(cat) == 2
    for v in cat:
        assert v.refined is not None and v.refined.is_fully_refined()
        assert validity.is_valid(v.refined)
        back = from_dict(to_dict(v.refined))
        v.refined_inverse.apply(back)
        assert typed_isomorphic(back, v.slab)                # level 2 → level 1 exactly


def test_grammar_catalogue_end_to_end():
    cat = bridge.grammar_catalogue(3, seed=0, max_steps=8)
    assert len(cat) == 3
    for v in cat:
        assert validity.is_valid(v.slab)
        assert v.spec.units > 0
        assert (v.coverage["units_docked"] + v.coverage["rooms_banked"]
                == v.coverage["units_realised"] == v.coverage["units_proposed"])
        assert len(v.derivation.steps) > 0                    # a real proposal, replayable
        boxes = nf.boxes_of(v.slab)
        assert all(_faces_touch(boxes[e["src"]], boxes[e["tgt"]]) for e in v.slab.edges())
    for i in range(len(cat)):
        for j in range(i + 1, len(cat)):
            assert not typed_isomorphic(cat[i].slab, cat[j].slab)
