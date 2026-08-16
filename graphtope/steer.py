"""SG8 — steering over two levels (G5).

Both grammar levels now vary (SG3) and are measurable (G4 macro, SG7 micro,
SG6 cross-level rates) — this module *steers* generation: sample a pool of
interior variants for a slab (the SG3 machinery: valid, distinct,
replayable), place each (SG4), evaluate every objective, and rank by a
within-pool standardised weighted score (min-sense) — deterministic, and
trivially replayable because every candidate carries its plan.

The objective vocabulary composes the three families:

* **macro** (``metrics.feature_vector``): compactness, area_per_unit,
  circulation_depth, …
* **micro** (``metrics.interior_quality_vector``): privacy_gradient,
  daylight_ratio, wet_core_compactness, interior_type_mix, …
* **cross-level penalties** (``crosslevel.violations`` counts): the SG6
  constraints that measured as "filtered **or steered**" — steering them is
  the point: instead of rejecting variants after the fact, the search finds
  interiors that satisfy the constraint *and* optimise the objective.

Scores are **within-pool z-scores** — the ranking is meaningful relative to
what the grammar offered for this slab, not on an absolute scale (which the
mixed units of the families would make meaningless).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Objective:
    """One steering term: minimise (or maximise) value ``name`` (from
    ``VALUE_REGISTRY``) with ``weight``. Defaults lean on the plan's SG8
    examples: daylight and compactness up, wet spread and cross-level
    violations down."""

    name: str
    weight: float = 1.0
    sense: str = "min"          # "min" | "max"


#: the objective vocabulary — every value `evaluate` can report (macro,
#: micro, cross-level); see metrics/crosslevel for the definitions
VALUE_REGISTRY = (
    "unit_count", "kf_ratio", "circulation_depth", "level_count",
    "gross_floor_area", "volume", "footprint", "compactness", "area_per_unit",
    "privacy_gradient", "daylight_ratio", "circ_area_ratio",
    "wet_core_compactness", "interior_type_mix",
    "wet_stacking", "bay_alignment", "void_coherence", "level_monotonicity",
)

#: a sensible default programme (the paper's SG8 demo): a lit, compact,
#: plumbing-coherent building
DEFAULT_OBJECTIVES = (
    Objective("daylight_ratio", 2.0, "max"),
    Objective("wet_stacking", 3.0, "min"),
    Objective("wet_core_compactness", 1.0, "min"),
    Objective("compactness", 1.0, "max"),
)


def evaluate(slab, refined) -> dict:
    """Every measurable value of one (block, interior) pair — the steering
    substrate, and the honest report of what a chosen variant *is*."""
    from . import crosslevel, metrics
    v = dict(metrics.interior_quality_vector(refined))
    v.update(metrics.feature_vector(slab))
    for name, lst in crosslevel.violations(refined, slab).items():
        v[name] = float(len(lst))
    return v


@dataclass
class Steered:
    """One ranked variant: the SG3 ``InteriorVariant`` (graph, exact inverse,
    replayable plan) plus its measured values and within-pool score."""

    variant: object
    values: dict
    score: float
    rank: int = 0


#: candidates rejected by the realisability gate of the last ``steer`` call —
#: ``[(variant, [reasons])]``; introspection for honest reporting
last_rejected: list = []


def steer(slab, objectives=DEFAULT_OBJECTIVES, *, candidates: int = 8,
          seed: int = 0, top_k: int = 3) -> tuple:
    """Search the slab's interior space for variants that best satisfy
    ``objectives``. Returns ``(ranked[:top_k], pool)`` — the pool carries
    every *accepted* candidate (with values); candidates whose placed
    geometry does not realise (SG4's tiling/edge→face/opening checks) are
    rejected outright and listed in the pool entry's place — steering never
    trades the grammar's guarantees for score. Deterministic: same slab,
    seed and objectives → the same ranking."""
    from . import bridge, interior_geom

    vs = bridge.interior_variants(slab, candidates, seed=seed)
    pool: list = []
    rejected: list = []
    for v in vs:
        interior_geom.place(v.graph, slab)
        rep = interior_geom.tile_report(v.graph, slab)
        if not rep["ok"]:            # not a building — honest rejection, kept
            reasons = ([f"edge:{a}-{b}" for r in rep["units"].values()
                        for a, b in r["edge_face_misses"]]
                       + [f"overlap:{a}-{b}" for r in rep["units"].values()
                          for a, b in r["overlaps"]]
                       + [f"opening:{n}" for n in rep["opening_faults"]])
            rejected.append((v, reasons))
            continue
        pool.append(Steered(v, evaluate(slab, v.graph), 0.0))
    global last_rejected
    last_rejected = rejected       # introspection, not a hidden channel

    # within-pool z-scores per objective; ties break by pool order (stable)
    if not pool:
        return [], []
    for o in objectives:
        col = [p.values[o.name] for p in pool]
        mu = sum(col) / len(col)
        sd = (sum((x - mu) ** 2 for x in col) / len(col)) ** 0.5
        for p in pool:
            z = (p.values[o.name] - mu) / sd if sd > 1e-12 else 0.0
            p.score += o.weight * (z if o.sense == "min" else -z)
    ranked = sorted(range(len(pool)), key=lambda i: (pool[i].score, i))
    for r, i in enumerate(ranked[:top_k]):
        pool[i].rank = r + 1
    return [pool[i] for i in ranked[:top_k]], pool


def replay(slab, steered: Steered):
    """Re-derive a steered variant from its plan (the SG3 guarantee) — the
    designer-in-the-loop handoff: the plan is the artefact. Places the fresh
    derivation first, so the comparison covers the placed geometry too."""
    from . import bridge, interior_geom, serialize
    g, _ = bridge.refine_units(slab, all_bays=True, plan=steered.variant.plan)
    interior_geom.place(g, slab)
    return serialize.to_dict(g) == serialize.to_dict(steered.variant.graph)
