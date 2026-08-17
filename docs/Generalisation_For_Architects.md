# From a Building to a Grammar — the generalisation, step by step

**Audience:** architects · **Grounded on:** the Dom Narkomfin case study
(graphtope, Stage 1 + the sub-grammar phase SG0–SG8) · **Date:** 2026-08-15

---

## 1. What you get, in one page

You hand over a building — a BIM model, a clean survey mesh, a drawn massing
— in which the spaces are *named or typeable* (living, corridor, bath…, or
at least apartment / circulation / service). In return you get four things:

1. **The building's graph.** Every space a node; every shared wall, party
   wall or slab an adjacency edge; every room type recorded; every real
   dimension (bay width, room depth, section height) measured from the model
   and kept. This graph *is* the building in its most compressed,
   queryable form — "which rooms lack daylight", "how deep is the plan from
   the corridor", "do the bathrooms stack" are one-line questions on it.
2. **A grammar that re-derives the building.** A set of rules, read off the
   building's recurring patterns, that start from a minimal armature (say:
   a corridor and one dwelling placeholder) and rebuild the building you
   handed over — room for room, wall for wall — and can then be run
   *differently* to produce the building's siblings: the variants the same
   language permits but the architect did not draw.
3. **A measured design space.** Every variant the grammar can make is
   measured — daylight, privacy, circulation depth, compactness, wet-room
   stacking — and placed on a map where the original building is one point
   among its possible family.
4. **A steering instrument.** Objectives over that map: "maximum daylight,
   bathrooms stacked, at this density" — and the search finds, among the
   grammar's own productions, the variants that meet them.

Everything is reversible. Every rule can be undone exactly, so any variant
can be traced back, step by step, to the armature it came from — and any
step of any derivation can be replayed. This is not an aesthetic claim; it
is the system's bookkeeping, and it is what makes the grammar *auditable*.

The Dom Narkomfin case produced exactly this: a 31-rule interior grammar
that re-derives the reference dwelling units room-for-room, generates
distinct valid interiors per slab (24–33 rooms across six samples), places
every room as real geometry that tiles the dwelling envelope, exports to
Blender, and is steered by measurable objectives.

---

## 2. Two grammars, one representation

The system speaks both of architecture's rule languages natively.

**The shape grammar nature.** In a classic shape grammar (Stiny), a rule
redraws geometry: *replace this shape with that shape*. Our block-level
rules do exactly this — but each rule folds its exact real-metre geometry
into the drawing itself. "Anchor a K-type maisonette on the corridor" adds
not an abstract node but a 3.66 m bay, 8.42 m deep, 8.0 m tall, rising from
the corridor level — the true Narkomfin section. Two spaces are adjacent
*if and only if* their boxes share a face. The geometry is never a
rendering of the graph; **the geometry is the graph's truth condition**.

**The graph grammar nature.** In a graph grammar, a rule rewrites a typed,
attributed graph. Our interior rules do exactly this: "attach a bathroom to
the sleeping gallery", "interpose a door in this wall" (a rule that
*genuinely deletes* the direct adjacency and joins the two rooms through
the door node — the wall gets a thickness and a leaf), "give every
habitable room one window". Types (living, kitchen, bath…), directions
(above / beside), attributes (double-height, niche vs. room) all
participate in matching, and each rule carries its **prohibitions** — the
grammar's planning bylaws: *at most one entrance per block*, *one window
per room*, *a paired K may only take the partial void, because the F behind
it claims the back of the bay*.

The two natures meet on one principle, used throughout:

> **An adjacency is a shared face.** If two spaces touch, there is an edge;
> if there is an edge, the geometry must show the touch. Every exported
> variant is machine-checked against this — every wall the graph claims is
> a wall the boxes share.

This is why the results can be tested in Blender: what the grammar asserts,
the geometry shows, and what the geometry shows, the validator checks.

---

## 3. The dictionary — architecture and the grammar, side by side

