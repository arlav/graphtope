"""Stage 2 — geometry realisation (spec §9).

The single rule Stage 1 hands forward is τ : Σ → ShapeType (``shape_iface``).
Stage 2 turns the typed space-adjacency graph into actual Topologic geometry:

* a **grid layout** places one unit ``Cell`` per node so that adjacency edges
  become **shared faces** (H ⇒ shared vertical face / wall, V ⇒ shared
  horizontal face / slab, with V stacking the cells);
* ``CellComplex.ByCells`` assembles the cells, identifying the shared faces;
* ``Graph.ByTopology(cc, direct=True)`` extracts the dual adjacency graph again —
  the **round-trip** that verifies the realisation against the Stage-1 graph;
* ``IsSimilar`` provides the **geometric matching predicate** that replaces the
  combinatorial matcher of §6.2 — none of the Stage-1 rule structure changes.

Not every typed graph embeds in a grid with all adjacencies as shared faces:
H-triangles (the condenser toilet triad) and the U/L split-level interlock are
genuinely non-grid-embeddable, so ``grid_layout`` reports which adjacencies it
could not realise rather than pretending coverage is total.
"""

from __future__ import annotations

from collections import deque

from topologicpy.Cell import Cell
from topologicpy.CellComplex import CellComplex
from topologicpy.Dictionary import Dictionary
from topologicpy.Edge import Edge
from topologicpy.Face import Face
from topologicpy.Graph import Graph
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex
from topologicpy.Wire import Wire

from . import alphabet as A
from .model import StateGraph

# τ shape proportions (width, length, height) per label — box-shaped types ----
_PROPORTIONS = {
    A.GENERIC: (1.0, 1.0, 1.0),       # box
    A.CORRIDOR: (2.0, 1.0, 1.0),      # elongated
    A.STAIRCASE: (1.0, 1.0, 2.0),     # vertical, spanning levels
    A.ENTRANCE: (0.6, 0.6, 1.0),      # opening volume
}

# section profiles (in the X-Z plane) for the non-box types, extruded along Y --
# u_section ↦ U-profile solid in section; l_section ↦ L-profile complement (§9).
_PROFILE = {
    A.U_SECTION: [(0, 0), (1.6, 0), (1.6, 1.2), (1.1, 1.2),
                  (1.1, 0.4), (0.5, 0.4), (0.5, 1.2), (0, 1.2)],
    A.L_SECTION: [(0, 0), (1.6, 0), (1.6, 0.5), (0.5, 0.5), (0.5, 1.6), (0, 1.6)],
}


