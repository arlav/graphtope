"""3-D exchange — the Blender / BIM round-trip (B1).

**Out:** a realised building → OBJ (one group per space, **named by id**, coloured
by τ type, with a ``.mtl``) for Blender, plus a ``.graph.json`` sidecar that
preserves the typed graph (geometry alone loses semantics — ``CellComplex.ByCells``
drops cell dictionaries, and OBJ stores only meshes).

**Back:** ``graph_from_realisation`` reconstructs a typed ``StateGraph`` from the
realised geometry — **adjacency + orientation are read from the geometry**
(``Graph.ByTopology`` + the box axes), **types from the cell semantics** (what a
BIM model carries as IfcSpace types). ``roundtrip`` does out-and-back in memory
for verification; ``graph_from_obj`` reads a (possibly Blender-edited) OBJ back
and recovers types from the sidecar by position.

See ``docs/Generative_Variation_Research_Plan.md`` (B1) and the Blender importer
in ``blender/import_graphtope.py``.
"""

from __future__ import annotations

import json
import re

from topologicpy.Dictionary import Dictionary
from topologicpy.Topology import Topology
from topologicpy.Vertex import Vertex

from . import alphabet as A
from . import realise as _realise
from . import serialize
from .model import StateGraph
from .topoview import COLOR


def legend_rgb(label: str) -> list:
    """τ legend colour for a label as an ``[r, g, b]`` 0–255 triple."""
    hexs = COLOR.get(label, "#777777").lstrip("#")
    return [int(hexs[i:i + 2], 16) for i in (0, 2, 4)]


# === export (out) =========================================================
def to_obj(sg: StateGraph, path: str, *, sidecar: bool = True) -> dict:
    """Realise ``sg`` and write an OBJ (group per space, named by id, coloured by
    type) plus a ``<path>.graph.json`` sidecar. Returns the written paths."""
    r = _realise.realise(sg)
    cells = []
    for nid, cell in r["cells"].items():
        d = Dictionary.ByKeysValues(["id", "label", "color"],
                                    [nid, sg.node_label(nid), legend_rgb(sg.node_label(nid))])
        cells.append(Topology.SetDictionary(cell, d))
    Topology.ExportToOBJ(cells, path=path, nameKey="id", colorKey="color",
                         transposeAxes=False, overwrite=True)
    out = {"obj": path}
    if sidecar:
        side = path + ".graph.json"
        with open(side, "w") as fh:
            json.dump(serialize.to_dict(sg), fh, indent=2)
        out["sidecar"] = side
    return out


# === reconstruct (back) ===================================================
def _cell_attr(cell, key):
    d = Topology.Dictionary(cell)
    return Dictionary.ValueAtKey(d, key) if d else None


def _touch_axis(b1, b2) -> str:
    """The axis on which two face-adjacent boxes touch: 'z' ⇒ V (slab), else H."""
    x1, y1, z1, w1, d1, h1 = b1
    x2, y2, z2, w2, d2, h2 = b2
    if abs((z1 + h1) - z2) < 1e-9 or abs((z2 + h2) - z1) < 1e-9:
        return "z"
    if abs((x1 + w1) - x2) < 1e-9 or abs((x2 + w2) - x1) < 1e-9:
        return "x"
    return "y"


def graph_from_realisation(realisation: dict) -> StateGraph:
    """Reconstruct a typed ``StateGraph`` from realised geometry: adjacency +
    orientation from the cells, labels/subtypes from their semantics."""
    boxes = realisation["boxes"]
    cells = realisation["cells"]
    adjacency, _, _ = _realise.extract_adjacency(realisation)

    g = StateGraph()
    for nid in boxes:
        label = _cell_attr(cells[nid], "label") or A.GENERIC
        subtype = _cell_attr(cells[nid], "subtype")
        g.add_node(label, id=nid, **({"subtype": subtype} if subtype else {}))
    for pair in adjacency:
        a, b = tuple(pair)
        if _touch_axis(boxes[a], boxes[b]) == "z":                # vertical: above → below
            src, tgt = (a, b) if boxes[a][2] > boxes[b][2] else (b, a)
            g.add_edge(src, tgt, A.V, bidirectional=False)
        else:                                                     # horizontal
            g.add_edge(a, b, A.H)
    return g


