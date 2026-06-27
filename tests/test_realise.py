"""Stage-2 tests — geometry realisation, the round-trip, the geometric matcher (§9)."""

from topologicpy.Cell import Cell

from graphtope import StateGraph, alphabet as A
from graphtope import grammar_dnf as dnf
from graphtope import realise


def _tree():
    """r1 — c1 — r2 with a staircase below c1: grid-embeddable, no cycles."""
    g = StateGraph()
    g.add_node(A.GENERIC, id="r1"); g.add_node(A.CORRIDOR, id="c1")
    g.add_node(A.GENERIC, id="r2"); g.add_node(A.STAIRCASE, id="s")
    g.add_edge("r1", "c1", A.H); g.add_edge("c1", "r2", A.H)
    g.add_edge("c1", "s", A.V)
    return g


# -- cells + layout --------------------------------------------------------
def test_realise_builds_unit_cells_and_complex():
    g = _tree()
    r = realise.realise(g)
    assert len(r["cells"]) == 4
    assert all(abs(Cell.Volume(c) - 1.0) < 1e-6 for c in r["cells"].values())
    assert r["complexes"]                       # at least one CellComplex built


def test_grid_layout_levels_follow_vertical_edges():
    g = _tree()
    coords, realised, unrealised = realise.grid_layout(g)
    # the staircase (below the corridor, V edge c1→s) sits one level under it
    assert coords["s"][2] == coords["c1"][2] - 1
    assert unrealised == set()                  # a tree embeds fully


def test_grid_layout_is_deterministic():
    g = dnf.derive_dnf()[0]
    a = realise.grid_layout(g)[0]
    b = realise.grid_layout(g)[0]
    assert a == b


# -- the round-trip (spec §9) ---------------------------------------------
def test_roundtrip_exact_on_grid_embeddable_graph():
    rep = realise.roundtrip_report(_tree())
    assert rep["exact"] and rep["complete"]
    assert len(rep["unrealised"]) == 0
    assert rep["graph_order"] == 4 and rep["graph_size"] == 3


def test_roundtrip_complete_on_full_dnf():
    G = dnf.derive_dnf()[0]
    rep = realise.roundtrip_report(G)
    assert rep["graph_order"] == 18
    assert rep["complete"]                       # every realised adjacency is a shared face
    assert len(rep["realised"]) >= 15            # strong coverage of the 18 adjacencies
    # the only misses are the genuinely non-grid-embeddable motifs
    miss = {frozenset((G.node_label(a), G.node_label(b))) for a, b in
            (tuple(s) for s in rep["unrealised"])}
    assert miss <= {frozenset((A.GENERIC, A.GENERIC)),         # toilet 3-cycle
                    frozenset((A.U_SECTION, A.L_SECTION))}     # split-level interlock


# -- the geometric matcher (replaces the combinatorial predicate, §9) -----
def test_typed_cell_proportions():
    assert abs(Cell.Volume(realise.typed_cell(A.GENERIC)) - 1.0) < 1e-6
    assert abs(Cell.Volume(realise.typed_cell(A.CORRIDOR)) - 2.0) < 1e-6
    assert abs(Cell.Volume(realise.typed_cell(A.STAIRCASE)) - 2.0) < 1e-6


def test_is_similar_discriminates_shape_classes():
    assert realise.is_similar(realise.typed_cell(A.GENERIC), realise.typed_cell(A.GENERIC))
    assert not realise.is_similar(realise.typed_cell(A.GENERIC), realise.typed_cell(A.STAIRCASE))


def test_find_similar_matches_by_congruence():
    G = dnf.derive_dnf()[0]
    cells = realise.typed_cells(G)
    sim = set(realise.find_similar(realise.typed_cell(A.STAIRCASE), cells))
    staircases = {n for n in G.nodes() if G.node_label(n) == A.STAIRCASE}
    generics = {n for n in G.nodes() if G.node_label(n) == A.GENERIC}
    assert staircases <= sim                      # all staircases are congruent to the query
    assert not (generics & sim)                   # cubes are a different congruence class


# -- (a) true U/L section profiles ----------------------------------------
def test_profile_cells_are_real_solids_not_boxes():
    u = realise.typed_cell(A.U_SECTION)
    l = realise.typed_cell(A.L_SECTION)
    assert len(Cell.Faces(u)) > 6 and len(Cell.Faces(l)) > 4   # not a 6-face box
    assert Cell.Volume(u) > 0 and Cell.Volume(l) > 0


