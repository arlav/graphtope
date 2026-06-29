"""G2 tests — parameterised block productions (macro variation)."""

from graphtope import StateGraph, alphabet as A
from graphtope import grammar_params as gp, generate, serialize, validity


def _corridor():
    g = StateGraph(); g.add_node(A.CORRIDOR, id="c"); return g


def test_add_units_adds_k_and_inverts():
    g = _corridor(); before = serialize.to_dict(g)
    inv, _ = gp.add_units(A.U_SECTION, 4).apply_first(g)
    assert sum(1 for n in g.nodes() if g.node_label(n) == A.U_SECTION) == 4
    inv.apply(g)
    assert serialize.to_dict(g) == before                # reversible


def test_corridor_block_single_vs_double():
    gs = StateGraph(); gs.add_node(A.GENERIC, id="b")
    gp.corridor_block(3, loading="single").apply_first(gs)
    gd = StateGraph(); gd.add_node(A.GENERIC, id="b")
    gp.corridor_block(3, loading="double").apply_first(gd)

    apts = lambda g: [n for n in g.nodes() if g.node_attrs(n).get("subtype") == "apartment"]
    assert len(apts(gs)) == 3 and len(apts(gd)) == 6
    cd = next(n for n in gd.nodes() if gd.node_label(n) == A.CORRIDOR)
    assert gd.node_attrs(cd)["loading"] == "double"
    assert validity.is_valid(gs) and validity.is_valid(gd)


def test_add_staircase_tower():
    g = _corridor()
    inv, _ = gp.add_staircase_tower(3).apply_first(g)
    assert sum(1 for n in g.nodes() if g.node_label(n) == A.STAIRCASE) == 3
    # the tower is a vertical chain of one-way V edges
    v_edges = [e for e in g.edges() if e["orientation"] == A.V]
    assert len(v_edges) == 3 and all(not e["bidirectional"] for e in v_edges)


def test_mirror_wing_doubles_and_inverts():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c"); g.add_node(A.GENERIC, id="r"); g.add_edge("c", "r", A.H)
    before = serialize.to_dict(g)
    inv, copies = gp.mirror(g, ["c", "r"], seam=["c"])
    assert g.order() == 4 and set(copies) == {"c", "r"}
    assert g.has_edge("c", copies["c"]) or g.has_edge(copies["c"], "c")
    inv.apply(g)
    assert serialize.to_dict(g) == before


def test_variation_pool_contains_base_and_parameterised():
    pool = gp.variation_pool()
    assert {"P1", "P6", "P8"} <= set(pool)               # base grammar present
    assert any(name.startswith("corridor-double") for name in pool)
    assert any(name.startswith("add-") for name in pool)


def test_generate_with_variation_pool_yields_valid_buildings():
    pool = gp.variation_pool()
    cat = generate.catalogue(
        2, axiom_factory=generate.single_block_axiom,
        strategy_factory=lambda i: generate.RandomStrategy(
            productions=pool, seed=i, max_steps=6),
        keep=validity.is_valid, max_attempts=20)
    assert len(cat) >= 1
    assert all(validity.is_valid(d.sg) for d in cat)
