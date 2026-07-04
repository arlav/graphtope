"""B1 tests — the Blender / BIM round-trip (export + reconstruct)."""

import json
import os

from graphtope import StateGraph, alphabet as A
from graphtope import exchange, serialize
from graphtope.compare import typed_isomorphic


def _clean_building():
    """No one-way H edges → geometry recovers everything exactly."""
    g = StateGraph()
    g.add_node(A.GENERIC, id="r1"); g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.GENERIC, id="r2"); g.add_node(A.STAIRCASE, id="s")
    g.add_edge("r1", "c", A.H); g.add_edge("c", "r2", A.H)
    g.add_edge("c", "s", A.V)                                  # c above s
    return g


# -- in-memory geometry round-trip ----------------------------------------
def test_roundtrip_exact_without_oneway_edges():
    g = _clean_building()
    back = exchange.roundtrip(g)
    assert typed_isomorphic(g, back)                          # geometry ⇒ typed graph
    v = [e for e in back.edges() if e["orientation"] == A.V][0]
    assert v["bidirectional"] is False                        # V recovered as one-way (above→below)


def test_roundtrip_carries_subtype():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c"); g.add_node(A.GENERIC, id="a", subtype="apartment")
    g.add_edge("c", "a", A.H)
    back = exchange.roundtrip(g)
    a = next(n for n in back.nodes() if back.node_label(n) == A.GENERIC)
    assert back.node_attrs(a).get("subtype") == "apartment"


def test_roundtrip_with_entrance_recovers_structure_not_access_direction():
    g = _clean_building()
    g.add_node(A.ENTRANCE, id="e"); g.add_edge("e", "c", A.H, bidirectional=False)
    back = exchange.roundtrip(g)
    # adjacency + node types are recovered; the entrance's one-way-ness is not
    # (a shared wall can't encode access direction) — so it's H-bidirectional here
    assert back.order() == g.order()
    assert {back.node_label(n) for n in back.nodes()} == {A.GENERIC, A.CORRIDOR, A.STAIRCASE, A.ENTRANCE}
    ent = next(n for n in back.nodes() if back.node_label(n) == A.ENTRANCE)
    assert back.neighbors(ent)                                # entrance is still adjacent to circulation


# -- OBJ + sidecar export -------------------------------------------------
def test_to_obj_writes_obj_mtl_and_sidecar(tmp_path):
    g = _clean_building()
    path = str(tmp_path / "building.obj")
    out = exchange.to_obj(g, path)
    assert os.path.exists(out["obj"]) and os.path.getsize(out["obj"]) > 0
    assert os.path.exists(str(tmp_path / "building.mtl"))     # colour material library
    assert os.path.exists(out["sidecar"])


def test_sidecar_is_the_source_graph(tmp_path):
    g = _clean_building()
    out = exchange.to_obj(g, str(tmp_path / "b.obj"))
    with open(out["sidecar"]) as fh:
        restored = serialize.from_dict(json.load(fh))
    assert typed_isomorphic(g, restored)                      # the sidecar preserves the typed graph


def test_legend_rgb():
    assert exchange.legend_rgb(A.CORRIDOR) == [232, 130, 30]  # #e8821e
    assert all(0 <= c <= 255 for c in exchange.legend_rgb(A.GENERIC))


# -- OBJ file round-trip (best-effort: types via sidecar, adjacency via bbox)
def test_graph_from_obj_recovers_types_and_some_adjacency(tmp_path):
    g = _clean_building()
    out = exchange.to_obj(g, str(tmp_path / "b.obj"))
    back = exchange.graph_from_obj(out["obj"], out["sidecar"])
    assert back.order() >= g.order()                          # OBJ re-import may add stray cells
    assert {A.CORRIDOR, A.STAIRCASE} <= {back.node_label(n) for n in back.nodes()}
    assert back.size() >= 1                                   # bounding-box adjacency recovered


# -- export at real proportions + batch -----------------------------------
def test_export_at_real_proportions(tmp_path):
    g = _clean_building()
    sizes = {A.GENERIC: (3.66, 7.01, 9.9), A.CORRIDOR: (3.66, 2.8, 4.89),
             A.STAIRCASE: (3.66, 21.0, 5.0)}
    out = exchange.to_obj(g, str(tmp_path / "b.obj"), sizes=sizes)
    assert os.path.exists(out["obj"]) and os.path.exists(out["sidecar"])
    zs = [float(l.split()[3]) for l in open(out["obj"]) if l.startswith("v ")]
    assert max(zs) - min(zs) >= 9.0                          # a real ~9.9 m storey height


def test_export_catalogue_writes_numbered_files(tmp_path):
    written = exchange.export_catalogue([_clean_building(), _clean_building()],
                                        str(tmp_path / "cat"))
    assert len(written) == 2
    files = set(os.listdir(str(tmp_path / "cat")))
    assert {"variant_00.obj", "variant_01.obj"} <= files
    assert all(os.path.exists(w["sidecar"]) for w in written)


def test_export_catalogue_combined_one_file(tmp_path):
    import json
    gs = [_clean_building(), _clean_building(), _clean_building()]
    out = exchange.export_catalogue_combined(gs, str(tmp_path / "cat.obj"), cols=2, gap=5.0)
    assert out["variants"] == 3 and os.path.exists(out["obj"]) and os.path.exists(out["sidecar"])
    meta = json.load(open(out["sidecar"]))
    assert len(meta["variants"]) == 3
    assert len({tuple(v["offset"]) for v in meta["variants"]}) == 3     # each variant offset
    names = [l.split()[1] for l in open(out["obj"]) if l.startswith("g ")]
    assert any(n.startswith("v0_") for n in names) and any(n.startswith("v2_") for n in names)


def test_to_obj_with_explicit_real_boxes(tmp_path):
    from graphtope import narkomfin as nf
    g = nf.derive_slab(bands=1, n_bays=3, pattern="KFK")
    out = exchange.to_obj(g, str(tmp_path / "slab.obj"), boxes=nf.boxes_of(g))
    assert os.path.exists(out["obj"])
    zs = [float(l.split()[3]) for l in open(out["obj"]) if l.startswith("v ")]
    assert max(zs) - min(zs) > 5                                  # real multi-floor section


def test_export_catalogue_combined_with_boxes_of(tmp_path):
    from graphtope import narkomfin as nf
    cat = nf.catalogue(3, seed=2)
    out = exchange.export_catalogue_combined(cat, str(tmp_path / "slabs.obj"),
                                             boxes_of=nf.boxes_of, cols=2, gap=20.0)
    assert out["variants"] == 3 and os.path.exists(out["obj"])
    names = [l.split()[1] for l in open(out["obj"]) if l.startswith("g ")]
    assert any(n.startswith("v0_") for n in names) and any(n.startswith("v2_") for n in names)
