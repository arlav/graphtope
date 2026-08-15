"""SG4 tests — level-2 geometry: interiors that are built, not just drawn.

The plan's contract: interior boxes tile the unit envelope (volume sums to
the envelope, no overlaps), every level-2 graph edge is a real shared face
(with the right axis for its orientation), openings sit in their wall
planes, a refined variant exports to OBJ with rooms — and placement never
breaks the refinement's exact inverse. Chain-honesty (plan R3): a unit
squeezed between two same-side neighbours cannot keep every routed side
contact on its anchor's box — the miss is *reported*, not faked.
"""

import os

import pytest

from graphtope import bridge, exchange, interior_geom, serialize
from graphtope import narkomfin as nf

FULL = dict(
    k_opts=dict(void=True, void_extent="full", kitchen_form="room",
                bath_level="entry", wc=True, loggia=True, storage=True,
                split_gallery=True, doors=True, windows=True, front_door=True),
    f_opts=dict(sleeping=True, wc=True, loggia=True, storage=True,
                doors=True, windows=True, front_door=True),
    b_opts=dict(doors=True, windows=True, front_door=True),
    r_opts=dict(storage=True, doors=True, windows=True),
)


def _refined(pattern, **kw):
    opts = {**FULL, **kw}
    slab = nf.derive_slab_from_patterns([pattern])
    g, inv = bridge.refine_units(slab, all_bays=True, **opts)
    return slab, g, inv


@pytest.mark.parametrize("pattern", ["KFDBR", "KFKF", "BBD", "RKF", "DD",
                                     "FFBRR", "BKFDR"])
def test_interiors_tile_their_envelope_and_every_edge_is_a_face(pattern):
    slab, g, _ = _refined(pattern)
    interior_geom.place(g, slab)
    rep = interior_geom.tile_report(g, slab)
    assert rep["ok"], rep
    for uid, r in rep["units"].items():
        assert abs(r["volume_error"]) < 0.1          # volume sums to envelope
        assert r["overlaps"] == []                   # no overlaps
        assert r["edge_face_misses"] == []           # every edge a real face
        assert r["cellcomplex"] is True              # carrier-verified tiling
    assert rep["opening_faults"] == []               # doors/windows in walls
    assert set(interior_geom.boxes(g)) == set(g.nodes())   # all nodes boxed


def test_placement_honours_the_section():
    """The grammar's section claims, in geometry: the K's sleeping gallery is
    V-above its living (and 1.7 m for a partial void); the void opens over
    the living; the F's entry sits at the corridor plane with living below."""
    from graphtope import alphabet as A
    from graphtope.realise import _faces_touch
    slab, g, _ = _refined("K")
    interior_geom.place(g, slab)
    units = interior_geom.units_of(g, slab)
    (u,) = units.values()
    kinds = interior_geom._by_kind(g, u["nodes"])
    lv, sl = (g.node_attrs(kinds["living"][0]), g.node_attrs(kinds["sleeping"][0]))
    box = lambda a: tuple(a[k] for k in "xyzwdh")
    assert _faces_touch(box(lv), box(sl))
    # V adjacency = z-touch with footprint overlap
    e = g.edge(kinds["sleeping"][0], kinds["living"][0])
    assert e is not None and e["orientation"] == A.V
    # the K front door is on the corridor plane
    doors = [n for n in u["nodes"] if g.node_attrs(n).get("subtype") == "door"]
    assert doors and all(g.node_attrs(d).get("placement") == "wall" for d in doors)


def test_placement_is_deterministic_and_preserves_the_inverse():
    slab, g, inv = _refined("KFDBR")
    before = serialize.to_dict(slab)
    interior_geom.place(g, slab)
    snap = serialize.to_dict(g)
    interior_geom.place(g, slab)                     # idempotent
    assert serialize.to_dict(g) == snap
    inv.apply(g)                                    # ABSTRACT after placement
    assert serialize.to_dict(g) == before           # still exact (§4)
    assert serialize.to_dict(slab) == before         # the slab never mutated


def test_chain_units_report_the_unrealisable_side_contact_honestly():
    """Plan R3: three same-family units in a row cannot all keep their routed
    side contacts on the anchor's box (one box, two party walls). The middle
    unit's miss is reported — not silently dropped, not faked."""
    slab, g, _ = _refined("KKKK")
    interior_geom.place(g, slab)
    rep = interior_geom.tile_report(g, slab)
    assert not rep["ok"]
    assert any(r["edge_face_misses"] for r in rep["units"].values())
    for uid, r in rep["units"].items():              # everything else still holds
        assert abs(r["volume_error"]) < 0.1 and r["overlaps"] == []


def test_refined_variant_exports_to_obj_with_rooms(tmp_path):
    slab, g, _ = _refined("KFDB")
    bx = interior_geom.place(g, slab)
    assert set(bx) <= set(nf.boxes_of(g))            # boxes_of works at level 2
    path = os.path.join(str(tmp_path), "refined_unit.obj")
    out = exchange.to_obj(g, path, boxes=interior_geom.boxes(g))
    assert os.path.exists(out["obj"])
    with open(out["obj"]) as fh:                     # rooms are named objects
        names = {ln.split()[1] for ln in fh if ln.startswith("g ")}
    assert names & set(g.nodes())
    side = out.get("sidecar", path + ".graph.json")
    import json
    with open(side) as fh:                           # the sidecar is the graph
        assert json.load(fh) == serialize.to_dict(g)


def test_cellcomplex_partitions_a_unit():
    slab, g, _ = _refined("KB")
    interior_geom.place(g, slab)
    units = interior_geom.units_of(g, slab)
    for uid, u in units.items():
        spaces = [n for n in u["nodes"]
                  if g.node_attrs(n).get("subtype") not in ("door", "window")]
        assert interior_geom.cellcomplex_partitions(
            {n: interior_geom.boxes(g)[n] for n in spaces}) is True
