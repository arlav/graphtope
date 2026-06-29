# STATUS

Build progress for `graphtope` (Stage 1). Authoritative design lives in
`Topologic_Graph_Grammar_Spec.md`; carrier gotchas in `CLAUDE.md`; the
TopologicPy contribution agenda in `docs/Topologic_Carrier_Contribution_Briefing.md`.

**Last updated:** 2026-06-29 · **Suite:** 151 tests passing · **Carrier:** topologicpy 0.9.43

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

Scope: Stage 1 (M1–M7) ✅, Stage 2 geometry ✅, and the **generative track has
started** (G0). Direction set: diverse *catalogue* · Blender *round-trip* (B1) ·
assembly *macro-first* (G2→G3). Plan: `docs/Generative_Variation_Research_Plan.md`.

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
  a sub-grammar refinement, and the 3-D massing model.

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

- **Realise variants at real proportions (G2 × B2)** — drive `realise`/`draw_massing`
  with `typical_sizes(REAL)` so generated catalogues render at true Narkomfin scale.
- **G3 — U/L section sub-grammars** — give `u_section`/`l_section` their own
  alphabets + productions (split-level, voids, internal stair, interlock) via
  `REFINE`, using `U_units_realised.obj` as the reference.
- Then **G4** metrics + a design-space map (now with real metric axes: area, volume).

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