def test_geometric_matcher_distinguishes_u_from_l():
    u, l = realise.typed_cell(A.U_SECTION), realise.typed_cell(A.L_SECTION)
    assert realise.is_similar(u, realise.typed_cell(A.U_SECTION))   # U ~ U
    assert not realise.is_similar(u, l)                            # U ≇ L (boxes couldn't tell)
    assert not realise.is_similar(u, realise.typed_cell(A.GENERIC))


def test_find_similar_separates_u_and_l_sections():
    G = dnf.derive_dnf()[0]
    cells = realise.typed_cells(G)
    u_hits = set(realise.find_similar(realise.typed_cell(A.U_SECTION), cells))
    assert {n for n in G.nodes() if G.node_label(n) == A.U_SECTION} <= u_hits
    assert not ({n for n in G.nodes() if G.node_label(n) == A.L_SECTION} & u_hits)


# -- (b) constraint repair: variable-size boxes for hard motifs -----------
def test_triangle_3cycle_realised_by_clique_repair():
    g = StateGraph()
    for i in "abc":
        g.add_node(A.GENERIC, id=i)
    g.add_edge("a", "b", A.H); g.add_edge("b", "c", A.H); g.add_edge("a", "c", A.H)
    rep = realise.roundtrip_report(g)
    assert rep["complete"] and len(rep["realised"]) == 3      # all 3 edges become shared faces
    assert rep["graph_order"] == 3 and rep["graph_size"] == 3


def test_interlock_realised_by_span_repair():
    g = StateGraph()
    g.add_node(A.U_SECTION, id="u1"); g.add_node(A.U_SECTION, id="u2")
    g.add_node(A.L_SECTION, id="l")
    g.add_edge("u1", "u2", A.H); g.add_edge("u1", "l", A.V); g.add_edge("u2", "l", A.V)
    rep = realise.roundtrip_report(g)
    assert rep["complete"] and len(rep["realised"]) == 3      # L spans under both U's
    # the L cell grew to a multi-unit footprint to bridge the two U's
    assert realise.box_layout(g)[0]["l"][3] * realise.box_layout(g)[0]["l"][4] >= 2


def test_repairs_never_reduce_dnf_coverage():
    G = dnf.derive_dnf()[0]
    rep = realise.roundtrip_report(G)
    assert rep["complete"]
    assert len(rep["realised"]) >= 16            # ≥ the unit-grid baseline; repairs only help


# -- (c) geometric matcher in the rule engine (§9 swap) -------------------
from graphtope.rules import Pattern, PNode, add_node_production, match_pattern


def test_geometric_matcher_groups_by_shape_not_label():
    G = dnf.derive_dnf()[0]
    gm = realise.shape_matcher(G)
    pat = Pattern([PNode("s", label=A.STAIRCASE)])
    combo = {m["s"] for m in match_pattern(pat, G)}
    geo = {m["s"] for m in match_pattern(pat, G, node_matcher=gm)}
    labels = lambda ids: {G.node_label(n) for n in ids}
    assert labels(combo) == {A.STAIRCASE}                       # label test
    assert labels(geo) == {A.STAIRCASE, A.CORRIDOR}             # shape class (2×1×1)
    assert combo <= geo


def test_geometric_matcher_separates_u_from_l():
    G = dnf.derive_dnf()[0]
    gm = realise.shape_matcher(G)
    geo = {m["u"] for m in match_pattern(Pattern([PNode("u", label=A.U_SECTION)]), G, node_matcher=gm)}
    assert {G.node_label(n) for n in geo} == {A.U_SECTION}      # profiles exclude l_section


def test_production_applies_via_geometric_matcher():
    G = dnf.derive_dnf()[0]
    gm = realise.shape_matcher(G)
    before = serialize_order = G.order()
    P = add_node_production("attach", A.GENERIC, host_label=A.STAIRCASE)
    inv, m = P.apply_first(G, node_matcher=gm)
    assert G.node_label(m["h"]) in (A.STAIRCASE, A.CORRIDOR)    # matched by shape, not label
    assert G.order() == before + 1
    inv.apply(G)                                                # rule application still reversible
    assert G.order() == before
