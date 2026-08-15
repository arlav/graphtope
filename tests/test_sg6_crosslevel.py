"""SG6 tests — cross-level constraints: the Q3 measurement.

The plan's contract: each constraint rejects a constructed violation; the
grammar's own constrained output passes; and ``measure`` quantifies what
independent two-level variation would do — which constraints must be
*modelled* (void coherence: a third of independent paired-K draws conflict),
which must be *filtered or steered* (wet stacking, bay alignment: violated
at a measurable rate under cross-family stacking), and which the grammar
already guarantees (level monotonicity: never violated).
"""

import pytest

from graphtope import bridge, crosslevel, interior_geom
from graphtope import narkomfin as nf


def _placed(bands, **opts):
    slab = nf.derive_slab_from_patterns(list(bands))
    g, inv = bridge.refine_units(slab, all_bays=True, **opts)
    interior_geom.place(g, slab)
    return slab, g


def test_stacked_pairs_see_the_stack_lines():
    slab, g = _placed(("KB", "BBK"))            # bay 0: B over K; bay 1: B over B
    pairs = set(crosslevel.stacked_pairs(g, slab))
    assert ("box_1_0", "K_0_0") in pairs         # B over K (cross-family)
    assert ("box_1_1", "box_0_1") in pairs       # B over B through the interlock


def test_same_family_defaults_stack_their_wet_rooms():
    """The built condition: repeating the same family in a stack line keeps
    the wet risers aligned (the family recipes are stack-symmetric)."""
    slab, g = _placed(("KB", "KB"))
    assert crosslevel.wet_stacking_violations(g, slab) == []


def test_wet_stacking_rejects_a_constructed_violation():
    slab, g = _placed(("KB", "KB"))
    assert crosslevel.wet_stacking_violations(g, slab) == []
    # slide the upper K's bath out of every riser below it
    up_k = "K_1_0"
    bath = next(n for n in g.nodes()
                if g.node_attrs(n).get("subtype") == "bath"
                and g.node_attrs(n).get("unit") == up_k)
    x, y, z, w, d, h = (g.node_attrs(bath)[k] for k in "xyzwdh")
    g.set_node_attr(bath, "x", x + w)            # fully beside the old footprint
    v = crosslevel.wet_stacking_violations(g, slab)
    assert any(room == bath for (_, room, _) in v)


def test_bay_alignment_rejects_a_misaligned_partition():
    slab, g = _placed(("KB", "KB"))
    crosslevel.bay_alignment_violations(g, slab)
    up_k = "K_1_0"
    kitchen = next(n for n in g.nodes()
                   if g.node_attrs(n).get("subtype") == "kitchen"
                   and g.node_attrs(n).get("unit") == up_k)
    a = g.node_attrs(kitchen)
    g.set_node_attr(kitchen, "x", a["x"] + 0.61)   # off every line below (±0.25)
    g.set_node_attr(kitchen, "w", a["w"] - 0.61)
    assert any(line == round(a["x"] + 0.61, 2)
               for (_, line, _) in crosslevel.bay_alignment_violations(g, slab))


def test_void_coherence_is_modelled_and_the_control_measures_the_need():
    """The constraint lives in the productions (``refine_pair`` refuses a
    full void for a paired K — §5.1, before any mutation); a bypassing
    interior is flagged by the post-check."""
    from graphtope import grammar_units as gu
    slab, g = _placed(("DD",))                          # constrained path
    assert crosslevel.void_coherence_violations(g, slab) == []
    void = next(n for n in g.nodes() if g.node_attrs(n).get("subtype") == "void")
    g.set_node_attr(void, "extent", "full")             # a hand-built bypass
    assert crosslevel.void_coherence_violations(g, slab)
    slab2 = nf.derive_slab_from_patterns(["DD"])        # the modelled refusal
    k = next(n for n in slab2.nodes() if slab2.node_label(n) == "u_section")
    with pytest.raises(ValueError):
        gu.refine_pair(slab2, k, slab2.node_attrs(k)["pair"], void_extent="full")


def test_level_monotonicity_rejects_an_inverted_v_edge():
    slab, g = _placed(("KB",))
    assert crosslevel.level_monotonicity_violations(g) == []
    from graphtope import alphabet as A
    bx = interior_geom.boxes(g)
    low = min(bx, key=lambda n: bx[n][2])            # lowest box…
    high = max(bx, key=lambda n: bx[n][2])           # …directly "above" it
    g.add_edge(low, high, A.V, bidirectional=False)  # src below target: inverted
    assert crosslevel.level_monotonicity_violations(g) != []


def test_measure_quantifies_q3():
    m = crosslevel.measure(variants=2, seed=0)
    assert m["interiors"] >= 8
    v, r = m["violations"], m["rates_per_interior"]
    # modelled in the productions: zero, and the control shows the need
    assert v["void_coherence"] == 0
    assert m["unconstrained_void_conflicts"] > 0.15
    # guaranteed by the grammar: zero
    assert v["level_monotonicity"] == 0
    # filtered/steered candidates: measurably violated under cross-family
    # stacking — the rates are the finding, not a pass/fail
    assert r["wet_stacking"] > 0
    assert r["bay_alignment"] > 0
