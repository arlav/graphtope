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
the F-unit entered off the same corridor as its u_sections, **sharing a bay with
one of them** (a ``D`` bay: K front, F back, double-loaded) — and the report says
so rather than pretending the V edge became a slab face. A generic room the
abstract grammar grew off another room (P1 chain, no corridor of its own) is
realised **double-banked behind its host's bay** (an ``R`` bay: apartment front,
room behind, entered through the apartment) — one room deep; deeper chains are
still reported as skipped, the honest boundary of the slab section.
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
    """What the graph grammar asked the shape grammar to build: one K/F/B/D/R
    bay pattern per band (band = corridor, in canonical id order), plus the node
    ids the slab section cannot express (reported, never silently dropped)."""

    band_patterns: tuple
    skipped: tuple = ()

    @property
    def units(self) -> int:
        """Habitable spaces asked for (a D bay holds K+F, an R bay holds B+room)."""
        return sum(2 if ch in "DR" else 1
                   for p in self.band_patterns for ch in p if ch != ".")


def _h_adjacent_corridors(sg, n, corridors) -> list:
    return sorted(c for c in corridors
                  if any(e["orientation"] == A.H and {e["src"], e["tgt"]} == {n, c}
                         for e in sg.incident_edges(n)))


def _h_neighbours(sg, n) -> set:
    return {e["src"] if e["tgt"] == n else e["tgt"]
            for e in sg.incident_edges(n) if e["orientation"] == A.H}


def _bay_pattern(k: int, f: int, b: int, d: int = 0, r: int = 0) -> str:
    """A canonical bay order for a band's unit counts — most-remaining first,
    avoiding repeats where possible, so (3K, 2F) reads ``KFKFK`` like the
    built section (the abstract graph has no bay order to preserve). With
    d == r == 0 this is exactly the K/F/B-only ordering."""
    remaining = {"K": k, "F": f, "B": b, "D": d, "R": r}
    out: list = []
    while any(remaining.values()):
        cands = sorted((c for c in "KFBDR" if remaining[c] > 0),
                       key=lambda c: (-remaining[c], "KFBDR".index(c)))
        pick = next((c for c in cands if not out or c != out[-1]), cands[0])
        out.append(pick)
        remaining[pick] -= 1
    return "".join(out)


