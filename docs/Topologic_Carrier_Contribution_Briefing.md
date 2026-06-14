# Briefing note — contributions to TopologicPy for directed / parallel-edge / typed-attributed graphs

**For discussion with:** Wassim Jabi (TopologicPy)
**From:** T. Dounas · graphtope
**Date:** 2026-06-14
**Tested against:** TopologicPy **0.9.43**, networkx 3.6.1, Python 3.11.9
**Companion docs:** `../Topologic_Graph_Grammar_Spec.md` (the grammar spec, esp. §2, §6, §10, §11), Dounas & Jabi (2025), *Towards bridging shape and graph grammars through topology* (eCAADe 43, 663–672).

---

## 0. Purpose

graphtope rewrites the **direct/dual space-adjacency graph** of a building as a
**typed, directed, weighted, attributed multigraph** graph grammar (spec §2.1).
We have decided to make **`topologicpy.Graph` the sole carrier** of that graph —
not a networkx graph with topologic bolted on for geometry, but topologic all the
way down — so that Stage 1 (the grammar) and Stage 2 (geometry via Cells /
CellComplexes) live in one substrate and round-trip cleanly.

That decision exposes a small number of places where the carrier the grammar
*needs* and the carrier topologic *currently provides* do not yet line up. This
note maps those gaps precisely, backs each with a reproducible test against
0.9.43, and proposes concrete, backward-compatible contributions, ordered by
priority. The aim is a shared agenda we can work through together — some items
graphtope can prototype as PRs, some are better designed inside topologic core.

The grammar's carrier requirements come straight from the spec and are not
negotiable for correctness; **how** topologic satisfies them is fully open.

---

## 1. What the grammar needs from the carrier

Drawn from spec §2.1–§2.2 and §6.2. Each is a hard requirement of the formalism.

| # | Requirement | Spec | Why the grammar needs it |
|---|---|---|---|
| **R1** | **Directed edges**, consistently honored across *all* graph operations (degree, adjacency, traversal, matching) | §2.1 (`src,tgt`), D-II | Vertical adjacency `a→b` ("a above b") is inherently ordered; one-way access (entrance) is directional. Direction must mean the same thing everywhere, not just in two query methods. |
| **R2** | **Parallel edges** (multigraph) between the same ordered pair | §2.1 | Two relations may hold between the same two spaces (e.g. an `adjacency` edge *and* a separately-attributed access/circulation link); Stage 2 needs `space–wall–space` plus other relations. |
| **R3** | **Typed + attributed** vertices and edges (label `λN`, edge type `λE`, orientation, `bidirectional`, weight `ω`, free attribute dicts `αN/αE`) | §2.1, §3 | Nodes carry a semantic label from Σ; edges carry type/orientation/weight. This is the data the grammar matches on and rewrites. |
| **R4** | **Typed-attributed directed subgraph monomorphism** — injective matches preserving node label/subtype, edge type + orientation, **edge direction**, optionally `bidirectional`/weight | §6.2 | This is the DPO match `m: L→G`. Without attribute- and direction-aware matching there is no rule application. |
| **R5** | **Stable logical identity** for vertices/edges, independent of coordinates | §10.1 (`"id"`) | Stage-1 graphs have no geometry; coordinates are arbitrary layout. Rules, traces (§10.2) and JSON refer to nodes by stable id, not position. |
| **R6** | **Incremental, invertible mutation** — add/remove/relabel/reweight/reverse with predictable in-place-vs-copy semantics | §4 (A1–A7), §11 | The atomic basis must be cheap to apply and to invert; reversibility is a core invariant. |
| **R7** | **Lossless JSON round-trip** of the typed/directed/attributed graph (and ideally without injected vocabulary leaking in) | §10.1 | Serialize/replay/invert derivations; interop. |

---

## 2. What TopologicPy 0.9.43 does today (measured, not assumed)

All claims below are from the probe in **Appendix A** run against 0.9.43.

