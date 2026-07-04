"""The graph→shape bridge — the graph grammar proposes, the shape grammar builds."""

from graphtope import alphabet as A
from graphtope import bridge, narkomfin as nf, validity
from graphtope.compare import typed_isomorphic
from graphtope.model import StateGraph
from graphtope.realise import _faces_touch


def _abstract_proposal() -> StateGraph:
    """A hand-built abstract proposal: two corridors; c2 serves two U's with an
    L interlocked below (P6+P7 shape), c1 serves two plain rooms; one room off
    in a P1 chain that no corridor reaches (must be *skipped*, not faked)."""
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
    g.add_edge("r1", "far", A.H)          # reachable room, but not on a corridor
    return g


def test_spec_reads_bands_units_and_interlock():
    spec = bridge.spec_from_graph(_abstract_proposal())
    assert len(spec.band_patterns) == 2                       # corridor per band
    assert sorted(spec.band_patterns[0]) == ["B", "B"]        # c1: two rooms
    assert sorted(spec.band_patterns[1]) == ["F", "K", "K"]   # c2: 2 U + L via P7
    assert spec.band_patterns[1][0] == "K"                    # canonical interleave
    assert spec.skipped == ("far",)                           # reported, not faked


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
    assert rep["units_realised"] == rep["units_proposed"] == 5
    assert rep["units_docked"] == 5                           # all entered off a corridor
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


def test_grammar_catalogue_end_to_end():
    cat = bridge.grammar_catalogue(3, seed=0, max_steps=8)
    assert len(cat) == 3
    for v in cat:
        assert validity.is_valid(v.slab)
        assert v.spec.units > 0
        assert v.coverage["units_docked"] == v.coverage["units_proposed"]
        assert len(v.derivation.steps) > 0                    # a real proposal, replayable
        boxes = nf.boxes_of(v.slab)
        assert all(_faces_touch(boxes[e["src"]], boxes[e["tgt"]]) for e in v.slab.edges())
    for i in range(len(cat)):
        for j in range(i + 1, len(cat)):
            assert not typed_isomorphic(cat[i].slab, cat[j].slab)
