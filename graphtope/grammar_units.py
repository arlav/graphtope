"""U/L section sub-grammars — unit interiors via REFINE (G3, spec §7.6.2).

Each non-terminal carries its own transformation grammar: ``G_U`` for the
K-type maisonette (``u_section``, split-level rising off the corridor) and
``G_L`` for the F-type maisonette (``l_section`` — the built F-unit *is* the
L-section; domain correction to Appendix A). ``refine_k`` / ``refine_f`` run
``hierarchy.Refine`` (the REPLACE to the sub-grammar's start graph, interface
``K`` = the non-terminal's incident edges, **routed** per edge class to the
architecturally correct interior node — SG0) and then
develop the interior with the sub-grammar's own DPO productions. Both return
the composed inverse ``ABSTRACT(S → n)``, so refinement is exactly reversible
(§4, §7.6.2).

Sub-alphabet: Σ is *open* (§3.1) — interior room kinds are ``subtype`` values
over ``generic`` (living / sleeping / kitchen / bath / void / entry) plus the
``internal`` staircase subtype; no new labels enter ``alphabet.NODE_LABELS``.

Grounding: the reference ``graphtope/models/U_units_realised.obj`` imports
cleanly (``exchange.graph_from_model``) but every object is named
``3-4-5_apartment.*`` — it carries no room-type names — so the *vocabulary* is
grounded on the spec (§7.6.2: lower + upper joined by V, an internal staircase,
the double-height void as a vertical adjacency to a shared volume) and the
built K/F types. The OBJ grounds the *structure and metrics*: unit envelopes
one bay wide (3.7 m ≈ the 3.66 m module) × 8.4 m deep spanning three storeys
("3-4-5"), partial-width mezzanine strips (1.7 × 8.4 m — the sleeping gallery,
leaving a double-height void over the rest of the living volume), and V-stacked
interior pieces (the split level is real). See ``tests/test_grammar_units.py``.
"""

from __future__ import annotations

from .alphabet import CORRIDOR, GENERIC, H, STAIRCASE, V
from .composite import OpSequence
from .hierarchy import Refine, UnitSpec
from .model import StateGraph
from .rules import Pattern, PEdge, PNode, Production

# --- sub-alphabet: registered in interior.py (Σ_int, SG1); re-exported here
from .interior import (BATH, DOOR, ENTRY, INTERNAL, KITCHEN,  # noqa: F401
                       LIVING, LOGGIA, ROOM, SLEEPING, STORAGE,
                       VOID, WC, WINDOW)

#: interior vocabulary per unit family (rooms are generic subtypes)
K_INTERIOR = frozenset({LIVING, SLEEPING, KITCHEN, BATH, VOID, WC, LOGGIA,
                        STORAGE})
F_INTERIOR = frozenset({ENTRY, LIVING, SLEEPING, KITCHEN, BATH, WC, LOGGIA,
                        STORAGE})
B_INTERIOR = frozenset({ENTRY, LIVING, KITCHEN, BATH})
R_INTERIOR = frozenset({ROOM, STORAGE})


# --- start graphs (the R of the REFINE span, §7.6.2) ----------------------
def k_unit() -> UnitSpec:
    """G_U start graph — the K-type maisonette, entered at corridor level:
    living (double-height, front) at the entry level, the sleeping gallery
    above (V) — in the built section the gallery reaches back **over the
    corridor** (plan §5.3, resolved 2026-08-09; 8 m overall) — and an internal
    stair connecting the split levels.

    Interface routing (SG0): the corridor face and anything below land on
    ``living`` (the entry level); a unit stacked *above* meets the gallery."""
    return UnitSpec(
        nodes=[("living", GENERIC, {"subtype": LIVING}),
               ("sleeping", GENERIC, {"subtype": SLEEPING}),
               ("stair", STAIRCASE, {"subtype": INTERNAL})],
        edges=[("sleeping", "living", V, False),   # the gallery above living
               ("living", "stair", H, True),
               ("sleeping", "stair", H, True)],
        anchor="living",
        interface={(H, CORRIDOR): "living",   # entered off the corridor
                   (V, "above"): "sleeping",  # stacked above → the gallery
                   (V, "below"): "living"},
    )


