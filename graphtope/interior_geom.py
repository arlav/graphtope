"""SG4 — level-2 geometry: interiors that are built, not just drawn.

The block level (``narkomfin``) folds exact real-metre boxes into the graph;
this module does the same **inside the unit envelope**: every interior node a
refinement produces receives its sub-box, placed by a deterministic recursive
split of the envelope driven by the refined graph itself (subtypes, extents,
adjacency — never the plan), so the two grammar levels share one
representation down to the room scale (spec §9, plan SG4).

Placement rules (per family, grounded on the built section and
``U_units_realised.obj``'s measured strips):

* **K** (``u_section``, 8 m): the internal stair is a full-height strip at the
  far-x edge; the lower zone (5 m, the double-height living volume) takes
  y-strips off its outer end (loggia → kitchen → bath@entry → wc); the gallery
  level (3 m) is the sleeping strip on the stair side (1.7 m — the built
  partial gallery; 0.9 m balcony edge for a full void) with the void claiming
  the rest, V-above the living footprint.
* **F** (``l_section``, 2×3 m): stair strip far-x; the entry hall hugs the
  corridor plane with the served rooms (kitchen/bath/wc/storage) as x-slices
  of the band behind it; the dropped living occupies the lower slab up to the
  corridor plane (so ``entry -V-> living`` is a real z-face), the optional
  sleeping beside it, the loggia on the outer face.
* **B** (single storey): entry strip on the corridor face (bath carved from
  its far end), kitchen a strip of the living's outer end.
* **R** (banked room): the room is the envelope, storage an outer strip.

Openings (§5.2 nodes) are **not spaces** — a door is a thin leaf centred in
the wall plane its two spaces share; a window a panel on its room's outermost
envelope face (a rooflight/z-face only as a reported fallback). Openings are
excluded from the tiling check (they live in walls) but carry real boxes, so
they export to OBJ.

Honesty (plan risk R3): the gallery-within-envelope reading places the
sleeping gallery over the *front zone* rather than reaching over the corridor
(the envelope ends at the corridor plane); ``tile_report`` measures everything
— exact tiling, overlaps, every graph edge a real shared face, openings in
their wall planes, and touches without edges (the coverage gap).
"""

from __future__ import annotations

from . import alphabet as A
from .interior import DOOR, WINDOW
from .model import StateGraph
from .realise import _faces_touch

# measured / module dimensions (m)
STAIR_W = 1.0          # internal stair strip
GALLERY_W = 1.7        # the built partial gallery strip (U_units_realised.obj)
BALCONY_W = 0.9        # the gallery edge a full void leaves
K_LOWER_H = 5.0        # the double-height living zone under the gallery
ENTRY_D = 1.2          # entry hall depth (F, B)
LOGGIA_D = 1.5
KITCHEN_D = 2.0
BATH_D = 1.8
WC_D = 1.2
STORAGE_D = 1.5
DOOR_T = 0.16          # opening leaf thickness
DOOR_W = 0.9
DOOR_H = 2.1
WINDOW_T = 0.12
WINDOW_W = 1.2

BOX_KEYS = ("x", "y", "z", "w", "d", "h")


# === strip helpers — always carve from an END so the remainder stays a box ===
def _take_x0(b, w):
    w = min(w, b[3] / 2)
    return (b[0] + w, b[1], b[2], b[3] - w, b[4], b[5]), (b[0], b[1], b[2], w, b[4], b[5])


def _take_x1(b, w):
    w = min(w, b[3] / 2)
    return (b[0], b[1], b[2], b[3] - w, b[4], b[5]), (b[0] + b[3] - w, b[1], b[2], w, b[4], b[5])


def _take_y0(b, d):
    d = min(d, b[4] / 2)
    return (b[0], b[1] + d, b[2], b[3], b[4] - d, b[5]), (b[0], b[1], b[2], b[3], d, b[5])


def _take_y1(b, d):
    d = min(d, b[4] / 2)
    return (b[0], b[1], b[2], b[3], b[4] - d, b[5]), (b[0], b[1] + b[4] - d, b[2], b[3], d, b[5])


def _vol(b):
    return b[3] * b[4] * b[5]


