# Testing the two-level system, and generalising it

**For:** the graphtope repo (post-SG8) · **Date:** 2026-08-15
**Scope:** (1) how to test what exists — Jupyter × Blender, headless and
visual; (2) a design reflection on generalising the pipeline: someone hands
us a Topologic `CellComplex`, we generate a graph, then manipulate it into a
graph grammar — and how many manipulations can be found *systematically*.

---

## Part 1 — Testing: three runways, one core

The load-bearing decision (SG8) is that there is **one validation core** —
`graphtope/validate_io.py` — and three runways execute it: **pytest** (every
commit), **Jupyter** (the interactive loop), **Blender** (headless gate +
visual QA). The contract between runways is not code but **artefacts**: the
OBJ plus its `.graph.json` sidecar, with the sidecar authoritative for the
graph and the OBJ authoritative for the geometry. Validate artefacts, never
live objects, and all three runways necessarily agree.

What the core checks, per exported variant:

| check | meaning | catches |
|---|---|---|
| integrity | every sidecar node with a box ↔ a named OBJ group | deleted/renamed rooms, exporter flakes |
| tiling | per unit: space volumes sum to the envelope, no overlaps | misplaced rooms, slivers |
| adjacency | every graph edge between spaces is a real shared face of the OBJ boxes | the "one representation" claim — geometry that drifted from the graph |

### 1.1 Jupyter — the interactive QA loop

The notebook (`notebooks/01_graphtope.ipynb`, closing section) already runs
the loop; the recipe for testing *any* new variant set is:

```python
from graphtope import steer, exchange, interior_geom, validate_io
from graphtope import narkomfin as nf

slab = nf.derive_slab_from_patterns(["KFB", "BFK"])
top, pool = steer.steer(slab, steer.DEFAULT_OBJECTIVES, candidates=6, seed=0)
# 1. guarantees survive steering: valid, replayable, invertible
assert all(steer.replay(slab, s) for s in top)
# 2. export the winners — artefacts, not objects
for s in top:
    exchange.to_obj(s.variant.graph, f"exports/steered/r{s.rank}.obj",
                    boxes=interior_geom.boxes(s.variant.graph))
# 3. validate over the files
report = validate_io.validate_directory("exports/steered")
assert report["ok"]
```

Beyond the happy path, two Jupyter-specific tests matter:

- **Perturbation testing.** Deliberately damage an export — rename a group,
  translate one room by a metre, delete a group — and watch the validator
  catch it (`tests/test_sg8_steering.py` does exactly this under pytest;
  doing it live in the notebook is the fastest way to *see* what each check
  is worth). A validator that cannot fail is not a validator.
- **Determinism audits.** Everything downstream of a seed is deterministic —
  same seed, byte-identical `to_dict`, byte-identical OBJ. Re-run a cell and
  `diff` the exports; if they differ, a non-determinism entered (historically:
  carrier vertex ordering — the CLAUDE.md gotcha that canonical, sorted
  serialisation exists to suppress).

The notebook is also where the *visual* registers get checked inline:
`topoview.draw_massing(boxes=...)` for room readability (does the gallery
read as a strip over the living volume? do door leaves sit *in* walls, not
beside them?), and the two-level map for whether a steered winner actually
moved in the intended direction.

### 1.2 Blender headless — the CI gate

`blender/validate_variants.py` runs the same core inside Blender's
interpreter, so what a designer opens is what the suite verified:

```
blender --background --python blender/validate_variants.py -- <dir> [--render <outdir>]
```

- writes `<dir>/validation.json` (same schema as in-process);
- exits non-zero on any failure → usable as a CI gate;
- `--render` adds a thumbnail per variant (QA artefacts, never gates).

Wiring it into CI is three lines of YAML — run pytest, then run Blender over
a fixed-seed exported set; upload `validation.json` + thumbnails as
artefacts. The pytest suite skips this when no binary is on PATH (the
in-process core has already run over the same files), so CI can treat
Blender as the *stronger* gate that runs where the binary exists and the
*same* gate logically everywhere else.