def spec_from_graph(sg: StateGraph) -> SlabSpec | None:
    """Read a slab spec off an abstract proposal. Corridors (canonical order) are
    the bands. Each habitable unit is assigned to exactly one corridor — its
    first H-adjacent corridor. An l_section placed by P7 under two u_sections is
    hosted by the corridor serving its u_sections and **pairs with one of its
    K's into a D bay** (K front, F back — the built interlock). A generic room
    with no corridor of its own (P1's room-off-room chain) is **banked behind**
    a corridor-served apartment it is H-adjacent to — that host's bay becomes R
    (one room per host, one level deep). Staircases and entrances are ignored
    (the armature is canonical); toilets and rooms nothing can host are recorded
    in ``skipped``. ``None`` if there is no corridor to hang a slab on."""
    corridors = sorted(n for n in sg.nodes() if sg.node_label(n) == A.CORRIDOR)
    if not corridors:
        return None
    counts = {c: {"K": 0, "F": 0, "B": 0, "D": 0, "R": 0} for c in corridors}
    host_of: dict = {}       # habitable node -> the corridor that serves it
    interlocked: list = []   # (l_section, host corridor) placed by P7
    unplaced: list = []      # generic rooms that reach no corridor directly
    skipped: list = []
    for n in sorted(sg.nodes()):
        lab = sg.node_label(n)
        if lab not in UNIT_CHAR:
            continue                            # corridor/staircase/entrance
        if lab == A.GENERIC and sg.node_attrs(n).get("subtype") == "toilet":
            skipped.append(n)                   # sub-room scale, not a bay unit
            continue
        hosts = _h_adjacent_corridors(sg, n, corridors)
        if hosts:
            host_of[n] = hosts[0]
            counts[hosts[0]][UNIT_CHAR[lab]] += 1
        elif lab == A.L_SECTION:
            # P7 interlock: the L hangs under u_sections — enter it off their corridor
            ups = [e["src"] for e in sg.incident_edges(n)
                   if e["orientation"] == A.V and e["tgt"] == n
                   and sg.node_label(e["src"]) == A.U_SECTION]
            c_hosts = sorted({c for u in sorted(ups)
                              for c in _h_adjacent_corridors(sg, u, corridors)})
            if c_hosts:
                interlocked.append((n, c_hosts[0]))
            else:
                skipped.append(n)               # unreachable from any corridor
        elif lab == A.GENERIC:
            unplaced.append(n)                  # maybe bankable behind a host
        else:
            skipped.append(n)
    # P7 interlocks: pair the L with one of its corridor's K's into a D bay
    # (the built form — same bay, K front / F back); no K left ⇒ its own F bay.
    for l, c in interlocked:
        if counts[c]["K"] > 0:
            counts[c]["K"] -= 1
            counts[c]["D"] += 1
        else:
            counts[c]["F"] += 1
        host_of[l] = c
    # P1 chains, one deep: bank the room behind a corridor-served apartment
    banked: dict = {}        # host apartment -> its banked room (max one each)
    for room in unplaced:
        cands = sorted(m for m in _h_neighbours(sg, room)
                       if sg.node_label(m) == A.GENERIC and m in host_of
                       and m not in banked)
        if cands:
            host = cands[0]
            counts[host_of[host]]["B"] -= 1
            counts[host_of[host]]["R"] += 1
            banked[host] = room
        else:
            skipped.append(room)                # deeper than one room: honest skip
    return SlabSpec(tuple(_bay_pattern(**{k.lower(): v for k, v in counts[c].items()})
                          for c in corridors),
                    skipped=tuple(sorted(skipped)))


def realise_spec(spec: SlabSpec) -> StateGraph:
    """The shape grammar builds the proposed slab (exact geometry, edges derived
    from real shared faces)."""
    return nf.derive_slab_from_patterns(list(spec.band_patterns))


