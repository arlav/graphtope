"""The Narkomfin shape grammar — circulation-first, geometry-exact (rebuild).

One grammar whose productions are *shape rules*: they add a node **and** its exact
real-metre box (folded into the node's attributes), so the typed graph and the
geometry are a single representation that cannot diverge. Adjacency edges are the
faces that actually touch.

Productions (circulation-first):
    add_corridor_spine   the armature — a corridor at a band level
    add_stair_cores      vertical circulation capping the ends (all bands)
    anchor_K(bay)        a K-type maisonette rising above the corridor  → u_section
    anchor_F(bay)        an F-type maisonette dropping below            → l_section
    anchor_box(bay)      a single-storey apartment                      → generic
    anchor_KF(bay)       the built interlock in ONE bay: K front + F back
    anchor_room_behind   an apartment with a room double-banked behind it

The section is the real Narkomfin principle: **one corridor every three floors**
serving K-units up and F-units down that interlock across the 3-floor module.
Geometry read back with ``boxes_of(g)``; dimensions are the real module.
"""

from __future__ import annotations

from . import alphabet as A
from .model import StateGraph

# real Narkomfin module (metres), from the imported model
BAY = 3.66
CORRIDOR_DEPTH = 2.8
UNIT_DEPTH = 8.42
ROOM_DEPTH = UNIT_DEPTH / 2  # a double-banked room behind a front apartment
FLOOR = 3.0
MODULE = 3 * FLOOR          # a section module is three floors (corridor every 3rd)
K_HEIGHT = 8.0              # the K maisonette section (confirmed vs the built section,
                            # 2026-08-09): 8 m tall, sleeping gallery over the corridor


def _place(g: StateGraph, nid: str, label: str, box, subtype: str | None = None,
           **attrs):
    """Add a node carrying its exact box in attributes (geometry == graph)."""
    x, y, z, w, d, h = box
    g.add_node(label, id=nid, subtype=subtype, **attrs,
               level=int(round(z / FLOOR)),
               x=round(x, 3), y=round(y, 3), z=round(z, 3),
               w=round(w, 3), d=round(d, 3), h=round(h, 3))


def boxes_of(g: StateGraph) -> dict:
    """Read every node's box ``(x, y, z, w, d, h)`` from its attributes."""
    out = {}
    for n in g.nodes():
        a = g.node_attrs(n)
        out[n] = (a["x"], a["y"], a["z"], a["w"], a["d"], a["h"])
    return out


# === the circulation-first shape productions =============================
def add_corridor_spine(g: StateGraph, band: int, n_bays: int, *,
                       bay=BAY, cd=CORRIDOR_DEPTH, floor=FLOOR) -> str:
    """P1 — the armature: a corridor spine at this band's level (z = 2F + 3F·band,
    so the lowest F-units sit on the ground)."""
    cid = f"corridor_{band}"
    zc = 2 * floor + MODULE * band
    _place(g, cid, A.CORRIDOR, (0.0, -cd / 2, zc, n_bays * bay, cd, floor))
    return cid


def add_stair_cores(g: StateGraph, corridors: list, n_bays: int, *,
                    bay=BAY, cd=CORRIDOR_DEPTH, floor=FLOOR, entrance=True) -> None:
    """P2 — vertical cores capping both ends, spanning all served bands + an
    entrance at grade (geometry only)."""
    zs = [g.node_attrs(c)["z"] for c in corridors]
    z0, z1 = min(zs), max(zs) + floor
    for sid, x0 in (("stair_W", -bay), ("stair_E", n_bays * bay)):
        _place(g, sid, A.STAIRCASE, (x0, -cd / 2, z0 - 2 * floor, bay, cd, (z1 - z0) + 2 * floor))
    if entrance:
        _place(g, "entrance", A.ENTRANCE, (-bay, cd / 2, 0.0, bay, 2.5, floor))


def anchor_K(g: StateGraph, corridor: str, band: int, bay_i: int, *,
             bay=BAY, cd=CORRIDOR_DEPTH, ud=UNIT_DEPTH, floor=FLOOR,
             height=K_HEIGHT, **attrs) -> str:
    """P3 — a K-type maisonette on the **front**, rising 8 m from the corridor
    level (u_section). The confirmed section (plan §5.3, 2026-08-09):
    double-height living in front, the sleeping gallery reaching back **over
    the corridor** — the over-corridor wing is interior (level-2) geometry, so
    the level-1 box is the front zone at the full section height."""
    zc = g.node_attrs(corridor)["z"]
    uid = f"K_{band}_{bay_i}"
    _place(g, uid, A.U_SECTION, (bay_i * bay, cd / 2, zc, bay, ud, height),
           **attrs)
    return uid


def anchor_F(g: StateGraph, corridor: str, band: int, bay_i: int, *,
             bay=BAY, cd=CORRIDOR_DEPTH, ud=UNIT_DEPTH, floor=FLOOR,
             **attrs) -> str:
    """P4 — an F-type maisonette on the **back**, entered at the corridor with
    living dropping a floor below (l_section) — the section interlock."""
    zc = g.node_attrs(corridor)["z"]
    fid = f"F_{band}_{bay_i}"
    _place(g, fid, A.L_SECTION, (bay_i * bay, -cd / 2 - ud, zc - floor, bay, ud, 2 * floor),
           **attrs)
    return fid


def anchor_box(g: StateGraph, corridor: str, band: int, bay_i: int, *,
               bay=BAY, cd=CORRIDOR_DEPTH, ud=UNIT_DEPTH, floor=FLOOR) -> str:
    """P5 — a single-storey apartment on the front (generic)."""
    zc = g.node_attrs(corridor)["z"]
    aid = f"box_{band}_{bay_i}"
    _place(g, aid, A.GENERIC, (bay_i * bay, cd / 2, zc, bay, ud, floor), subtype="apartment")
    return aid


