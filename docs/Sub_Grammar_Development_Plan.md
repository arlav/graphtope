# Sub-grammar development plan — the second grammar level

**For:** T. Dounas · W. Jabi · `graphtope`
**Date:** 2026-07-30 · **Suite at time of writing:** 195 tests passing
**Builds on:** G3 (`graphtope/grammar_units.py`, `bridge.refine_units`) — see `STATUS.md`
2026-07-18 and `Planning&State.md`.
**Feeds:** `docs/paper/Graphtope_Journal_Paper.md` expansion slots **B, D, E, F, G, H**.

---

## 0. Where the sub-grammars actually stand

G3 landed a *working, reversible, minimal* second grammar level. Stated precisely, so the
plan builds on fact rather than on the STATUS headline:

**What exists.**
- `G_U` (K-type maisonette): a 3-node start graph — `living` (anchor) / `sleeping` above by
  `V` / internal `stair` — plus three DPO productions: `GU-void` (double-height void over
  living, opening onto the gallery), `GU-kitchen` (off living), `GU-bath` (off the gallery).
- `G_L` (F-type maisonette): a 3-node start graph — `entry` (anchor, at corridor level) /
  `living` a floor below by `V` / internal `stair` — plus `GL-kitchen`, `GL-bath` (both off
  entry).
- `hierarchy.Refine` implements the `REFINE` span with the interface contract, returning the
  composed `ABSTRACT(S → n)`; `bridge.refine_units` drives every K/F unit in a realised slab
  and the inverse restores the slab to `to_dict` equality.
- Measured on the seed-0 catalogue: slabs of 18–20 nodes refine to 53–75 nodes, 36–55
  interior rooms, 3.0–3.7 rooms/unit, 6–7 voids per variant.
- Metrics at level 2: `interior_rooms`, `void_count`, `rooms_per_unit`.
- 6 tests (`tests/test_grammar_units.py`) + 2 bridge tests.

**Total production count at level 2: five.** That is the honest scale of the current
sub-grammars — enough to prove the mechanism, not enough to constitute a grammar of the
dwelling.

### 0.1 The seven gaps

| # | Gap | Why it matters |
|---|---|---|
| **1** | **Single-anchor interface.** `Refine` re-attaches *all* of the non-terminal's incident edges to one anchor node. A K unit's corridor face, its `V` edges to units above/below, and its shared face with the F behind it in a `D` bay all land on `living`. | Architecturally wrong and formally weak: a `V` edge from the unit above should meet the *sleeping gallery*, not the living room. Until this is fixed, level-2 topology is only locally correct. |
| **2** | **No choice in refinement.** `_apply_in_unit` takes the first match; `refine_units` applies the same boolean flags to every unit. One slab yields exactly one interior. | The sub-grammars are not yet a *space* of variation — which is the whole point of a second grammar level. |
| **3** | **Missing sub-grammars.** Only `u_section` and `l_section` refine. The `B` (single-storey apartment), `D` (K+F double-loaded pair) and `R` (banked room) bays, and the corridor/staircase armature, have none. | The bridge realises five bay types; only two develop. Coverage at level 2 is ~2/5 of the built vocabulary. |
| **4** | **No interior geometry.** Refined units carry no boxes; `boxes_of` applies to the slab only. | Breaks the paper's central claim (*graph and geometry are one representation*) precisely at the level where rooms live. |
| **5** | **No interior validity predicates.** `validity.py` is block-level: circulation, entrance, U/L pairing, floating rooms. Nothing checks that every room is reachable from the unit entry, that wet rooms stack, that a void adjoins living, that a gallery sits over its living volume. | Nothing prevents an invalid interior; §9.2's "constraints inside the productions" argument does not yet hold at level 2. |
| **6** | **Σ_int is free-form.** Interior kinds are bare `subtype` strings (`LIVING = "living"`, …). A typo silently creates a new room kind; `metrics.INTERIOR_SUBTYPES` duplicates the list by hand. | Needs to become a registered sub-alphabet before the vocabulary grows (paper slot B). |
| **7** | **Vocabulary is spec-grounded, not model-grounded.** `U_units_realised.obj` grounds unit *structure and metrics* but carries no room names (every object is `3-4-5_apartment.*`). | Blocks the level-2 analogue of the fig-5 reproduction result — the strongest claim the sub-grammar phase could make (paper slot G). |