def f_unit() -> UnitSpec:
    """G_L start graph — the F-type maisonette, entered at corridor level: an
    entry hall at the corridor level, living dropping a floor below (V), an
    internal stair down.

    Interface routing (SG0): the corridor face and anything above land on
    ``entry`` (the F-unit tops out at corridor level); anything below meets
    the dropped ``living``."""
    return UnitSpec(
        nodes=[("entry", GENERIC, {"subtype": ENTRY}),
               ("living", GENERIC, {"subtype": LIVING}),
               ("stair", STAIRCASE, {"subtype": INTERNAL})],
        edges=[("entry", "living", V, False),      # entry directly above living
               ("entry", "stair", H, True),
               ("living", "stair", H, True)],
        anchor="entry",
        interface={(H, CORRIDOR): "entry",
                   (V, "above"): "entry",
                   (V, "below"): "living"},
    )


def b_unit() -> UnitSpec:
    """G_B start graph — the single-storey apartment: entry hall and living
    on one level (plan §SG2). The corridor face lands on the entry; stacked
    neighbours meet the living space (one storey — same level)."""
    return UnitSpec(
        nodes=[("entry", GENERIC, {"subtype": ENTRY}),
               ("living", GENERIC, {"subtype": LIVING})],
        edges=[("entry", "living", H, True)],
        anchor="entry",
        interface={(H, CORRIDOR): "entry",
                   (V, "above"): "living",
                   (V, "below"): "living"},
    )


def r_unit() -> UnitSpec:
    """G_R start graph — the banked room (the level-1 R bay): a single room
    entered through its host apartment; every interface edge lands on it."""
    return UnitSpec(
        nodes=[("bed", GENERIC, {"subtype": ROOM})],
        edges=[],
        anchor="bed",
    )


# --- production factories (DPO, §6) ---------------------------------------
def add_room(name: str, subtype: str, *, host_subtype: str,
             attrs: dict | None = None) -> Production:
    """Attach one ``subtype`` room (H, bidirectional) to a ``host_subtype``
    space, carrying ``attrs`` (e.g. ``form``/``face``). NAC: the host does not
    already serve such a room — so alternates of one room (niche vs separate
    room, bath at either level) stay mutually exclusive per host."""
    host = PNode("host", label=GENERIC, subtype=host_subtype)
    room = PNode("room", label=GENERIC, subtype=subtype, attrs=dict(attrs or {}))
    return Production(
        name,
        lhs=Pattern([host]),
        interface={"host"},
        rhs=Pattern([host, room], [PEdge("host", "room", orientation=H)]),
        nacs=[Pattern([host, PNode("existing", label=GENERIC, subtype=subtype)],
                      [PEdge("host", "existing", orientation=H)]),
              # …nor behind a door: interposition (§5.2) deletes the direct
              # edge, so the doored room needs its own NAC
              Pattern([host, PNode("dd", label=GENERIC, subtype=DOOR),
                       PNode("doored", label=GENERIC, subtype=subtype)],
                      [PEdge("host", "dd", orientation=H),
                       PEdge("dd", "doored", orientation=H)])],
        instantiates=f"+N({subtype}) + UNION",
    )