| architectural concept | in the grammar | notes |
|---|---|---|
| a space (room, corridor, stair) | a **typed node** | type = its room kind; dimensions carried as attributes |
| a shared wall / slab | an **adjacency edge** | must be a real shared face |
| "above" vs. "beside" | the edge's **direction** | vertical adjacency points downwards |
| the room programme | the **type alphabet** | an open registry: new room kinds are added by registering them |
| a door | an **opening node** *between* two spaces | inserting it deletes the direct adjacency — the wall becomes passable |
| a window | an opening node *on* one space | one per room; habitable rooms require one (daylight check arms itself) |
| a party wall, a riser alignment | a **cross-level constraint** | checked, counted, steered |
| a planning bylaw ("one entrance per block") | a **prohibition (NAC)** on a rule | the rule cannot fire where the bylaw is already satisfied or violated |
| the building section (split level, gallery) | level attributes + placement recipes | the gallery really sits over the living volume, at its measured 1.7 m |
| a derivation (the design history) | a recorded, **reversible** sequence | replayable; invertible back to the armature |

---

## 4. The process, step by step

The generalisation is a pipeline of nine steps. Steps 1–4 turn *a building*
into *a grammar*; steps 5–8 turn the grammar into *a design instrument*;
step 9 is the research horizon. Each step has a worked precedent in the
Narkomfin case — the bracketed notes are what actually happened there.

### Step 0 · Bring a model

What is needed: a model whose spaces are individually addressable — an IFC
with space types (the natural fit), an OBJ with named objects, or a
Topologic `CellComplex` built in the Modelling bundle. Non-space structure
(slabs, columns, beams) is recognised and skipped. Naming does not have to
be perfect; a classifier maps common naming to the room registry, and
unrecognised spaces still import (typed as generic) rather than being lost.

*[Narkomfin: three named OBJ models — the whole building, a full grammar
catalogue, and the realised unit envelopes — imported with actual sizes:
57 spaces, 127 adjacencies, the 73.2 m corridor spine, the 3.66 m bay
measured, not assumed.]*

### Step 1 · Read the building as a graph

Spaces become nodes; shared faces become edges; the face's normal says
*above* or *beside*; the model's names or types say what each space is; the
geometry is measured (typical room dimensions per type — the median
bathroom, the standard bay). The result is the building's graph **with its
real dimensions attached** — the ground truth every later rule will quote.

Honesty rule: if the source carries no room names (our unit envelopes were
like this), the *structure* imports but the vocabulary waits — dimensions
can be measured, room kinds cannot. Say so; do not guess.

### Step 2 · Find the recurring motifs

A grammar's rules are the building's habits. Systematically:

- **repeated patterns** — the same configuration appearing in many places
  (every K unit entered off the corridor, rising past it; every bathroom on
  the gallery level) are rule candidates;
- **invariants** — what never varies (the corridor every third floor; one
  bay per dwelling; the gallery always over the living volume) become the
  armature or prohibitions;
- **alternates** — where the building itself varies (kitchen as niche here,
  as a room there; void partial in one unit, full-width in another), each
  observed variant is one setting of one rule.

This step can be done by expert reading (as in the case study) or, in the
research extension, by mining a *corpus* of buildings — see Step 9.

### Step 3 · Turn motifs into rules

Each rule is written as three drawings — before, kept, after:

- **before (L):** the situation the rule needs — e.g. *a sleeping gallery
  directly above a living volume*;
- **kept (K):** what survives untouched — the two rooms themselves;
- **after (R):** what is added or removed — *a double-height void above the
  living volume, opening onto the gallery*.

Plus its **prohibitions**: this rule may not fire twice on one living
volume; that rule may not add a second entrance to a block already served.
Prohibitions are where the building's planning discipline lives, and they
are checked *before* any geometry moves — an illegal rule application is
refused, not repaired.

Two rule families matter architecturally:

- **Structural rules** (the shape-grammar nature): anchor a unit on the
  corridor with its exact section; place the stair strip; carve the gallery.
  These *place geometry* — metres, not symbols.