---

## 1. What the second level is *for* (the research questions)

The sub-grammar phase is not "add more rooms". It is the phase that tests three claims:

- **Q1 — Does the formalism scale down?** Does the same reversible DPO machinery that
  develops a slab develop a dwelling, with the same guarantees (well-formedness, exact
  inverse, NAC-enforced validity) — or does the room scale need a different formalism?
- **Q2 — Does the interface contract hold under load?** A `REFINE` span promises to preserve
  the non-terminal's boundary. With multi-face units (corridor + interlock + stack) that
  promise needs *routing*, not just re-attachment. Getting this right is the formal
  contribution of the phase.
- **Q3 — Does independent variation at two levels compose?** If block and unit vary
  independently, do the results remain coherent buildings — or do cross-level constraints
  (wet-room stacking, structural bay alignment, void coherence across an interlocked pair)
  have to be modelled explicitly? This is the most publishable single finding available
  here, and it can only be answered once both levels vary (SG3) and cross-level checks
  exist (SG6).

---

## 2. Milestones

Each is small, testable, and lands with a notebook section — the working rhythm of Stages
1–2. **Paper slot** names where it lands in `docs/paper/Graphtope_Journal_Paper.md`.

### SG0 · Typed interface routing *(the key enabler — do this first)* — ✅ done 2026-08-09
Replace the single `anchor` with an **interface router**: `UnitSpec` declares, per incident
edge class, which local node receives it.

```
UnitSpec(..., interface={
    (H, "corridor"): "living",     # the corridor face
    (V, "above"):    "sleeping",   # a unit stacked above meets the gallery
    (V, "below"):    "living",
    (H, "*"):        "living",     # default: an interlocked neighbour
})
```
`Refine` routes each interface edge by `(orientation, direction, neighbour label)`, falling
back to a default. Keep `anchor` working as sugar for a one-entry router (backwards
compatible; `hierarchy` tests must not change).

**Deliver:** interface edges land on the architecturally correct interior node.
**Test:** refine a unit with corridor + above + below + interlock edges and assert each
lands on its declared node; `ABSTRACT` still restores the host exactly; property test —
for a random host graph, the multiset of interface edges is preserved under
`REFINE`-then-`ABSTRACT`.
**Paper slot:** D (and the formal statement in §5.2 becomes materially stronger).
**Effort:** small. **Blocks:** SG2, SG3, SG4, SG6.

### SG1 · The interior sub-alphabet Σ_int — ✅ done 2026-08-09 (`graphtope/interior.py`)
Promote interior kinds to a first-class registered sub-alphabet: a frozen registry with a
label, an architectural description, whether it is habitable, whether it is wet, and its
typical metric footprint. Have `metrics.INTERIOR_SUBTYPES` derive from it rather than
restate it. Add interior **validity predicates** in the same shape as `validity.py`'s
block-level checks: every room reachable from the unit's entry; exactly one entry per unit;
wet rooms adjacent to a wet stack; a void adjoins the volume it opens over; a sleeping
gallery sits `V`-above a living volume.

Vocabulary (to confirm against the reference — see SG5): `entry`, `living`, `dining`,
`sleeping`, `kitchen`, `bath`, `wc`, `void`, `loggia`/`balcony`, `storage`, `internal
stair` — **plus `door` and `window` as first-class opening node types** (§5.2 resolution,
2026-08-09): reachability predicates run through doors, and habitable rooms require a
window.

**Deliver:** interior kinds are declared, checkable, and documented in one place.
**Test:** each predicate rejects a hand-built violation and accepts every refined unit the
current sub-grammars produce.
**Paper slot:** B (Σ openness, Table 1 second panel) and Table 7.
**Effort:** small.

### SG2 · The production corpus — ✅ done 2026-08-11 (31 productions, frozen per R2)
Grow five productions into a grammar of the section. Every production reversible, each with
NACs, each grounded in the type it develops.

- **`G_U` (K-type, rising):** stair position (front / back / mid-bay); void extent
  (full-width / partial gallery — the built condition, per `U_units_realised.obj`'s
  1.7 × 8.4 m mezzanine strips); kitchen as niche vs separate room; bath at gallery vs entry
  level; loggia on the outer face; sleeping-gallery subdivision (1 / 2 rooms).