def door_between(name: str, a_subtype: str | None, b_subtype: str, *,
                 a_label: str = GENERIC) -> Production:
    """Interpose a ``door`` node in an existing H adjacency (§5.2: openings
    are nodes): the direct edge is *deleted* (a genuine edge-deleting DPO,
    like P3) and the door joins the two spaces. Re-application cannot match —
    the direct edge is gone — so no NAC is needed."""
    a = PNode("a", label=a_label, subtype=a_subtype)
    b = PNode("b", label=GENERIC, subtype=b_subtype)
    d = PNode("d", label=GENERIC, subtype=DOOR)
    return Production(
        name,
        lhs=Pattern([a, b], [PEdge("a", "b", orientation=H)]),
        interface={"a", "b"},
        rhs=Pattern([a, b, d], [PEdge("a", "d", orientation=H),
                                PEdge("d", "b", orientation=H)]),
        instantiates="+N(door) + SPLIT(adjacency)",
    )


def window_on(name: str, room_subtype: str) -> Production:
    """Give a room a ``window`` node on the façade (§5.2). NAC: the room is
    not already lit — one window per room at this grammar level."""
    room = PNode("room", label=GENERIC, subtype=room_subtype)
    w = PNode("w", label=GENERIC, subtype=WINDOW)
    return Production(
        name,
        lhs=Pattern([room]),
        interface={"room"},
        rhs=Pattern([room, w], [PEdge("room", "w", orientation=H)]),
        nacs=[Pattern([room, PNode("existing", label=GENERIC, subtype=WINDOW)],
                      [PEdge("room", "existing", orientation=H)])],
        instantiates="+N(window) + UNION",
    )


def _void(name: str, extent: str) -> Production:
    """The K-unit's double-height void over living: a shared volume directly
    above the living space (V), opening onto the sleeping gallery (H).
    ``extent`` = ``"partial"`` (the built 1.7 m gallery strip remains) or
    ``"full"`` (full-width void, the gallery reduced to a balcony edge). NAC:
    one void per living volume — so the two extents are mutually exclusive."""
    return Production(
        name,
        lhs=Pattern([PNode("lv", label=GENERIC, subtype=LIVING),
                     PNode("sl", label=GENERIC, subtype=SLEEPING)],
                    [PEdge("sl", "lv", orientation=V, bidirectional=False)]),
        interface={"lv", "sl"},
        rhs=Pattern([PNode("lv"), PNode("sl"),
                     PNode("vd", label=GENERIC, subtype=VOID,
                           attrs={"extent": extent})],
                    [PEdge("sl", "lv", orientation=V, bidirectional=False),
                     PEdge("vd", "lv", orientation=V, bidirectional=False),
                     PEdge("vd", "sl", orientation=H)]),
        nacs=[Pattern([PNode("lv"), PNode("sl"),
                       PNode("vv", label=GENERIC, subtype=VOID)],
                      [PEdge("vv", "lv", orientation=V)])],
        instantiates="+N(void) + UNION(V) + UNION",
    )


# GU-gallery-split · subdivide the sleeping gallery: a second sleeping room
# beside it, also over the living volume. NAC: at most one subdivision.
GU_GALLERY_SPLIT = Production(
    "GU-gallery-split",
    lhs=Pattern([PNode("sl", label=GENERIC, subtype=SLEEPING),
                 PNode("lv", label=GENERIC, subtype=LIVING)],
                [PEdge("sl", "lv", orientation=V, bidirectional=False)]),
    interface={"sl", "lv"},
    rhs=Pattern([PNode("sl"), PNode("lv"),
                 PNode("sl2", label=GENERIC, subtype=SLEEPING)],
                [PEdge("sl", "lv", orientation=V, bidirectional=False),
                 PEdge("sl2", "lv", orientation=V, bidirectional=False),
                 PEdge("sl", "sl2", orientation=H)]),
    nacs=[Pattern([PNode("sl"), PNode("lv"),
                   PNode("other", label=GENERIC, subtype=SLEEPING)],
                  [PEdge("sl", "other", orientation=H)])],
    instantiates="+N(sleeping) + UNION(V) + UNION",
)