| Capability | Status today | Evidence |
|---|---|---|
| Edge has start/end (ordered) | ✅ `Edge.ByStartVertexEndVertex`, `StartVertex/EndVertex`; `AddEdge` records `src`/`dst` index keys | signatures |
| Direction in **queries** | ⚠️ **opt-in & partial**: `OutgoingEdges/IncomingEdges(..., directed=True)` work; **`AdjacentVertices` has no `directed` param** and is undirected | `b OutgoingEdges(directed)=0` ✅ but `AdjacentVertices(b)=1` |
| **Parallel edges** | ❌ **deduped**: adding 2 edges between the same pair yields **`Graph.Size = 1`** | TEST 1 |
| Vertex/edge dictionaries (attributes) | ✅ survive construction & round-trip (`orientation`, `weight` preserved) | TEST 4 |
| Reserved/auto keys | ⚠️ topologic injects `category`, `ontology_class`, `ontology_uri`, `src`, `dst` into edge dicts (toggle via `ontology=False`) | TEST 4 |
| Subgraph matching | ⚠️ `SubGraphMatches(subGraph, superGraph, strict, vertexMatcher, vertexKey)`: vertices matchable by key/fn; **no `edgeMatcher`, no edge-type/orientation/direction constraint**; `strict=False` allows edge-or-**path** | signature/doc |
| Isomorphism check | ✅ `Graph.IsIsomorphic` (for M5 recovery test) | present |
| Stable id | ✅ via dict `id`/`index` + `VertexByKeyValue`, `AddEdgeByIndex` | present |
| Mutation | ✅ `AddVertex/RemoveVertex/AddEdge/RemoveEdge/ContractEdge` — **functional**, return a graph (copy semantics to confirm) | signatures |
| JSON | ✅ `ExportToJSON/ByJSONPath/JSONString` | present |
| networkx bridge | ✅ `ByNetworkXGraph/NetworkXGraph` (escape hatch) | present |

**Net:** R3, R5, R6, R7 are essentially met today. **R1 (consistent direction),
R2 (parallel edges), and R4 (typed-attributed directed matching) are the three
real gaps.**

---

## 3. Gap analysis & proposed contributions

Priority: **P0** blocks the grammar; **P1** needed for full spec fidelity; **P2**
quality-of-life / future-proofing.

### C1 · Parallel edges (multigraph)  — **P1**  · gap R2
**Today:** `Graph.Size == 1` after adding two edges between the same pair —
silently deduped. The likely cause is geometric: two edges between coincident
vertices are the same segment within tolerance.

**Why it may be hard:** if `topologic_core.Graph` keys adjacency by vertex pair
(or by edge geometry), true parallel edges may be impossible at the C++ core
without a data-model change.

**Proposed design (least invasive first):**
- **C1a — "bundled relationships" convention (topologicpy level).** Keep **one
  core edge per ordered vertex pair**, but standardize storing *multiple*
  relations in its dictionary as a list (e.g. `relations: [{type, orientation,
  bidirectional, weight, key}, …]`). Add helpers `Graph.AddRelation(edge, …)`,
  `Graph.Relations(edge)`, and make `Graph.Edges(..., explode=True)` return one
  logical edge per relation. This unblocks R2 with no core change and degrades
  gracefully to today's behavior.
- **C1b — first-class multigraph (core).** A `multigraph: bool` on graph
  construction that lets the core hold parallel edges distinguished by an edge
  `key`/id. Larger change; the principled long-term answer.

**graphtope interim workaround:** Stage 1 of the DNF grammar uses a *single*
`adjacency` type and encodes mutual adjacency via a `bidirectional` flag on **one**
edge (spec §3.2) — so we mostly avoid parallel edges now. We need C1 for: (i) the
rare two-relations-between-same-spaces case, and (ii) Stage 2's heterogeneous /
dual graph. **Not a launch blocker, but the cleanest of the three to prototype.**

> ⚠️ Note this also means **bidirectional-as-two-opposite-edges is unavailable**
> (a→b and b→a are the same segment and would dedupe) — confirming the spec's
> choice to model symmetry with a `bidirectional` attribute rather than two edges.

### C2 · First-class, consistent directedness — **P0**  · gap R1
**Today:** direction is an opt-in interpretation (`directed=True` on
`Outgoing/IncomingEdges`) layered on an undirected core, and it is **not applied
uniformly** — `AdjacentVertices` ignores direction entirely (returns the same
count from either endpoint). Any analytic/traversal/matching method that doesn't
thread `directed` will silently treat `a→b` as `a—b`.

**Proposed design:**
- A **graph-level `directed` property**, set at construction and stored on the
  graph dictionary, that becomes the default for every direction-sensitive method.
