"""SG6 — cross-level constraints (the Q3 measurement).

With both grammar levels varying independently (SG3), do the results remain
coherent buildings — or must cross-level conditions be modelled explicitly?
This module gives the four constraints of the plan their formal reading,
as **post-checks over placed interiors** (SG4 geometry), and
``measure`` runs the experiment: sample buildings with independent
two-level variation, count violations, and report which constraints are
*modelled in the productions* (violations impossible), which must be
*filtered or steered* (violated at a measurable rate), and which the
grammar already guarantees (never violated — a cheap invariant check).

The constraints:

* **wet stacking** — wet rooms (kitchen/bath/wc, Σ_int's ``wet`` flag) of
  vertically stacked units align in plan, so plumbing shares risers.
  Violation: a wet room in the upper unit whose footprint overlaps no wet
  room below (when the lower unit has wet rooms at all).
* **bay alignment** — the upper unit's interior partition lines (faces
  strictly inside the envelope, measured in x) continue a partition line of
  the unit below (± tol): load-path and module continuity. A *rate*, not a
  hard rule — the built building's partitions sit on a finer, survey grid.
* **void coherence (§5.1)** — a K's double-height void and the F behind it
  cannot claim the same bay volume: a paired K takes the partial void only.
  **Modelled in the productions** (``refine_pair`` raises on ``full``) — the
  measurement shows what independent variation would do without it: the
  fraction of sampled paired-K interiors that draw a full void.
* **level monotonicity (§12.2)** — every V edge points downward in z (its
  source box sits above its target box). Never violated by the grammar's
  own derivations — the post-check exists to catch bad compositions.
"""

from __future__ import annotations

from . import alphabet as A
from . import interior as I
from . import narkomfin as nf
from .interior_geom import BOX_KEYS, boxes, units_of

#: wet interior kinds come from the Σ_int registry's flag (SG1) — never
#: hand-listed here
WET_KINDS = frozenset(k.name for k in I.SIGMA_INT.values() if k.wet)


# === unit stacking (informed by the level-1 slab, read from geometry) ======
def _side(env) -> int:
    """+1 front (y > 0), −1 back — which side of the corridor the unit is on."""
    return 1 if env[1] + env[4] / 2 > 0 else -1


def _x_gap(a, b) -> float:
    return min(a[0] + a[3], b[0] + b[3]) - max(a[0], b[0])


def _z_separation(a, b) -> float:
    """Vertical clear distance between two envelopes (0 if they overlap)."""
    return max(0.0, max(a[2] - (b[2] + b[5]), b[2] - (a[2] + a[5])))


def stacked_pairs(refined, slab) -> list:
    """Vertically stacked unit pairs ``(upper_id, lower_id)``: same corridor
    side, plans overlap in x, one directly above the other with **no third
    unit between them** (a B's riser may run the 6 m through the interlock
    zone of the band above — the section is 3 floors, not 1). The pairs a
    plumbing/load path runs through."""
    units = units_of(refined, slab)
    cand = []
    for a in sorted(units):
        for b in sorted(units):
            if a == b:
                continue
            ea, eb = units[a]["envelope"], units[b]["envelope"]
            if _side(ea) != _side(eb) or _x_gap(ea, eb) < 0.5:
                continue
            if _z_separation(ea, eb) > 0.2 and ea[2] > eb[2]:
                cand.append((a, b, ea, eb))
    out = []
    for a, b, ea, eb in cand:
        between = any(
            c not in (a, b) and _side(units[c]["envelope"]) == _side(ea)
            and _x_gap(units[c]["envelope"], ea) >= 0.5
            and eb[2] + eb[5] - 0.2 < units[c]["envelope"][2]
            and units[c]["envelope"][2] + units[c]["envelope"][5] < ea[2] + 0.2
            for c in units)
        if not between:
            out.append((a, b))
    return out


def _wet_rooms(refined, u) -> list:
    return [n for n in u["nodes"]
            if refined.node_attrs(n).get("subtype") in WET_KINDS]


def _x_interval(b):
    return (b[0], b[0] + b[3])


def _overlaps(i1, i2, min_ov=0.3) -> bool:
    return min(i1[1], i2[1]) - max(i1[0], i2[0]) >= min_ov


# === the constraints (post-checks over placed interiors) ===================
def wet_stacking_violations(refined, slab, *, min_overlap=0.3) -> list:
    """Wet rooms of stacked units that share no riser (plan footprint does
    not overlap). ``(upper_room, lower_unit)`` per unsupported wet room —
    only when the lower unit *has* wet rooms to align with."""
    bx = boxes(refined)
    units = units_of(refined, slab)
    out = []
    for up_id, lo_id in stacked_pairs(refined, slab):
        wet_lo = _wet_rooms(refined, units[lo_id])
        if not wet_lo:
            continue
        lo_ivs = [_x_interval(bx[n]) for n in wet_lo if n in bx]
        for n in _wet_rooms(refined, units[up_id]):
            if n in bx and not any(_overlaps(_x_interval(bx[n]), iv, min_overlap)
                                   for iv in lo_ivs):
                out.append((up_id, n, lo_id))
    return out