# === the corpus (SG2) — five families + openings ==========================
# G_U · the K-type maisonette (rising; gallery over the corridor, §5.3)
GU_VOID = _void("GU-void", "partial")            # the built condition
GU_VOID_FULL = _void("GU-void-full", "full")
GU_KITCHEN = add_room("GU-kitchen", KITCHEN, host_subtype=LIVING,
                      attrs={"form": "niche"})
GU_KITCHEN_ROOM = add_room("GU-kitchen-room", KITCHEN, host_subtype=LIVING,
                           attrs={"form": "room"})
GU_BATH = add_room("GU-bath", BATH, host_subtype=SLEEPING)      # gallery level
GU_BATH_ENTRY = add_room("GU-bath-entry", BATH, host_subtype=LIVING)
GU_WC = add_room("GU-wc", WC, host_subtype=LIVING)
GU_LOGGIA = add_room("GU-loggia", LOGGIA, host_subtype=LIVING,
                     attrs={"face": "outer"})
GU_STORAGE = add_room("GU-storage", STORAGE, host_subtype=SLEEPING)

# G_L · the F-type maisonette (dropping; entered at corridor level)
GL_KITCHEN = add_room("GL-kitchen", KITCHEN, host_subtype=ENTRY,
                      attrs={"form": "niche"})
GL_BATH = add_room("GL-bath", BATH, host_subtype=ENTRY)
GL_SLEEPING = add_room("GL-sleeping", SLEEPING, host_subtype=LIVING)
GL_WC = add_room("GL-wc", WC, host_subtype=ENTRY)
GL_LOGGIA = add_room("GL-loggia", LOGGIA, host_subtype=LIVING,
                     attrs={"face": "outer"})
GL_STORAGE = add_room("GL-storage", STORAGE, host_subtype=ENTRY)

# G_B · the single-storey apartment (new)
GB_KITCHEN = add_room("GB-kitchen", KITCHEN, host_subtype=LIVING,
                      attrs={"form": "niche"})
GB_BATH = add_room("GB-bath", BATH, host_subtype=ENTRY)

# G_R · the banked room (new, small — entered through its host apartment)
GR_STORAGE = add_room("GR-storage", STORAGE, host_subtype=ROOM)

# openings (§5.2 — nodes, shared across families)
DOOR_CORRIDOR_LIVING = door_between("D-corridor-living", None, LIVING,
                                    a_label=CORRIDOR)   # the K front door
DOOR_CORRIDOR_ENTRY = door_between("D-corridor-entry", None, ENTRY,
                                   a_label=CORRIDOR)    # the F/B front door
DOOR_LIVING_KITCHEN = door_between("D-living-kitchen", LIVING, KITCHEN)
DOOR_SLEEPING_BATH = door_between("D-sleeping-bath", SLEEPING, BATH)
DOOR_LIVING_BATH = door_between("D-living-bath", LIVING, BATH)
DOOR_ENTRY_BATH = door_between("D-entry-bath", ENTRY, BATH)
DOOR_LIVING_WC = door_between("D-living-wc", LIVING, WC)
DOOR_ENTRY_WC = door_between("D-entry-wc", ENTRY, WC)
DOOR_APARTMENT_ROOM = door_between("D-apartment-room", "apartment", ROOM)
WINDOW_LIVING = window_on("W-living", LIVING)
WINDOW_SLEEPING = window_on("W-sleeping", SLEEPING)
WINDOW_ROOM = window_on("W-room", ROOM)

U_PRODUCTIONS = {p.name: p for p in (
    GU_VOID, GU_VOID_FULL, GU_KITCHEN, GU_KITCHEN_ROOM, GU_BATH,
    GU_BATH_ENTRY, GU_WC, GU_LOGGIA, GU_STORAGE, GU_GALLERY_SPLIT)}
L_PRODUCTIONS = {p.name: p for p in (
    GL_KITCHEN, GL_BATH, GL_SLEEPING, GL_WC, GL_LOGGIA, GL_STORAGE)}
