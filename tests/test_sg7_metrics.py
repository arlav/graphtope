"""SG7 tests — interior quality metrics + the two-level design space.

The plan's contract: the metrics are stable and deterministic; the reference
(SG5's reproduction) lands where expected on both axes — its micro signature
equals the derived interior's (they are typed-isomorphic, and the metrics
are isomorphism-invariant); and the joint map positions by block while
colouring by interior.
"""

import pytest

from graphtope import bridge, interior_geom, metrics, narkomfin as nf, reference
from graphtope.compare import typed_isomorphic

FULL = dict(
    k_opts=dict(wc=True, storage=True, split_gallery=True, doors=True,
                windows=True, front_door=True),
    f_opts=dict(sleeping=True, wc=True, storage=True, doors=True,
                windows=True, front_door=True),
    b_opts=dict(doors=True, windows=True, front_door=True),
    r_opts=dict(storage=True, doors=True, windows=True),
)


def _placed(pattern, **kw):
    opts = {**FULL, **kw}
    slab = nf.derive_slab_from_patterns([pattern])
    g, _ = bridge.refine_units(slab, all_bays=True, **opts)
    interior_geom.place(g, slab)
    return slab, g


def test_quality_metrics_are_deterministic_and_discriminating():
    _, g = _placed("KFDB")
    v1, v2 = metrics.interior_quality_vector(g), metrics.interior_quality_vector(g)
    assert v1 == v2                                   # deterministic
    assert set(v1) == set(metrics.INTERIOR2_FEATURES)
    _, g_plain = _placed("KFDB", k_opts=dict(windows=False, front_door=False),
                         f_opts=dict(windows=False, front_door=False),
                         b_opts=dict(windows=False, front_door=False),
                         r_opts=dict(windows=False))
    plain = metrics.interior_quality_vector(g_plain)
    assert v1["privacy_gradient"] > plain["privacy_gradient"]   # doors withdraw
    assert v1["daylight_ratio"] == 1.0                          # every room lit
    assert plain["daylight_ratio"] == 0.0                       # no windows


def test_metrics_are_isomorphism_invariant():
    """The reference (geometry-read) and the derived interior agree on every
    axis — the SG5 result restated as a measurement."""
    r = reference.reproduce("K")
    assert typed_isomorphic(r["derived"], reference.reference_graph("K"))
    assert metrics.interior_quality_vector(r["derived"]) == \
        metrics.interior_quality_vector(reference.reference_graph("K"))


def test_two_level_map_shape_and_determinism():
    pairs = []
    for i, pattern in enumerate(("KFKF", "BBD", "KFDBR")):
        slab = nf.derive_slab_from_patterns([pattern])
        for v in bridge.interior_variants(slab, 2, seed=i):
            interior_geom.place(v.graph, slab)
            pairs.append((slab, v.graph))
    ref = _placed("KF")
    space = metrics.two_level_design_space(pairs, reference=ref)
    n = len(pairs) + 1
    assert space["macro"].shape == (n, 2) and space["micro"].shape == (n, 2)
    assert space["reference_index"] == n - 1
    assert set(space["micro_features"][0]) == set(metrics.INTERIOR2_FEATURES)
    again = metrics.two_level_design_space(pairs, reference=ref)
    assert (space["macro"] == again["macro"]).all()
    assert (space["micro"] == again["micro"]).all()


def test_two_level_map_draws():
    import matplotlib
    matplotlib.use("Agg")
    from graphtope import topoview
    pairs = []
    for i, pattern in enumerate(("KFKF", "BBD")):
        slab = nf.derive_slab_from_patterns([pattern])
        for v in bridge.interior_variants(slab, 2, seed=i):
            interior_geom.place(v.graph, slab)
            pairs.append((slab, v.graph))
    space = metrics.two_level_design_space(pairs)
    fig = topoview.draw_two_level(space, labels=[f"p{i}" for i in range(len(pairs))])
    assert fig is not None
    matplotlib.pyplot.close(fig)


def test_reference_lands_on_both_axes():
    """The plan's acceptance: the reference is placeable on the map and its
    features are what the derivation says they are (macro from its slab,
    micro equal to its interior's vector)."""
    ref = _placed("KF")
    pairs = [ref, ref]        # a minimal population containing the reference
    space = metrics.two_level_design_space(pairs)
    assert space["micro_features"][0] == metrics.interior_quality_vector(ref[1])
    assert space["macro_features"][0] == metrics.feature_vector(ref[0])
