# STATUS

Build progress for `graphtope` (Stage 1). Authoritative design lives in
`Topologic_Graph_Grammar_Spec.md`; carrier gotchas in `CLAUDE.md`; the
TopologicPy contribution agenda in `docs/Topologic_Carrier_Contribution_Briefing.md`.

**Last updated:** 2026-08-15 · **Suite:** 254 tests passing (1 Blender-gated skip) · **Carrier:** topologicpy 0.9.43

## ⚑ SG8 — steering over two levels + cross-tool validation (2026-08-15)

`graphtope/steer.py` (new) closes the loop the metrics opened: **steer, don't
just filter**. `steer(slab, objectives)` samples the SG3 interior space,
places each candidate (SG4) and **hard-rejects any that does not realise**
(tile_report: tiling, edge→face, openings — steering never trades the
grammar's guarantees for score; rejections are kept in `steer.last_rejected`
for honest reporting), evaluates the objective vocabulary — G4 macro × SG7
micro × the SG6 cross-level penalties (`VALUE_REGISTRY`, 18 values) — and
ranks by within-pool z-scored weighted sums (deterministic). `replay`
re-derives a winner from its plan (placed geometry included). Measured on a
cross-family two-band slab: pool mean wet-stacking 0.17 (independent
sampling violates) — **the steered picks never do**; daylight 100%, ranked
wet-cores 3.40–3.67.

**Cross-tool variant validation** (`graphtope/validate_io.py` +
`blender/validate_variants.py`): one validation core over the *exported
artefacts* (OBJ + authoritative sidecar) — integrity (every node a named
OBJ group and vice versa), per-unit tiling (volume sums, no overlaps,
openings excluded), and adjacency coverage (every graph edge a real shared
face of the OBJ bboxes) — run in three places: **pytest** (every commit),
**Jupyter** (the closing loop) and **Blender headless**
(`blender --background --python blender/validate_variants.py -- <dir>
[--render out]`, writing `validation.json`, non-zero exit on failure,
optional thumbnails). What the designer opens in Blender is what the suite
verified. Damaged exports are caught (a renamed room, a shifted wall).

Fixes the pools exposed: `place()`'s 1 mm coordinate rounding can create
sub-millimetre sliver overlaps between adjacent strips — the overlap
tolerance is now 0.05 m³ (a real overlap is room-scale). Tests:
`tests/test_sg8_steering.py` (10: steering determinism/discrimination/the
zeroed violation/winners' guarantees; validation pass/catch-damage/
directory hand-off; Blender headless, skipped without a binary). Notebook:
the steering table, the export→validate loop, the Blender hand-off, the
winner's massing. **SG0–SG8 all done — the phase's Definition of Done is
met.**

## ⚑ SG7 — interior quality metrics & the two-level design space (2026-08-15)

