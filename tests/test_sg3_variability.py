"""SG3 tests — sub-derivation variability: one slab, many interiors.

The plan's contract: N refinements of one slab are pairwise non-isomorphic,
each passes SG1's predicates, each inverts to the same slab exactly, and each
carries a replayable sub-derivation (its plan).
"""

from graphtope import bridge, interior, metrics, serialize
from graphtope import narkomfin as nf
from graphtope.compare import typed_isomorphic


def test_one_slab_many_distinct_valid_interiors():
    slab = nf.derive_slab_from_patterns(["KFDB"])
    vs = bridge.interior_variants(slab, 5, seed=0)
    assert len(vs) == 5
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            assert not typed_isomorphic(vs[i].graph, vs[j].graph)
    for v in vs:
        assert interior.violations(v.graph) == []
        assert v.graph.is_fully_refined()


def test_variants_replay_exactly_and_invert_to_the_slab():
    slab = nf.derive_slab_from_patterns(["KFD"])
    before = serialize.to_dict(slab)
    vs = bridge.interior_variants(slab, 3, seed=1)
    assert len(vs) == 3
    for v in vs:
        # the plan is the replayable sub-derivation: same plan → same graph
        replay, _ = bridge.refine_units(slab, all_bays=True, plan=v.plan)
        assert serialize.to_dict(replay) == serialize.to_dict(v.graph)
        # …and the inverse is exact, back to the untouched slab
        v.inverse.apply(v.graph)
        assert serialize.to_dict(v.graph) == before
    assert serialize.to_dict(slab) == before     # the slab itself never mutated


def test_paired_k_in_a_variant_never_takes_the_full_void():
    slab = nf.derive_slab_from_patterns(["DD"])
    vs = bridge.interior_variants(slab, 4, seed=2)
    for v in vs:
        extents = {v.graph.node_attrs(n).get("extent")
                   for n in v.graph.nodes()
                   if v.graph.node_attrs(n).get("subtype") == "void"}
        assert extents <= {"partial"}            # §5.1 holds across the space


def test_interior_design_space_is_deterministic():
    slab = nf.derive_slab_from_patterns(["KFB"])
    vs = bridge.interior_variants(slab, 4, seed=3)
    ref, _ = bridge.refine_units(slab, all_bays=True)    # default interior
    m = metrics.interior_design_space([v.graph for v in vs], reference=ref)
    assert m["coords"].shape == (len(vs) + 1, 2)
    assert m["reference_index"] == len(vs)
    assert set(m["features"][0]) == set(metrics.INTERIOR_FEATURES)
    m2 = metrics.interior_design_space([v.graph for v in vs], reference=ref)
    assert (m["coords"] == m2["coords"]).all()
