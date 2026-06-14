# CLAUDE.md

Guidance for working in this repo. Keep it lean; link to the spec/briefing rather
than duplicating them.

## What this is
`graphtope` — a typed, directed, weighted, attributed **graph grammar** for
building space-adjacency graphs (Dom Narkomfin reference). Stage 1 = pure graph
level; Stage 2 = geometry via TopologicPy. Follows Dounas & Jabi (2025), eCAADe 43.

## Key documents (read these first)
- **`Topologic_Graph_Grammar_Spec.md`** — the authoritative spec. (Note: README
  links to `SPEC.md`, which does **not** exist — the file has the long name.)
- **`docs/Topologic_Carrier_Contribution_Briefing.md`** — measured gaps in
  TopologicPy 0.9.43 and the contribution agenda to discuss with Wassim Jabi.

## Locked decisions
- **Carrier:** `topologicpy.Graph` is the sole carrier (not networkx). networkx is
  an *escape hatch only* (via `Graph.ByNetworkXGraph`/`NetworkXGraph`), e.g. for
  matching — not a second store.
- **Workflow:** develop iteratively in `notebooks/01_graphtope.ipynb`; extract each
  stabilized section into `graphtope/*.py` and re-import. Notebook drives, package
  becomes truth.
- **Scope (current):** milestones M0–M5 — reproduce the figure-5 DNF graph from
  axiom `A₀`, verified by `Graph.IsIsomorphic` + reverse derivation. M6–M7 deferred.
- **Spec defaults adopted:** property model = hybrid (§12.1); levels = L3 optional
  `level` attr (§12.2); edge weight default `1.0`, merge takes `max` (§12.4).

## TopologicPy carrier gotchas (0.9.43) — and our workarounds
The carrier doesn't natively give the grammar everything; details + evidence in the
briefing note. Until upstreamed:
- **Parallel edges are deduped** (`Graph.Size==1` for 2 edges on one pair). Avoid
  multigraph at Stage 1: one `adjacency` edge per pair; model symmetry with a
  `bidirectional` flag, not two opposite edges (which also dedupe).
- **Direction is opt-in & inconsistent.** Pass `directed=True` to
  `Outgoing/IncomingEdges`; `AdjacentVertices` ignores direction. Wrap all
  traversal in `StateGraph` and always supply direction explicitly.
- **`SubGraphMatches` has no edge/direction/attribute matcher.** Implement the
  typed-attributed directed monomorphism ourselves in `rules.py` (or via the
  networkx bridge's `MultiDiGraphMatcher`).
- **Reserved dict keys:** topologic injects `category`, `ontology_class`,
  `ontology_uri`, `src`, `dst`, `index`. Don't reuse them; strip on read/JSON export.
- **Identity:** carrier mutates **in place**, but `Vertex` object identity is **not**
  preserved across ops — never cache `Vertex` refs; address nodes by stable `id` via
  `VertexByKeyValue`, never by coordinates (Stage-1 coords are arbitrary layout).
- **`AddEdge` drops edge dicts unless `transferEdgeDictionaries=True`.** Always pass it.
- **Bools coerce to int** in dictionaries (`True`→`1`); read `bidirectional` back as `bool`.

## Environment
Python 3.11, `topologicpy` 0.9.43, `networkx` 3.6, Jupyter (ipykernel/ipywidgets) —
all already installed. Stage-1 graphs have **no geometry**; vertex coordinates are
layout only (e.g. x=index, y=level), used for `Graph.Show`/`PyvisGraph`.

## Planned layout
```
graphtope/  model alphabet atomic composite rules grammar_dnf engine serialize topoview
notebooks/  01_graphtope.ipynb
tests/      mirror the notebook assertions
```

## Conventions
- Don't commit or push unless asked.
- Mirror surrounding code style; keep modules small, each maps to a spec section.
- Every operation must preserve well-formedness (§2.2) and be reversible (§4).