# === level 2 — refine each unit's interior (G3 sub-grammars) ==============
def refine_units(slab: StateGraph, *, void: bool = True, kitchen: bool = True,
                 bath: bool = True, all_bays: bool = False,
                 k_opts: dict | None = None, f_opts: dict | None = None,
                 b_opts: dict | None = None, r_opts: dict | None = None,
                 plan: dict | None = None,
                 seed: int | None = None) -> tuple[StateGraph, "OpSequence"]:
    """Drive the **second** grammar level: refine every unit in a realised
    slab into its interior sub-grammar (``grammar_units``). Each unit's
    exterior adjacencies (the corridor face, any interlock) are routed to the
    architecturally correct interior node by ``hierarchy.Refine`` (SG0), so
    the slab's connectivity survives. Returns ``(refined, inverse)``:
    applying ``inverse`` collapses every interior back, restoring ``slab``
    exactly (reversible, §7.6.2). The caller's ``slab`` is not mutated.

    By default only K/F maisonettes refine (the G3 behaviour, exactly).
    ``all_bays=True`` develops **every** bay type the bridge realises (SG2):
    banked R rooms first (their host door needs the apartment intact), then
    B apartments, then the D pairs via ``refine_pair`` (the §5.1 cross-unit
    constraint), then unpaired K/F. ``k_opts``/``f_opts``/``b_opts``/
    ``r_opts`` pass the SG2 options through (wc, loggia, storage,
    split_gallery, doors, windows, front_door, …).

    SG3: a ``plan`` (from ``interior_plan``) gives each unit its *own*
    options — the replayable sub-derivation record — plus the building-level
    opening choices under ``"_openings"``; ``seed`` samples such a plan.
    Per-unit plan entries override the ``*_opts`` bases; the same plan always
    reproduces the same refined graph exactly.

    The refined interiors are graph-level topology (§7.6.2), not placed
    geometry — unlike the slab, they carry no boxes, so ``boxes_of`` applies
    to the slab, not to the refined graph."""
    from . import grammar_units as gu
    from .composite import OpSequence
    from .serialize import from_dict, to_dict
    g = from_dict(to_dict(slab))                 # refine a copy — leave the slab intact
    if seed is not None and plan is None:
        import random
        plan = interior_plan(slab, random.Random(seed))
    openings = dict(plan.get("_openings", {})) if plan else {}
    r_openings = {k: v for k, v in openings.items()
                  if k in ("doors", "windows")}  # G_R has no front door

    def _po(n, base):                # per-unit options: the plan overrides
        o = dict(base or {})
        if plan is not None:
            o.update(plan.get(n, {}))
        return o

    inverses = []
    if all_bays:
        rooms = [n for n in sorted(g.nodes())
                 if g.node_label(n) == A.GENERIC
                 and g.node_attrs(n).get("subtype") == "room"]
        for n in rooms:                          # R before B: host door
            inverses.append(gu.refine_r(g, n, **{**_po(n, r_opts),
                                                 **r_openings})[0])
        boxes = [n for n in sorted(g.nodes())
                 if g.node_label(n) == A.GENERIC
                 and g.node_attrs(n).get("subtype") == "apartment"]
        for n in boxes:
            inverses.append(gu.refine_b(g, n, kitchen=kitchen, bath=bath,
                                        **{**_po(n, b_opts), **openings})[0])
    units = [n for n in sorted(g.nodes())
             if g.node_label(n) in (A.U_SECTION, A.L_SECTION)]
    paired = set()
    if all_bays:
        for n in units:                          # D bays: the §5.1 pair driver
            mate = g.node_attrs(n).get("pair")
            if not mate or n in paired or g.node_label(n) != A.U_SECTION:
                continue
            if mate in units:
                ko = _po(n, k_opts)
                ko.pop("void_extent", None)      # a paired K is always partial
                fo = _po(mate, f_opts)
                inv, _ = gu.refine_pair(
                    g, n, mate, void=ko.pop("void", void),
                    k_opts={"kitchen": kitchen, "bath": bath, **ko, **openings},
                    f_opts={"kitchen": kitchen, "bath": bath, **fo, **openings})
                inverses.append(inv)
                paired.update((n, mate))
    for n in units:
        if n in paired:
            continue
        if g.node_label(n) == A.U_SECTION:
            ko = _po(n, k_opts)
            inv, _ = gu.refine_k(g, n, void=ko.pop("void", void),
                                 kitchen=kitchen, bath=bath,
                                 **{**ko, **openings})
        else:
            inv, _ = gu.refine_f(g, n, kitchen=kitchen, bath=bath,
                                 **{**_po(n, f_opts), **openings})
        inverses.append(inv)
    return g, OpSequence(list(reversed(inverses)))


# === SG3 — one slab, many interiors =======================================
def interior_plan(slab: StateGraph, rng, *, doors: bool = True,
                  windows: bool = True, front_doors: bool = True) -> dict:
    """Sample one replayable interior plan for ``slab``: each unit draws its
    own sub-grammar options (``grammar_units.sample_*_options``); the opening
    choices live under ``"_openings"`` and are building-level — doors and
    windows are all-or-nothing per building, because SG1's daylight check
    arms on the first window (see STATUS 2026-08-11)."""
    from . import grammar_units as gu
    plan: dict = {"_openings": {"doors": doors, "windows": windows,
                                "front_door": front_doors}}
    for n in sorted(slab.nodes()):
        lab = slab.node_label(n)
        sub = slab.node_attrs(n).get("subtype")
        if lab == A.U_SECTION:
            plan[n] = gu.sample_k_options(rng)
        elif lab == A.L_SECTION:
            plan[n] = gu.sample_f_options(rng)
        elif lab == A.GENERIC and sub == "apartment":
            plan[n] = gu.sample_b_options(rng)
        elif lab == A.GENERIC and sub == "room":
            plan[n] = gu.sample_r_options(rng)
    return plan


