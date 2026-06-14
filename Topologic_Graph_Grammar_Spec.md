# Topologic Graph Grammar — Specification

**Version 0.2 — Stage 1 (pure graph level; geometry deferred)**
Authors: T. Dounas, W. Jabi · Reference case: Dom Narkomfin (DNF)

---

## 0. Status, scope, and provenance

This document specifies a **typed, directed, weighted, attributed graph grammar**
for architectural space-adjacency graphs. It is **Stage 1**: the grammar is
defined and operates entirely at the **graph level**. No geometry, no shapes, no
coordinates. The attachment of shapes (objects, lines, rectangles, volumes) is
**Stage 2** and is only previewed here, in §9, as the single bridging rule that
Stage 1 already determines.

The grammar is grounded in three sources, read together:

1. **Dounas & Jabi (2025)**, *Towards bridging shape and graph grammars through
   topology* (eCAADe 43, pp. 663–672) — the Topologic Grammar method, the basic
   operations, and the matching machinery.
2. **The figures**: the *Rule Application Process* flowchart (operation
   taxonomy), *figure 4* (the two graph representations), and *figure 5* (the
   typed DNF graph development, Steps 1–3, with its node-type legend).
3. **The source model** (`...Dom_Narkomfin__Full_Grammar_development.blend`) —
   the actual named spaces, which fix the semantic vocabulary (Appendix A).

Two graphs are present in the source material (figure 4): a **dense extracted
graph** (every topological element a node, shared topologies the edges; produced
by `Graph.ByTopology` over the full cell complex) and a **simpler direct graph**
(spaces as nodes, adjacency as edges — the dual). **This grammar rewrites the
direct/dual graph.** The dense graph is a derived view and is out of scope for
the productions.

### Changes in v0.2

This revision folds in four decisions and opens two for your choice:

- **§7.6 (new)** — `u_section` and `l_section` become **non-terminals**, each
  refined by its own **sub-grammar** that develops the unit's architecture
  (decision on item 4); blocks are developed as **separate grammars** and joined
  by the inter-block **bridge as a composition step** that enters only after all
  block graphs are complete (decision on item 6).
- **§12.1 (new)** — differential options for how nodes carry **properties**
  (spaces, walls, windows, energy performance, thickness), for you to weigh.
- **§12.2 (new)** — differential options for **levels and the building–ground
  relationship**: explicit labelling vs. ML-inference after Alymani & Jabi (2024).
- The full **NAC** catalogue (item 5) is **deferred to the sub-grammar stage**,
  as agreed.

Three independent layerings appear below and should not be conflated:
**Stage** (1 = graph, 2 = shape); **Tier** (0 atomic → 1 core verbs → 2 named
productions, by composition); and **Hierarchy** (building → block → section, by
architectural decomposition).

---

## 1. Design principles (the four resolved decisions)

The formalism follows four decisions taken explicitly:

- **D-I — One reversible, oriented adjacency relation.** Horizontal and vertical
  adjacency are two *orientations* of a single adjacency relation produced by a
  single operation. That operation is **reversible**: the inverse of subdividing
  one space into two adjacent spaces is **merging** two adjacent spaces into one.
- **D-II — Directed and weighted.** Edges carry a direction and a non-negative
  weight. Adjacency is represented directionally; symmetry, where present, is an
  explicit property, not an absence of direction.
- **D-III — Generic nodes, semantic labels.** At the graph level every node is a
  generic node carrying a **semantic label** (an attribute), e.g. a node *with* a
  `u_section` or `l_section` label — not a node *of class* U. At the shape level
  those labels **translate to shape types**. That translation is itself a rule
  (§9): it is the first thing Stage 2 inherits from Stage 1.
- **D-IV — Minimal atomic operations, compounding upward.** A small, complete set
  of **atomic** graph operations (§4) compose into **core composite operations**
  (the six generic operations, §5), which compose into **named productions** (the
  DNF grammar, §7). Three tiers, each built from the one below.

---

## 2. The graph object

### 2.1 Definition

A **state graph** is a tuple

```
G = (N, E, src, tgt, λN, λE, ω, αN, αE)
```

where

| Symbol | Type | Meaning |
|---|---|---|
| `N` | finite set | nodes (spaces); all structurally generic |
| `E` | finite set | directed edges |
| `src, tgt` | `E → N` | source and target of each edge |
| `λN` | `N → Σ` | node semantic label (§3.1) |
| `λE` | `E → Θ` | edge type (§3.2) |
| `ω` | `E → ℝ≥0` | edge weight (default `1.0`) |
| `αN` | `N → Dict` | node attribute dictionary (extensible) |
| `αE` | `E → Dict` | edge attribute dictionary (extensible) |

The structure is a **typed attributed directed multigraph**: parallel edges are
permitted (e.g. an `adjacency` edge and an `access` attribute carried separately),
and edges are directed. `αN`/`αE` mirror Topologic's `Dictionary` mechanism and
hold anything not yet promoted to a first-class field (level index, orientation
of the host space, provisional area, ML features, …).

### 2.2 Well-formedness invariants

A state graph is **well-formed** iff:

1. `src(e), tgt(e) ∈ N` for every `e ∈ E` (no dangling edges).
2. `λN(n) ∈ Σ` for every `n` (every node carries a known label; default `generic`).
3. `λE(e) ∈ Θ` and `ω(e) ≥ 0` for every `e`.
4. No self-loops: `src(e) ≠ tgt(e)` (a space is not adjacent to itself).
5. Adjacency orientation is consistent: an `adjacency` edge has
   `αE[e].orientation ∈ {H, V}` (§3.2).

Every operation in §4–§7 **preserves well-formedness**; this is the core
invariant the implementation must check (§11).

---

## 3. Alphabets

### 3.1 Node-label alphabet Σ

Every node is generic; `λN` assigns one **semantic label** from Σ. The label is an
attribute, matched on, and (Stage 2) translated to a shape type.

| Label | Short | Legend colour (fig. 5) | Role |
|---|---|---|---|
| `generic` | g | black | undifferentiated parallelepiped space |
| `corridor` | c | orange | horizontal-circulation space |
| `staircase` | s | green | vertical-circulation space |
| `u_section` | u | blue | space whose **section** is U-shaped (split-level unit) |
| `l_section` | l | cyan | space whose **section** is L-shaped (interlocking unit) |
| `entrance` | e | (black) | ground-floor entrance space |

Σ is **open**: finer sub-labels are carried in `αN["subtype"]` rather than
expanding Σ (e.g. `subtype = "toilet"`, `"lobby"`, `"balcony"`,
`"condenser_main"`). Matching may test either the label or the subtype.
Appendix A maps every label and subtype to the real spaces in the model.

**Terminals and non-terminals.** Σ partitions into **terminal** labels —
`generic`, `corridor`, `staircase`, `entrance` — which are final at the
space-adjacency level, and **non-terminal** labels — `u_section`, `l_section` —
which are *placeholders* for a unit whose internal architecture is developed by a
dedicated **sub-grammar** (§7.6). A graph is **fully refined** when it contains no
non-terminals; refinement may also be deliberately deferred, leaving a unit as an
abstract node. Matching (§6.2) may target either kind, and the matcher exposes a
`is_fully_refined(G)` predicate.

### 3.2 Edge-type alphabet Θ

| Type | Direction meaning | Attributes |
|---|---|---|
| `adjacency` | see below | `orientation ∈ {H, V}`, `bidirectional ∈ {true,false}` |

There is **one** edge type, `adjacency`, per D-I. Its **orientation** distinguishes
horizontal from vertical adjacency; its **direction** and `bidirectional` flag
carry D-II:

- **Vertical (`orientation = V`)**: a directed edge `a → b` means *a is directly
  above b* (a's floor is b's ceiling). The relation is inherently ordered, so
  `bidirectional = false` and direction is canonical (above → below).
- **Horizontal (`orientation = H`)**: a directed edge `a → b` means *spaces a and
  b share a vertical boundary, with access oriented a → b*. Plain mutual adjacency
  sets `bidirectional = true`; a one-way relation (e.g. an `entrance` that admits
  inward only) sets `bidirectional = false`.

**Weight** `ω(e) ∈ ℝ≥0` (default `1.0`) is a general-purpose magnitude for the
relation — provisionally the strength/permeability of the connection or the
extent of shared boundary, and the carrier for edge features in later graph-ML
use. Its precise semantics are an open item (§12); the grammar only requires that
it be non-negative and preserved/maintained by operations.

> **A future second edge type** (`circulation_link`, a non-adjacent connection
> mediated by a corridor or stair) is anticipated but **not** introduced in v0.1:
> in the DNF grammar, circulation is carried by *typed nodes* (`corridor`,
> `staircase`) bridged by ordinary `adjacency` edges, exactly as in figure 5.

---

## 4. Tier 0 — atomic operations (minimal, reversible)

The complete primitive basis. Every operation states a **precondition**, an
**effect**, and its **inverse**. Reversibility (D-I) is a property of the whole
basis: each atomic has an atomic inverse, so any derivation can be run backward.

| # | Operation | Signature | Precondition | Effect | Inverse |
|---|---|---|---|---|---|
| A1 | **add-node** | `+N(λ, α)` | — | new isolated node, label `λ`, attrs `α` | A2 |
| A2 | **del-node** | `−N(n)` | `deg(n)=0` | remove isolated node `n` | A1 |
| A3 | **add-edge** | `+E(a→b, θ, o, w)` | `a,b ∈ N`, edge absent | new edge `a→b`, type `θ`, orientation `o`, weight `w` | A4 |
| A4 | **del-edge** | `−E(e)` | `e ∈ E` | remove edge `e` | A3 |
| A5 | **relabel** | `ρ(n, λ→λ′)` | `λN(n)=λ` | set `λN(n)=λ′` | `ρ(n, λ′→λ)` |
| A6 | **reweight** | `ω̂(e, w→w′)` | `ω(e)=w` | set `ω(e)=w′` | `ω̂(e, w′→w)` |
| A7 | **reverse-edge** | `↔(e)` | `e ∈ E` | swap `src(e), tgt(e)` | `↔(e)` (self-inverse) |

These seven are sufficient: every operation in §5–§7 expands to a finite sequence
of A1–A7. The implementation realises A1–A7 directly and defines everything else
by composition (§11). Reversibility here is **operation-level**; exact round-trips
to an identical graph additionally require the derivation trace (see the note in
§5.1).

---