def anchor_KF(g: StateGraph, corridor: str, band: int, bay_i: int, *,
              bay=BAY, cd=CORRIDOR_DEPTH, ud=UNIT_DEPTH, floor=FLOOR) -> tuple:
    """P6 — the built interlock in **one** bay: a K rising on the front *and* an
    F dropping on the back of the same bay (double-loaded front/back, as built —
    the K and F share the bay and interlock across the section module).

    The pair is recorded on both nodes as a ``pair`` attribute (plan §5.1,
    resolved 2026-08-09: paired refinement + explicit cross-unit constraint).
    It is an attribute, **not** an edge — the pair meets only through the
    corridor, and every graph edge must remain a real shared face."""
    kid, fid = f"K_{band}_{bay_i}", f"F_{band}_{bay_i}"
    return (anchor_K(g, corridor, band, bay_i, bay=bay, cd=cd, ud=ud, floor=floor,
                     pair=fid),
            anchor_F(g, corridor, band, bay_i, bay=bay, cd=cd, ud=ud, floor=floor,
                     pair=kid))


def anchor_room_behind(g: StateGraph, corridor: str, band: int, bay_i: int, *,
                       bay=BAY, cd=CORRIDOR_DEPTH, ud=UNIT_DEPTH, rd=ROOM_DEPTH,
                       floor=FLOOR) -> tuple:
    """P7 — a front apartment with a room double-banked **behind** it: the room
    is entered through the apartment, not the corridor (realises the abstract
    grammar's room-off-room chain, one room deep)."""
    aid = anchor_box(g, corridor, band, bay_i, bay=bay, cd=cd, ud=ud, floor=floor)
    zc = g.node_attrs(corridor)["z"]
    rid = f"room_{band}_{bay_i}"
    _place(g, rid, A.GENERIC, (bay_i * bay, cd / 2 + ud, zc, bay, rd, floor),
           subtype="room")
    return (aid, rid)


_ANCHOR = {"K": anchor_K, "F": anchor_F, "B": anchor_box,
           "D": anchor_KF, "R": anchor_room_behind}


def derive_adjacency(g: StateGraph) -> None:
    """Derive every edge from the geometry — an edge iff two boxes share a real
    face (orientation from the touch axis, V above→below). Guarantees the graph
    and the geometry are one and the same."""
    from .exchange import _touch_axis
    from .realise import _faces_touch
    boxes = boxes_of(g)
    ids = list(boxes)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if not _faces_touch(boxes[a], boxes[b]):
                continue
            if _touch_axis(boxes[a], boxes[b]) == "z":
                src, tgt = (a, b) if boxes[a][2] > boxes[b][2] else (b, a)
                g.add_edge(src, tgt, A.V, bidirectional=False)
            else:
                g.add_edge(a, b, A.H)


# === derivation: assemble a slab ========================================
def derive_slab_from_patterns(band_patterns: list) -> StateGraph:
    """Assemble a slab from **per-band** bay patterns (the graph→shape bridge
    entry point): band ``b`` gets a corridor of ``len(band_patterns[b])`` bays
    with units anchored per its pattern (chars K/F/B, D = K front + F back in
    one bay, R = apartment + room banked behind; ``.`` leaves a bay empty).
    Bands may be ragged — an empty pattern yields a units-free corridor spanning
    the widest band. The west stair core reaches every band; geometry is placed
    by the shape productions and adjacency then *derived* from what touches."""
    g = StateGraph()
    n_max = max([len(p) for p in band_patterns] + [1])
    corridors = []
    for b, pattern in enumerate(band_patterns):
        cid = add_corridor_spine(g, b, len(pattern) or n_max)
        corridors.append(cid)
        for i, ch in enumerate(pattern):
            if ch != ".":
                _ANCHOR[ch](g, cid, b, i)
    add_stair_cores(g, corridors, n_max)
    derive_adjacency(g)
    return g


def derive_slab(bands: int = 2, n_bays: int = 5, pattern: str = "KFKFK") -> StateGraph:
    """Assemble a Narkomfin slab: ``bands`` section modules stacked, each a
    corridor of ``n_bays`` with units anchored per ``pattern`` (chars K/F/B per
    bay, cycled to fill)."""
    expanded = "".join(pattern[i % len(pattern)] for i in range(n_bays))
    return derive_slab_from_patterns([expanded] * bands)


# === parametric catalogue ================================================
def random_slab(rng) -> StateGraph:
    """A random but real slab: 1–3 section modules, 4–7 bays, a K/F/B/D/R
    per-bay pattern (guaranteed at least one maisonette)."""
    bands = rng.randint(1, 3)
    n_bays = rng.randint(4, 7)
    pattern = "".join(rng.choice("KFBDR") for _ in range(n_bays))
    if not any(ch in pattern for ch in "KFD"):
        pattern = "KF" + pattern[2:]
    return derive_slab(bands=bands, n_bays=n_bays, pattern=pattern)


def catalogue(n: int = 8, *, seed: int = 0) -> list:
    """A deduped catalogue of ``n`` distinct real slabs (every one buildable)."""
    import random
    from .compare import typed_isomorphic
    rng = random.Random(seed)
    out: list = []
    attempts = 0
    while len(out) < n and attempts < n * 15:
        g = random_slab(rng)
        attempts += 1
        if not any(typed_isomorphic(g, p) for p in out):
            out.append(g)
    return out