# === unit discovery ========================================================
def units_of(refined: StateGraph, slab: StateGraph) -> dict:
    """Refined nodes grouped by their ``unit`` tag → the slab node whose
    envelope they develop: ``{unit_id: {"family", "envelope", "nodes"}}``."""
    out: dict = {}
    for n in refined.nodes():
        uid = refined.node_attrs(n).get("unit")
        if uid is None or not slab.has_node(uid):
            continue
        if uid not in out:
            a = slab.node_attrs(uid)
            lab = slab.node_label(uid)
            fam = lab if lab in (A.U_SECTION, A.L_SECTION) else a.get("subtype")
            out[uid] = {"family": fam, "envelope": tuple(a[k] for k in BOX_KEYS),
                        "nodes": []}
        out[uid]["nodes"].append(n)
    return out


def _by_kind(refined: StateGraph, nodes: list) -> dict:
    """``{subtype: [node ids]}`` + ``"stair"`` by label (the start graphs'
    staircases carry subtype ``internal`` but a staircase label)."""
    kinds: dict = {}
    for n in nodes:
        if refined.node_label(n) == A.STAIRCASE:
            kinds.setdefault("stair", []).append(n)
        else:
            kinds.setdefault(refined.node_attrs(n).get("subtype"), []).append(n)
    return kinds


def _h_neighbours(refined: StateGraph, n: str) -> set:
    out = set()
    for e in refined.edges():
        if e["orientation"] != A.H or n not in (e["src"], e["tgt"]):
            continue
        out.add(e["tgt"] if e["src"] == n else e["src"])
    return out


def _hosts(refined: StateGraph, n: str) -> set:
    """The spaces ``n`` is really attached to: H-neighbours with §5.2 door
    nodes traversed transparently (the door interposition *deleted* the
    direct adjacency, so the host sits one hop further)."""
    out = set()
    for o in _h_neighbours(refined, n):
        if refined.node_attrs(o).get("subtype") == DOOR:
            out |= _h_neighbours(refined, o) - {n}
        else:
            out.add(o)
    return out


# === side occupancy — keep the anchor's routed side faces free ============
def _ext_sides(refined, anchor, env, unit_nodes, slab_env) -> set:
    """Which x-sides of the unit envelope carry a routed edge from ``anchor``
    to a node *outside* the unit (a side neighbour or a stair core) — those
    faces must stay on the anchor's box (SG0 routing meets real geometry)."""
    sides = set()
    for e in refined.edges():
        if anchor not in (e["src"], e["tgt"]):
            continue
        other = e["tgt"] if e["src"] == anchor else e["src"]
        if other in unit_nodes:
            continue
        a = refined.node_attrs(other)
        if all(k in a for k in BOX_KEYS):
            ob = tuple(a[k] for k in BOX_KEYS)
        else:                                # another unit's interior node
            uid = a.get("unit")
            if uid is None or uid not in slab_env:
                continue
            ob = slab_env[uid]
        if abs(ob[0] - (env[0] + env[3])) < 1e-6:
            sides.add(1)
        elif abs(ob[0] + ob[3] - env[0]) < 1e-6:
            sides.add(0)
    return sides


def _free_side(refined, anchor, env, unit_nodes, slab_env) -> int:
    """The x-side strips (stair, bath slice) may take: one with no routed
    side edge (default x1)."""
    busy = _ext_sides(refined, anchor, env, unit_nodes, slab_env)
    return 0 if 1 in busy else 1


# === the family recipes ====================================================
def _serve_in_y(host_box, served, boxes, side) -> tuple:
    """Serve ``served = [(node, depth), …]`` rooms off one ``host_box``:
    equal-depth x-strips at the ``side`` end, **stacked in y** — so every room
    shares the host's remaining face (sequential strips would leave all but
    the last carved room detached from its host). Returns the shrunken host."""
    if not served:
        return host_box
    x0, y0, z, w, d, h = host_box
    sw = min(max(dep for _, dep in served), w / 2)
    dy = d / len(served)
    for i, (n, _dep) in enumerate(served):
        if side:
            boxes[n] = (x0 + w - sw, y0 + i * dy, z, sw, dy, h)
        else:
            boxes[n] = (x0, y0 + i * dy, z, sw, dy, h)
    if side:
        return (x0, y0, z, w - sw, d, h)
    return (x0 + sw, y0, z, w - sw, d, h)