## 5. Tier 1 — core composite operations (the six generic operations)

The *Rule Application Process* flowchart enumerates exactly six operation verbs:
**Replace, Transform, Union, Difference, Divide, Other**. Each is defined here as
a recipe over Tier 0, with its inverse. Two of them — **Divide/Split** and
**Union/Merge** — are the reversible pair at the heart of D-I and are specified in
full; the rest are given as recipes.

### 5.1 SPLIT (the Divide primitive) and MERGE (its inverse)

These are the architecturally fundamental inverse pair.

**`SPLIT(n, o, π)`** — divide one space into two adjacent spaces.
- Parameters: node `n`; new-adjacency orientation `o ∈ {H,V}`; an **embedding map**
  `π` partitioning `n`'s incident edges into `(E₁, E₂)` (which inherited edge goes
  to which child). For `o = V`, `π` also designates which child is the **upper**
  one, so the new edge's above→below direction is fixed; for `o = H` the new edge is
  `bidirectional = true` by default.
- Expansion (Tier 0):
  1. `n₁ ← +N(λN(n), αN(n))`; `n₂ ← +N(λN(n), αN(n))` *(children inherit label/attrs)*
  2. for each `e ∈ E₁`: re-attach `e`'s `n`-endpoint to `n₁` (`+E` copy with same
     `θ,o,w`, then `−E(e)`); for each `e ∈ E₂`: likewise to `n₂`
  3. add the new shared-boundary edge: `+E(upper→lower, adjacency, V, 1.0)` if
     `o = V`; else `+E(n₁→n₂, adjacency, H, 1.0)` with `bidirectional = true`
  4. `−N(n)`
- Postcondition: `n₁ —[adjacency,o]→ n₂`; external context redistributed per `π`.
- **Inverse: `MERGE(n₁, n₂)`.**

