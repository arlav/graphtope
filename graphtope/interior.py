"""Σ_int — the interior sub-alphabet and interior validity (SG1).

The second grammar level's vocabulary, promoted from bare strings to a frozen
registry: every interior kind carries its architectural meaning and the flags
the predicates and metrics need (habitable / wet / opening / circulation).
Σ stays open (§3.1) — interior kinds remain ``subtype`` values over ``generic``
(plus the ``internal`` staircase subtype); registration adds checkability and
one documented home, not new labels. ``metrics.INTERIOR_SUBTYPES`` and
``grammar_units``'s constants derive from here.

Per the plan §5.2 resolution (2026-08-09), **openings are first-class nodes**:
``door`` and ``window`` are registered alongside the rooms. The current
sub-grammars (G3) do not yet *place* openings — that is SG2 — so the opening
predicates hold vacuously until they appear, then arm themselves.

Interior validity mirrors ``validity.py``'s shape: individual checks take
``(sg, comps, adj)`` and return reason strings; ``violations`` / ``is_valid``
aggregate. Deferred honestly: wet-room *stacking* is a cross-level constraint
(SG6); one-entry-per-unit needs per-unit bookkeeping (SG3).

Grounding: dims are measured from ``U_units_realised.obj`` where available
(the 1.7 × 8.4 m sleeping-gallery strip); everything else awaits SG5's
room-labelled reference and is spec-grounded until then.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from . import alphabet as A
from .validity import CIRCULATION, _adjacency, _components


@dataclass(frozen=True)
class InteriorKind:
    """One registered interior kind (a row of Σ_int, paper Table 7)."""

    name: str
    describes: str
    habitable: bool = False
    wet: bool = False
    opening: bool = False
    circulation: bool = False
    dims: tuple | None = None    # measured (w, d) in metres, where grounded


#: the interior sub-alphabet — frozen; grow it here, nowhere else
SIGMA_INT = MappingProxyType({k.name: k for k in (
    InteriorKind("entry", "the unit's corridor-level hall"),
    InteriorKind("living", "the main volume — double-height in the K unit",
                 habitable=True),
    InteriorKind("dining", "eating space off living", habitable=True),
    InteriorKind("sleeping", "the sleeping gallery — in the built K section a "
                 "partial-width strip over the corridor (plan §5.3)",
                 habitable=True, dims=(1.7, 8.4)),
    InteriorKind("kitchen", "kitchen niche or room", wet=True),
    InteriorKind("bath", "bathroom", wet=True),
    InteriorKind("wc", "separate toilet", wet=True),
    InteriorKind("void", "double-height air over a living volume"),
    InteriorKind("loggia", "open-air room on the outer face"),
    InteriorKind("storage", "storage space"),
    InteriorKind("room", "a banked room behind its host apartment (the level-1 "
                 "R bay; develops under G_R in SG2)", habitable=True),
    InteriorKind("internal", "the unit's internal stair (staircase subtype)",
                 circulation=True),
    InteriorKind("door", "an opening between two spaces (§5.2: a node, "
                 "not an edge attribute)", opening=True),
    InteriorKind("window", "an opening in the façade of one room (§5.2)",
                 opening=True),
)})

# --- names as constants (single source; grammar_units re-exports) ---------
ENTRY, LIVING, DINING, SLEEPING = "entry", "living", "dining", "sleeping"
KITCHEN, BATH, WC, VOID = "kitchen", "bath", "wc", "void"
LOGGIA, STORAGE, ROOM, INTERNAL = "loggia", "storage", "room", "internal"
DOOR, WINDOW = "door", "window"

#: derived views (never restate these lists elsewhere)
ROOM_SUBTYPES = frozenset(k.name for k in SIGMA_INT.values()
                          if not k.opening and not k.circulation)
HABITABLE_SUBTYPES = frozenset(k.name for k in SIGMA_INT.values() if k.habitable)
WET_SUBTYPES = frozenset(k.name for k in SIGMA_INT.values() if k.wet)
OPENING_SUBTYPES = frozenset(k.name for k in SIGMA_INT.values() if k.opening)


def _subtype(sg, n) -> str | None:
    return sg.node_attrs(n).get("subtype")


def _interior_rooms(sg) -> list:
    return [n for n in sg.nodes() if _subtype(sg, n) in ROOM_SUBTYPES]


# === individual checks (each returns a list of reason strings) ===========
def check_rooms_reach_circulation(sg, comps, adj) -> list:
    """Every interior room (except the void — it is air, not floor) must reach
    circulation: its component contains a corridor / staircase (the unit's
    internal stair counts — it carries the staircase label)."""
    out = []
    for comp in comps:
        if any(sg.node_label(n) in CIRCULATION for n in comp):
            continue
        for n in comp:
            st = _subtype(sg, n)
            if st in ROOM_SUBTYPES and st != VOID:
                out.append(f"interior room {n!r} ({st}) cannot reach circulation")
    return out


def check_gallery_sits_over_living(sg, comps, adj) -> list:
    """A sleeping space must adjoin its living volume: V-above it (the K
    gallery — in the built section the strip reaches over the corridor, plan
    §5.3) or H-beside it (a bedroom off the lower F level, SG2's
    ``GL-sleeping``)."""
    out = []
    for n in sg.nodes():
        if _subtype(sg, n) != SLEEPING:
            continue
        over = any(e["src"] == n and e["orientation"] == A.V
                   and _subtype(sg, e["tgt"]) == LIVING for e in sg.edges())
        beside = any(e["orientation"] == A.H and n in (e["src"], e["tgt"])
                     and _subtype(sg, e["tgt"] if e["src"] == n else e["src"])
                     == LIVING
                     for e in sg.edges())
        if not (over or beside):
            out.append(f"sleeping {n!r} is neither above nor beside a living volume")
    return out


def check_void_adjoins_its_volume(sg, comps, adj) -> list:
    """A double-height void must open *over* a living volume (V down) and
    *onto* a room (H — the gallery it lights)."""
    out = []
    for n in sg.nodes():
        if _subtype(sg, n) != VOID:
            continue
        over = any(e["src"] == n and e["orientation"] == A.V
                   and _subtype(sg, e["tgt"]) == LIVING for e in sg.edges())
        onto = any(e["orientation"] == A.H and n in (e["src"], e["tgt"])
                   and _subtype(sg, e["tgt"] if e["src"] == n else e["src"])
                   in ROOM_SUBTYPES - {VOID}
                   for e in sg.edges())
        if not over:
            out.append(f"void {n!r} does not open over a living volume")
        if not onto:
            out.append(f"void {n!r} does not open onto a room")
    return out


def check_openings_well_formed(sg, comps, adj) -> list:
    """Openings are nodes (§5.2) with fixed valence: a door joins exactly two
    spaces (H both sides); a window belongs to exactly one room (its other
    side is the façade). Vacuous until SG2 places openings."""
    out = []
    for n in sg.nodes():
        st = _subtype(sg, n)
        if st not in OPENING_SUBTYPES:
            continue
        others = sorted(adj[n])
        spaces = [m for m in others if _subtype(sg, m) not in OPENING_SUBTYPES]
        if any(e["orientation"] != A.H for e in sg.edges()
               if n in (e["src"], e["tgt"])):
            out.append(f"{st} {n!r} has a non-H edge (openings join laterally)")
        if st == DOOR and (len(others) != 2 or len(spaces) != 2):
            out.append(f"door {n!r} must join exactly two spaces, has {others}")
        if st == WINDOW and (len(others) != 1 or len(spaces) != 1):
            out.append(f"window {n!r} must belong to exactly one room, has {others}")
    return out


def check_habitable_rooms_lit(sg, comps, adj) -> list:
    """Once a graph carries windows, every habitable interior room must have
    one (§5.2 makes daylight checkable). Vacuous until SG2 places windows —
    the check arms itself the moment the first window appears."""
    if not any(_subtype(sg, n) == WINDOW for n in sg.nodes()):
        return []
    out = []
    for n in _interior_rooms(sg):
        if _subtype(sg, n) not in HABITABLE_SUBTYPES:
            continue
        if not any(_subtype(sg, m) == WINDOW for m in adj[n]):
            out.append(f"habitable room {n!r} ({_subtype(sg, n)}) has no window")
    return out


#: the interior counterpart of validity.DEFAULT_CHECKS
INTERIOR_CHECKS = (
    check_rooms_reach_circulation,
    check_gallery_sits_over_living,
    check_void_adjoins_its_volume,
    check_openings_well_formed,
    check_habitable_rooms_lit,
)


def violations(sg, checks=INTERIOR_CHECKS) -> list:
    """All reasons ``sg``'s interiors are invalid (empty list ⇒ valid)."""
    adj = _adjacency(sg)
    comps = _components(sg, adj)
    out = []
    for check in checks:
        out.extend(check(sg, comps, adj))
    return out


def is_valid(sg, checks=INTERIOR_CHECKS) -> bool:
    return not violations(sg, checks)
