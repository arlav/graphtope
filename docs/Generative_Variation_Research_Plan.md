# Generative variation — research framing & iterative plan

**For:** T. Dounas · W. Jabi · graphtope
**Status:** direction-setting (no code yet)
**Builds on:** the completed Stage-1 grammar (atomics → verbs → P1–P8 → engine →
hierarchy/bridge) and the Stage-2 geometry bridge (`realise`, round-trip,
geometric matcher). See `STATUS.md`.

---

## 0. The shift

Today `grammar_dnf.derive` is **one scripted derivation** `A₀ →* G_DNF`. To
*generate variations* we stop treating that path as fixed and treat the grammar
as a **space of derivations** to explore. The Dom Narkomfin graph becomes one
anchor point; variations are other points reachable by the same verbs.

The user named two axes; there are really **three nested spaces of variation**:

| Space | Axis | What varies | Governed by |
|---|---|---|---|
| **D — derivation** | *sequence of verbs* | which productions, order, counts, at which matches | the engine + a generative **strategy** |
| **A — assembly** | *how elements combine* | production **parameters** + the **U/L section sub-grammars** + composition (bridge, mirror) | parameterised productions (§7.5) + sub-grammars (§7.6.2) |
| **R — realisation** | *graph → shape* | how one graph embeds into geometry (layout, proportions, profiles) | Stage-2 `realise` / `box_layout` |

A generated building is a point **(d, a, r)**. The same graph `d·a` has many
realisations `r`; the same massing can come from many derivations (confluence).
Research = build **generators + constraints + metrics** over these spaces and
study what they produce — then close the loop back to 3-D / Blender.

---

## 1. The central tensions (the research questions)

1. **Validity vs diversity.** Pure random derivation explores widely but yields
   mostly non-buildings; tightly constrained derivation yields valid but dull
   output. The core research is finding the grammar + constraints that span a
   *rich yet valid* space.
2. **Confluence / equivalence.** Many verb sequences produce the *same* graph
   (independent productions commute). We must dedup by typed isomorphism
   (`compare.typed_isomorphic`, already built) and characterise when two
   derivations are equivalent — otherwise "1000 variations" is really 50.
3. **Modular composition.** Blocks and U/L units develop by independent
   (sub-)grammars and join by `BRIDGE` (§7.6.3). Does varying them independently
   compose into *coherent* buildings, or do cross-constraints (shared cores,
   aligned levels) need to be modelled?
4. **Control.** How do we *steer* generation — production probabilities, hard
   application conditions, objective functions, a designer in the loop, or a
   learned model? Each is a different research instrument.
5. **Grounding.** How do variations relate to the *real* Narkomfin (the `.blend`,
   Appendix A) and to architectural plausibility? The real model is the anchor
   and the validation target.

---

## 2. Method — anchor, perturb, measure, close the loop

1. **Anchor** at `G_DNF` (and, via the Blender track, at the real `.blend`).
2. **Perturb** along D / A / R with generators (§3, milestones G0–G3).
3. **Filter** by hard constraints — a building, not a graph (G1).
4. **Realise** to geometry (Stage 2) and **export to 3-D / Blender** (B-track).
5. **Measure & map** the population — graph + geometry + diversity metrics (G4).
6. **Iterate**: enrich grammar/constraints/objectives; eventually *learn* a
   generator from the rule-generated corpus (G5), tying into the group's
   graph-ML line (Alymani & Jabi BGR, §12.2).

This is design-space exploration with a grammar: rule-based generation first
(controllable, explainable, needs no data), optimisation second, learning last
(bootstrapped on the corpus the rules produce).

---

## 3. Iterative plan

Each milestone is a small, testable increment with a notebook section, mirroring
how Stages 1–2 were built. **G-track** = generation; **B-track** = Blender/3-D.
The two run in parallel; B0 can start as soon as G0 produces graphs.

### G0 · Generative engine seam  *(the key enabler)*
Make the derivation **driver pluggable**. Today `Derivation.apply(prod, match)`
is called by a hand-written script; instead, a **`Strategy`** chooses the next
step:

```
Strategy.next(sg, history) -> (production, match) | None     # None = stop
generate(axiom, strategy, budget) -> Derivation              # records a trace
```

- `RandomStrategy` — uniformly pick an applicable (production, match).
- `WeightedStrategy` — per-production probabilities; phase ordering (Step-1→2→3,
  §8) so output resembles the reference family.
- Dedup a population with `typed_isomorphic`; keep the trace per variant (already
  replayable/invertible via `engine`).
**Deliver:** "give me N distinct graphs from the DNF grammar." *Test:* every
generated graph is well-formed; the population dedups to < N; each replays.

### G1 · Validity & constraints  *(building, not noise)*
A `validity.py` of predicates, used both as **application conditions** (block a
production) and **post-filters**:
- circulation reaches every habitable space; entrance at grade per block (NAC
  exists); each `l_section` sits below `u_section`s; single connected building
  after `BRIDGE`; level monotonicity (§12.2 L-option).
**Deliver:** generation yields only valid buildings. *Test:* invalid candidates
are rejected; the DNF passes.

### G2 · Parameterised block productions  *(assembly — macro)*
Generalise P1–P8 to carry parameters and add variation operators:
- `ADD-UNITS(k)`, corridor type (single- / double-loaded / central core),
  which side a unit attaches, `MIRROR` a wing (P9 exists in `composite`),
  block length, number of levels.