B_PRODUCTIONS = {p.name: p for p in (GB_KITCHEN, GB_BATH)}
R_PRODUCTIONS = {p.name: p for p in (GR_STORAGE,)}
OPENING_PRODUCTIONS = {p.name: p for p in (
    DOOR_CORRIDOR_LIVING, DOOR_CORRIDOR_ENTRY, DOOR_LIVING_KITCHEN,
    DOOR_SLEEPING_BATH, DOOR_LIVING_BATH, DOOR_ENTRY_BATH, DOOR_LIVING_WC,
    DOOR_ENTRY_WC, DOOR_APARTMENT_ROOM,
    WINDOW_LIVING, WINDOW_SLEEPING, WINDOW_ROOM)}

#: the whole level-2 corpus — frozen at this scope (plan risk R2)
CORPUS = {**U_PRODUCTIONS, **L_PRODUCTIONS, **B_PRODUCTIONS,
          **R_PRODUCTIONS, **OPENING_PRODUCTIONS}


# --- refinement drivers (REFINE, then G_u's own productions, §7.6.2) ------
def _apply_in_unit(sg: StateGraph, prod: Production, pin: dict):
    """Apply ``prod`` at the match pinned to *this* unit's node ids (so a
    graph holding several refined units never cross-matches)."""
    ms = [m for m in prod.matches(sg)
          if all(m.get(k) == v for k, v in pin.items())]
    if not ms:
        raise ValueError(f"{prod.name}: no valid match inside the unit")
    return prod.apply_at(sg, ms[0])


def _refine(sg: StateGraph, node: str, unit: UnitSpec, steps: list) -> tuple:
    """REFINE ``node`` to ``unit``, then run ``steps`` = [(production,
    {pattern_name: local_name}, produced_local)]. Returns ``(inverse,
    produced)`` — the inverse is the composed ABSTRACT(S → n)."""
    r = Refine(node, unit)
    inverses = [r.apply(sg)]
    ids = dict(r.produced)
    for prod, pin_names, out_local in steps:
        app = _apply_in_unit(sg, prod, {p: ids[l] for p, l in pin_names.items()})
        inverses.append(app.inverse)
        (out_name,) = app.produced          # each step glues exactly one room
        ids[out_local] = app.produced[out_name]
    return OpSequence(list(reversed(inverses))), ids


def refine_k(sg: StateGraph, node: str, *, void: bool = True,
             kitchen: bool = True, bath: bool = True,
             void_extent: str = "partial", kitchen_form: str = "niche",
             bath_level: str = "gallery", wc: bool = False,
             loggia: bool = False, storage: bool = False,
             split_gallery: bool = False, doors: bool = False,
             windows: bool = False, front_door: bool = False) -> tuple:
    """Refine a ``u_section`` non-terminal into the K-type interior (G_U).
    Defaults reproduce the G3 interior exactly (void + kitchen niche + bath
    at the gallery); the SG2 options open the space: void extent (partial =
    the built strip / full), kitchen as niche or separate room, bath at
    gallery or entry level, wc, loggia on the outer face, storage under the
    gallery, a subdivided gallery, and §5.2 openings — doors on the closed
    rooms (a niche stays open), windows on every habitable room, the front
    door off the corridor. Returns ``(inverse, produced_ids)``."""
    steps = []
    if void:
        steps.append((GU_VOID if void_extent == "partial" else GU_VOID_FULL,
                      {"lv": "living", "sl": "sleeping"}, "void"))
    if kitchen:
        steps.append((GU_KITCHEN if kitchen_form == "niche" else GU_KITCHEN_ROOM,
                      {"host": "living"}, "kitchen"))
    if bath:
        steps.append((GU_BATH, {"host": "sleeping"}, "bath")
                     if bath_level == "gallery"
                     else (GU_BATH_ENTRY, {"host": "living"}, "bath"))
    if wc:
        steps.append((GU_WC, {"host": "living"}, "wc"))
    if loggia:
        steps.append((GU_LOGGIA, {"host": "living"}, "loggia"))
    if storage:
        steps.append((GU_STORAGE, {"host": "sleeping"}, "storage"))
    if split_gallery:
        steps.append((GU_GALLERY_SPLIT, {"sl": "sleeping", "lv": "living"},
                      "sleeping2"))
    if doors:
        if kitchen and kitchen_form == "room":
            steps.append((DOOR_LIVING_KITCHEN,
                          {"a": "living", "b": "kitchen"}, "door_kitchen"))
        if bath:
            steps.append((DOOR_SLEEPING_BATH, {"a": "sleeping", "b": "bath"},
                          "door_bath") if bath_level == "gallery"
                         else (DOOR_LIVING_BATH, {"a": "living", "b": "bath"},
                               "door_bath"))
        if wc:
            steps.append((DOOR_LIVING_WC, {"a": "living", "b": "wc"},
                          "door_wc"))
    if front_door:
        steps.append((DOOR_CORRIDOR_LIVING, {"b": "living"}, "front_door"))
    if windows:
        steps.append((WINDOW_LIVING, {"room": "living"}, "window_living"))
        steps.append((WINDOW_SLEEPING, {"room": "sleeping"}, "window_sleeping"))
        if split_gallery:
            steps.append((WINDOW_SLEEPING, {"room": "sleeping2"},
                          "window_sleeping2"))
    return _refine(sg, node, k_unit(), steps)


