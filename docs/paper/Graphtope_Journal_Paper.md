# Topology as the Bridge: A Reversible, Hierarchical Graph Grammar that Drives a Shape Grammar

**Draft scaffold — v0.1, 2026-07-30**
**Authors:** T. Dounas, W. Jabi *(order/affiliations TBC)*
**Repository:** `graphtope` · **Suite at time of writing:** 195 tests passing · **Carrier:** TopologicPy 0.9.43

> **How to use this document.** This is a *scaffold*, not a finished manuscript. Every
> section carries (a) a target length, (b) the material that already exists in the
> repository and can be written up today, and (c) an explicit **▣ Expansion slot** marking
> where the forthcoming sub-grammar work (see `docs/Sub_Grammar_Development_Plan.md`)
> lands. The slots are designed so the sub-grammar results *extend* sections rather than
> force a restructure. Text set in normal prose is draft-quality and can be lifted;
> text in `[brackets]` is an instruction to the author.

---

## 0. Venue, format, and framing

**Primary target:** *International Journal of Architectural Computing* (IJAC, SAGE) —
fits the shape-grammar/graph-grammar/computational-design audience and accepts
implementation-heavy papers with a reference building. Typical length 7,000–9,000 words,
unlimited figures in practice, SAGE Harvard references.

**Alternatives, in order:**
1. *Environment and Planning B: Urban Analytics and City Science* — the historical home of
   shape grammars (Stiny; Duarte's Malagueira grammar). Stronger theory bar, tighter word
   count (~8,000), and would want the formal reversibility result foregrounded.
2. *Nexus Network Journal* — good fit for the topology/formalism angle, weaker fit for the
   generative-catalogue results.
3. *Automation in Construction* — would require the BIM/IFC round-trip and a stated
   industry application to carry the paper; the TopologicPy carrier-limitation findings
   (§7) become the practical contribution.

**Framing decision (locked for this draft):** the paper is *not* "here is a Narkomfin
generator". It is **"here is a formal, reversible, hierarchical grammar in which the graph
level and the shape level are one representation, demonstrated on Dom Narkomfin"**. The
generated catalogue is evidence, not the claim. This framing is what leaves room for the
sub-grammar work to become the second half of the argument (or a companion paper — see
§11.2).

---

## 1. Abstract

*(~200 words. Draft below — real numbers already substitutable.)*

> Shape grammars and graph grammars have developed as parallel formalisms for
> architectural composition: the first operates on geometry and is hard to compute over,
> the second computes readily but is usually detached from the building it describes. We
> present `graphtope`, a typed, directed, weighted, attributed graph grammar in which
> **topology is the bridge** between the two. Buildings are represented as space-adjacency
> graphs carried directly on a topological kernel (TopologicPy); rewriting is defined as a
> three-tier algebra — seven reversible atomic edits, six composite verbs, and named
> double-pushout productions — in which every operation returns its exact inverse, so a
> building can be *taken apart* by the same grammar that builds it. The grammar is
> hierarchical: a block grammar develops slabs, section sub-grammars develop individual
> dwelling units through a reversible `REFINE`/`ABSTRACT` span, and completed blocks are
> joined by composition. We demonstrate the framework on Dom Narkomfin (Ginzburg &
> Milinis, 1930): the specified grammar reproduces the building's published adjacency
> graph from a two-node axiom and inverts back to it; a circulation-first *shape* grammar
> realises proposals as exact-metre geometry in which every graph edge is a physically
> shared face; and the pair generates a de-duplicated catalogue of valid variants measured
> and mapped in a common design space. We report the carrier's measured limitations and
> what a topological kernel must provide for grammar work.

**Keywords:** graph grammar; shape grammar; double pushout; architectural topology;
generative design; Dom Narkomfin; TopologicPy.

▣ **Expansion slot A — abstract.** When the sub-grammar programme (SG1–SG5) lands, the
sentence *"section sub-grammars develop individual dwelling units"* is upgraded to a
quantified claim: "…and a section sub-grammar reproduces the K- and F-type maisonette
interiors of the reference building, so the same formalism operates from block massing to
room adjacency across two grammar levels." One sentence changes; nothing else moves.

---

## 2. Introduction

*(~1,200 words)*

**2.1 The problem.** Shape grammars (Stiny, 1980) compute on geometry and are
architecturally expressive but computationally awkward: emergence and subshape detection
make general implementation hard, and the geometry carries no explicit relational
structure. Graph grammars (Ehrig et al., 2006) compute cleanly — matching, rewriting, and
confluence are well-founded — but the graph is usually a *description* of a building
produced after the fact, so nothing prevents graph and geometry from diverging. The
practical consequence in architectural computing is a class of tools that generate correct
*topologies* which realise into arbitrary geometry, or generate plausible geometry with no
manipulable structure behind it.

**2.2 The position.** Following Dounas & Jabi (2025), we take **topology** as the shared
substrate: a shape and the graph behind it are two readings of the same topological object,
and if the representation is carried on a topological kernel, the two cannot drift. This
paper turns that position into a formal system and an implementation.

**2.3 Contributions.** *(Keep this list — it is the paper's spine.)*

1. **A three-tier reversible operation algebra** for architectural graphs: 7 atomic edits →
   6 composite verbs → named productions, where every operation returns its exact inverse
   and inversion is verified by property tests over random graphs (§3, §8.2).
2. **A typed, directed, attributed DPO rule formalism with negative application
   conditions**, including a subgraph-monomorphism matcher that respects node labels,
   subtypes, edge orientation and direction — capabilities the carrier does not provide
   (§3.4, §7).
3. **A hierarchical grammar architecture** — building → block → section — with a
   `REFINE`/`ABSTRACT` span whose interface contract is preserved and whose round-trip is
   *exact*, demonstrated across two grammar levels end-to-end (§5, §8.5).
4. **A graph→shape bridge** in which an abstract derivation *proposes a programme* and a
   circulation-first shape grammar *realises* it as exact-metre geometry whose adjacency is
   derived from real shared faces — with honest coverage reporting for everything the
   section cannot express (§6, §8.4).
5. **An empirical account of what a topological kernel must offer** a grammar
   implementation, with measured gaps in TopologicPy 0.9.43 and the workarounds adopted
   (§7) — a contribution to the tool's development agenda as much as to the literature.
6. **A worked, reproducible demonstration** on Dom Narkomfin, including import of the real
   building model, reproduction of its published graph, a generated and de-duplicated
   variant catalogue, and a metric design-space map with the reference located in it (§8).

**2.4 Why Dom Narkomfin.** *(~250 words. The building is the canonical test case: its
section is a rule — a corridor every three floors serving K-type maisonettes rising and
F-type maisonettes dropping, interlocking across the three-floor module. It is a grammar
that was designed as a grammar, by architects who described it as a typological research
programme (Ginzburg's Stroikom types). It gives us: a published adjacency structure to
reproduce, a real model to import and measure against, and a unit section rich enough to
require a second grammar level — which is precisely what the sub-grammar work exploits.)*

**2.5 Paper structure.** *(one paragraph)*

---

## 3. Formal framework

*(~1,800 words. Source: `Topologic_Graph_Grammar_Spec.md` §§2–6; code in `model.py`,
`alphabet.py`, `atomic.py`, `composite.py`, `rules.py`.)*

### 3.1 The graph object
A building state is `G = (N, E, λ_N, λ_E, ω, α)`: a typed, directed, weighted, attributed
graph. Nodes are spaces labelled from Σ = {`generic`, `corridor`, `staircase`, `entrance`,
`u_section`, `l_section`}, Σ being *open* (new kinds enter as `subtype` attributes without
enlarging the label set — the mechanism the sub-grammars use). Edges are adjacencies
labelled by orientation Θ = {`H`, `V`} with a direction flag (access is one-way or
bidirectional) and a weight (default 1.0, coalesced by max on merge).

**Table 1.** Node-label alphabet Σ and edge alphabet Θ, with the architectural reading of
each. *(Lift from spec §3.1–3.2.)*

### 3.2 Well-formedness
Four invariants (spec §2.2) hold at every state: unique identifiers, labels drawn from Σ,
no self-loops, at most one adjacency per ordered pair per orientation. Every operation in
§3.3–3.4 preserves them; this is asserted in the implementation after each application.

### 3.3 Three tiers of operation
- **Tier 0 — atomics (A1–A7):** add/remove node, add/remove edge, relabel, re-weight,
  set-attribute. Each is a dataclass whose `apply` performs the edit *and returns the exact
  inverse operation*.
- **Tier 1 — verbs:** SPLIT/MERGE (mutual inverses, with weight coalescing ξ = max),
  DIVIDE, UNION, DIFFERENCE, MIRROR, TRANSFORM, AttachPendant — each a recipe over atomics
  returning an `OpSequence` inverse.
- **Tier 2 — named productions:** the building grammar proper (§4).

**Proposition (reversibility).** For every operation `op` at any tier,
`inverse(op) ∘ op = id` on the graph state. *(This is enforced constructively — an
operation cannot be applied without producing its inverse — and verified by property tests
over randomly generated graphs; §8.2. State it as a proposition with a two-line
constructive argument rather than a theorem with proof; the strength of the claim is that
it is checked, exhaustively, at every tier.)*

### 3.4 Productions as DPO spans
A production is a span `L ← K → R` with negative application conditions. Matching is a
**typed, attributed, directed subgraph monomorphism**: label and subtype must agree, edge
orientation must agree, and direction is matched either symmetrically (a bidirectional
pattern edge matches either) or strictly one-way. Application deletes `L∖K` subject to the
dangling condition and glues `R∖K`; the inverse span is returned, so derivations invert
step-by-step.

**Figure 1.** The three tiers, with one production expanded into its verb recipe and that
verb into its atomics — the "operation microscope" figure. *(Renderable from
`topoview`; currently drawn by hand.)*

▣ **Expansion slot B — §3.1.** The openness of Σ is exactly the mechanism by which the
sub-grammars introduce interior room kinds (`living`, `sleeping`, `kitchen`, `bath`,
`void`, `entry`) without touching the block-level alphabet. When SG1 formalises the
interior alphabet Σ_int as a first-class registered sub-alphabet, this subsection gains a
short paragraph and Table 1 gains a second panel. No change to §3.2–3.4.

---

## 4. The Dom Narkomfin grammar

*(~1,400 words. Source: spec §7–8; code `grammar_dnf.py`, `engine.py`.)*

### 4.1 Axiom and productions
From the axiom `A₀` — two generic blocks, residential and communal condenser — eight named
productions P1–P8 develop the building: internal subdivision, corridor insertion,
staircase, entrance, unit assignment (`u_section` / `l_section`), the U/L interlock, and
the inter-block link.

**Table 2.** The production catalogue P1–P8: name, informal reading, DPO span summary,
NACs, and which Tier-1 verb each instantiates. *(Lift from spec §7.5.)*

### 4.2 A worked derivation
The scripted sequence

`P1 · P1 · P3 · P3 · P4 · P4 · P5 · P6 · P7 · P2 · P4 · P5 · P8`

takes `A₀` to `G_DNF`: **18 nodes, 18 edges**, distributed as 8 `generic`, 3 `staircase`,
2 `corridor`, 2 `entrance`, 2 `u_section`, 1 `l_section`, in two blocks joined by P8.

**Figure 2.** The derivation as a grid of typed graph states, one panel per production, on
a shared layout — the visual proof that `A₀ →* G_DNF`. *(Produced by
`topoview.record_frames` + `draw_grid`; already generated in the notebook.)*

### 4.3 Reverse derivation
Inverting the trace returns the axiom exactly. The derivation trace serialises to JSON,
replays on a fresh axiom with deterministic identifiers, and inverts — so a derivation is a
first-class, transportable object rather than an execution artefact.

▣ **Expansion slot C — §4.** Nothing in §4 changes when the sub-grammars land; P1–P8 stay
block-level. This section is deliberately the *stable core* of the paper.

---

## 5. Hierarchy: three levels of one grammar

*(~1,200 words today; ~2,200 after the sub-grammar work. Source: spec §7.6; code
`hierarchy.py`, `compose.py`, `grammar_units.py`.)*

### 5.1 Terminals, non-terminals, and the three-level architecture
```
Building grammar    :  block graphs + composition            (§5.4)
 └─ Block grammar    :  P1–P8 → terminals + non-terminals     (§4)
     └─ Section sub-grammar :  refine each u_section/l_section (§5.2–5.3)
```
`generic`, `corridor`, `staircase`, `entrance` are terminal at the space level;
`u_section` and `l_section` are **non-terminals** standing for whole dwelling units that a
sub-grammar develops.

### 5.2 The `REFINE`/`ABSTRACT` span and its interface contract
`REFINE(n, G_u)` is a `REPLACE` whose left side is `{n}` and whose right side is the start
graph of the sub-grammar `G_u`; the **interface `K` is exactly the non-terminal's incident
edges**, which the sub-grammar receives as its boundary and must preserve — re-attached to a
designated *anchor* node of the start graph. Its inverse `ABSTRACT(S → n)` collapses the
developed unit back to the non-terminal. We report the round-trip as **exact**: refining
every unit of a realised slab and then applying the composed inverse restores the slab to
dictionary-level equality (§8.5).

### 5.3 The section sub-grammars `G_U` and `G_L` *(current state)*
`G_U` develops the K-type maisonette: living at corridor entry level, a sleeping gallery
directly above (a `V` adjacency), an internal stair joining the split levels, then optional
productions for the double-height void over the living volume, a kitchen niche off living,
and a bath off the gallery. `G_L` develops the F-type maisonette entered at corridor level
with living dropping a floor below, plus kitchen and bath at entry level.

Two honest qualifications belong in the paper, not in a footnote:
1. **Vocabulary is spec-grounded, structure is model-grounded.** The reference model
   `U_units_realised.obj` confirms the *structure and metrics* of the unit (one bay wide
   ≈ 3.7 m, 8.4 m deep, spanning three storeys, with partial-width mezzanine strips leaving
   a double-height void, and genuinely `V`-stacked interior pieces) but carries no room
   names, so the room *vocabulary* rests on the specification and the published type
   descriptions.
2. **A domain correction to the reference grounding.** Import of the real model shows every
   built maisonette is an F-type mapping to `l_section`; the F-type maisonette *is* the
   L-section. There is no separately modelled U-section, so the grammar's U/L pairing
   abstracts one built maisonette family into two non-terminals. This is stated as a
   finding, not hidden.

### 5.4 Composition: `BRIDGE`
Blocks are developed by independent grammars to completion and only then joined by a
composition operation over designated interface nodes. We verify that modular development
plus `BRIDGE` is typed-isomorphic to monolithic development of the same building.

▣ **Expansion slot D — §5.3 (the largest slot in the paper).** The sub-grammar programme
replaces the current three paragraphs with a full subsection of the same weight as §4:
a sub-alphabet table (Σ_int), a production catalogue for `G_U`, `G_L`, and the currently
missing `G_B` / `G_D` / `G_R` (single-storey apartment, double-loaded interlocked pair,
banked room), interior validity predicates, and a worked unit derivation figure paralleling
Figure 2. **Planned figure: Figure 7 — "one slab, many interiors": a single block-level
graph refined into N distinct, valid unit-interior variants.** See
`docs/Sub_Grammar_Development_Plan.md` §SG2–SG3.

---

## 6. From graph to shape

*(~1,600 words. Source: `Planning&State.md`; code `narkomfin.py`, `bridge.py`,
`realise.py`, `exchange.py`.)*

### 6.1 Two ways to realise a graph, and why the first failed
Stage-2 realisation was first attempted as a general *layout solver*: τ maps each node to a
cell and a constraint-repair pass turns adjacencies into shared faces. It works — the full
DNF realises with **17 of 18** adjacencies recovered as real shared faces by round-tripping
the cell complex back through `Graph.ByTopology`, and 100% on the isolated hard motifs —
but the resulting geometry, while topologically correct, is architecturally arbitrary. A
correct topology does not make a building.

### 6.2 The circulation-first shape grammar
The alternative — and the paper's methodological turn — is to **rebuild the grammar as a
shape grammar whose productions place exact geometry, and derive the graph from what
physically touches**. `add_corridor_spine` and `add_stair_cores` lay the armature; `anchor_K`
(rising), `anchor_F` (dropping), `anchor_box`, `anchor_KF` (the built double-loaded
interlock in one bay) and `anchor_room_behind` dock units onto the corridor at the real
module (bay 3.66 m, floor 3.0 m, unit depth 8.42 m, corridor every three floors). Graph and
geometry are then a single representation that *cannot* diverge, because every edge is a
face that touches.

**Figure 3.** The Narkomfin section as a shape production: corridor band, K rising, F
dropping, and the interlock in one bay — drawn as a rule, alongside a photograph/section of
the built type. *(Needs drawing.)*

### 6.3 The bridge is a reader, not a solver
An abstract derived graph has no bay order, no left/right, and no metric, so realising it is
under-determined. Rather than a general graph→layout solver, the bridge **reads the
proposal into the shape grammar's own vocabulary**: corridors become *bands*, the units each
corridor serves become its *bay pattern* (`u_section`→K, `l_section`→F, generic→B), a P7
interlock becomes a same-bay front/back pair (D), and a room the graph grew off another room
becomes a bay with a room banked behind it (R). Bay order is a free choice made canonically
(most-remaining-first, avoiding repeats), so equal proposals give equal slabs and
de-duplication stays meaningful.

**Division of labour** (worth stating explicitly as a design principle): the graph grammar
proposes the *programme*; the shape grammar owns the *armature* and the metric section.
Vertical circulation and entry are canonical, so the abstract productions for staircase and
entrance are deliberately excluded from the proposal pool rather than double-counted.

### 6.4 Honest coverage
Everything slab-expressible is realised; everything else is **reported, never silently
dropped or faked**. `report()` returns units proposed / realised / docked (docked = sharing a
real face with the band's corridor), rooms banked, interlocks reinterpreted, and the node
ids the section cannot express. Room chains deeper than one bank remain a stated boundary.

*(This "report coverage, don't inflate it" stance should be argued in the discussion as a
methodological point: generative-design papers routinely report what their system produced
and not what it could not.)*

▣ **Expansion slot E — §6.** Level-2 interiors are currently *graph-level topology only* —
refined units carry no boxes, unlike the slab. SG4 gives interior productions sub-boxes
inside the unit envelope, at which point §6.2's claim ("graph and geometry are one
representation") extends from the block level to the room level and this section gains a
subsection §6.5 plus a second row in Table 5.

---

## 7. Implementing a grammar on a topological carrier

*(~1,000 words. Source: `docs/Topologic_Carrier_Contribution_Briefing.md`, `CLAUDE.md`.
This section is a genuine contribution and reviewers will value it — it is the only
published account we know of measuring a topological kernel against the demands of graph
rewriting.)*

**Decision.** `topologicpy.Graph` is the **sole** carrier; networkx is an escape hatch for
specific algorithms, never a second store. The rationale is §2.2's: one representation.

**Table 3.** Measured carrier behaviours in TopologicPy 0.9.43 and the workaround adopted.

| # | Observed behaviour | Consequence for a grammar | Workaround |
|---|---|---|---|
| 1 | Parallel edges are de-duplicated | No multigraph; opposite-direction pairs collapse | One adjacency per pair; model symmetry as a `bidirectional` flag |
| 2 | Direction is opt-in and inconsistent across API surfaces | Traversal silently ignores direction | All traversal wrapped, direction always supplied explicitly |
| 3 | `SubGraphMatches` has no edge, direction, or attribute matcher | The core of DPO matching is missing | Typed-attributed directed monomorphism implemented in `rules.py` |
| 4 | Reserved dictionary keys are injected | Attribute collisions | Reserved namespace avoided; stripped on serialisation |
| 5 | Vertex object identity is not preserved across operations | Cached references become invalid | Nodes addressed by stable `id` only, never by object or coordinate |
| 6 | `AddEdge` drops edge dictionaries by default | Silent attribute loss | `transferEdgeDictionaries=True` always |
| 7 | Booleans coerce to integers in dictionaries | Round-trip type drift | Coerced back on read |
| 8 | `Graph.Vertices` order is unstable across processes | Non-reproducible serialisation and comparison | Canonical sorted serialisation; comparison by id or isomorphism |
| 9 | `CellComplex.ByCells` returns `None` for disconnected cell sets | Stage-2 failures on multi-block buildings | One complex per face-connected component |
| 10 | `Topology.ExportToOBJ` sporadically raises on unstable vertex ordering | Flaky export in long runs | Reported upstream; observed once in three full-suite runs |

**Argument to make:** these are not defects so much as a *specification of what a
topological kernel owes a rewriting system*: stable identity, explicit direction,
attribute-aware matching, deterministic ordering. The list doubles as a contribution agenda
for TopologicPy.

▣ **Expansion slot F — §7.** SG4 (level-2 geometry) will exercise `CellComplex` at the room
scale inside a unit envelope, which is a stricter test of the kernel than block massing;
expect one or two additional rows in Table 3.

---

## 8. Results

*(~1,800 words. All numbers below are measured from the repository at the stated commit;
none are illustrative.)*

### 8.1 Reproduction of the reference graph
The scripted derivation from `A₀` produces a graph typed-isomorphic to the hand-built
figure-5 graph of Dounas & Jabi (2025): **18 nodes, 18 edges**, two blocks. The reverse
derivation returns `A₀`.

### 8.2 Reversibility and verification
Every tier is verified by an automated suite of **195 tests**, including property tests that
generate random graphs, apply each atomic and composite operation, and assert exact
inversion. *(Table 4 below — a verification table is unusual in an architectural-computing
paper and is a quiet strength; it converts "we implemented it" into "here is what is
checked".)*

**Table 4.** Verification map — formal claim → module → test functions. (167 test functions
expand to **195 collected cases** under parameterisation; the suite runs in ≈4 min against
the pinned carrier.)

| Claim | Module | Tests |
|---|---|---|
| Graph object + well-formedness invariants | `model` | 12 |
| Atomic reversibility (A1–A7) | `atomic` | 11 |
| Composite verbs + inverse sequences | `composite` | 16 |
| DPO matching, NACs, reversible application | `rules` | 11 |
| DNF grammar reproduces fig-5, inverts to `A₀` | `grammar_dnf` | 8 |
| Trace record / replay / invert | `engine` | 6 |
| Hierarchy `REFINE`/`ABSTRACT`, composition | `hierarchy`, `compose` | 8 |
| Stage-2 realisation + shared-face round-trip | `realise` | 19 |
| Generation, validity, parameterisation | `generate`, `validity`, `grammar_params` | 22 |
| Shape grammar + graph→shape bridge | `narkomfin`, `bridge` | 17 |
| Section sub-grammars (level 2) | `grammar_units` | 6 |
| Metrics + design space | `metrics` | 11 |
| Exchange / real-model import | `exchange`, `realmodel`, `topoview` | 20 |
| **Total** | | **167 functions / 195 cases** |

### 8.3 Grounding against the built work
Importing the real Dom Narkomfin model yields **57 spaces, 127 adjacencies, 8 storeys,
≈16,416 m³, one connected component**, with a 73.2 m spine corridor of degree 12. Object
names classify to Σ; adjacency and orientation are derived from real bounding-box geometry;
each node carries measured width, depth, height, volume, and level. Median dimensions per
type give the metric constants the shape grammar uses. This import is also what produced the
domain correction reported in §5.3.

### 8.4 The grammar-driven catalogue
Six distinct, valid variants generated end-to-end at seed 0 — proposed by the abstract graph
grammar, read by the bridge, realised by the shape grammar, filtered by architectural
validity, de-duplicated by typed isomorphism:

**Table 5.** The seed-0 catalogue. *(Measured; `bridge.grammar_catalogue(6, seed=0,
refine=True)`.)*

| v | abstract derivation | bands read off | units prop./real./docked | banked | interlocks | skipped | GFA (m²) | vol (m³) | compact. | m²/unit |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | P1×4 · P3×2 · P6×3 · add-2-L | `BB` / `KFKFKBKRKK` | 13/13/12 | 1 | 0 | 0 | 537.8 | 2660.6 | 0.121 | 41.4 |
| 1 | P1×3 · P3×2 · P6×2 · add-3-U · P7×2 | `KBKDKBKDK` / `R` | 13/13/12 | 1 | 4 | 0 | 517.3 | 2691.5 | 0.156 | 39.8 |
| 2 | P1×2 · P3×2 · P6×2 · add-2-L×2 · add-3-U · P7 | `KBKBKD` / `FKFKFKFB` | 15/15/15 | 0 | 2 | 0 | 635.4 | 3323.0 | 0.220 | 42.4 |
| 3 | P1×4 · P3×3 · P6×2 · add-3-U | `KBKR` / `KBK` / `KBKK` | 12/12/11 | 1 | 0 | 0 | 496.8 | 2629.4 | 0.259 | 41.4 |
| 4 | P1×4 · P3×3 · add-2-L · add-3-U×2 | `FBFB` / `KBKRK` / `KKK` | 13/13/12 | 1 | 0 | 0 | 537.8 | 2845.0 | 0.155 | 41.4 |
| 5 | P1×3 · P3×2 · P6×2 · add-2-L×2 · add-3-U | `KFKFKBKRKKK` / `FBF` | 15/15/14 | 1 | 0 | 0 | 620.0 | 3184.3 | 0.156 | 41.3 |

**The headline result of this table:** across the catalogue, **every proposed unit is
realised, and every realised unit is either docked directly onto a corridor or banked one
room deep behind a unit that is — zero skipped spaces.** Variation comes from the
*derivation space* (which productions fired, at which matches), not from parameter dice;
each variant carries its replayable, invertible derivation, so the abstract proposal and the
built geometry are linked end-to-end.

**Table 6.** Population statistics over N = 60 independent proposals (seeds 0–59, max 10
productions each), answering the "how much of the derivation space is buildable?" question.
*(Measured.)*

| Quantity | Value |
|---|---|
| Proposals generated | 60 |
| Rejected — no corridor to hang a slab on | 0 |
| Rejected — zero units proposed | 0 |
| Rejected — realised slab fails architectural validity | 0 |
| Rejected — typed-isomorphic to an earlier variant | 0 |
| **Accepted into the catalogue** | **60 (100%)** |
| Units proposed / realised | 778 / 778 (100%) |
| Units docked directly onto a corridor | 728 (93.6%) |
| Units banked one room deep behind a docked unit | 50 (6.4%) |
| P7 V-interlocks realised as same-bay D pairs | 80 |
| Spaces the slab section cannot express (reported, not dropped) | 20 (0.33 per variant) |

Metric ranges spanned by the population: **6–20 units**, K:F ratio **0–7**, circulation
depth **1–2**, **3–6 levels**, GFA **225–851 m²**, volume **982–4,340 m³**, footprint
**226–1,581 m²**, compactness **0.10–0.28**, area per unit **37.5–51.2 m²**.

Two observations deserve comment in the text rather than the table. First, **every proposal
that the bridge could read realised into a valid building** — validity is achieved by the
grammar and its application conditions, not by rejection sampling, which is the outcome the
"constraints inside the productions" argument of §9.2 predicts. Second, **no two of the 60
realised slabs were typed-isomorphic**, so at this derivation depth the space is not yet
saturated; we do not claim this holds asymptotically, and the confluence question of §9.3
remains the right way to state it.

**Figure 4.** Three catalogue variants as 3-D massing at real proportions, each with its
derived graph beside it. *(From `topoview.draw_massing`; exports already in
`notebooks/exports/`.)*

### 8.5 Two grammar levels, end-to-end
With refinement enabled, each variant carries a second-level graph in which every K and F
unit has been developed by its section sub-grammar. Measured on the seed-0 catalogue: slabs
of 18–20 nodes refine to **53–75 nodes**, yielding **36–55 interior rooms** (3.0–3.7 rooms
per unit) and **6–7 double-height voids** per variant, and the composed inverse restores the
slab **exactly**.

The pipeline is therefore:
**`A₀` →(graph grammar)→ proposal →(bridge)→ slab →(section sub-grammar)→ unit interiors**,
with every step invertible.

### 8.6 The design space
Nine graph and geometry features per variant (unit count, K:F ratio, circulation depth,
level count, GFA, volume, footprint, compactness, area per unit) are standardised and
embedded in 2-D by classical multidimensional scaling; the reference building is placed by
realising *its* proposal through the same bridge, so it occupies the same metric space as
the variants.

**Figure 5.** The design-space map — each variant a point coloured by a chosen metric, the
Dom Narkomfin reference marked. *(Already rendered:
`notebooks/exports/design_space_map.png`.)*

▣ **Expansion slot G — §8.5–8.6 (the second-largest slot).** Today §8.5 reports interior
*counts*. After SG3 (sub-derivation variability) it reports a **distribution**: one slab
refined into N distinct valid interiors, de-duplicated by typed isomorphism at level 2, with
its own diversity statistics. After SG5 (grounding) it reports a **reproduction result**
paralleling §8.1: the sub-grammar derives the reference K and F unit interiors, verified by
typed isomorphism against the imported unit plans. §8.6's map then becomes **two-level** —
macro coordinates from block metrics, micro coordinates from interior metrics — which is
the natural closing figure of the expanded paper (planned **Figure 8**).

---

## 9. Discussion

*(~1,200 words)*

**9.1 What the two-level pipeline demonstrates.** Not that the system can produce
Narkomfin-like buildings — a parametric script can do that — but that the *same formalism*,
with the *same reversibility guarantee*, operates from block massing down to room adjacency,
and that at every step the geometry is derivable from the graph and the graph from the
geometry.

**9.2 Validity versus diversity.** Unconstrained derivation explores widely but yields
mostly non-buildings; tight constraint yields valid but dull output. We report where the
grammar plus validity predicates sit on that trade-off (§8.4, Table 6) and argue that
placing the constraints *inside* the productions (as NACs) rather than as a post-filter is
what keeps the space both rich and buildable.

**9.3 Confluence and the meaning of "N variants".** Independent productions commute, so many
derivation sequences yield the same graph. De-duplication by typed isomorphism is therefore
not housekeeping but a semantic requirement: without it, a claimed catalogue of 1,000
variants may contain 50 designs. *(Worth a short formal remark and a measurement.)*

**9.4 The reader-not-solver decision, and its cost.** Reading a proposal into the shape
grammar's vocabulary buys exact, buildable geometry at the cost of expressive coverage: room
chains deeper than one bank, and any programme the slab section cannot host, are reported as
outside the realisable set. A general rectangular-dual or constraint-based floor planner
would widen coverage and lose the guarantee that every edge is a built face. We argue the
trade is the right one for a *grammar* — but name it.

**9.5 Limitations.** *(State plainly: the grid massing cannot embed cycles or true
interlocks at the block level; the last DNF adjacency (17/18) fails because the greedy layout
boxes a staircase into an interlock gap; the level-2 interiors carry no geometry yet; the
interior room vocabulary is spec-grounded pending a room-labelled reference; the OBJ path is
best-effort and IFC is the production upgrade; one carrier export is flaky.)*

▣ **Expansion slot H — §9.** The sub-grammar work supplies the paper's answer to the third
research question in the programme — **does independent variation at two levels compose into
coherent buildings, or do cross-level constraints (wet-room stacking, structural bay
alignment, void coherence across an interlocked pair) have to be modelled explicitly?**
That answer becomes §9.6 and is, arguably, the most publishable single finding of the
sub-grammar phase. See `docs/Sub_Grammar_Development_Plan.md` §SG6.

---

## 10. Conclusion

*(~400 words. Restate: topology as the bridge; reversibility as the organising constraint;
hierarchy as the route from massing to room; honest coverage as method. Close on the
two-level pipeline and what it opens — steering and learning over a grammar-generated
corpus.)*

---

## 11. Publication strategy

### 11.1 What can be submitted today
§§1–10 as scaffolded, with the sub-grammar material at its current (minimal but working and
reversible) state, is a complete and defensible paper: the formal framework, the reference
reproduction, the graph→shape bridge, the carrier findings, and a measured catalogue. The
expansion slots are written so that the paper reads as finished without them.

### 11.2 One paper or two?
**Recommended: one paper, expanded.** The two-level claim is what distinguishes this work
from both the shape-grammar and the graph-grammar literature, and a paper that only reaches
the block level makes a weaker version of the same argument. Sub-grammar milestones SG1–SG3
(roughly the first half of the plan) are sufficient to fill slots D, G, and H; SG4–SG6 can
follow in a companion paper on *unit* architecture and cross-level constraints.

**Fallback: two papers.** Paper 1 = framework + bridge + catalogue (this scaffold, submitted
as-is). Paper 2 = "Sub-grammars of the section: two-level reversible refinement", with §5.3
and §8.5 as its core. Choose this if SG5 (grounding against room-labelled unit plans) is
blocked on source material, since without it Paper 2's central reproduction claim cannot be
made.

**Decision gate:** whether a room-labelled reference for the K/F unit interiors can be
obtained or reconstructed (see plan §SG5, Risk R1). This is the single dependency that
determines the shape of the publication.

---

## 12. Figure and table manifest

| # | Item | Status | Source |
|---|---|---|---|
| Fig 1 | Three tiers: production → verb → atomics | to draw | — |
| Fig 2 | `A₀ →* G_DNF` derivation grid | ✅ generated | `topoview.record_frames`/`draw_grid` |
| Fig 3 | The Narkomfin section as a shape production | to draw | — |
| Fig 4 | Catalogue variants as 3-D massing + graphs | ✅ generated | `topoview.draw_massing`, `notebooks/exports/` |
| Fig 5 | The design-space map with the reference marked | ✅ generated | `notebooks/exports/design_space_map.png` |
| Fig 6 | Real-model import: 57 spaces, adjacency graph | partial | `exchange.graph_from_model` |
| Fig 7 | ▣ "One slab, many interiors" | planned (SG3) | — |
| Fig 8 | ▣ Two-level design space (macro × micro) | planned (SG7) | — |
| Tab 1 | Alphabets Σ, Θ | lift from spec | — |
| Tab 2 | Production catalogue P1–P8 | lift from spec | — |
| Tab 3 | Carrier behaviours and workarounds | ✅ drafted here | briefing note |
| Tab 4 | Verification map | ✅ measured | test suite |
| Tab 5 | Seed-0 catalogue | ✅ measured | `bridge.grammar_catalogue` |
| Tab 6 | Population statistics over 60 proposals | ✅ measured | `scratchpad/pop.json` |
| Tab 7 | ▣ Interior sub-alphabet + production catalogue | planned (SG1–SG2) | — |

## 13. Reproducibility statement

*(Short subsection — increasingly expected, and cheap for us: the repository, the pinned
carrier version, the seeds, the test suite, and the exact calls that generate every table
and figure. Include a one-page appendix listing them.)*

---

## 14. References *(working list — verify all page numbers and years before submission)*

- Dounas, T. & Jabi, W. (2025). *Towards Bridging Shape and Graph Grammars Through
  Topology.* Proceedings of eCAADe 43, Vol. 1, pp. 663–672.
- Stiny, G. (1980). Introduction to shape and shape grammars. *Environment and Planning B*,
  7(3), 343–351.
- Stiny, G. & Mitchell, W.J. (1978). The Palladian grammar. *Environment and Planning B*,
  5(1), 5–18.
- Ehrig, H., Ehrig, K., Prange, U. & Taentzer, G. (2006). *Fundamentals of Algebraic Graph
  Transformation.* Springer.
- Rozenberg, G. (ed.) (1997). *Handbook of Graph Grammars and Computing by Graph
  Transformation, Vol. 1.* World Scientific.
- Grasl, T. & Economou, A. (2013). From topologies to shapes: parametric shape grammars
  implemented by graphs. *Environment and Planning B*, 40(5), 905–922. [verify]
- Duarte, J.P. (2005). Towards the mass customization of housing: the grammar of Siza's
  houses at Malagueira. *Environment and Planning B*, 32(3), 347–380. [verify]
- Eloy, S. & Duarte, J.P. (2011/2015). A transformation grammar for housing rehabilitation.
  [verify venue/year]
- Heitor, T., Duarte, J.P. & Pinto, R. (2004). Combining grammars and space syntax.
  [verify venue]
- Hillier, B. & Hanson, J. (1984). *The Social Logic of Space.* Cambridge University Press.
- Steadman, P. (1983). *Architectural Morphology.* Pion. [verify]
- Jabi, W., Aish, R., Lannon, S., Chatzivasileiadi, A. & Wardhana, N.M. (2018). Topologic: tools
  to explore architectural topology. *Advances in Architectural Geometry.* [verify]
- Jabi, W. (2024/2025). *TopologicPy* (software). Zenodo. https://doi.org/10.5281/zenodo.11555172
- Alymani, A., Jabi, W. & Corcoran, P. (2023). Graph machine learning classification using
  architectural 3D topological models. *SIMULATION.* [verify]
- Nauata, N., Chang, K.-H., Cheng, C.-Y., Mori, G. & Furukawa, Y. (2020). House-GAN:
  relational generative adversarial networks for graph-constrained house layout generation.
  *ECCV.*
- Merrell, P., Schkufza, E. & Koltun, V. (2010). Computer-generated residential building
  layouts. *ACM TOG (SIGGRAPH Asia).*
- Ginzburg, M. (1934). *Zhilishche* [Dwelling]. Moscow. [verify]
- Buchli, V. (1998). Moisei Ginzburg's Narkomfin Communal House in Moscow. *Journal of
  Design History*, 11(2). [verify]
- Cooke, C. (1995). *Russian Avant-Garde: Theories of Art, Architecture and the City.*
  Academy Editions. [verify]

*(To add during writing: a citation for the Stroikom unit-type research programme; one for
architectural graph-grammar work in the eCAADe/CAADRIA proceedings of the last five years to
position the contribution; and — for §9.3 — a confluence/critical-pair reference from the
graph-transformation literature.)*
