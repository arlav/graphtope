"""Metrics & the design-space map (G4)."""

import math

import pytest

from graphtope import alphabet as A
from graphtope import bridge, grammar_dnf, metrics, narkomfin as nf


# === graph metrics =======================================================
def test_type_mix_and_unit_count():
    g = nf.derive_slab_from_patterns(["KFK"])
    mix = metrics.type_mix(g)
    assert mix[A.U_SECTION] == 2 and mix[A.L_SECTION] == 1
    assert mix[A.CORRIDOR] == 1 and mix[A.STAIRCASE] == 2
    assert metrics.unit_count(g) == 3                     # the three maisonettes


def test_kf_ratio():
    assert metrics.kf_ratio(nf.derive_slab_from_patterns(["KKF"])) == 2.0
    assert metrics.kf_ratio(nf.derive_slab_from_patterns(["KK"])) == float("inf")
    assert metrics.kf_ratio(nf.derive_slab_from_patterns(["BB"])) == 0.0


def test_circulation_depth_docked_vs_banked():
    # a K/F slab: every unit sits straight on the corridor → depth 1
    assert metrics.circulation_depth(nf.derive_slab_from_patterns(["KFK"])) == 1
    # an R bay banks a room behind an apartment → that room is depth 2
    assert metrics.circulation_depth(nf.derive_slab_from_patterns(["RB"])) == 2


def test_level_and_component_counts():
    g = nf.derive_slab_from_patterns(["KFK", "KFK"])
    assert metrics.level_count(g) >= 2                    # stacked section modules
    assert metrics.component_count(g) == 1               # one coherent building


# === geometry metrics ====================================================
def test_geometry_metrics_are_positive_and_consistent():
    g = nf.derive_slab_from_patterns(["KFKF"])
    boxes = nf.boxes_of(g)
    gfa = metrics.gross_floor_area(g, boxes)
    vol = metrics.volume(g, boxes)
    assert gfa > 0 and vol > 0
    assert 0 < metrics.compactness(g, boxes) <= 1
    assert metrics.area_per_unit(g, boxes) == pytest.approx(
        round(gfa / metrics.unit_count(g), 2))
    dx, dy, dz = metrics.bbox_extents(boxes)
    assert dx > 0 and dy > 0 and dz > 0


def test_double_loaded_bay_builds_more_volume_than_single():
    single = nf.derive_slab_from_patterns(["KK"])       # front only
    double = nf.derive_slab_from_patterns(["DD"])       # front + back in each bay
    # each D bay adds an F on the back, so more habitable volume for the same bays
    assert metrics.volume(double) > metrics.volume(single)
    assert metrics.unit_count(double) == 2 * metrics.unit_count(single)


# === interior richness (level-2) =========================================
def test_interior_richness_on_refined_slab():
    slab = nf.derive_slab_from_patterns(["KF"])
    refined, _ = bridge.refine_units(slab)
    assert metrics.interior_rooms(refined) > metrics.interior_rooms(slab)
    assert metrics.void_count(refined) >= 1              # the K unit's void
    assert metrics.rooms_per_unit(refined, slab) > 1     # units are developed


# === the design-space signature & map ====================================
def test_feature_vector_is_complete_and_numeric():
    g = nf.derive_slab_from_patterns(["KFK"])
    fv = metrics.feature_vector(g)
    assert set(fv) == set(metrics.FEATURES)
    assert all(isinstance(v, float) and math.isfinite(v) for v in fv.values())


def test_design_space_embeds_population_with_reference():
    cat = bridge.grammar_catalogue(4, seed=0, max_steps=8)
    slabs = [v.slab for v in cat]
    dnf_slab = bridge.realise_spec(bridge.spec_from_graph(grammar_dnf.derive_dnf()[0]))
    space = metrics.design_space(slabs, reference=dnf_slab)
    coords = space["coords"]
    assert coords.shape == (len(slabs) + 1, 2)
    assert space["reference_index"] == len(slabs)        # reference is the last row
    assert all(math.isfinite(c) for row in coords for c in row)
    # deterministic: same input → same embedding
    again = metrics.design_space(slabs, reference=dnf_slab)
    assert (again["coords"] == coords).all()


def test_identical_variants_embed_on_top_of_each_other():
    import numpy as np
    a = nf.derive_slab_from_patterns(["KFK"])
    b = nf.derive_slab_from_patterns(["KFK"])            # same signature
    c = nf.derive_slab_from_patterns(["BBBB"])           # different
    space = metrics.design_space([a, b, c])
    coords = space["coords"]
    d_ab = np.hypot(*(coords[0] - coords[1]))
    d_ac = np.hypot(*(coords[0] - coords[2]))
    assert d_ab < 1e-6 < d_ac                            # twins coincide, the odd one out doesn't


def test_cluster_labels_every_point_in_range():
    cat = bridge.grammar_catalogue(5, seed=1, max_steps=8)
    space = metrics.design_space([v.slab for v in cat])
    labels = metrics.cluster(space["coords"], k=2, seed=0)
    assert len(labels) == len(space["coords"])
    assert set(int(l) for l in labels) <= {0, 1}