- **Infrastructural rules** (the graph-grammar nature): interpose a door;
  add a window; attach a wet room to its host. These *rewire adjacency* and
  carry the bylaws.

*[Narkomfin: 31 interior productions across five dwelling families — the
rising K maisonette, the dropping F, the single-storey apartment, the
double-loaded pair sharing one bay, the room banked behind its host — plus
12 opening rules.]*

### Step 4 · The reproduction test — the grammar must re-derive the building

The single most important check in the method: start from the armature,
run the rules, and require that the building you started with comes back —
the same rooms, the same adjacencies, the same types (compared as graphs,
so furniture and wall finishes rightly do not matter) — and that running
the derivation *backwards* returns the armature exactly.

If the grammar cannot reproduce its own source, it is not a grammar of that
building yet — it is a sketch. Failures are informative: each missing room
names a rule that has not been written.

*[Narkomfin: the interior grammar re-derives the reference K and F units
room-for-room, and the whole-building grammar reproduces the published
figure-5 graph from a two-block axiom. Where no room-labelled survey
existed, the reference was redrawn from the published section and the
provenance stated — weaker evidence, honestly labelled, still a
reproduction.]*

### Step 5 · Vary — the building's siblings

A grammar that can only rebuild its source has archived it. Run the rules
with different choices at each match — kitchen as niche or room, void
partial or full, bath at gallery or entry, doors and windows where the
bylaws allow — and the building's *family* appears: all the dwellings the
same language permits. Duplicates are removed automatically (variants are
compared as typed graphs, so only genuinely different plans count), and
every variant still satisfies the interior bylaws (reachability from the
entry, daylight wherever windows exist, openings of the right valence).

*[Narkomfin: one slab of five dwellings yields interiors spanning 24–33
rooms across six sampled variants — distinct, valid, each traceable and
invertible back to the slab.]*

### Step 6 · Place the rooms

Each interior is then *built*: rooms become boxes inside the dwelling
envelope, placed by deterministic recipes that respect the section — the
gallery above the living volume at its measured width, the stair as a
full-height strip, wet rooms stacked where the plumbing runs, doors centred
in the walls they open, windows on façade faces. The checks of Step 4's
principle apply now at room scale: rooms tile the envelope without gaps or
overlaps, and every adjacency the graph claims is a face the boxes share.

Where a configuration cannot be realised geometrically (a dwelling squeezed
between two neighbours cannot keep both party-wall contacts on its living
room), the miss is **reported, never faked** — the honest coverage number.

### Step 7 · Validate, in your tools

The placed variants export as OBJ + a sidecar carrying the graph, and one
validator runs over those files everywhere: in the test suite, in the
Jupyter notebooks, and inside Blender itself (headless for the pipeline,
interactively for design review). Three families of checks: *integrity*
(every space present, none invented), *tiling* (no overlaps, no gaps),
*adjacency* (every graph wall is a real shared face; every door sits in its
wall plane). A designer who edits the model in Blender and exports back
gets the same validation on their edit — the grammar's guarantees travel
with the artefacts.

### Step 8 · Measure and steer