def _place_k(refined, u, boxes, slab_env) -> None:
    env = u["envelope"]
    x, y, z, w, d, h = env
    kinds = _by_kind(refined, u["nodes"])
    nodes = set(u["nodes"])
    side = _free_side(refined, kinds["living"][0], env, nodes, slab_env)
    rest = env
    if kinds.get("stair"):
        rest, sbox = _take_y1(env, STAIR_W)     # full-height strip, outer end
        boxes[kinds["stair"][0]] = sbox
    x0, y0, w, d = rest[0], rest[1], rest[3], rest[4]
    lower = (x0, y0, z, w, d, K_LOWER_H)
    gallery = (x0, y0, z + K_LOWER_H, w, d, h - K_LOWER_H)

    # rooms served by the living: stacked strips on the free x-side, so the
    # living keeps the corridor face (y0), the stair face (y1) and the routed
    # side face — and every served room touches it (last = loggia, outermost)
    sleeps = set(kinds.get("sleeping", []))
    served = [(n, BATH_D) for n in kinds.get("bath", [])
              if not _hosts(refined, n) & sleeps]
    for sub, dep in (("wc", WC_D), ("kitchen", KITCHEN_D), ("loggia", LOGGIA_D)):
        served += [(n, dep) for n in kinds.get(sub, [])]
    living = _serve_in_y(lower, served, boxes, side)
    boxes[kinds["living"][0]] = living

    g = gallery
    voids = kinds.get("void", [])
    sleeps = kinds.get("sleeping", [])
    if voids:
        extent = refined.node_attrs(voids[0]).get("extent", "partial")
        gw = GALLERY_W if extent == "partial" else BALCONY_W
        g, sbox = _take_y1(g, gw)              # sleeping reaches the stair
        boxes[voids[0]] = g                    # the void claims the corridor
        g = sbox                                # side, V-above the living
    gserved = [(n, BATH_D) for n in kinds.get("bath", [])
               if _hosts(refined, n) & set(kinds.get("sleeping", []))]
    gserved += [(n, STORAGE_D) for n in kinds.get("storage", [])]
    g = _serve_in_y(g, gserved, boxes, side)    # the gallery's served rooms
    boxes[sleeps[0]] = g
    if len(sleeps) > 1:                        # GU-gallery-split (in x): the
        stairs = set(kinds.get("stair", []))    # split room takes the end AWAY
        main = next((s for s in sleeps          # from the served strips (so it
                     if _h_neighbours(refined, s) & stairs), sleeps[0])   # can-
        other = [s for s in sleeps if s != main][0]                      # not
        g0, g1 = g[0], g[0] + g[3]              # come between them and their
        l0, l1 = living[0], living[0] + living[3]   # host), with the split
        mid = (g0 + g1) / 2                     # point kept inside the living's
        if side:                                # footprint (both V-above it)
            s = max(l0 + 0.05, min(g1 - 0.05, mid))
            boxes[other] = (g0, g[1], g[2], s - g0, g[4], g[5])
            boxes[main] = (s, g[1], g[2], g1 - s, g[4], g[5])
        else:
            s = min(l1 - 0.05, max(g0 + 0.05, mid))
            boxes[main] = (g0, g[1], g[2], s - g0, g[4], g[5])
            boxes[other] = (s, g[1], g[2], g1 - s, g[4], g[5])


def _place_f(refined, u, boxes, slab_env) -> None:
    env = u["envelope"]
    kinds = _by_kind(refined, u["nodes"])
    nodes = set(u["nodes"])
    side = _free_side(refined, kinds["entry"][0], env, nodes, slab_env)
    rest = env
    if kinds.get("stair"):
        if side:
            rest, sbox = _take_x1(env, STAIR_W)
        else:
            rest, sbox = _take_x0(env, STAIR_W)
        boxes[kinds["stair"][0]] = sbox
    x, y, z, w, d, h = rest
    lower = (x, y, z, w, d, h / 2)
    upper = (x, y, z + h / 2, w, d, h / 2)

    band, entry = _take_y1(upper, ENTRY_D)     # the corridor plane side
    served = [n for sub in ("kitchen", "bath", "wc", "storage")
              for n in kinds.get(sub, [])
              if _hosts(refined, n) & set(kinds.get("entry", []))]
    if served:
        bw = band[3] / len(served)
        for i, n in enumerate(served):
            boxes[n] = (band[0] + i * bw, band[1], band[2], bw, band[4], band[5])
    else:                                       # nothing off the entry: it is the floor
        entry = (entry[0], band[1], entry[2], entry[3],
                 entry[4] + band[4], entry[5])
    boxes[kinds["entry"][0]] = entry

    low = lower
    for n in kinds.get("loggia", []):
        low, boxes[n] = _take_y0(low, LOGGIA_D)   # F's outer face is low-y
    if kinds.get("sleeping"):
        if side:                                # living keeps the stair side
            low, sbox = _take_x0(low, low[3] / 2)
        else:
            low, sbox = _take_x1(low, low[3] / 2)
        boxes[kinds["sleeping"][0]] = sbox
    boxes[kinds["living"][0]] = low