def roundtrip(sg: StateGraph) -> StateGraph:
    """Out-and-back in memory: realise ``sg``, then reconstruct from geometry.
    Equals ``sg`` (typed) when the realisation is complete (all adjacencies as
    shared faces); otherwise equals the *realised* subgraph."""
    return graph_from_realisation(_realise.realise(sg))


# === B2: import a real named OBJ model with actual sizes =================
def classify_space(name: str):
    """Map a real Blender object name → ``(label, subtype)`` per Appendix A, or
    ``None`` for non-space elements (slabs, columns, …) that are skipped."""
    n = re.sub(r"\.\d+$", "", name).lower()                 # drop Blender's .001 suffix
    if any(k in n for k in ("slab", "column", "mesh_", "wall", "beam", "roof")):
        return None
    if "entrance" in n or "auxiliary_ground" in n:
        return (A.ENTRANCE, None)
    if "corridor" in n:
        return (A.CORRIDOR, None)
    if "stair" in n:
        return (A.STAIRCASE, None)
    if "mesonete" in n or "maisonette" in n:
        return (A.L_SECTION, None)                          # F-type maisonette = the L-section
    if "toilet" in n:
        return (A.GENERIC, "toilet")
    if "lobby" in n:
        return (A.GENERIC, "lobby")
    if "balcony" in n:
        return (A.GENERIC, "balcony")
    if "condenser" in n and "main" in n:
        return (A.GENERIC, "condenser_main")
    if "apartment" in n:
        return (A.GENERIC, "apartment")
    return (A.GENERIC, None)


