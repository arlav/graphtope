# Graphtope

**A topology-driven graph grammar for architecture.**

`graphtope` builds and rewrites the space-adjacency graphs of buildings as a
typed, directed, weighted graph grammar — bridging **shape grammars, topology,
and graph grammars**. Architectural graphs are grown from a small set of
reversible operations and can be read back just as easily, with the Dom Narkomfin
building as the reference grammar. *(The name fuses **graph** + **-tope**, as in
polytope — a shape with topology.)*

The approach follows Dounas & Jabi, *Towards Bridging Shape and Graph Grammars
Through Topology* (eCAADe 43, 2025): topology is the bridge between a shape and
the graph that stands behind it. `graphtope` works at the **graph level first**;
geometry — via [TopologicPy](https://doi.org/10.5281/zenodo.11555172) — is
attached as a later stage.

> **Status:** early development. The design is fully specified in
> [`SPEC.md`](SPEC.md); the implementation is being built against it.

## What it does

- Represents a building as a **typed, directed, weighted, attributed graph** —
  spaces are nodes carrying a semantic label (`generic`, `corridor`, `staircase`,
  `u_section`, `l_section`, `entrance`); adjacencies are oriented edges
  (`H` horizontal / `V` vertical).
- Rewrites that graph with a **minimal set of reversible operations** that compound
  upward: **7 atomic edits → 6 core verbs** (replace, transform, union,
  difference, divide, other) **→ named productions** (the Narkomfin grammar).
- Is **reversible** — splitting one space into two and merging two into one are
  inverses, so a building can be taken apart as well as built up.
- Is **hierarchical and modular** — `u_section` / `l_section` units expand via
  their own sub-grammars, and separate block grammars are joined by a bridge.

## Install

```bash
git clone https://github.com/arlav/graphtope
cd graphtope
pip install -e .
```

Requires Python ≥ 3.10 and `networkx`.

## Quick start

```python
from graphtope import StateGraph
from graphtope import grammar_dnf as dnf

# axiom: two generic blocks (residential + condenser)
G = StateGraph.axiom()                 # b1:generic , b2:generic

# grow the residential block
dnf.add_internal_volume(G, "b1")       # split a block into adjacent spaces
dnf.add_corridor(G, ["s1", "s2"])      # insert a horizontal-circulation node
dnf.add_staircase(G, "c1")             # insert a vertical-circulation node

assert G.is_well_formed()              # invariant check
G.to_json("dnf_partial.json")          # serialise the graph
```

The full Dom Narkomfin derivation — and its reverse — is described in
[`SPEC.md` §8](SPEC.md).

## Repository layout

```
graphtope/
  model.py        # the graph object + well-formedness invariants
  alphabet.py     # node and edge label sets
  atomic.py       # the 7 reversible primitives
  composite.py    # split / merge and the six core verbs
  rules.py        # DPO productions + typed subgraph matcher
  grammar_dnf.py  # the Dom Narkomfin productions (P1–P9)
  engine.py       # apply / replay / invert derivations
  hierarchy.py    # sub-grammars (refine / abstract)
  compose.py      # modular block composition (bridge)
  serialize.py    # JSON I/O
  shape_iface.py  # Stage-2 boundary (label -> shape type)
SPEC.md           # the full specification
```

## Citation

> Dounas, T. & Jabi, W. (2025). *Towards Bridging Shape and Graph Grammars
> Through Topology.* Proceedings of eCAADe 43, Volume 1, pp. 663–672.

## License

TBD.
# graphtope
exploring building graph and shape grammar couplings with a strong topologic infrastructure