def _partition_lines(refined, u, bx) -> list:
    """The unit's interior partition positions in x (box faces strictly
    inside the envelope — the envelope's own faces are the party walls)."""
    env = u["envelope"]
    lo, hi = env[0] + 0.05, env[0] + env[3] - 0.05
    lines = set()
    for n in u["nodes"]:
        if n not in bx or refined.node_attrs(n).get("subtype") in (I.DOOR, I.WINDOW):
            continue
        for x in (bx[n][0], bx[n][0] + bx[n][3]):
            if lo < x < hi:
                lines.add(round(x, 2))
    return sorted(lines)


def bay_alignment_violations(refined, slab, *, tol=0.25) -> list:
    """Partition lines of the upper unit that continue nothing below — each
    a misaligned interior wall across a stacking pair (only counted when the
    lower unit has partitions at all)."""
    bx = boxes(refined)
    units = units_of(refined, slab)
    out = []
    for up_id, lo_id in stacked_pairs(refined, slab):
        lo_lines = _partition_lines(refined, units[lo_id], bx)
        if not lo_lines:
            continue
        for x in _partition_lines(refined, units[up_id], bx):
            if not any(abs(x - y) <= tol for y in lo_lines):
                out.append((up_id, x, lo_id))
    return out


def void_coherence_violations(refined, slab) -> list:
    """Paired K units (``pair`` attr, §5.1) whose void claims the full bay —
    impossible via ``refine_pair`` (modelled in the productions); this check
    is the independent-variation control."""
    out = []
    for n in refined.nodes():
        a = refined.node_attrs(n)
        if a.get("subtype") == I.VOID and a.get("extent") == "full" and a.get("unit"):
            uid = a["unit"]
            if slab.has_node(uid) and slab.node_attrs(uid).get("pair"):
                out.append((uid, n))
    return out


def level_monotonicity_violations(refined) -> list:
    """V edges whose source box does not sit above their target box (§12.2).
    The grammar's derivations never produce one; the check exists to catch
    bad compositions (and hand-built graphs)."""
    bx = boxes(refined)
    out = []
    for e in refined.edges():
        if e["orientation"] != A.V:
            continue
        if e["src"] not in bx or e["tgt"] not in bx:
            continue
        if bx[e["src"]][2] < bx[e["tgt"]][2]:
            out.append((e["src"], e["tgt"]))
    return out


CHECKS = {
    "wet_stacking": wet_stacking_violations,
    "bay_alignment": bay_alignment_violations,
    "void_coherence": void_coherence_violations,
    "level_monotonicity": level_monotonicity_violations,
}


def violations(refined, slab) -> dict:
    """All four constraint checks in one call: ``{name: [entries]}``."""
    return {name: (fn(refined) if name == "level_monotonicity" else fn(refined, slab))
            for name, fn in CHECKS.items()}


# === the Q3 experiment =====================================================
#: two-band slabs whose bands differ — the per-bay stacks mix families (K
#: over B, F over K, …), which is what independent level-1 variation makes
BAND_PAIRS = (("KB", "BBK"), ("KF", "FKD"), ("KFB", "BFK"), ("KD", "DB"),
              ("KFDBR", "RDFKB"))


def measure(*, band_pairs=BAND_PAIRS, variants=3, seed: int = 0) -> dict:
    """Sample buildings with **independent** two-level variation — differing
    band patterns (level 1) and SG3 interior plans (level 2), no cross-level
    awareness — place them (SG4), and count constraint violations: the
    quantified answer to Q3. Also measures the *unconstrained* void-conflict
    rate: how often a paired K independently draws a full void, which the
    production-level constraint (``refine_pair``) refuses — the evidence
    that void coherence must be *modelled*, not filtered. Returns
    per-constraint violation counts and rates per interior, plus the
    unconstrained void rate over paired-K draws."""
    import random

    from . import bridge
    from .interior_geom import place

    rng = random.Random(seed)
    counts = {k: 0 for k in CHECKS}
    interiors = 0
    full_void_draws = paired_draws = 0
    for bands in band_pairs:
        slab = nf.derive_slab_from_patterns(list(bands))
        for v in bridge.interior_variants(slab, variants, seed=rng.randrange(1 << 30)):
            g = v.graph
            place(g, slab)
            vv = violations(g, slab)
            for k, lst in vv.items():
                counts[k] += len(lst)
            interiors += 1
        # the independent-draw control: what refine_pair exists to prevent
        for _ in range(variants * 2):
            plan = bridge.interior_plan(slab, rng)
            for n, opts in plan.items():
                if n.startswith("K_") and slab.has_node(n) \
                        and slab.node_attrs(n).get("pair"):
                    paired_draws += 1
                    if opts.get("void", True) and opts.get("void_extent") == "full":
                        full_void_draws += 1
    rates = {k: (counts[k] / interiors if interiors else 0.0) for k in counts}
    return {"interiors": interiors, "violations": counts, "rates_per_interior": rates,
            "unconstrained_void_conflicts":
                (full_void_draws / paired_draws if paired_draws else None),
            "paired_k_draws": paired_draws}
