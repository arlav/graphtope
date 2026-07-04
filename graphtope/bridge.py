"""The graph→shape bridge — the graph grammar *drives* the shape grammar.

``narkomfin`` realises exact slabs but (until now) chose its parameters randomly;
the abstract graph grammar (P1–P8, ``generate``) derives rich typed topologies
but stopped at the graph. Here they meet:

    propose(seed)         abstract derivation over a slab-shaped production pool
    spec_from_graph(g)    read a ``SlabSpec`` off the proposal — corridors become
                          bands, the units each corridor serves become its bay
                          pattern (u_section→K, l_section→F, apartment→B)
    realise_spec(spec)    the shape grammar builds the slab (exact geometry,
                          adjacency derived from what touches)
    report(...)           honest coverage — what the proposal asked for, what the
                          slab realised, what it couldn't express

Division of labour: the graph grammar proposes the *programme* (how many
corridors, what mix of units each serves, the U/L interlocks); the shape grammar
owns the *armature* (stair cores + entrance are canonical, so P4/P5 are excluded
from the proposal pool) and the metric section. The abstract V interlock (P7,
l_section under two u_sections) is realised the way the built Narkomfin does it —
the F-unit entered off the same corridor, dropping below — and the report says so
rather than pretending the V edge became a slab face.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import alphabet as A
from . import narkomfin as nf
from . import validity
from .compare import typed_isomorphic
from .engine import Derivation
from .generate import RandomStrategy, generate, single_block_axiom
from .model import StateGraph

#: what each proposed unit label realises as (a bay char of the shape grammar)
UNIT_CHAR = {A.U_SECTION: "K", A.L_SECTION: "F", A.GENERIC: "B"}


@dataclass(frozen=True)
class SlabSpec:
    """What the graph grammar asked the shape grammar to build: one K/F/B bay
    pattern per band (band = corridor, in canonical id order), plus the node ids
    the slab section cannot express (reported, never silently dropped)."""

    band_patterns: tuple
    skipped: tuple = ()

    @property
    def units(self) -> int:
        return sum(len(p) for p in self.band_patterns)


def _h_adjacent_corridors(sg, n, corridors) -> list:
    return sorted(c for c in corridors
                  if any(e["orientation"] == A.H and {e["src"], e["tgt"]} == {n, c}
                         for e in sg.incident_edges(n)))


def _bay_pattern(k: int, f: int, b: int) -> str:
    """A canonical bay order for a band's unit counts — most-remaining first,
    avoiding repeats where possible, so (3K, 2F) reads ``KFKFK`` like the
    built section (the abstract graph has no bay order to preserve)."""
    remaining = {"K": k, "F": f, "B": b}
    out: list = []
    while any(remaining.values()):
        cands = sorted((c for c in "KFB" if remaining[c] > 0),
                       key=lambda c: (-remaining[c], "KFB".index(c)))
        pick = next((c for c in cands if not out or c != out[-1]), cands[0])
        out.append(pick)
        remaining[pick] -= 1
    return "".join(out)


def spec_from_graph(sg: StateGraph) -> SlabSpec | None:
    """Read a slab spec off an abstract proposal. Corridors (canonical order) are
    the bands. Each habitable unit is assigned to exactly one corridor — its
    first H-adjacent corridor, or (for an l_section placed by P7 under two
    u_sections) the corridor serving a u_section above it. Staircases and
    entrances are ignored (the armature is canonical); toilets and rooms that
    reach no corridor are recorded in ``skipped``. ``None`` if there is no
    corridor to hang a slab on."""
    corridors = sorted(n for n in sg.nodes() if sg.node_label(n) == A.CORRIDOR)
    if not corridors:
        return None
    counts = {c: {"K": 0, "F": 0, "B": 0} for c in corridors}
    skipped: list = []
    for n in sorted(sg.nodes()):
        lab = sg.node_label(n)
        if lab not in UNIT_CHAR:
            continue                            # corridor/staircase/entrance
        if lab == A.GENERIC and sg.node_attrs(n).get("subtype") == "toilet":
            skipped.append(n)                   # sub-room scale, not a bay unit
            continue
        hosts = _h_adjacent_corridors(sg, n, corridors)
        if not hosts and lab == A.L_SECTION:
            # P7 interlock: the L hangs under u_sections — enter it off their corridor
            ups = [e["src"] for e in sg.incident_edges(n)
                   if e["orientation"] == A.V and e["tgt"] == n
                   and sg.node_label(e["src"]) == A.U_SECTION]
            hosts = sorted({c for u in sorted(ups)
                            for c in _h_adjacent_corridors(sg, u, corridors)})
        if hosts:
            counts[hosts[0]][UNIT_CHAR[lab]] += 1
        else:
            skipped.append(n)                   # unreachable from any corridor
    return SlabSpec(tuple(_bay_pattern(**{k.lower(): v for k, v in counts[c].items()})
                          for c in corridors),
                    skipped=tuple(skipped))


def realise_spec(spec: SlabSpec) -> StateGraph:
    """The shape grammar builds the proposed slab (exact geometry, edges derived
    from real shared faces)."""
    return nf.derive_slab_from_patterns(list(spec.band_patterns))


# === the proposal pool (abstract side) ====================================
def slab_pool() -> tuple[dict, dict]:
    """Productions the graph grammar proposes slabs with, and their weights.
    P4/P5 (staircase/entrance) are deliberately absent — the shape grammar's
    armature owns vertical circulation and entry."""
    from .grammar_dnf import PRODUCTIONS
    from .grammar_params import add_units
    pool = {p: PRODUCTIONS[p] for p in ("P1", "P3", "P6", "P7")}
    weights = {"P1": 2.0, "P3": 2.5, "P6": 2.0, "P7": 1.5}
    for label, k in ((A.U_SECTION, 3), (A.L_SECTION, 2)):
        p = add_units(label, k)
        pool[p.name] = p
        weights[p.name] = 1.0
    return pool, weights


def propose(seed: int, *, max_steps: int = 10) -> Derivation:
    """One abstract proposal: a recorded (replayable, invertible) derivation from
    a single-block axiom over the slab pool."""
    pool, weights = slab_pool()
    return generate(RandomStrategy(productions=pool, weights=weights,
                                   max_steps=max_steps, seed=seed),
                    single_block_axiom())


# === honest coverage ======================================================
def report(abstract: StateGraph, spec: SlabSpec, slab: StateGraph) -> dict:
    """What the proposal asked for vs. what the slab realised. ``docked`` counts
    units that really share a face with their band's corridor (in the realised
    graph, whose edges *are* shared faces); ``interlocks_reinterpreted`` counts
    the abstract u→l V edges realised as corridor-entered F-units."""
    docked = sum(1 for e in slab.edges()
                 if A.CORRIDOR in (slab.node_label(e["src"]), slab.node_label(e["tgt"]))
                 and any(slab.node_label(n) in UNIT_CHAR
                         for n in (e["src"], e["tgt"])))
    v_interlocks = sum(1 for e in abstract.edges()
                       if e["orientation"] == A.V
                       and abstract.node_label(e["src"]) == A.U_SECTION
                       and abstract.node_label(e["tgt"]) == A.L_SECTION)
    return {"units_proposed": spec.units,
            "units_realised": sum(1 for n in slab.nodes()
                                  if slab.node_label(n) in UNIT_CHAR),
            "units_docked": docked,
            "bands": len(spec.band_patterns),
            "skipped": list(spec.skipped),
            "interlocks_reinterpreted": v_interlocks,
            "valid": validity.is_valid(slab)}


# === end-to-end: the grammar-driven catalogue =============================
@dataclass
class Variant:
    """One grammar-driven variant: the abstract proposal (replayable derivation),
    the spec read off it, the realised slab, and the coverage report."""

    derivation: Derivation
    spec: SlabSpec
    slab: StateGraph
    coverage: dict = field(default_factory=dict)

    @property
    def sg(self) -> StateGraph:                 # exchange.export_* duck-type
        return self.slab


def grammar_catalogue(n: int = 6, *, seed: int = 0, max_steps: int = 10,
                      max_attempts: int | None = None) -> list:
    """Up to ``n`` distinct valid slabs, every one *proposed by the graph grammar*
    and realised by the shape grammar. Dedup is typed isomorphism on the realised
    slab; validity is checked on the realised slab (the geometry that would be
    built). Returns ``Variant`` objects."""
    max_attempts = max_attempts if max_attempts is not None else n * 15
    out: list = []
    i = 0
    while len(out) < n and i < max_attempts:
        d = propose(seed + i, max_steps=max_steps)
        i += 1
        spec = spec_from_graph(d.sg)
        if spec is None or spec.units == 0:
            continue
        slab = realise_spec(spec)
        if not validity.is_valid(slab):
            continue
        if any(typed_isomorphic(slab, v.slab) for v in out):
            continue
        out.append(Variant(d, spec, slab, report(d.sg, spec, slab)))
    return out