- **`G_L` (F-type, dropping):** the mirror set, entered at corridor level.
- **`G_B` (single-storey apartment):** new — entry, living, kitchen, bath on one level.
- **`G_D` (the double-loaded interlocked pair):** new, and the interesting one — the `D` bay
  is *two* units sharing a bay front/back. Either a sub-grammar over the pair (one
  non-terminal, two dwellings) or a paired refinement with a shared-face constraint between
  the two sub-derivations. **Recommendation: the latter** — it keeps `G_U`/`G_L` reusable
  and makes the shared face an explicit cross-unit interface (which SG6 then constrains).
- **`G_R` (banked room):** new and small — the room entered through its host apartment.
- **Openings (all families):** door/window-placement productions (§5.2 resolution —
  openings are nodes), so every room connection and façade face is explicit.

**Deliver:** ≥ 20 level-2 productions across five sub-grammars; every bay type the bridge
realises now develops.
**Test:** per sub-grammar — every production reversible; every derivable interior passes
SG1's predicates; `REFINE`/`ABSTRACT` exact for each.
**Paper slot:** D (the full §5.3 subsection), Table 7.
**Effort:** the largest single item in the plan. **Depends on:** SG0, SG1.

### SG3 · Sub-derivation variability — "one slab, many interiors" — ✅ done 2026-08-15
Make refinement a *choice*: a level-2 `Strategy` (reuse `generate.RandomStrategy`, which is
already pluggable) selects which interior productions fire and at which matches; `refine_units`
gains a strategy/seed argument and refines each unit independently. De-duplicate refined
graphs by typed isomorphism at level 2. Measure the interior design space the way G4
measures the block space.

**Deliver:** one block-level slab → N distinct, valid interior variants, each with a
replayable, invertible sub-derivation.
**Test:** N refinements of one slab are pairwise non-isomorphic; each inverts to the same
slab exactly; each passes SG1's predicates.
**Paper slot:** G (§8.5 becomes a distribution, not a count) and **Figure 7**.
**Effort:** small–medium once SG2 exists. **Depends on:** SG0, SG2.

### SG4 · Level-2 geometry — interiors that are built, not just drawn — ✅ done 2026-08-15
Give interior productions **boxes inside the unit envelope**, exactly as `narkomfin.py`'s
shape productions do at block level: the unit's box is a container; each interior production
places a sub-box within it; interior adjacency is derived from what touches. Verify with
`CellComplex` per unit that the interior partitions the envelope without gaps or overlaps.

**Deliver:** `boxes_of` works at level 2; a refined variant exports to OBJ with rooms.
**Test:** interior boxes tile the unit envelope (volume sums to the envelope, no overlaps);
every level-2 graph edge is a real shared face; export/round-trip a refined unit.
**Paper slot:** E (§6 gains §6.5; the "one representation" claim reaches the room scale) and
F (a stricter carrier test — expect new rows in Table 3).
**Effort:** medium–large. **Depends on:** SG2. **Note:** this is the milestone that makes
the sub-grammar work *architecturally* rather than only formally convincing.

### SG5 · Grounding against the built unit *(the reproduction result)* — ✅ done 2026-08-15 (reconstructed per R1: `graphtope/reference.py`, `models/KF_unit_interiors_reference.obj`; G_U and G_L derive it, typed-isomorphic, reversibly — the §11.2 gate answers **one paper**)
Obtain or reconstruct a **room-labelled** reference for the K and F unit interiors —
Ginzburg's published unit plans redrawn as a named OBJ in the same convention as
`graphtope/models/*.obj` — import it via `exchange.graph_from_model`, and show the
sub-grammar **derives it**, verified by typed isomorphism. This is the level-2 analogue of
§8.1's fig-5 reproduction and the strongest claim the phase can make.

**Deliver:** `G_U` and `G_L` reproduce the reference unit interiors from their start graphs.
**Test:** typed-isomorphic to the imported reference; the reverse sub-derivation returns the
non-terminal.
**Paper slot:** G (a reproduction result in §8.5) — and it is the **decision gate** for
one-paper vs two-paper (paper §11.2).
**Effort:** small in code, **entirely dependent on source material** (Risk R1).

