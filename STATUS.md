# STATUS

Build progress for `graphtope` (Stage 1). Authoritative design lives in
`Topologic_Graph_Grammar_Spec.md`; carrier gotchas in `CLAUDE.md`; the
TopologicPy contribution agenda in `docs/Topologic_Carrier_Contribution_Briefing.md`.

**Last updated:** 2026-08-15 · **Suite:** 215 tests passing · **Carrier:** topologicpy 0.9.43

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

Scope: Stage 1 (M1–M7) ✅, Stage 2 geometry ✅, the generative track (G0–G4) ✅,
and the **sub-grammar phase's one-paper minimum is met** (SG0–SG3 ✅; next
SG4 level-2 geometry, SG5 the reference hunt, SG6 cross-level constraints).

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
- **SG4 — level-2 geometry** *(next)* — interior productions place sub-boxes
  inside the unit envelope; `boxes_of` at level 2; verified tiling per unit
  (report coverage, don't fake it — R3).
- **SG5 source hunt** *(open, decides publication shape)* — a room-labelled
  K/F interior reference, obtained or redrawn from Ginzburg's published plans.
- **G5 — steering** *(optional)* — search or designer-in-the-loop over the
  derivation space against a metric objective (e.g. target compactness, N units at
  min circulation depth), now that the objective functions exist.

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