def _place_b(refined, u, boxes, slab_env) -> None:
    env = u["envelope"]
    kinds = _by_kind(refined, u["nodes"])
    nodes = set(u["nodes"])
    side = _free_side(refined, kinds["entry"][0], env, nodes, slab_env)
    rest, entry = _take_y0(env, env[4] / 3)    # the corridor face side
    for n in kinds.get("bath", []):
        if _hosts(refined, n) & set(kinds.get("entry", [])):
            if side:
                entry, boxes[n] = _take_x1(entry, entry[3] / 2)
            else:
                entry, boxes[n] = _take_x0(entry, entry[3] / 2)
    boxes[kinds["entry"][0]] = entry
    living = rest
    for n in kinds.get("kitchen", []):
        living, boxes[n] = _take_y1(living, KITCHEN_D)
    boxes[kinds["living"][0]] = living


def _place_r(refined, u, boxes, slab_env) -> None:
    kinds = _by_kind(refined, u["nodes"])
    bed = u["envelope"]
    for n in kinds.get("storage", []):
        bed, boxes[n] = _take_y1(bed, bed[4] / 3)
    boxes[kinds["room"][0]] = bed


_PLACERS = {"K": _place_k, "F": _place_f, "B": _place_b, "R": _place_r,
            A.U_SECTION: _place_k, A.L_SECTION: _place_f,
            "apartment": _place_b, "room": _place_r}


# === openings — wall-plane geometry, not spaces ============================
def _axis_touch(b1, b2):
    """``(axis, plane, (lo1, hi1), (lo2, hi2))`` where the boxes share the face
    ``axis == plane``; the intervals are the *other two* axes' overlaps."""
    iv = {"x": ((b1[0], b1[0] + b1[3]), (b2[0], b2[0] + b2[3])),
          "y": ((b1[1], b1[1] + b1[4]), (b2[1], b2[1] + b2[4])),
          "z": ((b1[2], b1[2] + b1[5]), (b2[2], b2[2] + b2[5]))}
    for axis in ("x", "y", "z"):
        others = [a for a in iv if a != axis]
        ov = {a: (max(iv[a][0][0], iv[a][1][0]), min(iv[a][0][1], iv[a][1][1]))
              for a in others}
        if all(v[1] - v[0] > 1e-9 for v in ov.values()):
            p1, p2 = iv[axis]
            if abs(p1[1] - p2[0]) < 1e-9:
                return axis, p1[1], ov
            if abs(p2[1] - p1[0]) < 1e-9:
                return axis, p2[1], ov
    return None


def _place_door(refined, n, boxes, unit_env) -> None:
    nb = _h_neighbours(refined, n)
    for a in nb:                               # envelope fallback (R host door)
        for b in nb:
            if a == b:
                continue
            for ba in [boxes.get(a)] + ([unit_env[a]] if a in unit_env else []):
                for bb in [boxes.get(b)] + ([unit_env[b]] if b in unit_env else []):
                    if ba is None or bb is None:
                        continue
                    t = _axis_touch(ba, bb)
                    if not t:
                        continue
                    axis, plane, ov = t
                    if axis == "z":
                        continue
                    hz = ov["z"]
                    (o_axis,) = [k for k in ov if k != "z"]
                    lo, hi = ov[o_axis]
                    w0 = min(DOOR_W, hi - lo)
                    c = (lo + hi) / 2
                    box = [None, None, None, None, None, None]
                    box["xyz".index(axis)] = plane - DOOR_T / 2
                    box["xyz".index(axis) + 3] = DOOR_T
                    box["xyz".index(o_axis)] = c - w0 / 2
                    box["xyz".index(o_axis) + 3] = w0
                    box[2], box[5] = hz[0], min(DOOR_H, hz[1] - hz[0])
                    boxes[n] = tuple(box)
                    refined.set_node_attr(n, "placement", "wall")
                    return
    refined.set_node_attr(n, "placement", "unplaced")