### SG6 · Cross-level constraints *(the research finding — Q3)* — ✅ done 2026-08-15 (`graphtope/crosslevel.py`; measured: wet 0.25/interior steered, bays 0.40 soft, void coherence modelled with a 10–35% unconstrained control, levels guaranteed 0)
Once both levels vary independently, test whether they compose. Model the cross-level
conditions explicitly:
- **wet-room stacking** — baths/kitchens aligned vertically across stacked units;
- **structural bay alignment** — interior partitions respecting the 3.66 m module;
- **void coherence in a `D` pair** — a K's double-height void and the F behind it cannot
  claim the same volume;
- **level monotonicity** across the refined graph (spec §12.2).

Implement as NACs *at level 1* informed by level 2 where possible (the interesting result is
whether block-level rules must anticipate unit-level choices), and as post-checks otherwise.
Measure how often unconstrained independent variation violates each.

**Deliver:** a quantified answer to Q3 — the violation rate of independent two-level
variation, and which constraints must be modelled rather than filtered.
**Test:** each constraint rejects a constructed violation; the reference building passes all.
**Paper slot:** H (§9.6) — likely the headline discussion finding.
**Effort:** medium. **Depends on:** SG3 (variation at both levels), SG4 (for the geometric
constraints).

### SG7 · Level-2 metrics and the two-level design space — ✅ done 2026-08-15 (`metrics.interior_quality_vector` / `two_level_design_space`, `topoview.draw_two_level` — Figure 8)
Interior metrics beyond counts: privacy gradient (depth from the unit entry), daylight per
habitable room (real, via window nodes — §5.2), circulation-to-habitable area ratio, wet-core
compactness, and the interior's own type mix. Then the joint map: macro coordinates from
block metrics × micro coordinates from interior metrics — a two-level design space in which
a point is a *building with an interior architecture*.

**Deliver:** `metrics` gains an interior family; `topoview.draw_design_space` gains a
two-level mode.
**Test:** metrics stable and deterministic; the reference lands where expected on both axes.
**Paper slot:** G (**Figure 8**, the closing figure of the expanded paper).
**Effort:** small–medium. **Depends on:** SG3, SG4.