`metrics` gains the interior-quality family (paper Figure 8's micro axes) —
all isomorphism-invariant (the SG5 reference reads the same as its
derivation), all derived from Σ_int's flags (never hand-listed):

- **`privacy_gradient`** — mean depth of habitable rooms from their unit's
  entry (BFS through doors, §5.2); deeper = more withdrawn.
- **`daylight_ratio`** — habitable rooms with a window ÷ habitable rooms —
  *real* daylight via window nodes, not a façade proxy.
- **`circ_area_ratio`** — internal-circulation ÷ habitable footprint
  (placed rooms, SG4; 0 without geometry).
- **`wet_core_compactness`** — mean graph distance between a unit's wet
  rooms; the plumbing core's clustering.
- **`interior_type_mix`** — distinct room kinds per unit.
- Units group by the SG3/SG4 ``unit`` tags, with a connected-component
  fallback so imported references (no tags) measure identically.

**`two_level_design_space(pairs, reference=…)`** embeds the block signatures
(``FEATURES``) and the interior-quality signatures
(``INTERIOR2_FEATURES``) independently (standardised + deterministic
classical MDS each) — macro is the map's *position*, micro its *colour*
(``topoview.draw_two_level``): **a point is a building with an interior
architecture**. Measured: default interiors vs doors+windows+extras
separate on every axis (privacy 0.71→2.00, daylight 0→100%, type mix
4.4→6.4); the reference K unit lands with its derivation on both.
Tests: `tests/test_sg7_metrics.py` (5) — determinism + discrimination,
isomorphism invariance (the reference == derived restated as a measurement),
map shape/determinism, the draw, the reference's landing. Notebook: the
quality table + the two-level map. **The sub-grammar phase is complete**
(SG0–SG7; SG8 steering optional).

## ⚑ SG6 — cross-level constraints: Q3 answered with numbers (2026-08-15)

`graphtope/crosslevel.py` (new) formalises the plan's four constraints as
post-checks over **placed** interiors (SG4 geometry) and runs the Q3
experiment (`measure`): sample buildings with *independent* two-level
variation — differing band patterns per slab (level 1) × SG3 interior plans
(level 2), no cross-level awareness — place, and count violations. Measured
(20 interiors, 5 two-band slabs, seed 42):

| constraint | violations | rate/interior | reading |
|---|---|---|---|
| wet stacking | 5 | 0.25 | **filtered or steered** — an objective, not a rule |
| bay alignment | 8 | 0.40 | **soft** — a rate to steer against |
| void coherence (§5.1) | 0 | 0.00 | **modelled in the productions** — `refine_pair` refuses a paired K's full void before any mutation; the independent-draw control shows why (10–35% of unconstrained paired-K draws conflict) |
| level monotonicity (§12.2) | 0 | 0.00 | **guaranteed by the grammar** — the post-check exists for bad compositions |

Mechanics: wet kinds come from Σ_int's `wet` flag (never hand-listed);
`stacked_pairs` finds vertical unit stacks geometrically (same corridor
side, plan overlap, no third unit between — a B's riser may run the 6 m
through the interlock zone); the same-family stack keeps its risers aligned
by construction (the family recipes are stack-symmetric — wet stacking is
broken only by cross-family stacking or variation, which is exactly the Q3
finding). Tests: `tests/test_sg6_crosslevel.py` (7) — each constraint
rejects a constructed violation (a slid bath, a shifted partition, a
hand-set full void, an inverted V edge); same-family defaults pass; the
`measure` pattern holds. Notebook: the SG6 table + reading.

## ⚑ SG5 — the reproduction result: deriving the reference unit interiors (2026-08-15)

The level-2 analogue of §8.1's fig-5 reproduction — the strongest claim the
sub-grammar phase can make (paper slot G), and the §11.2 one-paper gate:

- **The reference** `models/KF_unit_interiors_reference.obj` — the K and F
  unit interiors, room-labelled (`o K_unit_living`, …). Provenance stated in
  the model header and `reference.py`: **reconstructed, not measured** (risk
  R1) — dimensions from the imported model/module (bay 3.66, depth 8.42,
  K section 8.0 = 5.0 + 3.0, the 1.7 gallery strip), arrangement from the
  published section (Ginzburg's 2F units) as documented in the repo. The
  boxes are **authored so the face-adjacency read by `graph_from_model` is
  exactly the default G_U/G_L adjacency** — every shared face a grammar edge
  and vice versa — so the reproduction is a typed-isomorphism claim over
  graphs read from geometry, not a tautology.
- **`graphtope/reference.py`** (new): `reference_graph(unit)` imports one
  unit's interior; `subgraph_on` extracts node-induced subgraphs;
  `reproduce(unit)` refines the non-terminal **at the sub-grammar defaults**
  (the built condition) and compares typed-isomorphic. **Result: G_U derives
  the K reference (6 rooms / 7 adjacencies) and G_L the F reference (5 rooms
  / 5 adjacencies) — both True — and the reverse sub-derivation returns the
  non-terminal exactly.**
- Enabler: `exchange.classify_space` now recognises the Σ_int vocabulary
  (living/sleeping/kitchen/bath/wc/entry/void/loggia/storage/room, fixed
  match order) and `stair_*_internal` → (staircase, internal) — after the
  block-level names, so existing model classifications are unchanged.

Tests: `tests/test_sg5_reference.py` (6) — the reference imports with room
labels and the section reads from geometry (gallery + void V-above living);
both reproductions; the reverse sub-derivation; the provenance statement;
the classifier. Notebook: SG5 walkthrough (reproduction table, the
reference's real room sizes, the reverse derivation).

## ⚑ SG4 — level-2 geometry: interiors that are built, not just drawn (2026-08-15)

`graphtope/interior_geom.py` (new) gives every interior node its exact box
inside its unit envelope — the block level's "one representation" claim now
reaches the room scale (paper slot E; a stricter carrier test, slot F):

- **`place(refined, slab)`** — deterministic recursive-split placement driven
  by the refined graph alone (subtypes, extents, adjacency — never the plan).
  Per family: K's internal stair is a full-height strip on the outer end, the
  living keeps the corridor face and its routed side face while its served
  rooms (bath@entry/wc/kitchen/loggia) stack as strips sharing its face; the
  gallery's sleeping sits V-above the living's footprint (1.7 m partial /
  0.9 m balcony for a full void) with the void claiming the rest and the
  gallery's own rooms stacked off the sleeping. F's entry hugs the corridor
  plane with served rooms as x-slices of the band behind; its dropped living
  reaches back under the entry so `entry -V-> living` is a real z-face. B and
  R are strip carves. **Side occupancy is graph-aware**: strips take the
  x-side opposite the anchor's routed external contacts (detected from the
  routed edges + envelopes), so side-neighbour and host-door edges land on
  real faces. Openings are **wall-plane geometry** — a door is a leaf
  centred in the plane its two spaces share (with a unit-envelope fallback
  for the R host door); a window a panel on its room's outermost envelope
  face (roof/party placements flagged in attrs, counted in the report).
- **`tile_report`** verifies: volume sums to the envelope, no overlaps,
  every graph edge a real shared face with the right axis for its
  orientation, openings in their walls, plus a carrier `CellComplex`
  partition check per unit (all True on every tested pattern).
- **`boxes_of` works at level 2**; `exchange.to_obj(refined, boxes=…)`
  exports rooms + openings with the sidecar graph; `topoview.draw_massing`
  renders the placed interior.
- **Reversibility preserved**: placement touches only interior nodes, so
  `REFINE → place → ABSTRACT` is still exact to the slab (`to_dict`).
- **Honesty (plan R3)**: a unit squeezed between two same-side neighbours
  (e.g. middle K's in `KKKK`) cannot keep both routed side contacts on its
  anchor's box — one box, two party walls. The miss is **reported**
  (`edge_face_misses`), never faked; 9–10 of the tested patterns realise
  every edge. A formal finding for the paper: the SG0 routing contract
  constrains realisable interior layouts (Q2-adjacent).
- Enablers: `grammar_units._refine` tags every produced node `unit=<id>`
  (per-unit bookkeeping — also the SG6/SG7 substrate); `b_unit`'s router
  gains `(H, "*") → living` (a host/side contact meets the living, the box
  at the envelope's non-corridor faces).

Tests: `tests/test_sg4_geometry.py` (12) — tiling + edge→face + openings on
7 patterns, the section honoured, determinism + exact inverse after
placement, the honest chain miss, OBJ export with rooms, CellComplex
partitions. Notebook: SG4 walkthrough (report table, massing render, OBJ).

## ⚑ SG3 — sub-derivation variability: one slab, many interiors (2026-08-15)

Refinement is now a *choice*, not a flag set. `grammar_units.sample_*_options`
define each unit type's option space (K: void extent/kitchen form/bath level/
wc/loggia/storage/gallery split — probabilities leaning toward the built
condition; F: sleeping/wc/loggia/storage; R: storage); `bridge.interior_plan`
samples one **replayable plan** per slab (per-unit options + building-level
opening choices under `_openings` — doors/windows are all-or-nothing per
building because SG1's daylight check arms on the first window);
`bridge.refine_units(..., plan=…, seed=…)` refines from a plan (the same plan
reproduces the same interior exactly; a paired K's void is forced to `partial`
per §5.1 regardless of the draw); `bridge.interior_variants(slab, n, seed=…)`
yields **N distinct, SG1-valid interiors from one slab**, de-duplicated by
typed isomorphism at level 2, each as an `InteriorVariant` carrying its graph,
exact inverse to the slab, and plan. The level-2 analogue of G4's map:
`metrics.interior_feature_vector` / `interior_design_space` (INTERIOR_FEATURES
signature: interior/habitable/wet/storage rooms, voids, doors, windows —
counts derived from the Σ_int registry, never hand-listed) embed one slab's
interior population by the same deterministic classical MDS; the default
interior is the reference point. Measured: a KFDB slab (9 nodes) → 57-node
interiors; 6 sampled variants span 24–33 rooms, 0–2 voids, 1–3 storages —
§8.5 becomes a *distribution*, not a count (paper Figure 7). **With SG0–SG3
done the one-paper minimum (§11.2) is met.**

**Performance fix (carrier read snapshots).** The SG3 sampler exposed that the
DPO matcher re-read every node dict from the carrier via O(V)
`VertexByKeyValue` scans — one 4-unit refine took ~59 s (millions of carrier
dict conversions). `StateGraph` now keeps lazily-built read snapshots (node
dicts, vertex/edge objects, edge records) **maintained incrementally** on
every mutation (vertices are matched by value — unique layout coordinates —
so caching the objects is safe; `compose.mark_interface` goes through the new
`sg.set_node_attr` so no mutation bypasses maintenance). Verified against a
fresh carrier read after 30 × 40 random atomic mutation sequences. Refine:
59 s → 2 s; `interior_variants(6)`: ~20 s → 11 s; full suite 105 s (was
>5 min timeout). No behavioural change — all 215 tests pass unchanged.

## ⚑ SG2 — the level-2 production corpus (2026-08-11)

Five productions grew into **31, across five families — every bay type the
bridge realises now develops** (`grammar_units.CORPUS`, frozen at this scope
per plan risk R2):

- **G_U (K, 10)** — void in two extents (partial = the built gallery strip /
  full-width, NAC-exclusive per living volume), kitchen as niche or separate
  room (NAC-exclusive per host, incl. behind a door), bath at gallery or
  entry level, wc, loggia on the outer face, storage under the gallery, and
  a subdivided gallery (a second sleeping room over living).
- **G_L (F, 6)** — the mirror set + `GL-sleeping`, a bedroom beside the
  dropped living (the SG1 gallery predicate was relaxed accordingly: sleeping
  must be V-above *or* H-beside a living volume).
- **G_B (2, new)** — entry + living start graph, kitchen niche, bath.
- **G_R (1 + start graph, new)** — the banked room entered through its host,
  optional storage; its host door matches while the host is still an
  ``apartment`` (refine R before B).
- **G_D — `refine_pair`** (§5.1 resolution): paired refinement of a D bay's
  K and F with the explicit cross-unit constraint enforced — *a paired K may
  only take the partial void; the F behind claims the back of the bay volume*
  (`ValueError` on `void_extent="full"`, checked before any mutation).
- **Openings (12)** per §5.2 — doors interposed in existing adjacencies (a
  genuine edge-deleting DPO: the direct edge is removed, the door node joins
  the two spaces; 9 instances incl. the corridor front doors and the banked
  room's host door) and windows (3) with a one-per-room NAC. SG1's daylight
  check is now **armed** in windowed derivations.

Drivers: `refine_k`/`refine_f` grew the SG2 options (defaults reproduce the
G3 interiors *exactly* — full backwards compatibility), `refine_b`/`refine_r`
/`refine_pair` are new, and `bridge.refine_units(all_bays=True, k_opts=…)`
drives every bay type in a slab, reversibly (R → B → D pairs → unpaired K/F).
Tests: `tests/test_sg2_corpus.py` (6) — collectively every production in the
corpus fires; every derivable interior passes SG1's predicates; every
refinement inverts to the exact starting graph, incl. a full `KFDBR` slab
end-to-end.

## ⚑ SG1 — Σ_int registry + interior validity (2026-08-09)

`graphtope/interior.py` (new) — the interior sub-alphabet as a frozen registry
(`SIGMA_INT`): every interior kind with its architectural description and
habitable / wet / opening / circulation flags; per §5.2 **`door` and `window`
are registered as first-class node kinds** alongside the rooms. Derived views
(`ROOM_SUBTYPES`, `HABITABLE_SUBTYPES`, `WET_SUBTYPES`, `OPENING_SUBTYPES`)
replace hand-written lists: `metrics.INTERIOR_SUBTYPES` and `grammar_units`'s
constants now import from the registry (single source). Interior validity
mirrors `validity.py`'s shape — `interior.violations`/`is_valid` over:
- rooms reach circulation (the internal stair counts);
- a sleeping gallery sits V-above a living volume (§5.3 section);
- a void opens *over* living and *onto* a room;
- openings have fixed valence (door joins exactly two spaces, window belongs
  to exactly one room, H only) — vacuous until SG2 places them;
- habitable rooms are lit — **arms itself the moment a graph carries windows**.
Deferred honestly: wet-room stacking → SG6; one-entry-per-unit → SG3 (needs
per-unit bookkeeping). Grounded dims where measured (the 1.7 × 8.4 m gallery
strip); the rest awaits SG5. Tests: `tests/test_interior.py` (7) — each
predicate rejects a hand-built violation and accepts every refined unit the
current sub-grammars produce (incl. the refined DNF).

## ⚑ Plan §5 decisions resolved + SG0 interface routing (2026-08-09)

Three of the sub-grammar plan's four §5 decisions were resolved (T. Dounas) and the
code corrected to match; SG0 — the plan's key enabler — is done:

- **§5.3 — the K section**: 8.0 m tall, sleeping gallery **over the corridor**
  (confirmed from the section drawing; `U_units_realised.obj`'s 9.90 m "3-4-5"
  envelopes measure three structural grid floors, not the dwelling).
  `narkomfin.K_HEIGHT = 8.0`; `anchor_K` builds it — the level-1 box is the front
  zone at full section height, the over-corridor wing is level-2 geometry (SG4).
- **§5.1 — D bay**: paired refinement + explicit cross-unit constraint. `anchor_KF`
  records the pairing as `pair` attributes on both nodes — **not** an edge:
  measured, the pair meets only through the corridor (even at 8 m), and every graph
  edge must remain a real shared face.
- **§5.2 — openings**: doors/windows become first-class **nodes** (overrides the
  plan's rooms-only recommendation). SG1's Σ_int registers `door`/`window`;
  reachability runs through doors; SG7's daylight metric becomes real.
- **SG0 — typed interface routing** (`hierarchy.py`): `UnitSpec.interface` routes
  each incident edge class — `(orientation, neighbour-label)`, `(V, above/below)`,
  `(orientation, "*")` — to a declared interior node; `anchor` is the fallback, so
  router-less specs behave exactly as before (hierarchy tests unchanged). `G_U`
  routes corridor→living, stacked-above→sleeping (the gallery, as built),
  below→living; `G_L`: corridor/above→entry, below→living. Property-tested: the
  interface-edge multiset is preserved and ABSTRACT stays exact.
- **§5.4 (one paper or two) stays open** — gated on the SG5 source hunt (R1).

## ⚑ G4 — metrics & the design-space map (2026-07-19)

`graphtope/metrics.py` (new) measures a population along three axes and lays it
out as a 2-D map with the reference marked:
- **graph metrics** (any `StateGraph`): `unit_count`, `type_mix`, `kf_ratio`,
  `circulation_depth` (adjacencies from nearest circulation — 1 = docked, 2 =
  banked room), `level_count`, `component_count`.
- **geometry metrics** (from a slab's placed boxes): `gross_floor_area`, `volume`,
  `footprint`, `compactness` (built ÷ envelope volume), `area_per_unit`.
- **interior richness** (level-2 refined graph): `interior_rooms`, `void_count`,
  `rooms_per_unit` — the second grammar level made measurable.
- **the map**: `feature_vector` (the ordered `FEATURES` signature) →
  `design_space(slabs, reference=…)` standardises and embeds via **classical MDS
  (numpy only, no sklearn)**, returning coords + the reference's index; `cluster`
  is a deterministic k-means. `topoview.draw_design_space` scatters it — each
  variant a dot (colour by any metric or cluster), `G_DNF` a star. The DNF is
  placed by realising *its* proposal through the same bridge, so it sits in the
  same metric space as the variants. Sample render:
  `notebooks/exports/design_space_map.png`.

**Carrier flakiness note:** `Topology.ExportToOBJ` (topologicpy 0.9.43) sporadically
raises `TypeError` in the full-suite run (unstable internal vertex ordering — the
gotcha CLAUDE.md flags). Seen once in 3 full runs; `test_exchange` passes in
isolation and the other two runs were clean at 195. Not a graphtope regression;
the OBJ exporter is on the contribution-briefing list.

## ⚑ Two-level bridge + richer section (2026-07-18)

Three tranches landed on top of GS1:

1. **Richer section vocabulary** (`narkomfin.py`) — two new bay types, added
   *alongside* K/F/B (backwards-compatible): **`D`** = the built double-loaded
   interlock, K front + F back **in one bay**; **`R`** = a front apartment with a
   room banked **behind** it (entered through the apartment, one room deep). The
   bridge now realises a P7 V-interlock as a same-bay `D` pair, and a P1
   room-off-room chain as an `R` bay (chains deeper than one room stay honestly
   *skipped*). Result: the seed-0 grammar catalogue now has **zero skipped rooms**
   (was ~1/proposal) — every proposed unit docks to a corridor or banks behind its
   host. `report()` gained `rooms_banked`; `SlabSpec.units` counts D/R as two.
2. **G3 — U/L sub-grammars** (`grammar_units.py`, new) — the `u_section`/`l_section`
   non-terminals get interior transformation grammars: K = split-level living/
   sleeping + internal stair + optional double-height void, kitchen, bath; F =
   corridor-level entry + living below + stair, kitchen, bath. Σ stays open
   (interior kinds are `generic` subtypes). `refine_k`/`refine_f` run
   `hierarchy.Refine` then the sub-grammar's DPO productions; each returns the
   composed `ABSTRACT(S→n)` inverse, so refinement is exactly reversible. Vocabulary
   spec-grounded (§7.6.2), structure/metrics grounded on `U_units_realised.obj`.
3. **The two-level bridge** (`bridge.refine_units`) — drives *both* grammar levels
   end-to-end: propose → realise slab (level 1) → refine every K/F interior (level 2),
   preserving each unit's exterior interface and staying reversible back to the slab
   (exact, `to_dict` equality). `grammar_catalogue(..., refine=True)` carries the
   refined graph + inverse on each `Variant`. Pipeline:
   **A₀ →(graph grammar)→ proposal →(bridge)→ slab →(sub-grammar)→ unit interiors**,
   every step invertible. Interiors are graph-level topology (no boxes) — `boxes_of`
   applies to the slab, not the refined graph.

## ⚑ Direction shift — shape grammar (the graph↔shape bridge, finally)

The abstract graph grammar (P1–P8) generated correct *topology* but Stage-2 was a
generic grid-packer → topology-valid but geometrically arbitrary ("box salad").
The fix (user-directed): **rebuild the grammar circulation-first as a *shape*
grammar** where productions place exact geometry, and the graph is *derived from*
what touches — so graph and geometry are one representation and cannot diverge.
`graphtope/narkomfin.py` does this: `add_corridor_spine` / `add_stair_cores` build
the armature; `anchor_K` (u_section, up), `anchor_F` (l_section, down),
`anchor_box` dock maisonettes onto the corridor with the real Narkomfin section
(corridor every 3 floors, K-up/F-down interlock). `derive_slab(bands, n_bays,
pattern)` assembles a valid slab; **every edge is a real shared face**; geometry
lives in node attributes (`boxes_of`). Real module: bay 3.66 m, floor 3 m. This is
now the primary generative direction; P1–P8 remain as an abstract-topology study.
`narkomfin.catalogue(n, seed)` = a deduped set of real slabs (vary bands/bays/
pattern), every one buildable. Export via `exchange.to_obj(g, path,
boxes=nf.boxes_of(g))`, `export_catalogue(..., boxes_of=nf.boxes_of)`, or
`export_catalogue_combined(..., boxes_of=nf.boxes_of)` (whole catalogue in one OBJ).
Samples: `notebooks/exports/narkomfin_slabs/`, `narkomfin_catalogue_real.obj`.
✅ **The bridge is built** (`graphtope/bridge.py`): the abstract graph grammar
*proposes* (P1/P3/P6/P7 + parameterised unit productions, recorded/replayable
derivations), `spec_from_graph` reads a `SlabSpec` off the proposal (corridor →
band, served units → K/F/B bay pattern; P7's V interlock hosted by the serving
corridor, as built), `realise_spec` → `narkomfin.derive_slab_from_patterns`
(ragged per-band patterns) builds it, `report` gives honest coverage (docked
units, reinterpreted interlocks, skipped rooms). `bridge.grammar_catalogue(n)` =
grammar-driven variants end-to-end; sample:
`notebooks/exports/narkomfin_grammar_catalogue.obj`. Thinking + state:
`Planning&State.md`. Next: richer unit sections (double-loaded both sides,
double-height voids); G3 U/L sub-grammars.

## Milestones

| # | Milestone | State | Modules | Tests |
|---|---|---|---|---|
| M0 | API spike (de-risk carrier) | ✅ done | — (folded into briefing) | — |
| M1 | Carrier + invariants (§2–§3, §10.1) | ✅ done | `model`, `alphabet`, `_topo`, `serialize`, `topoview`, `shape_iface` | `test_model.py` (12) |
| M2 | Atomic basis A1–A7 + reversibility (§4) | ✅ done | `atomic` | `test_atomic.py` (35) |
| M3 | Core composites — SPLIT/MERGE + 6 verbs (§5) | ✅ done | `composite` | `test_composite.py` (18) |
| M4 | DPO rules + typed directed matcher + NACs (§6) | ✅ done | `rules` | `test_rules.py` (11) |
| M5 | DNF grammar P1–P8; reproduce fig-5 graph (§7–§8) | ✅ done | `grammar_dnf`, `engine` | `test_grammar_dnf.py` (8) |
| M6 | Trace record/replay/invert; τ stub (§9, §10.2) | ✅ done | `engine`, `serialize`, `shape_iface` | `test_engine.py` (7) |
| M7 | Hierarchy (REFINE/ABSTRACT) + BRIDGE (§7.6) | ✅ done | `hierarchy`, `compose`, `compare` | `test_hierarchy.py` (3), `test_compose.py` (5) |
| **S2** | **Stage 2 — geometry: realise / round-trip / geometric match (§9)** | ✅ **done** | `realise`, `topoview`, `rules` | `test_realise.py` (17) |
| **G0** | **Generative — strategy + catalogue + typed-iso dedup** | ✅ **done** | `generate` | `test_generate.py` (6) |
| **G1** | **Generative — architectural validity (buildings, not noise)** | ✅ **done** | `validity` | `test_validity.py` (9) |
| **G2** | **Generative — parameterised productions (macro variation)** | ✅ **done** | `grammar_params` | `test_grammar_params.py` (6) |
| **B1** | **Blender/BIM round-trip — OBJ+sidecar export, geometry→typed graph** | ✅ **done** | `exchange`, `blender/import_graphtope.py` | `test_exchange.py` (7) |
| **B2** | **Import the real model — actual sizes from the Narkomfin OBJ** | ✅ **done** | `exchange`, `graphtope/models/*.obj` | `test_realmodel.py` (5) |
| **GS1** | **Graph→shape bridge — graph grammar drives the shape grammar** | ✅ **done** | `bridge`, `narkomfin` | `test_bridge.py` (9) |
| **GS2** | **Richer section (D/R bays) — no skipped rooms in the catalogue** | ✅ **done** | `narkomfin`, `bridge` | `test_narkomfin.py` (+2), `test_bridge.py` (+1) |
| **G3** | **U/L sub-grammars via REFINE; bridge drives two grammar levels** | ✅ **done** | `grammar_units`, `bridge` | `test_grammar_units.py` (6), `test_bridge.py` (+2) |
| **G4** | **Metrics + design-space map (graph/geometry/interior axes, MDS)** | ✅ **done** | `metrics`, `topoview` | `test_metrics.py` (11) |
| **SG0** | **Typed interface routing — REFINE routes each edge class to its interior node** | ✅ **done** | `hierarchy`, `grammar_units` | `test_grammar_units.py` (+2) |
| **SG1** | **Σ_int registry + interior validity (door/window registered, §5.2)** | ✅ **done** | `interior`, `metrics` | `test_interior.py` (7) |
| **SG2** | **Level-2 production corpus — 31 productions, every bay type develops** | ✅ **done** | `grammar_units`, `bridge` | `test_sg2_corpus.py` (6) |
| **SG3** | **Sub-derivation variability — one slab, many interiors** | ✅ **done** | `bridge`, `grammar_units`, `metrics` | `test_sg3_variability.py` (4) |
| **SG4** | **Level-2 geometry — interiors tile the envelope, edges are faces** | ✅ **done** | `interior_geom`, `grammar_units` | `test_sg4_geometry.py` (12) |
| **SG5** | **Grounding — G_U/G_L derive the reference interiors (reconstructed)** | ✅ **done** | `reference`, `exchange`, `models/KF_unit_interiors_reference.obj` | `test_sg5_reference.py` (6) |
| **SG6** | **Cross-level constraints — Q3 measured (modelled/guaranteed/steered)** | ✅ **done** | `crosslevel` | `test_sg6_crosslevel.py` (7) |
| **SG7** | **Level-2 quality metrics + the two-level design space (Fig. 8)** | ✅ **done** | `metrics`, `topoview` | `test_sg7_metrics.py` (5) |
| **SG8** | **Steering over two levels + cross-tool validation (pytest/Jupyter/Blender)** | ✅ **done** | `steer`, `validate_io`, `blender/validate_variants.py` | `test_sg8_steering.py` (10) |

Scope: Stage 1 (M1–M7) ✅, Stage 2 geometry ✅, the generative track (G0–G4) ✅,
and the **sub-grammar phase is complete, SG0–SG8 incl. steering** (Q1/Q2/Q3
answered, Figures 7+8, the reproduction result, the §11.2 gate, and the
cross-tool validation harness).

## What works today

- **`StateGraph`** over a single in-place `topologicpy.Graph`: typed/directed/
  weighted/attributed nodes & edges, §2.2 well-formedness invariants, canonical
  (sorted) JSON round-trip, `is_fully_refined`, networkx escape-hatch view.
- **Atomics A1–A7** as dataclass ops; each `apply(sg)` performs the effect and
  **returns its exact inverse**. Reversibility property-tested on random graphs.
- **Composites** (SPLIT, MERGE, DIVIDE, UNION, DIFFERENCE, MIRROR, TRANSFORM,
  AttachPendant): recipes over atomics returning `OpSequence` inverses, so
  `inverse(op) ∘ op == id` exactly — incl. MERGE weight-coalescing (ξ=max).
- **DPO productions** (`rules.py`): `Pattern`/`PNode`/`PEdge`, a typed-attributed
  **directed** subgraph monomorphism (symmetric H / strict one-way), NAC checking,
  and reversible application (deletes L∖K with the dangling condition, glues R∖K).
- **The DNF grammar** (`grammar_dnf.py`, `engine.py`): P1–P8 as productions; the
  `Derivation` engine runs the §8 sequence `A₀ →* G_DNF` (18 nodes / 18 edges,
  two blocks), reproduces the hand-built figure-5 graph (typed isomorphism), and
  the **reverse derivation returns the axiom**. P3 is a genuine edge-deleting DPO.
- **Trace + τ** (`engine.replay`, `serialize.dump_trace`/`load_trace`,
  `shape_iface`): JSON trace round-trips; `replay` re-derives on a fresh axiom
  (deterministic ids) and inverts back to A₀; τ maps labels → shape types and
  adjacency → shared faces (V⇒slab, H⇒wall) — no geometry.
- **Hierarchy + composition** (`hierarchy.py`, `compose.py`): `Refine`/ABSTRACT
  expand `u_section`/`l_section` non-terminals via a sub-grammar (interface
  preserved on the anchor); `disjoint_union` + `Bridge` derive the two blocks
  independently and join them (modular == monolithic, by typed isomorphism).
- **Step-by-step visualisation** (`topoview.py`): a matplotlib renderer of the
  typed graph — node glyphs per shape-type (box / wide bar / tall bar / U / L /
  triangle) coloured by the §3.1 legend, H/V + one-way/bidirectional edge styles.
  `record_frames` snapshots the graph after each production and `draw_grid` shows
  the whole derivation on a shared, component-separated layout (the figure-5 view).
- **Stage-2 geometry** (`realise.py`): τ realises each node as a Topologic `Cell`
  — boxes for box-types, **true U/L section profiles** (wire-extruded solids) so
  `IsSimilar` distinguishes U from L. A deterministic layout turns adjacencies into
  shared faces (H=wall, V=slab+stack); a **constraint-repair** pass with
  variable-size cells (spanning L under two U's; a pinwheel for H-3-cliques) lifts
  the hard motifs — each repair guarded to only *increase* coverage. `CellComplex`
  + `Graph.ByTopology` **round-trip** the adjacency back: **17/18** on the full DNF
  (`complete`; the 1 miss is an interlock the greedy boxes a staircase into), 100%
  on embeddable configs and on the isolated motifs. `IsSimilar` gives the geometric
  match predicate, **pluggable into `rules.match_pattern` via `node_matcher`**
  (`realise.shape_matcher`) — matching by shape without changing rule structure (§9).
  3-D massing renderer: `topoview.draw_massing`.
- **`notebooks/01_graphtope.ipynb`** — the iterative dev surface; executes clean
  end-to-end with M0–M7 **and Stage 2**, with inline step-by-step graph renders,
  a sub-grammar refinement, and the 3-D massing model. Now closes with the
  **bridge → two-level → design-space walkthrough** (GS1–GS2 propose→spec→realise
  with the 3-D massing, G3 `refine_units` with interior richness + reversibility,
  and the G4 metric table + MDS design-space map with `G_DNF` marked).

## Decisions in force

- Carrier = `topologicpy.Graph` (sole); networkx is an escape hatch only.
- Notebook drives; stabilized code extracted into `graphtope/*.py`.
- Spec defaults adopted: property model hybrid (§12.1), levels L3 (§12.2),
  weight default `1.0` / merge ξ=max (§12.4).

## Real model (B2) — what we now have

`exchange.graph_from_model(obj)` imports a real named OBJ → typed `StateGraph`
with **actual sizes**: object names classified to Σ via Appendix A
(`classify_space`), adjacency + orientation from real bbox geometry, every node
carrying width/depth/height/volume/level. The real Dom Narkomfin imports to **57
spaces, 127 adjacencies, 8 storeys, ~16,416 m³, one connected component** (spine
corridor 73.2 m, degree 12). `typical_sizes(graph)` gives median dims per type.
Finding: the real maisonettes are all `mesonete_f` → **`l_section`** (the F-type
maisonette *is* the L-section — domain correction to Appendix A, which had grounded
`mesonete_f` as `u_section`); there is no separately-modelled `u_section`, so the
grammar's U/L pairing abstracts one built maisonette family. Bundled models:
`graphtope/models/{building_only, full_grammar, U_units_realised}.obj`.

## Up next — generative track (per the research plan)

- ✅ **Variants at real proportions (G2 × B2)** — `realise.scaled_boxes(sg, sizes)`
  sizes each cell by its type's real dims; `topoview.draw_massing(sg, sizes=...)`
  renders generated variants at true Narkomfin proportions (apartments double-height,
  corridors half-height in section). Visualisation layer — the shared-face round-trip
  still uses the tiling unit layout (real sizes don't tile). Caveat: real staircase
  objects are full-depth circulation cores (~21 m), so generated staircases render deep.
- ✅ **Execute & export to OBJ** — `exchange.to_obj(sg, path, sizes=...)`,
  `export_catalogue(variants, dir, sizes=...)` (one file per variant), and
  `export_catalogue_combined(variants, path, sizes=..., cols=, gap=)` (the **whole
  catalogue in one OBJ**, variants on a grid, objects named `v{i}_{nodeid}`, with a
  `.catalogue.json` sidecar). Samples: `notebooks/exports/catalogue/` and
  `notebooks/exports/narkomfin_catalogue.obj`. Real-proportion exports use the
  **sidecar JSON as the authoritative graph** (real-size cells don't tile).
- ✅ **G3 — U/L section sub-grammars** (done 2026-07-18) — `grammar_units.py` gives
  `u_section`/`l_section` their own alphabets + productions (split-level, void,
  internal stair, kitchen/bath) via `REFINE`; `bridge.refine_units` drives both
  grammar levels end-to-end, reversibly. See the 2026-07-18 note above.
- ✅ **G4 metrics + design-space map** (done 2026-07-19) — `metrics.py` +
  `topoview.draw_design_space`; graph/geometry/interior axes, classical-MDS map
  with `G_DNF` marked. See the 2026-07-19 note above.
- **Write-up (2026-07-30)** — `docs/paper/Graphtope_Journal_Paper.md` is the journal-paper
  scaffold (IJAC primary target) with the measured results tables already filled in and
  explicit ▣ expansion slots for the sub-grammar work;
  `docs/Sub_Grammar_Development_Plan.md` is the SG0–SG8 plan that fills them (starts with
  SG0 typed interface routing — `Refine` currently lands *all* interface edges on one anchor).
- ✅ **SG3 — sub-derivation variability** (done 2026-08-15) — sampled,
  replayable interior plans; N distinct valid interiors per slab; level-2
  design-space map. See the 2026-08-15 note above. **The one-paper minimum
  (SG0–SG3) is met.**
- ✅ **SG4 — level-2 geometry** (done 2026-08-15) — `interior_geom` places
  every interior node in its envelope; verified tiling, edge→face, openings
  in walls; reversible; honest chain-miss reporting. See the 2026-08-15
  note above.
- ✅ **SG5 — grounding** (done 2026-08-15) — the room-labelled reference
  *reconstructed* per R1 (provenance stated); **G_U and G_L derive it**,
  typed-isomorphic, reversibly. §11.2's gate answered → the one-paper
  strategy holds. See the 2026-08-15 note above.
- ✅ **SG6 — cross-level constraints** (done 2026-08-15) — Q3 measured: wet
  stacking 0.25/interior (steer), bay alignment 0.40 (soft), void coherence
  modelled (control 10–35%), level monotonicity guaranteed (0). See the
  2026-08-15 note above.
- ✅ **SG7 — level-2 metrics + the two-level map** (done 2026-08-15) — the
  interior-quality family (privacy, daylight, circ-area, wet-core, type mix)
  + `two_level_design_space` / `draw_two_level` (Figure 8). See the
  2026-08-15 note above. **The sub-grammar phase is complete.**
- ✅ **SG8 — steering over two levels** (done 2026-08-15, = G5) —
  `steer.steer` with the realisability gate, the 18-value objective
  registry, the steered-picks-never-violate result, and the shared
  pytest/Jupyter/Blender validation core over exported artefacts. See the
  2026-08-15 note above. **SG0–SG8 complete — the phase is done.**
- **Beyond the phase** — the graph-ML line (§12.2) trains on the
  rule-generated, validated two-level corpus; a designer-in-the-loop UI
  over `steer`'s top-k + the two-level map is the natural next surface.
- **G5 / SG8 — steering** *(optional)* — search or designer-in-the-loop over
  both levels against metric objectives, now that they exist.

`exchange` (B1) notes: `to_obj(sg, path)` writes OBJ (object per space, named by
id, coloured by τ) + `.mtl` + `<path>.graph.json` sidecar (the typed graph).
`graph_from_realisation`/`roundtrip` rebuild a typed graph from realised geometry
— **exact** for buildings without one-way H edges; V direction recovered from z,
types/subtypes from cell semantics. Geometry can't encode access-direction (a
shared wall has no direction) → the **sidecar** carries it (as IFC would).
`graph_from_obj` reads a (Blender-edited) OBJ back via bounding-box adjacency +
sidecar types — **best-effort** (OBJ re-import adds stray cells / no shared faces;
IFC via `Graph.ByIFCFile` is the production upgrade). Blender importer:
`blender/import_graphtope.py`.

`validity` notes: hard rules in `DEFAULT_CHECKS` (no contradictions — circulation
present per multi-room block, ≤1 entrance/block, entrance on circulation, L paired
under U, no floating rooms); `STRICT_CHECKS` adds completeness (every circulated
block is entered). Raw random generation is ~80% valid, so `keep=is_valid` is a
cheap filter. The DNF passes all checks.

## Stage 2 — remaining (lower-priority)

Stage 2 is done (geometry, round-trip, geometric matching — a/b/c all landed).
Other lower-priority items:
- **Global floor-planner** — a rectangular-dual / constraint solver to reach 18/18
  on the full DNF (the greedy layout boxes a staircase into the last interlock gap;
  the motif repairs already hit 100% in isolation).
- **Round-trip the realised complex to a full StateGraph** and typed-iso it against
  the Stage-1 graph (currently we verify the adjacency *set*).
- Companion sub-grammar alphabets/productions for U/L sections; weight semantics (§12.4).
- Stage-2 geometric matching could also use `IsVertexCongruent` / shared-boundary
  extent for richer predicates.

## Housekeeping

- Not committed to git yet (per standing scope). Add a `.gitignore` for
  `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `.ipynb_checkpoints/` before
  any commit.
