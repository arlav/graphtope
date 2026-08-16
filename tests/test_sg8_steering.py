"""SG8 tests — steering over two levels + cross-tool variant validation.

Three layers of validation, matching how the results will actually be used:

* **steering** (in-process): the search is deterministic, beats the pool it
  sampled on its own objectives, and its winners stay valid, replayable and
  invertible — steering must never trade the grammar's guarantees for score;
* **the validation core** (files): what gets exported (OBJ + authoritative
  sidecar) passes the same integrity/tiling/adjacency checks pytest runs —
  and damaged exports are *caught* (a deleted room, a moved wall);
* **Blender headless** (external): the identical core runs under
  ``blender --background`` on the same artefacts, writing ``validation.json``
  — the Jupyter↔Blender hand-off. Skipped unless a Blender binary exists;
  the notebook runs it opportunistically.
"""

import json
import os
import shutil
import subprocess

import pytest

from graphtope import bridge, exchange, interior, interior_geom, serialize
from graphtope import narkomfin as nf
from graphtope import steer, validate_io

WS_SLICE = steer.Objective("wet_stacking", 3.0, "min")


def _placed(pattern, **kw):
    slab = nf.derive_slab_from_patterns(list(pattern))
    g, _ = bridge.refine_units(slab, all_bays=True, **kw)
    interior_geom.place(g, slab)
    return slab, g


# === steering =============================================================
def test_evaluate_reports_the_full_registry():
    slab, g = _placed(["KB"], k_opts=dict(windows=True, front_door=True),
                      f_opts=dict(windows=True, front_door=True),
                      b_opts=dict(windows=True, front_door=True))
    vals = steer.evaluate(slab, g)
    assert set(vals) == set(steer.VALUE_REGISTRY)
    assert vals["daylight_ratio"] == 1.0          # windows on every room


def test_steer_is_deterministic():
    slab = nf.derive_slab_from_patterns(["KFB", "BFK"])
    a_top, a_pool = steer.steer(slab, (WS_SLICE,), candidates=5, seed=0)
    b_top, b_pool = steer.steer(slab, (WS_SLICE,), candidates=5, seed=0)
    assert [s.score for s in a_top] == [s.score for s in b_top]
    assert [s.values for s in a_pool] == [s.values for s in b_pool]


def test_steer_zeroes_the_cross_level_violation_where_sampling_violates():
    """The SG6→SG8 story: on this slab one-in-six independent variants
    violates wet stacking; steering with it as an objective never returns a
    violator — the constraint is steered, not just filtered."""
    slab = nf.derive_slab_from_patterns(["KFB", "BFK"])
    top, pool = steer.steer(slab, (WS_SLICE,), candidates=6, seed=0)
    mean_ws = sum(p.values["wet_stacking"] for p in pool) / len(pool)
    assert mean_ws > 0                             # the pool really violates…
    assert all(s.values["wet_stacking"] == 0 for s in top)   # …steering dodges it


def test_steer_maximising_a_micro_objective_takes_the_pool_max():
    slab = nf.derive_slab_from_patterns(["KFB", "BFK"])
    top, pool = steer.steer(slab, (steer.Objective("interior_type_mix", 1.0, "max"),),
                            candidates=5, seed=0)
    assert top[0].values["interior_type_mix"] == \
        max(p.values["interior_type_mix"] for p in pool)


def test_steered_winners_stay_valid_replayable_and_invertible():
    slab = nf.derive_slab_from_patterns(["KFB", "BFK"])
    top, _ = steer.steer(slab, steer.DEFAULT_OBJECTIVES, candidates=5, seed=1)
    before = serialize.to_dict(slab)
    for s in top:
        assert interior.violations(s.variant.graph) == []      # SG1 validity
        assert steer.replay(slab, s)                           # the plan re-derives
        s.variant.inverse.apply(s.variant.graph)               # §4 exact inverse
        assert serialize.to_dict(s.variant.graph) == before
    assert serialize.to_dict(slab) == before


# === the validation core (files: OBJ + authoritative sidecar) =============
def _export_best(tmp_path, name="steered"):
    slab = nf.derive_slab_from_patterns(["KB"])
    top, _ = steer.steer(slab, steer.DEFAULT_OBJECTIVES[:1], candidates=3,
                         seed=0, top_k=1)
    path = os.path.join(str(tmp_path), name + ".obj")
    out = exchange.to_obj(top[0].variant.graph, path,
                          boxes=interior_geom.boxes(top[0].variant.graph))
    return out, slab, top[0]


def test_validate_variant_passes_an_honest_export(tmp_path):
    out, _, _ = _export_best(tmp_path)
    r = validate_io.validate_variant(out["obj"])
    assert r["ok"], r
    assert r["objects"] == r["nodes"]               # every node a named object
    assert r["integrity"]["ok"] and r["tiling_ok"] and r["adjacency_ok"]
    assert all(u["ok"] for u in r["units"].values())
    assert r["edges_checked"] > 0                   # the face checks ran


def test_validate_variant_catches_a_deleted_room(tmp_path):
    out, _, _ = _export_best(tmp_path)
    with open(out["obj"]) as fh:
        lines = fh.readlines()
    # rename one interior room's group — the sidecar's node is now missing
    # from the OBJ and a stray unnamed-in-graph group appears
    i = next(i for i, ln in enumerate(lines)
             if ln.startswith("g n"))
    lines[i] = "g moved_away\n"
    with open(out["obj"], "w") as fh:
        fh.writelines(lines)
    r = validate_io.validate_variant(out["obj"])
    assert not r["integrity"]["ok"]
    assert "moved_away" in r["integrity"]["stray"]


def test_validate_variant_catches_a_shifted_wall(tmp_path):
    out, _, _ = _export_best(tmp_path)
    with open(out["obj"]) as fh:
        text = fh.read()
    # nudge one interior group 1 m along +x (all its vertices after its name)
    lines = text.split("\n")
    idx = next(i for i, ln in enumerate(lines)
               if ln.startswith("g ") and ln.strip() != "g corridor_0"
               and ln.strip() != "g entrance")
    moved, seen = [], 0
    for k, ln in enumerate(lines):
        if k > idx and ln.startswith("v ") and seen < 8:
            x, y, z = ln.split()[1:]
            moved.append(f"v {float(x) + 1.0} {y} {z}")
            seen += 1
        else:
            moved.append(ln)
    with open(out["obj"], "w") as fh:
        fh.write("\n".join(moved))
    r = validate_io.validate_variant(out["obj"])
    assert not r["ok"]          # tiling and/or adjacency broke — and it showed


def test_validate_directory_writes_the_handoff_artefact(tmp_path):
    out, _, _ = _export_best(tmp_path, name="v0")
    out2, _, _ = _export_best(tmp_path, name="v1")
    report = validate_io.validate_directory(str(tmp_path))
    assert report["ok"] and report["variants"] == 2
    with open(os.path.join(str(tmp_path), "validation.json")) as fh:
        assert json.load(fh)["ok"]


# === Blender headless (the external gate) =================================
@pytest.mark.skipif(shutil.which("blender") is None,
                    reason="no blender binary on PATH")
def test_blender_headless_runs_the_same_core(tmp_path):
    _export_best(tmp_path, name="v0")
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(repo, "blender", "validate_variants.py")
    res = subprocess.run(
        ["blender", "--background", "--python", script, "--", str(tmp_path)],
        capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
    with open(os.path.join(str(tmp_path), "validation.json")) as fh:
        report = json.load(fh)
    assert report["ok"] and report["variants"] >= 1
    assert "variants ok" in res.stdout