@dataclass
class InteriorVariant:
    """One interior of a slab (SG3): the refined level-2 graph, the exact
    inverse back to the slab, and the replayable plan that derives it."""

    graph: StateGraph
    inverse: object                  # OpSequence — ABSTRACT back to the slab
    plan: dict


def interior_variants(slab: StateGraph, n: int = 8, *, seed: int = 0,
                      doors: bool = True, windows: bool = True,
                      front_doors: bool = True) -> list:
    """SG3 — one block-level slab → ``n`` distinct, valid interior variants.
    Sample per-unit sub-derivations (``interior_plan``), refine every bay
    type, filter on SG1's interior predicates (honesty — violations are not
    expected from the drivers), and de-duplicate by typed isomorphism at
    level 2. Each variant carries its replayable plan and exact inverse."""
    import random
    from . import interior
    rng = random.Random(seed)
    out: list = []
    attempts = 0
    while len(out) < n and attempts < n * 15:
        attempts += 1
        plan = interior_plan(slab, rng, doors=doors, windows=windows,
                             front_doors=front_doors)
        refined, inv = refine_units(slab, all_bays=True, plan=plan)
        if interior.violations(refined):
            continue
        if any(typed_isomorphic(refined, v.graph) for v in out):
            continue
        out.append(InteriorVariant(refined, inv, plan))
    return out


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
    graph, whose edges *are* shared faces); ``rooms_banked`` counts rooms entered
    through their host apartment (R bays — a real face with the host, not the
    corridor); ``interlocks_reinterpreted`` counts the abstract u→l V edges,
    realised as same-bay front/back D pairs entered off the corridor."""
    docked = sum(1 for e in slab.edges()
                 if A.CORRIDOR in (slab.node_label(e["src"]), slab.node_label(e["tgt"]))
                 and any(slab.node_label(n) in UNIT_CHAR
                         for n in (e["src"], e["tgt"])))
    banked = sum(1 for n in slab.nodes()
                 if slab.node_label(n) == A.GENERIC
                 and slab.node_attrs(n).get("subtype") == "room")
    v_interlocks = sum(1 for e in abstract.edges()
                       if e["orientation"] == A.V
                       and abstract.node_label(e["src"]) == A.U_SECTION
                       and abstract.node_label(e["tgt"]) == A.L_SECTION)
    return {"units_proposed": spec.units,
            "units_realised": sum(1 for n in slab.nodes()
                                  if slab.node_label(n) in UNIT_CHAR),
            "units_docked": docked,
            "rooms_banked": banked,
            "bands": len(spec.band_patterns),
            "skipped": list(spec.skipped),
            "interlocks_reinterpreted": v_interlocks,
            "valid": validity.is_valid(slab)}


# === end-to-end: the grammar-driven catalogue =============================
@dataclass
class Variant:
    """One grammar-driven variant across both grammar levels: the abstract
    proposal (replayable derivation), the spec read off it, the realised slab
    (level 1), the coverage report, and — when refined — the interior-refined
    graph (level 2) with the inverse that collapses it back to the slab."""

    derivation: Derivation
    spec: SlabSpec
    slab: StateGraph
    coverage: dict = field(default_factory=dict)
    refined: StateGraph | None = None
    refined_inverse: object = None

    @property
    def sg(self) -> StateGraph:                 # exchange.export_* duck-type
        return self.slab


def grammar_catalogue(n: int = 6, *, seed: int = 0, max_steps: int = 10,
                      max_attempts: int | None = None, refine: bool = False) -> list:
    """Up to ``n`` distinct valid slabs, every one *proposed by the graph grammar*
    and realised by the shape grammar. Dedup is typed isomorphism on the realised
    slab; validity is checked on the realised slab (the geometry that would be
    built). With ``refine=True`` each variant also carries its **level-2**
    interior-refined graph (``refine_units``) and the inverse back to the slab.
    Returns ``Variant`` objects."""
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
        v = Variant(d, spec, slab, report(d.sg, spec, slab))
        if refine:
            v.refined, v.refined_inverse = refine_units(slab)
        out.append(v)
    return out
