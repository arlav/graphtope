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
FLOOR = 3.0
MODULE = 3 * FLOOR          # a section module is three floors (corridor every 3rd)


def _place(g: StateGraph, nid: str, label: str, box, subtype: str | None = None):
    """Add a node carrying its exact box in attributes (geometry == graph)."""
    x, y, z, w, d, h = box
    g.add_node(label, id=nid, subtype=subtype, level=int(round(z / FLOOR)),
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
             bay=BAY, cd=CORRIDOR_DEPTH, ud=UNIT_DEPTH, floor=FLOOR) -> str:
    """P3 — a K-type maisonette on the **front**, rising two floors from the
    corridor (u_section)."""
    zc = g.node_attrs(corridor)["z"]
    uid = f"K_{band}_{bay_i}"
    _place(g, uid, A.U_SECTION, (bay_i * bay, cd / 2, zc, bay, ud, 2 * floor))
    return uid


def anchor_F(g: StateGraph, corridor: str, band: int, bay_i: int, *,
             bay=BAY, cd=CORRIDOR_DEPTH, ud=UNIT_DEPTH, floor=FLOOR) -> str:
    """P4 — an F-type maisonette on the **back**, entered at the corridor with
    living dropping a floor below (l_section) — the section interlock."""
    zc = g.node_attrs(corridor)["z"]
    fid = f"F_{band}_{bay_i}"
    _place(g, fid, A.L_SECTION, (bay_i * bay, -cd / 2 - ud, zc - floor, bay, ud, 2 * floor))
    return fid


def anchor_box(g: StateGraph, corridor: str, band: int, bay_i: int, *,
               bay=BAY, cd=CORRIDOR_DEPTH, ud=UNIT_DEPTH, floor=FLOOR) -> str:
    """P5 — a single-storey apartment on the front (generic)."""
    zc = g.node_attrs(corridor)["z"]
    aid = f"box_{band}_{bay_i}"
    _place(g, aid, A.GENERIC, (bay_i * bay, cd / 2, zc, bay, ud, floor), subtype="apartment")
    return aid


_ANCHOR = {"K": anchor_K, "F": anchor_F, "B": anchor_box}


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
    with units anchored per its pattern (chars K/F/B; ``.`` leaves a bay empty).
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
    """A random but real slab: 1–3 section modules, 4–7 bays, a K/F/B per-bay
    pattern (guaranteed at least one maisonette)."""
    bands = rng.randint(1, 3)
    n_bays = rng.randint(4, 7)
    pattern = "".join(rng.choice("KFB") for _ in range(n_bays))
    if "K" not in pattern and "F" not in pattern:
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