def refine_f(sg: StateGraph, node: str, *, kitchen: bool = True,
             bath: bool = True, sleeping: bool = False, wc: bool = False,
             loggia: bool = False, storage: bool = False, doors: bool = False,
             windows: bool = False, front_door: bool = False) -> tuple:
    """Refine an ``l_section`` non-terminal into the F-type interior (G_L).
    Defaults reproduce the G3 interior exactly (kitchen niche + bath at the
    entry level); SG2 adds the mirror set — a bedroom beside the dropped
    living, wc, loggia on the lower outer face, storage off the entry hall,
    and §5.2 openings. Returns ``(inverse, produced_ids)``."""
    steps = []
    if kitchen:
        steps.append((GL_KITCHEN, {"host": "entry"}, "kitchen"))
    if bath:
        steps.append((GL_BATH, {"host": "entry"}, "bath"))
    if sleeping:
        steps.append((GL_SLEEPING, {"host": "living"}, "sleeping"))
    if wc:
        steps.append((GL_WC, {"host": "entry"}, "wc"))
    if loggia:
        steps.append((GL_LOGGIA, {"host": "living"}, "loggia"))
    if storage:
        steps.append((GL_STORAGE, {"host": "entry"}, "storage"))
    if doors:
        if bath:
            steps.append((DOOR_ENTRY_BATH, {"a": "entry", "b": "bath"},
                          "door_bath"))
        if wc:
            steps.append((DOOR_ENTRY_WC, {"a": "entry", "b": "wc"}, "door_wc"))
    if front_door:
        steps.append((DOOR_CORRIDOR_ENTRY, {"b": "entry"}, "front_door"))
    if windows:
        steps.append((WINDOW_LIVING, {"room": "living"}, "window_living"))
        if sleeping:
            steps.append((WINDOW_SLEEPING, {"room": "sleeping"},
                          "window_sleeping"))
    return _refine(sg, node, f_unit(), steps)