def _place_window(refined, n, boxes, unit_env) -> None:
    room = next(iter(_h_neighbours(refined, n)), None)
    rb = boxes.get(room)
    env = unit_env.get(room)
    if rb is None or env is None:
        refined.set_node_attr(n, "placement", "unplaced")
        return
    for axis, order, tag in (("y", 1, "outer"), ("z", 1, "roof"),
                             ("x", 1, "party"), ("x", 0, "party")):
        i = "xyz".index(axis)
        face = rb[i] + rb[i + 3] if order else rb[i]
        eface = env[i] + env[i + 3] if order else env[i]
        if abs(face - eface) > 1e-9:
            continue
        if axis == "z":
            fa = (rb[0], rb[0] + rb[3])
        else:
            fa = (rb[0], rb[0] + rb[3]) if axis == "y" else (rb[1], rb[1] + rb[4])
        fw = min(WINDOW_W, fa[1] - fa[0])
        fc = (fa[0] + fa[1]) / 2
        box = [None] * 6
        box[i], box[i + 3] = face - WINDOW_T / 2, WINDOW_T
        if axis == "z":
            box[0], box[3] = fc - fw / 2, fw
            box[1], box[4] = rb[1] + rb[4] / 2 - fw / 2, fw
        else:
            oi = 0 if axis == "y" else 1
            box[oi], box[oi + 3] = fc - fw / 2, fw
            zlo = rb[2] + min(0.9, rb[5] / 3)
            box[2], box[5] = zlo, min(1.4, rb[2] + rb[5] - zlo)
        boxes[n] = tuple(box)
        refined.set_node_attr(n, "placement", tag)
        return
    refined.set_node_attr(n, "placement", "unplaced")


# === the driver ============================================================
def place(refined: StateGraph, slab: StateGraph) -> dict:
    """Give every interior node of ``refined`` its exact box inside its unit
    envelope (read from ``slab``). Deterministic in the refined graph alone —
    the same interior always places the same. Returns ``{node: box}`` for the
    placed nodes; the refined graph now carries geometry at level 2, so
    ``narkomfin.boxes_of(refined)`` and ``exchange.to_obj(..., boxes=...)``
    work on rooms. Only interior nodes are touched — the refinement's exact
    inverse (which deletes them) still restores the slab."""
    units = units_of(refined, slab)
    slab_env = {uid: u["envelope"] for uid, u in units.items()}
    bx: dict = dict(boxes(refined))             # the armature already placed
    unit_env: dict = {}                         # node -> its unit's envelope
    for uid, u in units.items():
        _PLACERS[u["family"]](refined, u, bx, slab_env)
        for n in u["nodes"]:
            unit_env[n] = u["envelope"]
    for n in refined.nodes():
        sub = refined.node_attrs(n).get("subtype")
        if sub == DOOR:
            _place_door(refined, n, bx, unit_env)
        elif sub == WINDOW:
            _place_window(refined, n, bx, unit_env)
    for n, b in bx.items():
        if n in unit_env:                       # never touch the armature
            for k, v in zip(BOX_KEYS, b):
                refined.set_node_attr(n, k, round(v, 3))
    return {n: b for n, b in bx.items() if n in unit_env}


def boxes(refined: StateGraph) -> dict:
    """``{node: box}`` for every node that carries one (armature + interiors)."""
    out = {}
    for n in refined.nodes():
        a = refined.node_attrs(n)
        if all(k in a for k in BOX_KEYS):
            out[n] = tuple(a[k] for k in BOX_KEYS)
    return out


# === verification (plan SG4: verify the partition, report the coverage) ====
def _overlap(b1, b2) -> float:
    ov = 1.0
    for i in (0, 1, 2):
        ov *= max(0.0, min(b1[i] + b1[i + 3], b2[i] + b2[i + 3]) - max(b1[i], b2[i]))
    return ov


def _axis_of_touch(b1, b2):
    t = _axis_touch(b1, b2)
    return t[0] if t else None


def cellcomplex_partitions(unit_boxes: dict) -> bool | None:
    """Carrier check: the boxes form one cell complex with no gaps/overlaps.
    ``None`` = the carrier declined (its known flakiness, briefing Table 3)."""
    from topologicpy.CellComplex import CellComplex
    from .realise import _box_cell
    try:
        cells = [_box_cell(b, n, "generic") for n, b in unit_boxes.items()]
        cc = CellComplex.ByCells(cells, silent=True)
        return bool(cc)
    except Exception:
        return None


