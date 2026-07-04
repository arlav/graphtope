"""Narkomfin shape grammar — circulation-first, geometry-exact (rebuild)."""

import pytest

from graphtope import alphabet as A
from graphtope import narkomfin as nf, validity
from graphtope.realise import _faces_touch


def test_slab_is_valid_and_graph_equals_geometry():
    g = nf.derive_slab(bands=2, n_bays=6, pattern="KFKFKF")
    assert g.is_well_formed() and validity.is_valid(g)
    boxes = nf.boxes_of(g)
    # every edge is a real shared face — the graph and the geometry cannot diverge
    assert all(_faces_touch(boxes[e["src"]], boxes[e["tgt"]]) for e in g.edges())


def test_circulation_first_armature_and_docked_units():
    g = nf.derive_slab(bands=2, n_bays=5, pattern="KFKFK")
    boxes = nf.boxes_of(g)
    corridors = [n for n in g.nodes() if g.node_label(n) == A.CORRIDOR]
    stairs = [n for n in g.nodes() if g.node_label(n) == A.STAIRCASE]
    assert len(corridors) == 2 and len(stairs) == 2          # armature present
    # every maisonette shares a face with a corridor (anchored, not floating)
    units = [n for n in g.nodes() if g.node_label(n) in (A.U_SECTION, A.L_SECTION)]
    assert all(any(_faces_touch(boxes[c], boxes[u]) for c in corridors) for u in units)


def test_section_has_k_up_and_f_down():
    g = nf.derive_slab(bands=1, n_bays=4, pattern="KFKF")
    cz = g.node_attrs("corridor_0")["z"]
    k = g.node_attrs("K_0_0"); f = g.node_attrs("F_0_1")
    assert k["z"] >= cz                                       # K rises from the corridor
    assert f["z"] < cz                                       # F drops below it (interlock)
    assert g.node_label("K_0_0") == A.U_SECTION and g.node_label("F_0_1") == A.L_SECTION


@pytest.mark.parametrize("bands,bays,pattern", [(1, 4, "KF"), (3, 5, "KFKFK"), (2, 6, "KFBFKB")])
def test_parametric_variants_are_valid_buildings(bands, bays, pattern):
    g = nf.derive_slab(bands=bands, n_bays=bays, pattern=pattern)
    assert validity.is_valid(g)
    boxes = nf.boxes_of(g)
    assert all(_faces_touch(boxes[e["src"]], boxes[e["tgt"]]) for e in g.edges())


def test_boxes_carry_real_metric_dimensions():
    g = nf.derive_slab(bands=1, n_bays=3, pattern="KFK")
    boxes = nf.boxes_of(g)
    for b in boxes.values():
        assert b[3] > 0 and b[4] > 0 and b[5] > 0             # w, d, h all real
    assert boxes["corridor_0"][3] == 3 * nf.BAY               # corridor spans its bays


def test_catalogue_generates_distinct_valid_slabs():
    from graphtope.compare import typed_isomorphic
    cat = nf.catalogue(5, seed=1)
    assert len(cat) == 5
    assert all(validity.is_valid(g) for g in cat)
    for i in range(len(cat)):
        for j in range(i + 1, len(cat)):
            assert not typed_isomorphic(cat[i], cat[j])           # deduped