# === grid layout (adjacency → grid face-adjacency) =======================
def grid_layout(sg: StateGraph) -> tuple[dict, set, set]:
    """Embed the graph in ℤ³ so adjacencies become grid-face-adjacencies.

    Returns ``(coords, realised, unrealised)`` where ``coords`` maps node id →
    ``(gx, gy, gz)`` and the two sets hold ``frozenset({a, b})`` adjacencies that
    did / did not end up grid-face-adjacent.
    """
    nodes = sorted(sg.nodes())   # deterministic: the carrier's node order is not stable
    edges = sorted(sg.edges(), key=lambda e: (e["src"], e["tgt"]))
    h_edges = [(e["src"], e["tgt"]) for e in edges if e["orientation"] == A.H]
    v_edges = [(e["src"], e["tgt"]) for e in edges if e["orientation"] == A.V]  # src above tgt

    # union-find over H edges: each group is a single-level floor plate
    parent = {n: n for n in nodes}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in h_edges:
        parent[find(a)] = find(b)
    groups: dict = {}
    for n in nodes:
        groups.setdefault(find(n), []).append(n)

    # group levels from V constraints: level(above) = level(below) + 1
    glevel = {g: 0 for g in groups}
    for _ in range(len(groups) + 1):
        changed = False
        for a, b in v_edges:
            ga, gb = find(a), find(b)
            if ga != gb and glevel[ga] < glevel[gb] + 1:
                glevel[ga] = glevel[gb] + 1
                changed = True
        if not changed:
            break

    # group adjacency via V edges: each link lets one group align onto the other
    gV: dict = {g: [] for g in groups}
    for a, b in v_edges:                          # a above b
        ga, gb = find(a), find(b)
        if ga != gb:
            gV[ga].append((gb, a, b))             # from ga: neighbour gb, my node a, their node b
            gV[gb].append((ga, b, a))

    h_in_group: dict = {g: {} for g in groups}
    for a, b in h_edges:
        g = find(a)
        h_in_group[g].setdefault(a, []).append(b)
        h_in_group[g].setdefault(b, []).append(a)

    coords: dict = {}
    occupied: set = set()

    def free_near(gx, gy, gz):
        if (gx, gy, gz) not in occupied:
            return gx, gy
        r = 1
        while r < 64:
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) == r and (gx + dx, gy + dy, gz) not in occupied:
                        return gx + dx, gy + dy
            r += 1
        return gx + 1000, gy

    def place(n, gx, gy, gz):
        coords[n] = (gx, gy, gz)
        occupied.add((gx, gy, gz))

    def place_group(g, anchor, anchor_xy):
        gz = glevel[g]
        ax, ay = free_near(anchor_xy[0], anchor_xy[1], gz)
        place(anchor, ax, ay, gz)
        dq = deque([anchor]); seen = {anchor}
        while dq:
            cur = dq.popleft()
            cx, cy, _ = coords[cur]
            for nb in sorted(h_in_group[g].get(cur, [])):
                if nb in seen:
                    continue
                seen.add(nb)
                spot = next(((cx + dx, cy + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                             if (cx + dx, cy + dy, gz) not in occupied), None)
                place(nb, *(spot or free_near(cx, cy, gz)), gz)
                dq.append(nb)
        for m in groups[g]:                       # any H-isolated members of the group
            if m not in coords:
                place(m, *free_near(anchor_xy[0], anchor_xy[1], gz), gz)

    # place one building component at a time: BFS over the V-linked group graph
    placed, remaining, next_region_x = set(), set(groups), 0
    while remaining:
        seed = max(remaining, key=lambda g: (len(groups[g]), g))
        place_group(seed, sorted(groups[seed])[0], (next_region_x, 0))
        placed.add(seed); remaining.discard(seed)
        gq = deque([seed])
        while gq:
            cg = gq.popleft()
            for ng, my_node, their_node in gV[cg]:
                if ng in placed:
                    continue
                place_group(ng, their_node, coords[my_node][:2])   # align over/under the V link
                placed.add(ng); remaining.discard(ng); gq.append(ng)
        next_region_x = max((x for x, _, _ in occupied), default=0) + 3

    def face_adjacent(p, q):
        return sum(abs(p[i] - q[i]) for i in range(3)) == 1

    realised, unrealised = set(), set()
    for e in edges:
        a, b = e["src"], e["tgt"]
        key = frozenset((a, b))
        if a in coords and b in coords and face_adjacent(coords[a], coords[b]):
            realised.add(key)
        else:
            unrealised.add(key)
    return coords, realised, unrealised


# === constraint repair: variable-size boxes for the hard motifs ==========
def _faces_touch(b1, b2) -> bool:
    """True if two boxes ``(x, y, z, w, d, h)`` share a face (touch on one axis,
    overlap with positive area on the other two) without overlapping in volume."""
    x1, y1, z1, w1, d1, h1 = b1
    x2, y2, z2, w2, d2, h2 = b2
    ix = (x1, x1 + w1); jx = (x2, x2 + w2)
    iy = (y1, y1 + d1); jy = (y2, y2 + d2)
    iz = (z1, z1 + h1); jz = (z2, z2 + h2)
    ov = lambda p, q: max(0.0, min(p[1], q[1]) - max(p[0], q[0]))
    tc = lambda p, q: abs(p[1] - q[0]) < 1e-9 or abs(q[1] - p[0]) < 1e-9
    ox, oy, oz = ov(ix, jx), ov(iy, jy), ov(iz, jz)
    return ((tc(ix, jx) and oy > 0 and oz > 0)
            or (tc(iy, jy) and ox > 0 and oz > 0)
            or (tc(iz, jz) and ox > 0 and oy > 0))


def _cells_of(box):
    x, y, z, w, d, h = box
    return {(ix, iy, iz) for ix in range(x, x + w)
            for iy in range(y, y + d) for iz in range(z, z + h)}


def _coverage(boxes, edges) -> int:
    return sum(1 for e in edges if _faces_touch(boxes[e["src"]], boxes[e["tgt"]]))


def _collides(boxes, plan) -> bool:
    """True if the re-planned boxes would overlap any cell occupied by a node
    not in the plan."""
    moving = set(plan)
    occ = set()
    for n, b in boxes.items():
        if n not in moving:
            occ |= _cells_of(b)
    new = set().union(*(_cells_of(b) for b in plan.values())) if plan else set()
    return bool(new & occ)


def box_layout(sg: StateGraph) -> tuple[dict, set, set]:
    """Grid layout with variable-size boxes. A constraint-repair pass grows /
    re-arranges cells so grid-unfriendly motifs (one-below-many interlocks,
    H 3-cliques) can also become shared faces. Each repair is applied only if it
    **increases** coverage (it can never make the realisation worse). Returns
    ``(boxes, realised, unrealised)`` with ``boxes[id] = (x, y, z, w, d, h)``."""
    coords, _, _ = grid_layout(sg)
    boxes = {n: (x, y, z, 1, 1, 1) for n, (x, y, z) in coords.items()}
    edges = sg.edges()
    h_edges = [(e["src"], e["tgt"]) for e in edges if e["orientation"] == A.H]
    v_edges = [(e["src"], e["tgt"]) for e in edges if e["orientation"] == A.V]

    def commit(plan):
        if _collides(boxes, plan):
            return
        trial = dict(boxes); trial.update(plan)
        if _coverage(trial, edges) > _coverage(boxes, edges):
            boxes.update(plan)

    # span repair: grow a lower cell to cover all cells sitting on its top face
    for n in list(boxes):
        x, y, z, w, d, h = boxes[n]
        above = [(b if a == n else a) for a, b in v_edges if n in (a, b)]
        above = [m for m in above if boxes[m][2] == z + h]
        if len(above) >= 2:
            xs = [x, x + w] + [boxes[m][0] for m in above] + [boxes[m][0] + boxes[m][3] for m in above]
            ys = [y, y + d] + [boxes[m][1] for m in above] + [boxes[m][1] + boxes[m][4] for m in above]
            commit({n: (min(xs), min(ys), z, max(xs) - min(xs), max(ys) - min(ys), h)})

    # triangle repair: realise an H 3-clique as a 2-wide-base pinwheel, trying
    # each growth direction so the hub's external edges can survive
    hadj: dict = {}
    for a, b in h_edges:
        hadj.setdefault(a, set()).add(b); hadj.setdefault(b, set()).add(a)
    for tri in {frozenset((a, b, c)) for a, b in h_edges for c in hadj[a] & hadj[b]}:
        a, b, c = tuple(tri)
        deg = lambda u: len(hadj.get(u, ())) + sum(1 for e in v_edges if u in e)
        hub = max((a, b, c), key=deg)
        o1, o2 = [u for u in (a, b, c) if u != hub]
        hx, hy, hz, _, _, _ = boxes[hub]
        for base, p1, p2 in (((hx, hy, hz, 2, 1, 1), (hx, hy + 1, hz), (hx + 1, hy + 1, hz)),
                             ((hx - 1, hy, hz, 2, 1, 1), (hx - 1, hy + 1, hz), (hx, hy + 1, hz)),
                             ((hx, hy, hz, 1, 2, 1), (hx + 1, hy, hz), (hx + 1, hy + 1, hz)),
                             ((hx, hy - 1, hz, 1, 2, 1), (hx + 1, hy - 1, hz), (hx + 1, hy, hz))):
            plan = {hub: base, o1: p1 + (1, 1, 1), o2: p2 + (1, 1, 1)}
            before = _coverage(boxes, edges)
            commit(plan)
            if _coverage(boxes, edges) > before:
                break

    realised, unrealised = set(), set()
    for e in edges:
        key = frozenset((e["src"], e["tgt"]))
        (realised if _faces_touch(boxes[e["src"]], boxes[e["tgt"]]) else unrealised).add(key)
    return boxes, realised, unrealised


# === realisation: a Cell per node ========================================
def _box_cell(box, nid, label):
    x, y, z, w, d, h = box
    c = Cell.Box(origin=Vertex.ByCoordinates(x + w / 2, y + d / 2, z + h / 2),
                 width=w, length=d, height=h, placement="center")
    return Topology.SetDictionary(c, Dictionary.ByKeysValues(["id", "label"], [nid, label]))


def _components(nodes, adjacency: set) -> list:
    """Connected components of ``nodes`` under the undirected ``adjacency`` set."""
    adj: dict = {n: set() for n in nodes}
    for pair in adjacency:
        a, b = tuple(pair)
        adj[a].add(b); adj[b].add(a)
    seen, comps = set(), []
    for n in nodes:
        if n in seen:
            continue
        stack, comp = [n], []
        seen.add(n)
        while stack:
            cur = stack.pop(); comp.append(cur)
            for m in adj[cur]:
                if m not in seen:
                    seen.add(m); stack.append(m)
        comps.append(comp)
    return comps


def realise(sg: StateGraph, boxes: dict | None = None) -> dict:
    """Realise the graph as cells (variable-size, from ``box_layout``), with one
    ``CellComplex`` per face-connected component — a disconnected set of cells
    has no single complex."""
    if boxes is None:
        boxes, realised, unrealised = box_layout(sg)
    else:
        realised = {frozenset((e["src"], e["tgt"])) for e in sg.edges()
                    if _faces_touch(boxes[e["src"]], boxes[e["tgt"]])}
        unrealised = {frozenset((e["src"], e["tgt"])) for e in sg.edges()} - realised
    cells = {nid: _box_cell(box, nid, sg.node_label(nid)) for nid, box in boxes.items()}
    complexes = []
    for comp in _components(list(boxes), realised):
        if len(comp) >= 2:
            cc = CellComplex.ByCells([cells[n] for n in comp])
            if cc is not None:
                complexes.append((comp, cc))
    return {"cells": cells, "complex": (complexes[0][1] if complexes else None),
            "complexes": complexes, "boxes": boxes,
            "coords": {n: (b[0], b[1], b[2]) for n, b in boxes.items()},
            "realised": realised, "unrealised": unrealised}


def typed_cell(label: str, origin=None):
    """A cell shaped by τ (§9): box types by proportion, U/L as true section
    profiles extruded along Y. Centred on ``origin`` (or the world origin)."""
    if label in _PROFILE:
        wire = Wire.ByVertices([Vertex.ByCoordinates(x, 0.0, z) for x, z in _PROFILE[label]],
                               close=True)
        cell = Cell.ByThickenedFace(Face.ByWire(wire), thickness=1.0, bothSides=True)
    else:
        w, l, h = _PROPORTIONS.get(label, (1.0, 1.0, 1.0))
        cell = Cell.Box(width=w, length=l, height=h, placement="center")
    oc = Vertex.Coordinates(Topology.Centroid(cell))
    tgt = Vertex.Coordinates(origin) if origin is not None else (0.0, 0.0, 0.0)
    return Topology.Translate(cell, tgt[0] - oc[0], tgt[1] - oc[1], tgt[2] - oc[2])


# === round-trip: CellComplex → adjacency graph ===========================
def extract_adjacency(realisation: dict):
    """Extract the dual adjacency from the realised CellComplexes (one per
    component) via ``Graph.ByTopology``, mapping vertices back to ids by
    centroid. Returns ``(adjacency_set, total_order, total_size)``."""
    boxes = realisation["boxes"]
    centroid = {(round(x + w / 2, 3), round(y + d / 2, 3), round(z + h / 2, 3)): nid
                for nid, (x, y, z, w, d, h) in boxes.items()}

    def vid(v):
        c = Vertex.Coordinates(v)
        return centroid.get((round(c[0], 3), round(c[1], 3), round(c[2], 3)))

    adj, order, size = set(), 0, 0
    for _comp, cc in realisation.get("complexes", []):
        g = Graph.ByTopology(cc, direct=True, silent=True)
        order += Graph.Order(g)
        size += Graph.Size(g)
        for e in (Graph.Edges(g) or []):
            a, b = vid(Edge.StartVertex(e)), vid(Edge.EndVertex(e))
            if a and b:
                adj.add(frozenset((a, b)))
    # single-cell components contribute a vertex but no complex
    order += sum(1 for c in _components(list(boxes), realisation["realised"]) if len(c) == 1)
    return adj, order, size


def roundtrip_report(sg: StateGraph) -> dict:
    """Realise ``sg``, extract its adjacency back, and report coverage."""
    r = realise(sg)
    extracted, order, size = extract_adjacency(r)
    realised = r["realised"]
    return {
        "cells": len(r["cells"]),
        "realised": realised,
        "unrealised": r["unrealised"],
        "extracted": extracted,
        "exact": extracted == realised,            # no incidental adjacencies
        "complete": realised <= extracted,         # every intended adjacency is a shared face
        "incidental": extracted - realised,        # extra shared faces from grid packing
        "graph_order": order,
        "graph_size": size,
    }


# === geometric matcher (replaces §6.2's combinatorial predicate) =========
def is_similar(a, b, epsilon: float = 0.1) -> bool:
    """Geometric congruence/similarity of two cells (§9 matching predicate)."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):   # mute IsSimilar's internal chatter
        res = Topology.IsSimilar(a, b, epsilon=epsilon, silent=True)
    return bool(res[0]) if isinstance(res, (tuple, list)) else bool(res)


def find_similar(query, cells: dict) -> list:
    """Ids of cells geometrically similar to ``query`` (a typed cell)."""
    return [nid for nid, c in cells.items() if is_similar(query, c)]


def shape_matcher(sg: StateGraph, epsilon: float = 0.1):
    """A geometric node predicate for ``rules.match_pattern`` (§9): a pattern
    node matches a host node when their τ shapes are congruent. This *replaces*
    the combinatorial label test — the rule structure is unchanged. A pattern
    node's ``label`` names the query shape; ``label=None`` is a wildcard."""
    host = typed_cells(sg)

    def matcher(pnode, _sg, host_id):
        shape = pnode.label
        if shape is None and not pnode.labels:
            return True
        queries = [typed_cell(s) for s in (pnode.labels or (shape,))]
        return any(is_similar(q, host[host_id], epsilon=epsilon) for q in queries)

    return matcher


def typed_cells(sg: StateGraph, coords: dict | None = None) -> dict:
    """One τ-shaped cell per node (for matching / massing; not a valid complex)."""
    if coords is None:
        coords, _, _ = grid_layout(sg)
    return {nid: typed_cell(sg.node_label(nid),
                            Vertex.ByCoordinates(x + 0.5, y + 0.5, z + 0.5))
            for nid, (x, y, z) in coords.items()}