def _opening_ok(refined, n, bx, unit_env) -> bool:
    """An opening is *in its wall*: the centre-plane of its thin axis lies on
    a face of every space it joins (a door straddles the wall its two rooms
    share; a window sits in its room's façade face) — or on its unit's
    envelope face, for the routed contacts whose box sits behind a carved
    strip (the R host door: the party wall is the envelope's, not the
    living's)."""
    b = bx.get(n)
    if b is None:
        return False
    thin = min(range(3), key=lambda i: b[i + 3])       # the wall axis
    c = b[thin] + b[thin + 3] / 2
    for e in refined.edges():
        if n not in (e["src"], e["tgt"]):
            continue
        other = e["tgt"] if e["src"] == n else e["src"]
        faces = []
        ob = bx.get(other)
        if ob is not None:
            faces += [ob[thin], ob[thin] + ob[thin + 3]]
        env = unit_env.get(other)
        if env is not None:
            faces += [env[thin], env[thin] + env[thin + 3]]
        if not any(abs(c - f) < 1e-6 for f in faces):
            return False
    return True


def tile_report(refined: StateGraph, slab: StateGraph) -> dict:
    """Measure the level-2 geometry: per unit — does it tile the envelope
    (volume sums, no overlaps)? is every graph edge a real shared face (with
    the right axis for its orientation)? are openings in their wall planes?
    Coverage honesty: ``touches_without_edge`` counts space pairs that share a
    face the grammar does not model, and ``roof``/``party`` window placements
    are listed rather than drawn as façade."""
    units = units_of(refined, slab)
    bx = boxes(refined)
    unit_env = {n: u["envelope"] for u in units.values() for n in u["nodes"]}
    openings = {n for n in refined.nodes()
                if refined.node_attrs(n).get("subtype") in (DOOR, WINDOW)}
    report = {"units": {}, "ok": True}
    for uid, u in units.items():
        env = u["envelope"]
        spaces = [n for n in u["nodes"] if refined.node_attrs(n).get("subtype")
                  not in (DOOR, WINDOW) and n in bx]
        vol_err = sum(_vol(bx[n]) for n in spaces) - _vol(env)
        overlaps = [(a, b) for i, a in enumerate(spaces) for b in spaces[i + 1:]
                    if _overlap(bx[a], bx[b]) > 1e-6]
        space_set = set(spaces)
        misses = []
        for e in refined.edges():
            if e["src"] not in bx or e["tgt"] not in bx:
                continue
            if e["src"] in openings or e["tgt"] in openings:
                continue                     # openings: the in-wall check
            pair = (e["src"], e["tgt"])
            if not (e["src"] in space_set or e["tgt"] in space_set):
                continue                     # neither side is this unit's space
            if not _faces_touch(bx[e["src"]], bx[e["tgt"]]):
                misses.append(pair)
                continue
            axis = _axis_of_touch(bx[e["src"]], bx[e["tgt"]])
            if (e["orientation"] == A.V) != (axis == "z"):
                misses.append(pair)
        adj = {(e["src"], e["tgt"]) for e in refined.edges()} | \
              {(e["tgt"], e["src"]) for e in refined.edges()}
        free = sum(1 for i, a in enumerate(spaces) for b in spaces[i + 1:]
                   if (a, b) not in adj and (b, a) not in adj
                   and _faces_touch(bx[a], bx[b]))
        cc = cellcomplex_partitions({n: bx[n] for n in spaces})
        unit_ok = abs(vol_err) < 0.1 and not overlaps and not misses
        report["units"][uid] = {
            "family": u["family"], "volume_error": round(vol_err, 6),
            "overlaps": overlaps, "edge_face_misses": misses,
            "touches_without_edge": free, "cellcomplex": cc, "ok": unit_ok}
        report["ok"] &= unit_ok
    openings, faults = {}, []
    for n in refined.nodes():
        sub = refined.node_attrs(n).get("subtype")
        if sub in (DOOR, WINDOW):
            openings[n] = refined.node_attrs(n).get("placement")
            if not _opening_ok(refined, n, bx, unit_env):
                faults.append(n)
    report["openings"] = openings
    report["opening_faults"] = faults
    report["ok"] &= (not faults
                     and all(p != "unplaced" for p in openings.values()))
    return report