The one thing headless Blender adds over in-process validation is the
**import path itself**: OBJ parsed by Blender's importer, not ours. Exporter
regressions that our parser forgives and Blender's does not (mtllib
references, face indices, `g`-vs-`o` conventions) surface here and only
here.

### 1.3 Blender visual — the designer loop

Interactive use, `blender/import_graphtope.py` (Scripting workspace → Run
Script, edit `OBJ` at the top):

1. **Import** — spaces arrive as objects named by node id, coloured by the τ
   legend, filed into `type_{label}` collections.
2. **Inspect** — the visual checklist that no automated check covers:
   room proportions vs the section (gallery 1.7 m *reads* narrow), doors in
   wall planes with sensible leaf sizes, windows on façades not party walls,
   wet rooms clustering, the corridor touching every unit's entry.
3. **Edit** — move/resize rooms (the intended use: a designer corrects what
   the grammar got wrong).
4. **Export → re-import** — export OBJ from Blender, then
   `exchange.graph_from_obj(obj, sidecar)` rebuilds the typed graph from
   bounding-box adjacency with types recovered from the sidecar by
   centroid. Then run `validate_io.validate_variant` on the *edited* pair.

The honest contract for edits (stated in `exchange.py`'s docstring, worth
restating to designers): geometry carries adjacency + orientation but **not
access direction** — a shared wall has no arrow — so one-way H semantics
come from the sidecar, exactly as they would from IFC. An edit that moves a
room changes the graph; an edit that only repaints one does not; an edit
that breaks tiling shows up as a validation failure with the offending pair
named.

### 1.4 The test matrix (what runs where)

| property | pytest | Jupyter | Blender headless | Blender visual |
|---|---|---|---|---|
| grammar invariants (§2.2), reversibility (§4) | ● | ● | | |
| SG1 interior validity, SG6 constraints | ● | ● | | |
| SG4 placement (in-process `tile_report`) | ● | ● | | |
| file integrity / tiling / adjacency (`validate_io`) | ● | ● | ● | |
| OBJ importable by Blender's own parser | | | ● | ● |
| rendering / readability / taste | | ○ (massing) | ○ (thumbnails) | ● |
| edit round-trip (`graph_from_obj`) | ● | ● | | ● (source of edits) |

● = the right place · ○ = available but secondary.

---

## Part 2 — Generalisation: from someone else's CellComplex to a graph grammar

The system currently runs one way:

$$A_0 \xrightarrow{\text{grammar}} \text{graph} \xrightarrow{\text{bridge}} \text{geometry}$$

The generalisation runs it the other way, then closes the loop:

$$\text{CellComplex} \to \text{graph} \to \text{motifs} \to \text{productions} \to \text{a grammar that re-derives the input and varies beyond it}$$

This is not speculative — every stage has a working precedent in the repo.
The import is B2 (`graph_from_model` on named OBJs; `Graph.ByTopology` on
complexes is measured in Stage 2); the motif→production step is what the
SG2 corpus did by hand; the re-derivation test is SG5; the "varies beyond
it" is SG3; the measurement is G4/SG7; the search is SG8.

### 2.1 The import ladder

Given an arbitrary `CellComplex` (someone's BIM/survey model):

1. **Topology → adjacency.** `Graph.ByTopology(cc)` gives the dual: a vertex
   per cell (at the centroid), an edge per shared face. Known carrier
   behaviour (briefing + CLAUDE.md): build **one complex per face-connected
   component** (`ByCells` returns `None` for disconnected sets); never rely
   on vertex identity — address by stable id.
2. **Faces → semantics.** The shared face's normal gives orientation (z ⇒ V,
   else H — `exchange._touch_axis` logic, or the face normal directly, which
   is *richer* than bbox axes for non-box cells); face area is a natural
   edge weight; V direction from which cell is above.
3. **Cells → types.** Cell dictionaries / IFC space types → Σ labels and
   Σ_int subtypes (`classify_space`; the Σ_int matcher already exists).
   This is where a real IFC import via `Graph.ByIFCFile` would slot in —
   the production upgrade our OBJ re-import honestly defers.