def _parse_obj_objects(path: str) -> dict:
    """Parse an OBJ into ``{object_name: bbox}`` where bbox = (x, y, z, w, d, h)
    in the model's own units (a robust own-parser; topologic's OBJ import is lossy)."""
    verts, objs, cur = [], {}, None
    with open(path) as fh:
        for line in fh:
            if line.startswith("o "):
                cur = line[2:].strip(); objs[cur] = set()
            elif line.startswith("v "):
                _, x, y, z = line.split()[:4]
                verts.append((float(x), float(y), float(z)))
            elif line.startswith("f ") and cur is not None:
                for tok in line.split()[1:]:
                    objs[cur].add(int(tok.split("/")[0]) - 1)
    boxes = {}
    for n, idx in objs.items():
        if not idx:
            continue
        pts = [verts[i] for i in idx]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
        boxes[n] = (min(xs), min(ys), min(zs),
                    max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    return boxes


def _real_adjacent(b1, b2, gap: float, min_overlap: float):
    """Orientation of the shared face between two real bboxes, or None: two axes
    overlap (a shared wall area) and the third is separated by ≤ ``gap`` (a wall)."""
    ov = []
    for k in range(3):
        lo = max(b1[k], b2[k]); hi = min(b1[k] + b1[k + 3], b2[k] + b2[k + 3])
        ov.append(hi - lo)
    big = [k for k in range(3) if ov[k] > min_overlap]
    if len(big) != 2:
        return None
    k = next(x for x in range(3) if x not in big)
    return ("V" if k == 2 else "H") if -ov[k] <= gap else None


def graph_from_model(path: str, *, gap: float = 0.8, min_overlap: float = 0.8) -> tuple:
    """Import a real named OBJ building → a typed ``StateGraph`` with **actual
    sizes**. Object names are classified to Σ (Appendix A); adjacency + orientation
    come from real bounding-box geometry; every node carries metric attributes
    (width/depth/height/volume/level). Returns ``(graph, boxes)`` — ``boxes`` maps
    node id → real bbox for realising/rendering at true scale."""
    raw = _parse_obj_objects(path)
    spaces = {n: b for n, b in raw.items() if classify_space(n)}
    levels = sorted({round(b[2], 1) for b in spaces.values()})   # z-mins → storey index

    g = StateGraph()
    boxes = {}
    for name, b in spaces.items():
        label, subtype = classify_space(name)
        x, y, z, w, d, h = b
        g.add_node(label, id=name, subtype=subtype, level=levels.index(round(z, 1)),
                   width=round(w, 2), depth=round(d, 2), height=round(h, 2),
                   volume=round(w * d * h, 1))
        boxes[name] = b
    ids = list(spaces)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            o = _real_adjacent(spaces[ids[i]], spaces[ids[j]], gap, min_overlap)
            if o == "V":
                a, b = ids[i], ids[j]
                src, tgt = (a, b) if spaces[a][2] > spaces[b][2] else (b, a)
                g.add_edge(src, tgt, A.V, bidirectional=False)
            elif o == "H":
                g.add_edge(ids[i], ids[j], A.H)
    return g, boxes


def typical_sizes(model_graph: StateGraph) -> dict:
    """Median ``(width, depth, height)`` per τ label from an imported real model —
    the actual proportions to realise generated variants at true scale."""
    from statistics import median
    by: dict = {}
    for n in model_graph.nodes():
        a = model_graph.node_attrs(n)
        if {"width", "depth", "height"} <= a.keys():
            by.setdefault(model_graph.node_label(n), []).append((a["width"], a["depth"], a["height"]))
    return {lab: tuple(round(median(v[i] for v in dims), 2) for i in range(3))
            for lab, dims in by.items()}


def _bbox(cell) -> tuple:
    """Axis-aligned bounding box ``(x, y, z, w, d, h)`` of a cell."""
    xs, ys, zs = [], [], []
    for v in Topology.Vertices(cell):
        x, y, z = Vertex.Coordinates(v)
        xs.append(x); ys.append(y); zs.append(z)
    return (min(xs), min(ys), min(zs), max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def graph_from_obj(obj_path: str, sidecar_path: str | None = None) -> StateGraph:
    """Read a (possibly Blender-edited) OBJ back to a typed ``StateGraph``.

    Adjacency + orientation are re-derived from each re-imported cell's
    **bounding box** (so a cell moved/resized in Blender changes the graph);
    types come from the ``.graph.json`` sidecar, matched by centroid. (Re-imported
    OBJ meshes don't reconstruct shared faces via ``Graph.ByTopology``, hence the
    bounding-box adjacency.) Access-direction of one-way H edges isn't carried by
    geometry — restore it from the sidecar where exactness is needed."""
    topos = Topology.ByOBJPath(obj_path, transposeAxes=False)
    cells = topos if isinstance(topos, list) else [topos]
    boxes = {f"m{i}": _bbox(c) for i, c in enumerate(cells)}

    label_at: dict = {}
    if sidecar_path:
        with open(sidecar_path) as fh:
            src = serialize.from_dict(json.load(fh))
        for nid, box in _realise.box_layout(src)[0].items():
            c = (round(box[0] + box[3] / 2, 2), round(box[1] + box[4] / 2, 2),
                 round(box[2] + box[5] / 2, 2))
            label_at[c] = (src.node_label(nid), src.node_attrs(nid).get("subtype"))

    g = StateGraph()
    for mid, box in boxes.items():
        c = (round(box[0] + box[3] / 2, 2), round(box[1] + box[4] / 2, 2),
             round(box[2] + box[5] / 2, 2))
        label, subtype = label_at.get(c, (A.GENERIC, None))
        g.add_node(label, id=mid, **({"subtype": subtype} if subtype else {}))

    ids = list(boxes)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if _realise._faces_touch(boxes[a], boxes[b]):
                if _touch_axis(boxes[a], boxes[b]) == "z":
                    src, tgt = (a, b) if boxes[a][2] > boxes[b][2] else (b, a)
                    g.add_edge(src, tgt, A.V, bidirectional=False)
                else:
                    g.add_edge(a, b, A.H)
    return g
