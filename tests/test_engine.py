"""M6 tests — derivation trace, replay, invert, and the τ shape stub (§9, §10.2)."""

from graphtope import StateGraph, alphabet as A
from graphtope import serialize, shape_iface
from graphtope.compare import typed_isomorphic
from graphtope.engine import Derivation, replay
from graphtope import grammar_dnf as dnf


def _forward():
    d = Derivation(StateGraph.axiom())
    dnf.derive(d)
    return d


# -- trace JSON round-trip -------------------------------------------------
def test_trace_json_round_trip(tmp_path):
    d = _forward()
    p = tmp_path / "trace.json"
    serialize.dump_trace(d, str(p))
    loaded = serialize.load_trace(str(p))
    assert loaded == d.trace()
    assert [s["rule"] for s in loaded][:3] == ["P1", "P1", "P3"]


# -- replay reproduces the forward run ------------------------------------
def test_replay_equals_forward_run():
    d = _forward()
    forward = serialize.to_dict(d.sg)
    d2 = replay(d.trace(), dnf.PRODUCTIONS)
    assert serialize.to_dict(d2.sg) == forward       # deterministic ids → exact
    assert typed_isomorphic(d2.sg, dnf.hand_built_dnf())


def test_replay_then_invert_returns_axiom():
    trace = _forward().trace()
    d = replay(trace, dnf.PRODUCTIONS)
    d.invert()
    assert serialize.to_dict(d.sg) == serialize.to_dict(StateGraph.axiom())


def test_replay_from_loaded_trace(tmp_path):
    d = _forward()
    p = tmp_path / "t.json"
    serialize.dump_trace(d, str(p))
    d2 = replay(serialize.load_trace(str(p)), dnf.PRODUCTIONS)
    assert typed_isomorphic(d2.sg, d.sg)


# -- τ : the graph→shape interface stub (§9) ------------------------------
def test_tau_node_shape_types():
    assert shape_iface.shape_type(A.GENERIC) == "parallelepiped"
    assert shape_iface.shape_type(A.STAIRCASE) == "vertical_parallelepiped"
    g, _ = dnf.derive_dnf()
    types = shape_iface.realise_node_types(g)
    assert set(types.values()) == {
        "parallelepiped", "elongated_parallelepiped", "vertical_parallelepiped",
        "u_profile_solid", "l_profile_solid", "ground_floor_opening",
    }


def test_tau_edge_faces():
    g = StateGraph()
    g.add_node(id="a"); g.add_node(id="b"); g.add_node(id="c")
    g.add_edge("a", "b", A.H)        # vertical face / wall
    g.add_edge("a", "c", A.V)        # horizontal face / slab
    faces = {(f["src"], f["tgt"]): f["face"] for f in shape_iface.realise_edge_faces(g)}
    assert faces[("a", "b")] == "shared_vertical_face_wall"
    assert faces[("a", "c")] == "shared_horizontal_face_slab"
