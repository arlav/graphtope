# Planning & State — the graph grammar drives the shape grammar

**Date:** 2026-07-03 · **Suite:** 173 tests passing · Companion to `STATUS.md`
(milestone ledger) and `Topologic_Graph_Grammar_Spec.md` (authoritative design).

## Where we stood (review)

Two mature but disconnected halves:

1. **The abstract graph grammar** (M1–M7 + G0–G2): P1–P8 as reversible DPO
   productions over the `topologicpy.Graph` carrier, a pluggable generative
   engine (`generate.RandomStrategy`), parameterised productions
   (`grammar_params`), validity filtering (`validity`), typed-iso dedup. It
   derives rich, correct *topologies* — and stopped at the graph. Stage-2
   realisation of these graphs was a generic grid-packer: topology-valid but
   geometrically arbitrary ("box salad").
2. **The Narkomfin shape grammar** (`narkomfin.py`, the recent direction
   shift): circulation-first shape productions that place exact real-metre
   geometry (corridor spine every 3 floors, K-maisonettes rising, F-maisonettes
   dropping, the built section's interlock), with the graph *derived from* what
   touches — graph and geometry are one representation. But its `catalogue()`
   sampled bands/bays/pattern **randomly**: parametric variation, not
   grammar-driven — the grammar machinery of half 1 was unused.

The gap was named in `STATUS.md` as the next move: *"let the abstract graph
grammar propose patterns the shape grammar realises."*

## The thinking (design decisions)

**The bridge is a reader, not a solver.** An abstract derived graph has no bay
order, no left/right, no metric — so realising it is under-determined. Rather
than a general graph→layout solver (the deferred "global floor-planner"), the
bridge reads the proposal *into the shape grammar's own vocabulary*: corridors
become **bands** (one section module each), and the units each corridor serves
become its **bay pattern** (`u_section`→`K`, `l_section`→`F`, generic
apartment→`B`). The shape grammar then builds exactly what it knows how to
build. Everything slab-expressible is realised; everything else is *reported*,
never silently dropped or faked.

**Division of labour.** The graph grammar proposes the *programme*: how many
corridors, what mix of units each serves, U/L interlocks (P7). The shape
grammar owns the *armature*: stair cores + entrance are canonical
(`add_stair_cores` always caps both ends and enters at grade), so P4/P5 are
deliberately excluded from the proposal pool — otherwise abstract staircases
and the armature's fixed cores would double-count with no principled mapping.

**Unit assignment.** Each habitable node is assigned to exactly **one**
corridor — its first H-adjacent corridor in canonical id order (a spine room
between two corridors would otherwise be built twice). An `l_section` placed by
P7 (V-under two u_sections, not on a corridor) is hosted by the corridor
serving its u_sections — which is precisely how the built Narkomfin works: the
F-unit is *entered off the same corridor* as the K-units it interlocks with.
The report counts these as `interlocks_reinterpreted` rather than pretending
the abstract V edge became a horizontal slab face.

**Bay order is a free choice, made canonically.** The abstract graph carries
only unit *counts* per corridor. `_bay_pattern` emits most-remaining-first,
avoiding repeats — so (3K, 2F) reads `KFKFK`, like the built section.
Deterministic, so equal proposals give equal slabs (dedup stays meaningful).

**Ragged bands.** Proposals rarely give every corridor the same unit count, so
`derive_slab_from_patterns` (new shape-grammar entry point) accepts per-band
patterns of different lengths; an empty band keeps its corridor (spanning the
widest band) with no units. The west stair core starts at x = −1 bay, so it
reaches *every* band's corridor regardless of raggedness — connectivity never
depends on band lengths matching. `derive_slab` now delegates to it (verified
typed-isomorphic to the old behaviour).

**Honesty over coverage-inflation** (house rule: report coverage, don't fake
it). `SlabSpec.skipped` lists nodes the slab section cannot express — toilets
(sub-room scale) and rooms reachable only through other rooms (P1 chains off
the corridor system). `bridge.report()` gives units proposed/realised/docked,
interlocks reinterpreted, skips, and validity — per variant.

## What was built

- **`graphtope/bridge.py`** (new): `propose(seed)` — abstract derivation over a
  slab-shaped pool (P1, P3, P6, P7 + parameterised `add-3-u_section` /
  `add-2-l_section`), from `single_block_axiom`, fully recorded/replayable;
  `spec_from_graph(g) → SlabSpec` — the reading rules above;
  `realise_spec(spec)` — the shape grammar builds it;
  `report(abstract, spec, slab)` — honest coverage;
  `grammar_catalogue(n, seed)` — end-to-end: propose → read → realise →
  validity-filter → typed-iso dedup → `Variant(derivation, spec, slab,
  coverage)`. `Variant.sg` duck-types for `exchange.export_*`.
- **`graphtope/narkomfin.py`**: added `derive_slab_from_patterns(band_patterns)`
  (ragged bands, `.` = empty bay); `derive_slab` now delegates to it.
- **`tests/test_bridge.py`** (6 tests): spec reading incl. the P7-interlock
  hosting and skip-reporting; no-corridor → no slab; realised spec is a valid
  building with *every edge a real shared face*; ragged/empty bands stay
  connected via the west core; `derive_slab` regression (typed-iso);
  end-to-end catalogue (distinct, valid, all units docked, derivations replayable).
- **Export**: `notebooks/exports/narkomfin_grammar_catalogue.obj` (+ `.mtl`,
  `.catalogue.json` sidecar) — 6 grammar-driven variants on a grid, browsable
  in Blender alongside the earlier parametric catalogue.

## Results

Full suite: **173 passing** (167 before + 6 bridge). The exported catalogue,
seed 0: every variant valid, every proposed unit realised *and* docked (a real
shared face with its band's corridor), e.g.

| | derivation (abstract) | bands read off | units | reinterpreted V |
|---|---|---|---|---|
| v0 | P1×4 · P3×2 · P6×3 · add-2-l | `BB` / `KFKBKFKBKK` | 12/12 | 0 |
| v1 | P1×3 · P3×2 · P6×2 · add-3-u · P7×2 | `KFKBKFKBKKK` / `B` | 12/12 | 4 |
| v2 | P1×2 · P3×2 · P6×2 · add-2-l×2 · add-3-u · P7 | `KBKFKBK` / `FKFKFKFB` | 15/15 | 2 |
| v3 | P1×4 · P3×3 · P6×2 · add-3-u | `KBKB` / `KBK` / `KBKK` | 11/11 | 0 |

Variation now comes from the *derivation space* (which productions fired, on
which matches) rather than from parameter dice — each variant carries its
replayable, invertible derivation, so the abstract proposal and the built slab
are linked end-to-end: **A₀ →(graph grammar)→ proposal →(bridge)→ spec
→(shape grammar)→ exact geometry**, with edges that are real shared faces.

## Update — 2026-07-18 (richer section + G3 + two-level bridge)

Items 1–3 below are now **done**; see `STATUS.md`'s 2026-07-18 note for detail.

1. ✅ **Skipped rooms** — resolved by *extending the vocabulary*, not accepting
   the boundary. New bay types (added alongside K/F/B, backwards-compatible):
   **`D`** = K front + F back in one bay (the built double-loaded interlock, how
   the real F-unit is entered off the same corridor as its K's — replaces the
   "reinterpret the V edge as a separate F bay" reading); **`R`** = an apartment
   with a room banked one deep behind it (the P1 room-off-room chain). Seed-0
   catalogue: **0 skipped rooms** now. Deeper-than-one-room chains stay skipped
   (honest boundary). `bridge.report` gained `rooms_banked`.
2. ✅ **Richer unit sections** — the `D` bay is exactly "K and F in the same bay,
   front/back". (Double-height voids now live at level 2, in the K sub-grammar.)
3. ✅ **G3 — U/L sub-grammars via `REFINE`** — `grammar_units.py` (K/F interior
   transformation grammars) + `bridge.refine_units` (drives both levels,
   interface-preserving, exactly reversible). `grammar_catalogue(refine=True)`
   carries the level-2 refined graph on each `Variant`.

### Still open

4. **Round-trip fidelity theorem**: abstract the realised slab back (units per
   corridor) and compare to the spec — beyond the current per-edge face check.
   (With D/R bays the abstraction now has to *un-pair* D→K+F and un-bank R→B+room.)
5. ✅ **Notebook section** (done 2026-07-19): `notebooks/01_graphtope.ipynb` now
   ends with the bridge → two-level → design-space walkthrough (propose → spec →
   slab + massing; `refine_units` interior richness + reversibility; the G4 metric
   table + MDS design-space map with `G_DNF` marked). Executed clean; outputs saved.
6. ✅ **G4 metrics** (done 2026-07-19) — `metrics.py`: graph axes (units, K:F,
   circulation depth, levels), geometry axes (GFA, volume, footprint, compactness,
   area/unit), interior-richness axes (rooms/unit, voids), and a classical-MDS
   `design_space` map with `G_DNF` placed via the same bridge.
   `topoview.draw_design_space` renders it. See `STATUS.md` 2026-07-19.
7. **Ground the interior room *names*** if a room-labelled reference model turns
   up — `U_units_realised.obj` grounds structure/metrics but carries no
   living/kitchen/bath vocabulary, so those subtypes are currently spec-grounded.

### G5 — steering (the next open axis)

With G4's metrics as objective functions, generation can now be *steered* rather
than sampled: evolutionary/MCTS search over derivations toward a target
(compactness, unit count at minimum circulation depth, distance-to-`G_DNF` in the
map), or a designer-in-the-loop pick-and-extend in the notebook. The rule corpus
+ validity + metrics are the training/scoring substrate for the eventual ML
generator (G5/§12.2).