- A consistent, threaded **`directed` parameter** (defaulting to the graph's flag)
  across `AdjacentVertices`, `VertexDegree` (→ in/out degree), `Connectivity`,
  `ShortestPath`, `ConnectedComponents`, and `SubGraphMatches` (see C3).
- Direction taken from the existing edge `src`/`dst` keys, so no new data model —
  this is largely a wrapper-level consistency pass.

**graphtope interim workaround:** wrap every traversal in our `StateGraph` and
always pass `directed=True`, hand-implementing direction where a method lacks the
param. Works, but fragile and exactly the duplication a first-class flag removes.
**This is the highest-value contribution** — small surface, big correctness win,
benefits every directed-graph user of topologic, not just us.

### C3 · Typed-attributed **directed** subgraph matching — **P0**  · gap R4
**Today:** `SubGraphMatches` matches **vertices** by `vertexKey`/`vertexMatcher`,
but offers **no edge matcher** and **no direction/edge-attribute constraint**;
`strict=False` even matches an edge to a whole *path*. DPO matching (spec §6.2)
needs injective maps preserving **node label/subtype, edge type + orientation,
edge direction**, and optionally `bidirectional`/weight.

**Proposed design — extend `SubGraphMatches`:**
- add **`edgeMatcher: callable(subEdge, superEdge) -> bool`** and/or
  **`edgeKeys: list[str]`** (match on edge dict values, mirroring `vertexKey`);
- add **`directed: bool`** so edge mapping respects `src`/`dst`;
- keep the default behavior unchanged (all new params optional);
- document/guarantee the result is an **injective monomorphism** (it already maps
  to unique vertices) and add a `strict="edge"` mode meaning *edge-to-edge only,
  same type/orientation/direction* (no path substitution).

**graphtope interim workaround:** implement the typed-attributed directed
monomorphism ourselves in `rules.py` over our id index (or via the `NetworkXGraph`
bridge, which has `MultiDiGraphMatcher` with node/edge predicates). Fully
unblocks us — but it means the matcher lives in graphtope, not topologic, so the
ecosystem doesn't benefit. Worth upstreaming once stable.

### C4 · Reserved-key namespace & lossless typed JSON — **P2**  · gap R3/R7
**Today:** topologic injects `category`, `ontology_class`, `ontology_uri`,
`src`, `dst` into dictionaries. Risk of collision with grammar attribute keys and
of leaking vocabulary into our JSON (§10.1).
**Proposed:** document the reserved-key set; honor `ontology=False` consistently
across constructors **and** exporters; optionally a key-namespace prefix (e.g.
`top:`) so app keys and topologic keys never collide. Low effort, prevents subtle
serialization bugs.

### C5 · Identity & mutation ergonomics — **P2**  · gap R5/R6
**Today:** mostly fine. To confirm/contribute: (i) guarantee `id` stability across
mutating ops; (ii) clarify in-place vs copy semantics of
`AddVertex/AddEdge/RemoveEdge` (matters for trace/replay cost, §10.2);
(iii) id-based convenience (`AddEdgeByIndex` exists; add `RemoveEdgeByIndex`,
`RelabelVertex`). Quality-of-life for any rewriting engine.

### C6 · (Future / optional) generic graph-rewriting primitive — **P2**
A `Graph.ReplaceSubgraph(match, L, K, R)` DPO step could eventually live in
topologic so rewriting is a first-class topologic capability, not just
graphtope's. Likely out of scope for now; flagged so we design C1–C3 in a way
that doesn't preclude it.

---

## 4. Summary table & suggested order

| ID | Contribution | Priority | Gap | Where it likely lives | graphtope blocked without it? |
|---|---|---|---|---|---|
| **C2** | First-class, consistent `directed` | **P0** | R1 | topologicpy wrapper | No (we wrap), but fragile |
| **C3** | Edge/direction-aware `SubGraphMatches` | **P0** | R4 | topologicpy | No (we implement), but not upstreamed |
| **C1** | Parallel edges (bundled → core multigraph) | P1 | R2 | wrapper → core | Partially (Stage 2 / rare cases) |
| **C4** | Reserved keys + lossless typed JSON | P2 | R3/R7 | wrapper | No |
| **C5** | Identity/mutation ergonomics | P2 | R5/R6 | wrapper | No |
| **C6** | Generic DPO rewrite primitive | P2 | — | topologic (future) | No |

**Suggested sequence:** C2 first (small, high-leverage, benefits everyone) →
C3 (the other correctness item; we can prototype as a PR from our matcher) →
C1a bundled-relations convention → C4/C5 cleanups → revisit C1b/C6 together.

**What graphtope can contribute as PRs:** C2 (consistency pass), C3 (donate our
typed-attributed directed matcher), C1a (bundled-relations helpers), C4 docs/flags.
**What needs Wassim / core:** C1b (core multigraph), final API shape of C2/C3,
C6.

---

## 5. Open questions for Wassim

1. **Parallel edges (C1):** is the dedup geometric (coincident-segment) or
   structural (pair-keyed adjacency) in `topologic_core.Graph`? Is core
   multigraph (C1b) feasible, or is the bundled-relations convention (C1a) the
   pragmatic answer?
2. **Directedness (C2):** appetite for a graph-level `directed` flag as the
   default for all direction-sensitive methods? Any methods that intentionally
   stay undirected?
3. **Matching (C3):** would you take an `edgeMatcher`/`edgeKeys`/`directed`
   extension to `SubGraphMatches`, and a `strict="edge"` mode? Should we PR our
   matcher or do you prefer a core implementation?
4. **Ontology keys (C4):** is `ontology=False` honored everywhere? Is a reserved
   `top:`-prefixed namespace acceptable to avoid app-key collisions?
5. **Mutation semantics (C5):** are `AddEdge`/`RemoveEdge` guaranteed copy or
   in-place? Any plan for id-stable, in-place incremental editing?
6. **Round-trip fidelity:** does `ExportToJSON`→`ByJSONPath` preserve direction,
   edge dicts, and (future) parallel relations losslessly?

---

## Appendix A — reproducible probe (TopologicPy 0.9.43)

```python
from topologicpy.Graph import Graph
from topologicpy.Vertex import Vertex
from topologicpy.Edge import Edge
from topologicpy.Dictionary import Dictionary
from topologicpy.Topology import Topology

def D(**kv): return Dictionary.ByKeysValues(list(kv), [kv[k] for k in kv])
def V(x, y, **kv):
    v = Vertex.ByCoordinates(x, y, 0)
    return Topology.SetDictionary(v, D(**kv)) if kv else v
def idof(v):
    d = Topology.Dictionary(v); return Dictionary.ValueAtKey(d, "id") if d else None

a = V(0, 0, id="a"); b = V(1, 0, id="b")

# TEST 1 — parallel edges?  -> Size == 1  (DEDUPED; multigraph unsupported)
g = Graph.ByVerticesEdges([a, b],
        [Edge.ByStartVertexEndVertex(a, b), Edge.ByStartVertexEndVertex(a, b)], silent=True)
print("parallel-edge Size:", Graph.Size(g))

# TEST 2/3 — direction
g2 = Graph.ByVerticesEdges([a, b], [Edge.ByStartVertexEndVertex(a, b)], silent=True)
m = {idof(v): v for v in Graph.Vertices(g2)}
print("a Outgoing(directed):", len(Graph.OutgoingEdges(g2, m['a'], directed=True)))  # 1
print("b Incoming(directed):", len(Graph.IncomingEdges(g2, m['b'], directed=True)))  # 1
print("b Outgoing(directed):", len(Graph.OutgoingEdges(g2, m['b'], directed=True)))  # 0
print("AdjacentVertices(b):", len(Graph.AdjacentVertices(g2, m['b'])))               # 1 (undirected!)

# TEST 4 — edge dict survives (+ injected ontology keys)
e = Topology.SetDictionary(Edge.ByStartVertexEndVertex(a, b), D(orientation="H", weight=2.0))
g3 = Graph.ByVerticesEdges([a, b], [e], silent=True)
ge = Graph.Edges(g3)
print("edge dict:", Dictionary.PythonDictionary(Topology.Dictionary(ge[0])))
```

### Observed output (0.9.43)
```
parallel-edge Size: 1
a Outgoing(directed): 1
b Incoming(directed): 1
b Outgoing(directed): 0
AdjacentVertices(b): 1
edge dict: {'category': 'relationship', 'dst': 1, 'ontology_class': 'top:Relationship',
            'ontology_uri': 'http://w3id.org/topologicpy#Relationship',
            'orientation': 'H', 'src': 0, 'weight': 2.0}
```

**Reading:** parallel edges deduped (C1); direction works only via opt-in and is
inconsistent across methods (C2); edge attributes persist but topologic vocabulary
is injected (C4); matching extensions still needed (C3, by signature inspection).