def refine_b(sg: StateGraph, node: str, *, kitchen: bool = True,
             bath: bool = True, doors: bool = False, windows: bool = False,
             front_door: bool = False) -> tuple:
    """Refine a single-storey apartment (the B bay, ``generic``/``apartment``)
    into the G_B interior: entry + living on one level, kitchen niche, bath
    off the entry, §5.2 openings. Returns ``(inverse, produced_ids)``."""
    steps = []
    if kitchen:
        steps.append((GB_KITCHEN, {"host": "living"}, "kitchen"))
    if bath:
        steps.append((GB_BATH, {"host": "entry"}, "bath"))
    if doors and bath:
        steps.append((DOOR_ENTRY_BATH, {"a": "entry", "b": "bath"},
                      "door_bath"))
    if front_door:
        steps.append((DOOR_CORRIDOR_ENTRY, {"b": "entry"}, "front_door"))
    if windows:
        steps.append((WINDOW_LIVING, {"room": "living"}, "window_living"))
    return _refine(sg, node, b_unit(), steps)


def refine_r(sg: StateGraph, node: str, *, storage: bool = False,
             doors: bool = False, windows: bool = False) -> tuple:
    """Refine a banked room (the R bay) into the G_R interior: the room
    entered through its host apartment, optional storage, the entry door on
    the host edge, a window on the outer face. Refine the R **before** its
    host B — the door production matches the host while it is still an
    ``apartment``. Returns ``(inverse, produced_ids)``."""
    steps = []
    if storage:
        steps.append((GR_STORAGE, {"host": "bed"}, "storage"))
    if doors:
        steps.append((DOOR_APARTMENT_ROOM, {"b": "bed"}, "door_host"))
    if windows:
        steps.append((WINDOW_ROOM, {"room": "bed"}, "window"))
    return _refine(sg, node, r_unit(), steps)


def refine_pair(sg: StateGraph, k_node: str, f_node: str, *,
                void: bool = True, void_extent: str = "partial",
                k_opts: dict | None = None, f_opts: dict | None = None) -> tuple:
    """G_D — the double-loaded interlocked pair (§5.1, resolved 2026-08-09:
    paired refinement, not a third grammar). Refines the K and the F of one
    D bay with their own sub-grammars and enforces the explicit cross-unit
    constraint: **the K's double-height void and the F behind it cannot claim
    the same bay volume**, so a paired K may only take the partial-gallery
    void (the built condition). Returns ``(inverse, {"K": ids, "F": ids})``."""
    if void and void_extent != "partial":
        raise ValueError(
            "G_D pair constraint: a paired K's void must be 'partial' — "
            "the F behind it claims the back of the bay volume")
    inv_k, ids_k = refine_k(sg, k_node, void=void, void_extent="partial",
                            **(k_opts or {}))
    inv_f, ids_f = refine_f(sg, f_node, **(f_opts or {}))
    return OpSequence([inv_f, inv_k]), {"K": ids_k, "F": ids_f}


# === SG3 · the sampled option space (one slab, many interiors) ============
def sample_k_options(rng) -> dict:
    """Draw one K interior from G_U's option space. A paired K's void is
    forced to 'partial' downstream by ``refine_pair`` (§5.1) regardless of
    the draw. Probabilities lean toward the built condition."""
    return {
        "void": rng.random() < 0.85,
        "void_extent": "full" if rng.random() < 0.3 else "partial",
        "kitchen_form": "room" if rng.random() < 0.4 else "niche",
        "bath_level": "entry" if rng.random() < 0.35 else "gallery",
        "wc": rng.random() < 0.4,
        "loggia": rng.random() < 0.5,
        "storage": rng.random() < 0.4,
        "split_gallery": rng.random() < 0.35,
    }


def sample_f_options(rng) -> dict:
    """Draw one F interior from G_L's option space."""
    return {
        "sleeping": rng.random() < 0.75,
        "wc": rng.random() < 0.35,
        "loggia": rng.random() < 0.5,
        "storage": rng.random() < 0.45,
    }


def sample_b_options(rng) -> dict:
    """G_B has no per-unit alternates yet — variation comes from openings."""
    return {}


def sample_r_options(rng) -> dict:
    """Draw one banked-room interior from G_R's option space."""
    return {"storage": rng.random() < 0.5}