**`MERGE(n₁, n₂)`** — fuse two adjacent spaces into one (D-I: "two adjacent
spaces could become one").
- Precondition: an `adjacency` edge exists between `n₁` and `n₂`.
- Parameters: a **label-resolution policy** `ζ` (default: if `λN(n₁)=λN(n₂)` keep
  it, else require an explicit resulting label) and a **weight-merge policy** `ξ`
  for parallel edges (default `max`).
- Expansion (Tier 0):
  1. `n ← +N(ζ(λN(n₁), λN(n₂)), αN(n₁) ⊕ αN(n₂))`
  2. for each external incident edge of `n₁` or `n₂`: re-attach to `n`; coalesce
     duplicates under `ξ`
  3. `−E(adjacency edge n₁–n₂)`; `−N(n₁)`; `−N(n₂)`
- **Inverse: `SPLIT(n, o, π)`** recovering the partition.

`SPLIT` and `MERGE` are mutually inverse: `MERGE ∘ SPLIT = id` (with `π` recorded),
`SPLIT ∘ MERGE = id` (with the partition recovered from the merge record).

> **Two senses of reversibility.** Every operation has an **inverse operation**
> (operation-level reversibility — A1↔A2, A3↔A4, `SPLIT`↔`MERGE`,
> `REFINE`↔`ABSTRACT`), so a graph can always be taken apart by inverse moves. An
> **exact round-trip** to the *identical* graph — recovering `π`, the pre-merge
> labels, and the apportioned weights — additionally requires the **derivation
> trace** (§10.2) to have recorded the forward step. Structural reversibility is a
> property of the operation set; exact invertibility is a property of a *recorded
> derivation*. The package guarantees the first unconditionally and the second
> whenever the trace is kept.

### 5.2 The remaining four verbs

| Verb | Graph meaning | Expansion / dispatch | Inverse |
|---|---|---|---|
| **DIVIDE** `(n → c₁…cₖ)` | partition a space into `k` cells | `(k−1)` chained `SPLIT`s | `(k−1)` `MERGE`s |
| **UNION** `(a ⊕ b)` | Boolean join of two volumes | **dispatch:** if the result is *one* space → `MERGE(a,b)`; if *two* spaces now sharing a boundary → `+E(a→b, adjacency, o, w)` | `MERGE`→`SPLIT`; `+E`→`−E` |
| **DIFFERENCE** `(a ⊖ b)` | carve `b` from `a` | **dispatch:** carved space is itself a room → `+N(void) ; +E(a→void)`; carve disconnects `a` → `SPLIT(a,…)`; carve only reshapes a boundary → no graph change (Stage 2 geometry only) | `−N`/`−E`; `MERGE` |
| **REPLACE** `(L ⇒ R)` | substitute a matched subgraph | general DPO application (§6) — the most general verb; all others are special cases | `R ⇒ L` |
| **TRANSFORM** `(τ)` | isometry on a subshape | rigid motion → **identity on the graph**; **reflection (mirror)** → duplicate a subgraph (`MIRROR`, §5.3) | identity; remove the mirror copy |
| **OTHER** | extensible | e.g. `relabel` (A5) to assign semantics; attach a pendant `aperture`/`content` node (`+N ; +E`) | A5 inverse; `−E`/`−N` |

### 5.3 MIRROR (the Transform-by-reflection operation)

The paper flags the **mirror technique** — *driving the shape grammar by extending
the graph grammar* — as untested. It is a graph operation and is defined here:

**`MIRROR(S, seam)`** where `S ⊆ N` is a subgraph and `seam ⊆ S` are its contact
nodes.
1. For each `v ∈ S`: `v′ ← +N(λN(v), αN(v))` *(a fresh labelled copy)*.
2. For each edge of `S`: add the corresponding edge among the copies (same
   `θ,o,w`; orientation/direction reflected for `H` access).
3. For each `v ∈ seam`: `+E(v → v′, adjacency, o_seam, w)` *(stitch the copy to the
   original along the mirror plane)*.
- **Inverse:** delete the mirror copy `S′` and its stitch edges.

`MIRROR` lets a unit (a maisonette section, a bay cluster) be reflected to build a
symmetric whole — the operation the DNF paper leaves open.

---

## 6. Rule formalism (writing and applying productions)

### 6.1 Productions as DPO spans

A **production** is a span of typed attributed directed graphs

```
p : L ⊇ K ⊆ R
```

- `L` — the **left pattern** (what must be present),
- `K` — the **interface / gluing** (what is preserved: the context the new
  material attaches to),
- `R` — the **right pattern** (what replaces `L`).

Applying `p` at a **match** `m: L → G` deletes `m(L∖K)`, keeps `m(K)`, and glues in
`R∖K`. This is the standard **double-pushout** construction, here over the typed,
attributed, directed, weighted category of §2. Because `K` is explicit, the
embedding of the surrounding host into `R` is total and deterministic — there is
no ad-hoc rewiring.

### 6.2 Matching

A match is a **typed, attributed subgraph monomorphism**: an injective map
`L → G` preserving

- node labels `λN` (or a specified `αN["subtype"]`),
- edge types `λE` and `adjacency` **orientation**,
- edge **direction** (and `bidirectional` where the pattern constrains it).

Weights are matched only if the pattern constrains them (default: unconstrained).
At Stage 1 matching is purely combinatorial; the geometric matching of the paper
(`IsSimilar` / `IsVertexCongruent`) belongs to Stage 2 and replaces *only* the
matching predicate, not the rule structure.

### 6.3 Application conditions (NACs)

A production may carry **negative application conditions** — forbidden extensions
of `L` that block the match (e.g. *do not add a second `entrance` adjacent to a
block that already has one*). NACs are the guard mechanism; they keep the named
grammar from over-generating.

### 6.4 Atomic, core, and named productions

- **Atomic productions** wrap a single Tier-0 operation as a one-line span.
- **Core productions** wrap a Tier-1 operation (`SPLIT`, `MERGE`, `MIRROR`, …).
- **Named productions** (§7) are the DNF grammar: each is a composite — a short,
  ordered programme of core/atomic productions with typed labels, an interface,
  and NACs.

Every named production therefore **expands to Tier 0** and is **reversible**.

---

## 7. The Dom Narkomfin grammar (Tier 2 — named productions)

Notation: nodes written `label`; an `adjacency` edge written `—` (H) or `‖` (V);
direction shown with `→`/`↑`. `[K]` marks interface nodes (preserved, matched).
Each rule lists the **Tier-1 operation(s)** it instantiates, its **NACs**, and its
**grounding** in the real model (Appendix A).

### 7.0 Axiom A₀

Two isolated generic nodes — the residential block and the communal (condenser)
block:

```
A₀ :  b₁:generic        b₂:generic           (no edges)
```

(Matches figure 5, Step 1, which begins with two unconnected black nodes.)

### 7.1 Step-1 productions

**P1 · ADD-INTERNAL-VOLUME** — *instantiates `SPLIT` (Divide).*
Subdivide a block by an internal generic space.
```
L:  [g]            K:  [g]            R:  [g] — g′         (orientation H)
```
NAC: none. Grounding: the long residential block → a row of apartment spaces
(`3-4-5_apartment`). Repeatable to yield `● — ● — ●`.

**P2 · ADD-EXTERNAL-VOLUME** — *instantiates `UNION` (add-adjacency).*
Attach a generic space externally to an existing one.
```
L:  [g]            K:  [g]            R:  [g] → g′          (new node + adjacency)
```
NAC: none. Grounding: an attached external volume (figure 5 Step 1 vertical chain).

### 7.2 Step-2 productions

**P3 · ADD-CORRIDOR (horizontal circulation)** — *instantiates `+N(corridor)` then
two `UNION` adds.* A corridor mediates two internal volumes.
```
L:  [g_i]   [g_j]          K:  [g_i] [g_j]          R:  [g_i] — c:corridor — [g_j]
```
NAC: no existing `corridor` already adjacent to both `g_i` and `g_j`.
Grounding: `Corridor_first_floor`, `Auxiliary_corridor_second_floor`.
(Figure 5: "Addition of two internal volumes / horizontal circulation".)

**P4 · ADD-STAIRCASE (vertical circulation)** — *instantiates `+N(staircase)` + `UNION`.*
A staircase connects spaces across levels.
```
L:  [x]   (x ∈ {generic, corridor})     K:  [x]     R:  [x] ‖ s:staircase   (orientation V)
```
NAC: no `staircase` already adjacent to `x` on the same vertical line.
Grounding: `Staircase_North`, `Staircase_South`. (Figure 5: "vertical circulation".)

### 7.3 Step-3 productions

**P5 · ADD-GROUND-FLOOR-ENTRANCE** — *instantiates `+N(entrance)` + directed
`UNION` (one-way).* Add an entrance at grade, adjacent to circulation; the access
edge is one-way inward.
```
L:  [x]  (x ∈ {corridor, staircase}, ground level)
K:  [x]
R:  e:entrance → [x]        (adjacency, orientation H, bidirectional = false)
```
NAC: `x`'s block has no existing `entrance`. Applied once per block.
Grounding: `auxiliary_ground_f_entrance_curved`, `Lobby_ground_floor`.

**P6 · ADD-TWO-U-SECTION-SPACES** — *instantiates `+N(u_section)` ×2 + `UNION` ×2.*
Add two split-level (U-in-section) units served by circulation.
```
L:  [c]  (a corridor/spine)
K:  [c]
R:  [c] — u₁:u_section ,  [c] — u₂:u_section
```
NAC: none. Grounding: the F-type maisonette duplex sections (`mesonete_f_1_2`).
(Figure 5: "Addition of two U shaped in section spaces".)

**P7 · ADD-L-SECTION-SPACE** — *instantiates `+N(l_section)` + vertical `UNION`.*
Add the interlocking L-in-section unit **below** the two U-units.
```
L:  [u₁:u_section]   [u₂:u_section]
K:  [u₁] [u₂]
R:  u₁ ‖ l:l_section ,  u₂ ‖ l:l_section      (orientation V, l below)
```
NAC: no `l_section` already below `u₁,u₂`. Grounding: the interlocking maisonette
section — the Narkomfin K/F split-level interlock. (Figure 5: "Addition of L shaped
in section space (below the two U shaped)".)

**P8 · ADD-THREE-SMALL-ROOMS** — *instantiates `DIVIDE` into 3 / `+N(generic)` ×3.*
Add a connected cluster of three small generic rooms.
```
L:  [x]
K:  [x]
R:  [x] — g_a — g_b — g_c   with  g_a — g_c     (a connected triad)
       (αN["subtype"] = "toilet" on each)
```
NAC: none. Grounding: `Condenser_toilet_1/2/3` in the communal block.
(Figure 5: "addition of three small rooms".)

### 7.4 Future production

**P9 · MIRROR** — *instantiates `MIRROR` (Transform-reflection).* Reflect a derived
sub-grammar (a unit or wing) to build a symmetric whole. Defined (§5.3) but not
exercised in v0.1; the paper's open problem.

### 7.5 Catalogue summary

| Rule | Operation(s) | Adds | Grounding |
|---|---|---|---|
| P1 | SPLIT | internal `generic` | apartment row |
| P2 | UNION(add-adj) | external `generic` | attached volume |
| P3 | +N + UNION×2 | `corridor` between two spaces | first/second-floor corridors |
| P4 | +N + UNION(V) | `staircase` | North/South staircases |
| P5 | +N + UNION(one-way) | `entrance` | curved ground entrance, lobby |
| P6 | +N×2 + UNION×2 | two `u_section` | F-type maisonette duplex |
| P7 | +N + UNION(V) | one `l_section` below | interlocking unit |
| P8 | DIVIDE / +N×3 | three small `generic` | condenser toilets |
| P9 | MIRROR | reflected sub-grammar | (future) |

---

### 7.6 Grammar architecture: hierarchy, sub-grammars, and composition

The grammar is **hierarchical and modular**, in three tiers that mirror the
building itself:

```
Building grammar        :  block-graphs   +   bridge composition          (§7.6.3)
   └─ Block grammar      :  P1–P8 per block → terminals + non-terminals     (§7.1–7.3)
        └─ Section sub-grammar :  refine each u_section / l_section node     (§7.6.2)
```

(This *Hierarchy* — building → block → section — is distinct from the *Tier*
0/1/2 of operation composition and from the *Stage* 1/2 graph-vs-shape split.)

#### 7.6.1 Terminals vs non-terminals
Terminal nodes (`generic`, `corridor`, `staircase`, `entrance`) are final at the
space level. Non-terminal nodes (`u_section`, `l_section`) are refined by a
sub-grammar before — or instead of — realisation.

#### 7.6.2 Section sub-grammars (resolves item 4)
Each non-terminal carries its **own transformation grammar** that develops the
unit's internal architecture. A node `n:u_section` is refined by

**`REFINE(n, G_u)`** — a `REPLACE` whose left side is `{n}` and whose right side is
the **start graph of the sub-grammar `G_u`**, after which `G_u`'s own productions
develop the unit. For a U-section duplex this typically yields a lower and an
upper space joined by a `V` adjacency and an internal `staircase`, with the
double-height void expressed as a vertical adjacency to a shared volume; `G_l`
does likewise for the L-section's interlock.

Each sub-grammar has its **own alphabet, productions, and (later) NACs**,
specified in a companion document; v0.2 fixes only the **interface contract**: a
sub-grammar receives the non-terminal's incident edges as its boundary and must
preserve them (these incident edges are exactly the interface `K` of the `REFINE`
span). Refinement is **reversible** in the operation-level sense (§4): its inverse
**`ABSTRACT(S → n)`** collapses a refined unit-subgraph back to its non-terminal,
and is an *exact* round-trip only when the derivation trace records the
sub-derivation (§5.1 note).

#### 7.6.3 Modular composition and the inter-block bridge (resolves item 6)
Each block is developed by its **own block grammar** to a complete graph
(`G_res` for the residential block, `G_con` for the condenser). The blocks are
**distinct grammars** whose derivations are independent. The **inter-block
bridge** is therefore *not* a production inside either block but a **composition
operation** over completed block graphs:

**`BRIDGE(G_a @ a*, G_b @ b*, κ)`** — given completed block graphs `G_a, G_b` and
**designated interface nodes** `a* ∈ G_a`, `b* ∈ G_b`, introduce a connector `κ`:
either a single `adjacency` edge `a* — b*`, or a `corridor`/bridge node
`a* — κ:corridor — b*` for an enclosed passage. The bridge **enters the
derivation only after all block graphs are complete**.

Interface nodes are designated explicitly — by an attribute `αN["interface"] =
true` set during the block derivation, or by a boundary label (a block-edge
`corridor`/`entrance`) — so composition never has to guess where blocks join.
`BRIDGE` generalises to more than two blocks: a set of block grammars joined by a
small **bridge graph** over their interface nodes. The building grammar is, in
this sense, a **graph of grammars** — block and sub-grammars as nodes, refinements
and bridges as composition edges.

---

## 8. A worked derivation (generating the DNF graph)

A derivation is a sequence of (production, match, parameters). Applying the
catalogue to `A₀` reproduces the DNF direct graph of figure 5:

```
A₀                                  b₁:generic , b₂:generic
─ P1 on b₁ (×2) ─▶                  long block → g — g — g            (residential spine)
─ P2 on b₂ ─▶                       condenser block + external g
─ P3 (×2) ─▶                        corridors inserted along the spine
─ P4 (×2) ─▶                        North & South staircases attached (V)
─ P5 (×1 per block) ─▶              ground-floor entrances (one-way)
─ P6 ─▶                             two u_section units on the spine
─ P7 ─▶                             one l_section below them (V)
─ P8 ─▶                             three small rooms (condenser toilets)
══▶  G_DNF                          the typed Dom Narkomfin space-adjacency graph
```

Because every rule is reversible (§4–§5), the **reverse derivation**
`G_DNF →* A₀` is a legal decomposition of the building back to its two blocks —
the grammar runs both ways. The derivation trace (§10.2) records enough to replay
or invert exactly.

> **Modular reading (v0.2).** Per §7.6.3 the sequence above is the *residential
> block* derivation; the *condenser block* is derived independently to `G_con`,
> and `BRIDGE` joins `G_res` and `G_con` only once both are complete. The
> `u_section` and `l_section` nodes appearing here are **non-terminals**, refined
> by their sub-grammars (§7.6.2) as a subsequent, independently reversible stage.

---

## 9. The graph→shape interface (Stage 2 preview — the first bridge rule)

Per D-III, a node's semantic label **translates to a shape type** at Stage 2. That
translation is the single rule Stage 1 hands forward — define it now, build it
later:

```
τ : Σ → ShapeType
   generic    ↦ parallelepiped (box) volume
   corridor   ↦ elongated parallelepiped (horizontal proportion, circulation)
   staircase  ↦ vertical parallelepiped spanning levels
   u_section  ↦ U-profile solid in section (split-level, double-height portion)
   l_section  ↦ L-profile solid in section (interlocking complement)
   entrance   ↦ ground-floor opening volume (curved variant via αN)
```

Stage 2 will, in addition: realise each node as a Topologic `Cell`/`CellComplex`;
realise each `adjacency` edge as a **shared face** (orientation `V` ⇒ shared
horizontal face/slab; `H` ⇒ shared vertical face/wall); restore the geometric
matching predicate (`IsSimilar` / `IsVertexCongruent`) in place of §6.2's
combinatorial match; and round-trip the realised cell complex back to a direct
graph for verification. **None of this changes the Stage-1 rule structure** — it
swaps the matcher and adds the realisation map. That separation is the point of
doing the graph grammar first.

---

## 10. Data model and serialization

### 10.1 Graph (JSON)

```json
{
  "directed": true,
  "multigraph": true,
  "nodes": [
    { "id": "n0", "label": "generic",   "attrs": { "block": "residential" } },
    { "id": "n1", "label": "corridor",  "attrs": { "level": 1 } },
    { "id": "n2", "label": "staircase", "attrs": { "id_name": "Staircase_North" } }
  ],
  "edges": [
    { "src": "n0", "tgt": "n1", "type": "adjacency",
      "orientation": "H", "bidirectional": true,  "weight": 1.0 },
    { "src": "n1", "tgt": "n2", "type": "adjacency",
      "orientation": "V", "bidirectional": false, "weight": 1.0 }
  ]
}
```

### 10.2 Derivation trace (JSON)

An ordered list of applications, each sufficient to **replay** and **invert**:

```json
[
  { "rule": "P1", "match": { "g": "b1" }, "params": { "orientation": "H",
      "partition": [["e3"],["e4"]] }, "produced": ["n5"] },
  { "rule": "P3", "match": { "g_i": "n5", "g_j": "n6" }, "produced": ["n7"] }
]
```

---

## 11. Implementation plan for Claude Code

Target: a small Python package implementing Stage 1, with a clean seam for
Stage 2. Backed by `networkx.MultiDiGraph` for the carrier.

**Module layout**

```
topograph/
  model.py        # StateGraph wrapper over MultiDiGraph; invariants (§2.2)
  alphabet.py     # Σ, Θ, defaults, validation (§3)
  atomic.py       # A1–A7, each with its inverse; pre/postcondition asserts (§4)
  composite.py    # SPLIT, MERGE, DIVIDE, UNION, DIFFERENCE, REPLACE,
                  #   TRANSFORM/MIRROR, OTHER — recipes over atomic (§5)
  rules.py        # DPO Production (L,K,R + NACs); typed-attributed matcher (§6)
  grammar_dnf.py  # the named productions P1–P9 (§7) as Production instances
  engine.py       # apply(rule, match, params) → records trace; replay; invert (§8,§10.2)
  serialize.py    # JSON read/write for graph + trace (§10)
  shape_iface.py  # τ stub (label → shape type); Stage-2 boundary (§9)
  hierarchy.py    # terminals/non-terminals; REFINE / ABSTRACT; sub-grammar interface (§7.6.2)
  compose.py      # BRIDGE; modular composition of completed block graphs (§7.6.3)
  tests/
```

**Build milestones**

1. **M1 — carrier + invariants.** `StateGraph`; well-formedness checks (§2.2);
   JSON round-trip. *Test:* construct/validate a hand-written DNF graph.
2. **M2 — atomic basis.** A1–A7 with inverses. *Test (reversibility):* for each
   atomic `op`, `inverse(op) ∘ op = id` on random well-formed graphs.
3. **M3 — core composites.** `SPLIT`/`MERGE` (with `π`, `ζ`, `ξ`), then the other
   verbs. *Test:* `MERGE ∘ SPLIT = id` and `SPLIT ∘ MERGE = id`; `DIVIDE(k)` =
   `(k−1)` splits.
4. **M4 — DPO rules + matcher.** Production span, typed-attributed monomorphism,
   NAC checking. *Test:* matches respect labels, orientation, direction.
5. **M5 — DNF grammar + derivation.** P1–P9; the §8 derivation script.
   *Test (recovery):* `A₀ →* G_DNF` reproduces the hand-written DNF graph
   (graph isomorphism); the reverse derivation returns `A₀`.
6. **M6 — trace + Stage-2 stub.** Record/replay/invert traces; `τ` stub returning
   shape-type tags (no geometry). *Test:* replay equals forward run; invert equals
   backward run.
7. **M7 — hierarchy + composition.** `REFINE`/`ABSTRACT` over non-terminals with a
   minimal U-section sub-grammar; `BRIDGE` over two completed block graphs.
   *Test:* refining then abstracting a `u_section` round-trips; two blocks derived
   independently and bridged reproduce the full DNF graph.

**Invariants the package must enforce continuously:** well-formedness (§2.2);
reversibility (every applied op is invertible and recorded); type-soundness
(matches and results respect Σ/Θ).

**Property model is pluggable.** The node/edge property representation is a
**configuration choice** (§12.1), not a hard dependency of the engine: the grammar
operates on the space-adjacency graph regardless, and the chosen schema
(flat / nested / dual / multiplex) is realised at the §9 boundary. Defer the choice
without blocking M1–M7.

---

## 12. Differential options and open items

Two modelling questions are left **open for your choice**; each is given as a set
of differential options with trade-offs and a recommendation. The remaining items
are either resolved in v0.2 or deferred.

### 12.1 How nodes carry properties — spaces, walls, windows, performance (item 1)

Should a node carry a **flat rich schema**, or should properties and sub-elements
live in **subgraphs**? Four options, in increasing structure:

**Option A — Flat attribute schema.** Every node carries a typed record
(`space_type`, `area`, `volume`, `level`, `energy_performance`, …); walls and
windows are attributes of `adjacency` edges (`thickness`, `u_value`,
`glazing_ratio`).
*Pros:* simplest; fixed-width feature vectors ideal for classical GNNs; maps
directly to IFC/BIM property sets. *Cons:* walls and windows are not first-class —
a wall shared by two spaces, or a window's own properties, sit awkwardly on an
edge; it forgoes the paper's *dual* ambition of representing discrete elements.

**Option B — Labels + nested subgraphs per node (recursive graphs).** A space node
*contains* a subgraph of its bounding elements — walls, slabs, windows — each a
child node with its own properties. Properties live at the level they belong to.
*Pros:* faithful to hierarchy (mirrors Topologic `Cell → Face → Edge → Vertex`);
properties attach correctly; composes naturally with the section sub-grammars of
§7.6; recursive and scalable. *Cons:* nested graphs need hierarchical GNNs or a
flattening step for ML; heavier to implement and to match.

**Option C — Dual heterogeneous graph (Topologic-native).** Spaces *and* discrete
elements (walls, windows, slabs) are **all nodes in one graph**, with typed edges
(`space –bounded_by– wall`, `wall –contains– window`); space-to-space adjacency
becomes a `space–wall–space` path. Properties on the respective nodes.
*Pros:* one flat graph → heterogeneous GNNs apply directly; first-class walls and
windows with their own properties; this is exactly the *dual graph* the paper
anticipates. *Cons:* the graph is larger and the clean space-adjacency view must be
*derived* (by contracting element nodes); the productions P1–P8 must be lifted to
act on element nodes too if used throughout.

**Option D — Multiplex (layered) graph.** Keep the space-adjacency graph as the
primary layer and maintain parallel **element** and **property** layers, linked by
inter-layer edges; operate per layer or jointly.
*Pros:* clean separation of concerns; the space grammar is untouched; flexible for
ML. *Cons:* the most machinery; likely premature now.

**Recommendation — a two-phase hybrid.** Keep v0.1's **space-adjacency graph as the
grammar's working representation** (Stage 1 stays small and combinatorial, and the
productions P1–P8 remain defined over it), and **realise properties and elements by
Option C — the dual graph — at the space→shape boundary** (Stage 2), where walls and
windows become real shared faces carrying attributes; fall back to **Option B's
nesting** where a space's internal section is itself a sub-grammar (§7.6.2). In
short: *adjacency graph to compute the grammar; dual graph to carry walls, windows
and performance; nesting for sub-grammar units.* This keeps the rewriting engine
light while giving BIM-grade properties their proper home, and it is the choice most
aligned with the paper's dual-graph statement. The main alternative worth weighing
is committing to **Option C throughout** (elements as nodes from the very start) if
the overriding priority is end-to-end graph-ML on a single heterogeneous graph.

### 12.2 Levels and the building–ground relationship (item 2)

Vertical position can be **carried** or **inferred**:

**Option L1 — Explicit level attribute.** Each node carries `level` (storey index;
ground = 0, with an optional `ground` node); `adjacency,V` edges respect
`level(a) = level(b) + 1`. *Pros:* exact, checkable, friendly to authored
derivations. *Cons:* must be supplied, and is brittle for the split-level units that
straddle storeys.

**Option L2 — Inferred levels (ML).** No explicit `level`; the stratification and
the building–ground relation are **recovered from the graph** by a graph
generative/neural model. This follows **Alymani & Jabi (2024)**, whose Building–
Ground Relationship (BGR) tool uses graph methods to retrieve and reason about how a
building's spaces relate to its levels and to the ground. *Pros:* no manual
labelling; robust to split-levels; turns "which level?" into a learned, queryable
property; reuses an established line of your group's work. *Cons:* inference is
approximate and needs a trained model and data.

**Option L3 — Hybrid (recommended).** Treat `level` as an **optional** attribute:
present and enforced in authored derivations, **absent and inferable** otherwise.
The representation supports both; an inference module (after Alymani & Jabi) fills or
checks levels for ML and retrieval, and the split-level units — whose section is a
sub-grammar (§7.6.2) — are the natural place to let inference, rather than a single
integer, express vertical position. *Pros:* authored rigour where wanted, ML
flexibility where needed. *Cons:* two code paths to keep consistent.

### 12.3 Resolved in v0.2
- **Item 4** — `u_section`/`l_section` are **non-terminals with their own
  sub-grammars** (§7.6.2).
- **Item 6** — the inter-block bridge is a **composition step** joining completed
  block graphs (§7.6.3).
- **Item 5 (NACs)** — **deferred to the sub-grammar stage**, as agreed.

### 12.4 Still open
- **Weight semantics** (§3.2) — what `ω` measures and how `SPLIT`/`MERGE`
  apportion/combine it (current default: children inherit `1.0`, merge takes `max`).
- The sub-grammar **alphabets and productions** for U- and L-sections (companion
  document).
- Which **property option** (§12.1) and **level option** (§12.2) to commit to for
  the build.

---

## Appendix A — grounding table

| Node label / subtype | Figure-5 operation | Real objects (`.blend`) |
|---|---|---|
| `generic` (apartments) | add internal volume (P1) | `3-4-5_apartment`, `Apartment_Second_floor_edge` |
| `generic` (lobby) | — | `Lobby_ground_floor` |
| `generic` (balcony) | — | `First_floor_balcony` |
| `corridor` | horizontal circulation (P3) | `Corridor_first_floor`, `Auxiliary_corridor_second_floor` |
| `staircase` | vertical circulation (P4) | `Staircase_North`, `Staircase_South`, `Condenser_staircase` |
| `u_section` | two U-in-section (P6) | `mesonete_f_1_2`, `mesonete_f_1` (F-type maisonette) |
| `l_section` | L-in-section below (P7) | interlocking maisonette section |
| `entrance` | ground-floor entrance (P5) | `auxiliary_ground_f_entrance_curved`, `auxiliary_ground_floor` |
| `generic` subtype `toilet` | three small rooms (P8) | `Condenser_toilet_1/2/3` |
| `generic` subtype `condenser_main` | — | `Condenser_main_space`, `Condenser_First/Second_floor_main_space` |

## Appendix B — notation

| Symbol | Meaning |
|---|---|
| `+N / −N` | add / delete node (A1/A2) |
| `+E / −E` | add / delete edge (A3/A4) |
| `ρ` | relabel (A5) |
| `ω̂` | reweight (A6) |
| `↔` | reverse edge (A7) |
| `—` / `‖` | H-adjacency / V-adjacency edge |
| `→` / `↑` | edge direction |
| `L ⊇ K ⊆ R` | DPO production span (left, interface, right) |
| `[x]` | interface node (matched and preserved) |
| `τ` | label → shape-type translation (Stage 2) |