**Deliver:** the *same* grammar produces a long single-loaded slab, a compact
double-loaded block, a mirrored pair, etc. *Test:* each parameterisation is
valid + reversible.

### G3 · U / L section sub-grammars  *(assembly — micro, §7.6.2)*
Flesh out the `u_section` / `l_section` sub-grammars (today: a minimal
`u_section_unit`). Give each its **own alphabet** (room, void, internal stair,
balcony) and **productions** with choices: split-level configuration, double-
height void placement, internal-stair position, the K/F interlock pattern.
`REFINE` selects a sub-derivation variant.
**Deliver:** "how U and L apartments get assembled" becomes a controllable axis;
one block graph → many unit-architecture variants. *Test:* REFINE/ABSTRACT
round-trips per variant; refined graph stays valid.

### G4 · Metrics & the design-space map
- **Graph metrics:** unit count, U:L ratio, circulation depth from entrance,
  symmetry, graph-edit-distance to `G_DNF`.
- **Geometry metrics (Stage 2):** footprint, volume, level count, compactness,
  area/unit, the round-trip coverage already reported by `realise`.
- **Diversity:** pairwise typed-graph distance → cluster the population; reduce
  to 2-D and plot the *design space* (each building a point; the DNF marked).
**Deliver:** a map of what the grammar generates and how far each variant is from
the reference. *Test:* metrics are stable; DNF lands where expected.

### G5 · Steering  *(optional / later)*
Drive generation toward goals:
- **Search** — evolutionary or MCTS over derivations against an objective
  (e.g., N units at min circulation, target compactness, match a massing sketch).
- **Designer-in-the-loop** — interactive pick-and-extend in the notebook.
- **Learning** — train a graph generative model (GNN/VAE/diffusion) on the
  rule-generated corpus; the rules supply *labelled, valid* training data, and
  the learned model proposes; the grammar/validity *checks* it. This is the
  bridge to the group's graph-ML work and §12.2 (BGR level inference).

### Blender / 3-D track (parallel)

**B0 · Export massing → Blender.** `realise` → `Topology.ExportToOBJ(cells,
path, nameKey="id", colorKey="color")` with a colour/name per cell by τ type and
level; also `ExportToBIM` for BlenderBIM. A small Blender Python script imports
the OBJ and sorts cells into **collections by type and by level**, applies
materials from the legend. *Deliver:* open any generated building in Blender,
organised and coloured. (Verify export options first; OBJ + per-cell colour is
confirmed available.)

**B1 · Round-trip back.** Model / edit a massing in Blender → export OBJ or IFC →
`Topology.ByOBJPath` / `Graph.ByIFCFile` → `Graph.ByTopology(direct=True)` →
reconstruct a `StateGraph` → `typed_isomorphic` check vs the source. Closes the
loop: the system reads buildings as well as writes them.

**B2 · Ground-truth the real Narkomfin.** Export the reference `Dom_Narkomfin…
.blend` from Blender to OBJ/IFC (TopologicPy can't read `.blend` directly) →
extract its adjacency graph → locate it in the design-space map → confirm the
grammar can *reproduce* it (a real validation of P1–P8, beyond the hand-built
figure-5 graph). The named spaces (Appendix A) become the semantic labels.

---

## 4. Dependencies & sequencing

```
G0 ─► G1 ─► G4 (map needs a population + validity)
  └─► G2 ─┐
  └─► G3 ─┴─► richer A-space feeds G4/G5
B0 (after G0) ─► B1 ─► B2
G5 needs G1+G4 (objectives) and, for ML, a corpus from G0–G3
```
Recommended first slice: **G0 + G1 + B0** — generate valid variations and see
them in Blender. Everything else builds on that loop.

## 5. Open decisions (to set direction)

1. **Primary goal** of generation — a diverse *catalogue*, *optimisation* toward
   a brief, *data* for an ML generator, or *interactive* design. Changes the
   weight of G4/G5.
2. **First generation strategy** — constrained-stochastic rules (recommended MVP)
   vs jump to search vs jump to ML.
3. **Blender first move** — export-for-viz (B0, recommended) vs full round-trip
   (B1) vs import the real `.blend` (B2).
4. **Assembly depth now** — parameterise P1–P8 (G2, fast) before or after building
   the U/L sub-grammars (G3, deeper).

These don't block G0; they set what we build *around* it.

---

## 6. Decisions (locked) & build order

- **Goal = diverse catalogue.** Optimise for a rich, deduped library of *valid*
  variants to browse and compare. ⇒ priority on G0 (generate), G1 (valid), G4
  (map/browse); G5 search/ML deferred.
- **Blender = full round-trip (B1).** Not just export: write a variant to
  OBJ/BIM **and** read a modelled/edited massing back to a `StateGraph`,
  verified by `typed_isomorphic`. (Export is the first half; import + iso-check
  the second.)
- **Assembly = both, macro first (G2 → G3).** Parameterise P1–P8 to widen the
  block-level space, then enrich the U/L unit sub-grammars.

**Build order:**
```
G0  generate (strategy + population + typed-iso dedup)      ◄ start here
G1  validity (valid buildings only)
G2  parameterised block productions (macro variation)
B1  Blender round-trip (export a catalogue item → edit → read back → iso)
G3  U/L sub-grammars (micro variation)
G4  metrics + design-space map (the catalogue browser)
```
G0 is goal-independent and unblocks all of the above — it is the first build.