4. **Measure.** `typical_sizes`-style per-type statistics — the ground truth
   the induced grammar's dimensions will quote (exactly how
   `U_units_realised.obj` grounded G_U).

The output is a `StateGraph` with geometry — the same representation the
grammar produces. **Import is not a special case; it is a derivation of
length zero.** Everything downstream (validity, metrics, maps, steering)
applies to imported graphs unmodified.

### 2.2 Grammar induction — reversibility is the enabling property

Every operation in this repo returns its exact inverse (atomics A1–A7,
composites, DPO applications, REFINE/ABSTRACT, even placement). That is
usually motivated as *undo*; for induction it is something stronger: **the
difference between two graphs, expressed as an invertible operation
sequence, *is* a production.**

Concretely, three induction routes, in increasing ambition:

- **Paired states** (we have the derivation): the trace *is* the grammar.
  Trivially true for our own derivations; useful when a designer's edit
  session on an imported model is logged — each accepted edit becomes a
  candidate production ("she kept splitting corner rooms; make that a
  rule").
- **Anti-unification** (we have start and result, not the steps): compute a
  maximal common subgraph K between two states; the spans L ⊇ K ⊆ R read
  off the differences are DPO productions by construction. This is the
  classic approach and it composes with our machinery because our matcher
  is typed-attributed-directed already (`rules.match_pattern`) — the
  anti-unifier can *be* a subgraph matcher run in "largest common"
  mode. The networkx escape hatch (`MultiDiGraphMatcher`) is available for
  the heavy matching, per the standing carrier decision.
- **Corpus mining** (we have many buildings, no steps): frequent
  typed-subgraph mining over the corpus yields candidate motifs; a motif
  plus its neighbourhood difference is an L/R pair; **NACs are mined from
  negative pairs** — configurations that never co-occur with the motif
  across the corpus become its blocking conditions. (One-per-room windows,
  one-void-per-living in SG2 are hand-mined instances of exactly this.)

The verification test generalises SG5 and is the whole game: **an induced
grammar must re-derive its corpus** (typed-isomorphic, reverse derivation
returns the start) — coverage reported honestly, never faked (the R3 house
rule). Held-out buildings then measure whether the grammar *generalised* or
merely memorised: the coverage rate on held-out vs training corpus is the
induction's generalisation score.

### 2.3 How many manipulations can we systematically find?

This has a clean answer if we enumerate by layer, because each layer has a
different *source of systematicness* — one is combinatorial, one is
geometric, one is algorithmic.

**Layer 0 — pure topology (the graph before geometry).** The atomic basis
already enumerates it exhaustively: add/delete node, add/delete edge,
relabel, reweight, reverse — 7 op *types*, and every graph transformation
we ever express is a sequence of them. The count of *sequences* is
unbounded; the count of *k-length sequences with valid results* is what
`generate.RandomStrategy` samples and `validity` filters — the design space
G0 measured. Systematic here means: enumerate ops, apply where they match,
keep what passes §2.2 + validity. This is done.

**Layer 1 — spaces and volumes (which topology changes a designer means).**
The composites are the vocabulary: SPLIT (and DIVIDE(k) = k−1 splits), MERGE
(with ξ for weights), UNION/DIFFERENCE, MIRROR, TRANSFORM, AttachPendant.
Per *host type* these parameterise into the alternates the sub-grammars
use — and the count is exactly the option spaces SG3 samples:

- K: void ∈ {none, partial, full} × kitchen ∈ {niche, room} × bath level ∈
  {gallery, entry} × wc × loggia × storage × gallery split = **3·2·2·2⁴ = 192**
  declared interiors (before openings);
- F: 2⁵ = 32; B: 2²; R: 2.

So "how many" at this layer is not a mystery — it is the **cross product of
per-host alternates**, pruned by NACs (mutual exclusivity), by validity, and
by typed-isomorphism dedup (SG3). What *systematic discovery* adds beyond
declaration: mining an imported corpus tells you which cells of that product
the built world actually occupies — the distribution, not just the support.
(Our `sample_*_options` probabilities "leaning toward the built condition"
are a hand-set prior; induction would *measure* it.)

**Layer 2 — openings.** Doors and windows are nodes (§5.2), so their
manipulations are Layer-0 ops with dedicated shapes, and the count is
bounded by two different things:

- *doors*: one interposition per **wall segment shared by two spaces** —
  the edge-deleting DPO that splices the door node in. The candidate set is
  enumerable directly from the graph (every H adjacency, minus NACs:
  front-door rules, one door per pair);
- *windows*: one per **habitable room × façade face** (the SG4 placement
  enumerates the faces; the one-per-room NAC bounds the count).

So openings contribute `O(walls + rooms)` candidate manipulations per
building — small, fully enumerable, and each verifiable in geometry (the
leaf must sit in the wall plane — `validate_io`'s opening checks).

**Layer 3 — internal walls, and the honest limit.** Inserting a wall
between two rooms is SPLIT at room scale (topology changes: yes).
*Removing* one is MERGE. But **shifting** a wall 300 mm is the interesting
case: it changes no adjacency, no orientation, no type — only dimensions.
The graph sees it as an attribute change (the placement's x/w), i.e. a
Reweight-class op on geometry attributes. This is the honest boundary of
what a graph grammar captures: **topological manipulations are discrete and
enumerable; metric manipulations are continuous and belong to the geometry
layer, entering the grammar only when they cross a visibility threshold**
(a shift that makes two rooms touch creates an edge; one that doesn't,
doesn't). A generalised system should state this as a feature — the grammar
is exactly the discrete quotient of the design space — and offer attribute
ranges (SG4's dims) as the continuous padding *inside* each discrete cell.

**Total count, honestly stated:** for a building with n spaces, the
systematic manipulation set is

$$\underbrace{O(n^2)}_{\text{edge add/remove}} + \underbrace{O(n \cdot |\Sigma_{int}|)}_{\text{relabel/refine}} + \underbrace{\prod_{\text{hosts}} (\text{alternates})}_{\text{Layer 1}} + \underbrace{O(\text{walls} + \text{rooms})}_{\text{Layer 2}} + \underbrace{O(\text{partitions})}_{\text{Layer 3}}$$

pruned by NACs, validity and iso-dedup. For the current corpus this
evaluates to the numbers above; for an imported corpus the *same formula*
applies with the alternates read off the mined motifs. The formula, not any
single number, is the answer.

### 2.4 What would need building (in dependency order)

1. **`graph_from_cellcomplex`** — Stage-2's `Graph.ByTopology` round-trip
   promoted to a first-class import (per-component complexes, face-normal
   orientation, cell-dict semantics, canonical ids). Small; everything
   waits on it.
2. **Motif miner** — frequent typed-subgraph mining over an imported corpus
   (escape-hatch networkx is fine at corpus scale; gSpan-style if it grows).
3. **Production inducer** — anti-unification between variant states → DPO
   spans; NAC mining from negative pairs; emission into `rules.Production`
   (the dataclass is already induction-shaped: L/K/R + NACs, no
   provenance assumed).
4. **Coverage harness** — the SG5 test as a function: `grammar.covers(
   graph) -> bool` (re-derivable, reverse returns start), corpus splits,
   generalisation score. The induced grammar's report card.
5. **Grammar diff** — edit distance over production sets, so "what did
   induction learn from *this* building that it didn't from that one" is
   measurable — the two-level map's third axis, in effect.

### 2.5 Risks, carried over

The carrier risks are the same ones the briefing documents, amplified by
scale: `CellComplex.ByCells` fragility on imported (non-manifold, survey-
dirty) cells — keep the per-component workaround and add failures to the
contribution list; vertex identity across ops — canonical ids, never cached
references; exporter flakiness under Blender's importer — the headless gate
exists precisely to catch this. And the honesty rules travel unchanged:
report coverage, don't fake it; the sidecar is the graph; a validator that
cannot fail is not a validator.

---

*The through-line: testing and generalisation are the same activity. The
test matrix says the artefacts carry the truth; induction says the graph
carries the building; and both rest on the one property this repo was built
to keep — every step reversible, so nothing is ever lost by taking it.*