The family from Step 5 is measured — at building scale (density,
compactness, circulation depth, units), at dwelling scale (privacy
gradient, daylight ratio, wet-core clustering, programme mix), and across
scales (do the bathrooms stack? do partitions align with the load path?) —
and laid out on a map where the original building is one point among its
siblings. Objectives then *steer*: the search samples the family and keeps
the variants that meet the brief ("every habitable room lit, wet rooms
stacked, this density") — with unrealisable candidates refused before they
are ever scored. In the case study, independent sampling violated
wet-stacking in a quarter of interiors; **the steered picks never did**.

### Step 9 · The horizon: induction from a corpus

Steps 2–3 were done by expert reading. The research generalisation does
them *statistically*: given many buildings, recurring motifs are mined,
each motif plus its neighbourhood difference becomes a rule candidate, and
prohibitions are learned from configurations that never occur. The
reproduction test (Step 4) generalises into a **coverage score** — what
fraction of the corpus the induced grammar can re-derive — and, split
against held-out buildings, a **generalisation score**: did the grammar
learn the language, or memorise the texts?

---

## 5. How many manipulations can be found, systematically?

The honest answer is a layered enumeration — each layer systematic in its
own way.

**Spaces and volumes.** For each dwelling family, the alternates the
building itself exhibits multiply out. The Narkomfin K unit, fully
parameterised: void (none / partial / full) × kitchen (niche / room) × bath
level (gallery / entry) × wc × loggia × storage × gallery subdivision —
**192 declared interiors** before openings; the F unit 32; the apartment 4;
the banked room 2. Pruned by prohibitions, bylaws and duplicate removal,
this is the family Step 5 samples. For an imported building, the same
product is *read off the corpus* — the alternates are observed, not
declared.

**Openings.** Fully enumerable: one candidate door per wall shared by two
spaces; one candidate window per habitable room per façade face. A
building with *w* internal walls and *r* rooms has O(w + r) opening
manipulations — small, complete, each checkable in geometry.

**Internal walls — the honest boundary.** Adding a wall and removing a wall
are graph operations (a split, a merge). But *moving* a wall 300 mm
changes no adjacency and no room type — only dimensions — and so is
invisible to the graph until the shift makes two spaces touch (or stop
touching). This is not a defect to fix but a property to state: **the
grammar is the discrete skeleton of the design space; dimensions are the
continuous flesh on each bone.** Dimension ranges travel as attributes
(the placement recipes already quote measured ranges), and a shift crosses
into the grammar exactly when it changes a relationship.

---

## 6. The contract — what the architect gives, what the system guarantees

**Give:** a model with addressable, typeable spaces; ideally measured, not
schematic. Better inputs buy better ground truth; imperfect inputs buy
honest partials, never silent guesses.

**Guaranteed:** the graph is the building (adjacency = shared face,
machine-checked); the grammar re-derives its source or reports what is
missing; every derivation is reversible and replayable; every bylaw is
enforced before geometry moves; every placement tiles or is reported;
every export validates in your tools; every measurement is deterministic.

**Not claimed:** taste. The grammar generates the *language's* space, not
the architect's judgement — it makes the family legible and steerable, and
leaves the choosing to you. That is the instrument's point.

---

## 7. Limitations, stated

- Non-box spaces (the L- and U-section profiles aside) are approximated by
  their bounding boxes at import; the topology is exact, the metric
  attributes are envelopes.
- Access *direction* (who enters whom, where a one-way corridor-served
  relation exists) cannot be read from geometry — a shared wall has no
  arrow — so it travels in the sidecar, exactly as IFC would carry it.
- The carrier library (TopologicPy) has known fragilities on complex
  imports; the pipeline is defensive (per-component assembly, canonical
  ids) and failures are surfaced, not swallowed.
- Where references were reconstructed rather than measured, that is said in
  the artefact itself.

---

## 8. Glossary

- **Typed node / edge** — a graph element carrying its kind (living, bath;
  beside, above) and attributes (dimensions, levels).
- **Rule (production)** — a before/kept/after rewrite on the graph, plus
  prohibitions; reversible.
- **Prohibition (NAC)** — a pattern that, if present, blocks the rule:
  the grammar's planning bylaw.
- **Derivation** — the recorded sequence of rule applications from the
  armature to a building; runs backwards exactly.
- **Reproduction test** — requiring the grammar to re-derive its source
  building, verified as a graph comparison.
- **Design space** — the measured family of variants, laid out on a map;
  the original building is one point in it.
- **Steering** — searching that family by objectives, with unrealisable
  candidates refused before scoring.
- **Coverage** — the fraction of a corpus a grammar can re-derive; with
  held-out buildings, the generalisation score.

---

*The through-line of the method is simple to state: **a building is
evidence of its own language.** Read carefully, the evidence yields rules;
the rules yield the family; the family, measured and steered, returns to
the architect as an instrument — one that never forgets where it came
from, because every step back to the source remains walkable.*