### SG8 · Steering over two levels *(ties into G5)* — ✅ done 2026-08-15 (`graphtope/steer.py`: realisability-gated pool search over the SG3 space with the G4/SG7/SG6 objective registry; `validate_io` + `blender/validate_variants.py`: the shared pytest/Jupyter/Blender validation core over exported artefacts)
With SG7's objectives, search over *sub*-derivations as well as derivations: target a
programme (N units of a given interior type), an interior objective (maximise rooms with
external wall at fixed GFA), or proximity to the reference in the two-level map. The
rule-generated two-level corpus is also the training substrate for the graph-ML line
(§12.2, the group's BGR work).

**Paper slot:** future work (§10), or a third paper.

---

## 3. Sequencing

```
SG0 interface routing  ──┬─► SG2 production corpus ──┬─► SG3 variability ──┬─► SG6 cross-level (Q3)
SG1 Σ_int + validity  ──┘                            ├─► SG4 level-2 geometry ─┘
                                                     └─► SG5 grounding (gated on source material)
SG3 + SG4 ─► SG7 two-level map ─► SG8 steering
```

**Recommended first slice: SG0 + SG1 + SG5-source-hunt in parallel.** SG0 and SG1 are small,
unblock everything, and immediately strengthen the paper's formal §5.2 — and starting the
search for room-labelled unit plans early is what determines the publication shape.

**Minimum viable for the one-paper strategy** (paper §11.2): **SG0 → SG1 → SG2 → SG3**.
That fills slots B, D and G, gives Figure 7, and lets §5.3 carry the same weight as §4.
SG4–SG6 can follow as the companion paper.

| Milestone | Effort | Unblocks | Paper slot |
|---|---|---|---|
| SG0 interface routing | S | SG2/3/4/6 | D |
| SG1 Σ_int + interior validity | S | SG2 | B, Tab 7 |
| SG2 production corpus | **L** | SG3/4/5 | D, Tab 7 |
| SG3 sub-derivation variability | M | SG6, SG7 | G, Fig 7 |
| SG4 level-2 geometry | **L** | SG6, SG7 | E, F |
| SG5 grounding | S (code) / ? (data) | — | G, §11.2 gate |
| SG6 cross-level constraints | M | — | H |
| SG7 two-level metrics + map | M | SG8 | G, Fig 8 |
| SG8 steering | M–L | — | §10 |

---

## 4. Risks

| | Risk | Mitigation |
|---|---|---|
| **R1** | **No room-labelled reference exists** for the K/F interiors, so SG5's reproduction claim cannot be made. This is the plan's one hard external dependency. | Redraw Ginzburg's published unit plans as a named OBJ ourselves, and *state in the paper that the reference was reconstructed from published drawings* rather than measured — weaker but honest, and still a reproduction result. Fall back to the two-paper strategy if even that is not defensible. |
| **R2** | **SG2 scope creep** — a grammar of the dwelling can absorb unlimited effort. | Fix the corpus at the productions listed in SG2 and freeze. Anything further is a fourth paper, not this one. |
| **R3** | **SG4's tiling constraint may be unsatisfiable** for some interiors (the block-level lesson: a grid cannot embed every topology). | Apply the block-level house rule — *report coverage, don't fake it*: interiors that cannot tile the envelope are reported, exactly as skipped rooms are at level 1. |
| **R4** | **Carrier flakiness at room scale** — `CellComplex` and the OBJ exporter are already the shakiest surfaces (Table 3, rows 9–10) and SG4 will hit them harder. | Add the failures to the TopologicPy contribution briefing as they surface; keep the per-component workaround; treat exporter flakes as known-and-reported, not as regressions. |
| **R5** | **Two-level combinatorics** — N slabs × M interiors makes de-duplication and mapping expensive. | De-duplicate at each level separately before combining; keep the classical-MDS map (numpy-only, deterministic) rather than reaching for a heavier embedding. |

---

## 5. Open decisions — status (three of four resolved 2026-08-09, T. Dounas)

1. **`D`-bay modelling — RESOLVED: paired refinement.** Keep K and F as separate
   placeholders (as `narkomfin.anchor_KF` already builds them), refine each with its own
   `G_U`/`G_L`, and tie the pair with an explicit cross-unit constraint. Measured caveat:
   the derived slab graph carries **no K–F edge** — the pair meets only through the
   corridor — so the pairing is recorded as node attributes (`pair`), *not* as a fake
   edge (every graph edge must remain a real shared face). SG6's void-coherence check
   attaches to that recorded pairing.
2. **Interior vocabulary depth — RESOLVED: openings are first-class nodes.** Doors and
   windows become typed nodes — this **overrides** the earlier rooms-only recommendation.
   Consequences: Σ_int (SG1) registers `door`/`window` from the start; interior
   reachability predicates run *through doors*, not bare adjacency; SG7's daylight metric
   becomes real rather than a proxy; SG2 gains opening-placement productions (its scope
   grows accordingly).
3. **Where the split-level actually is — RESOLVED: 8.0 m, gallery over the corridor.**
   The K maisonette is 8.0 m tall with the sleeping gallery directly **above the
   corridor** (confirmed from the section drawing; `U_units_realised.obj`'s 9.90 m
   "3-4-5" envelopes measure three structural grid floors, not the dwelling). Corrects
   `narkomfin.anchor_K` (was 2×FLOOR = 6 m standing beside the corridor) and `G_U`'s
   gallery-above-living assumption: the corridor interface routes to the entry level and
   the stacked-above interface to the gallery — exactly SG0's router.
4. **Publication shape:** **RESOLVED 2026-08-15 — one paper** — SG5's
   reconstruction satisfies the reproduction claim (weaker-but-honest, per
   R1's mitigation). See
   `docs/paper/Graphtope_Journal_Paper.md` §11.2.

---

## 6. Definition of done for the phase

- Every bay type the bridge realises (`K`, `F`, `B`, `D`, `R`) has a sub-grammar.
- Interface edges route to architecturally correct interior nodes, and `REFINE`/`ABSTRACT`
  remains exact under multi-face units — property-tested.
- One slab yields many distinct, valid interiors, each with a replayable, invertible
  sub-derivation.
- Interiors carry geometry, and every level-2 edge is a real shared face (or the failure is
  reported).
- The reference K and F interiors are reproduced by derivation and verified by typed
  isomorphism — or the inability to do so is stated, with the reason.
- Cross-level constraint violation rates are measured, and the paper can answer Q3.
- The suite grows from 195 to roughly 240–260 tests, with level-2 coverage mirroring the
  level-1 pattern.
