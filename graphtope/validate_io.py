"""Variant validation — the shared core for cross-tool QA (SG8).

The same checks run in three places — **pytest** (every commit), **Jupyter**
(the notebook's closing loop) and **Blender headless**
(``blender/validate_variants.py``, optionally rendering thumbnails) — over
the exported artefacts (OBJ + ``.graph.json`` sidecar), never over live
objects. Per the repo's standing convention **the sidecar JSON is the
authoritative graph**; the OBJ is the geometry under test.

Checks per variant (mirroring SG4's in-process ``tile_report``, but from
files — so what Blender receives is what was verified):

* **integrity** — every sidecar node with a box appears as an OBJ group and
  vice versa (counts + names);
* **tiling** — per unit (the SG3 ``unit`` tags, envelope = the tagged slab
  node's box): the spaces' volume sums to the envelope, no two overlap
  (openings excluded — a door leaf legitimately sits in a wall plane);
* **adjacency coverage** — every graph edge between boxed space nodes is a
  real shared face of the OBJ groups' bounding boxes (the "one
  representation" claim, tested at the file boundary).

``validate_variant`` returns the report dict; ``validate_directory``
validates an exported catalogue and writes ``validation.json`` (the
Blender/Jupyter hand-off artefact). ``ok`` aggregates everything.
"""

from __future__ import annotations

import json
import os

_TOL = 0.1          # m³ / m² slop for float round-trips through OBJ text
_EPS = 1e-6

#: node subtypes that live in walls, not floor area
_OPENINGS = ("door", "window")


def _parse_groups(path: str) -> dict:
    """``{group name: bbox (x, y, z, w, d, h)}`` from an OBJ's ``o``/``g``
    objects (a robust own-parser — handles both the 0.9.43 exporter's ``g``
    groups and ``o`` objects)."""
    verts, objs, cur = [], {}, None
    with open(path) as fh:
        for line in fh:
            if line.startswith(("o ", "g ")):
                cur = line[2:].strip()
                objs.setdefault(cur, set())
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
        xs, ys, zs = zip(*((p[0], p[1], p[2]) for p in pts))
        boxes[n] = (min(xs), min(ys), min(zs),
                    max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    return boxes


def _vol(b):
    return b[3] * b[4] * b[5]


def _overlap(b1, b2) -> float:
    ov = 1.0
    for i in (0, 1, 2):
        ov *= max(0.0, min(b1[i] + b1[i + 3], b2[i] + b2[i + 3]) - max(b1[i], b2[i]))
    return ov


def _faces_touch(b1, b2) -> bool:
    ov = []
    for k in range(3):
        lo = max(b1[k], b2[k])
        hi = min(b1[k] + b1[k + 3], b2[k] + b2[k + 3])
        ov.append(hi - lo)
    touching = [k for k in range(3) if abs(ov[k]) < 1e-6]
    big = [k for k in range(3) if ov[k] > 1e-6]
    return len(touching) == 1 and len(big) == 2


def _load_sidecar(obj_path: str) -> dict:
    side = obj_path + ".graph.json"
    if not os.path.exists(side):
        raise FileNotFoundError(f"no sidecar for {obj_path} (the authoritative graph)")
    with open(side) as fh:
        return json.load(fh)


def validate_variant(obj_path: str, *, sidecar: dict | None = None) -> dict:
    """Validate one exported variant (OBJ + sidecar). Returns the report."""
    data = sidecar if sidecar is not None else _load_sidecar(obj_path)
    boxes = _parse_groups(obj_path)
    nodes = {n["id"]: n for n in data["nodes"]}
    attrs = {i: n.get("attrs", {}) for i, n in nodes.items()}
    sub = {i: n.get("attrs", {}).get("subtype") for i, n in nodes.items()}

    # -- integrity: names both ways --------------------------------------
    boxed = {i for i, a in attrs.items()
             if all(k in a for k in ("x", "y", "z", "w", "d", "h"))}
    missing = sorted(boxed - set(boxes))
    stray = sorted(set(boxes) - boxed)
    integrity_ok = not missing and not stray

    # -- per-unit tiling (unit tags; envelope = the tagged slab node) -----
    units: dict = {}
    for i in boxed:
        uid = attrs[i].get("unit")
        if uid is not None and uid in attrs:
            units.setdefault(uid, []).append(i)
    unit_reports = {}
    tiling_ok = True
    for uid, members in sorted(units.items()):
        env = tuple(attrs[uid][k] for k in ("x", "y", "z", "w", "d", "h"))
        spaces = [m for m in members if sub[m] not in _OPENINGS]
        vol_err = sum(_vol(boxes[m]) for m in spaces) - _vol(env)
        overlaps = [tuple(sorted((a, b)))
                    for ii, a in enumerate(spaces) for b in spaces[ii + 1:]
                    if _overlap(boxes[a], boxes[b]) > _TOL]
        ok = abs(vol_err) < _TOL and not overlaps
        tiling_ok &= ok
        unit_reports[uid] = {"spaces": len(spaces),
                             "volume_error": round(vol_err, 4),
                             "overlaps": overlaps, "ok": ok}

    # -- adjacency coverage: every space edge a shared OBJ face -----------
    edges = [(e["src"], e["tgt"]) for e in data["edges"]
             if e["src"] in boxes and e["tgt"] in boxes
             and sub.get(e["src"]) not in _OPENINGS
             and sub.get(e["tgt"]) not in _OPENINGS]
    missed = [e for e in edges if not _faces_touch(boxes[e[0]], boxes[e[1]])]
    adjacency_ok = not missed

    ok = integrity_ok and tiling_ok and adjacency_ok
    return {"obj": os.path.basename(obj_path), "ok": ok,
            "objects": len(boxes), "nodes": len(nodes),
            "integrity": {"missing": missing, "stray": stray, "ok": integrity_ok},
            "units": unit_reports, "tiling_ok": tiling_ok,
            "edges_checked": len(edges), "edge_face_misses": missed,
            "adjacency_ok": adjacency_ok}


def validate_directory(directory: str, *, write: bool = True) -> dict:
    """Validate every ``*.obj`` (+ sidecar) in ``directory``; write
    ``validation.json`` there (the Blender↔Jupyter hand-off artefact)."""
    reports, all_ok = {}, True
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".obj") or fn.endswith(".graph.json"):
            continue
        path = os.path.join(directory, fn)
        if not os.path.exists(path + ".graph.json"):
            continue
        r = validate_variant(path)
        reports[fn] = r
        all_ok &= r["ok"]
    out = {"ok": all_ok, "variants": len(reports), "reports": reports}
    if write:
        with open(os.path.join(directory, "validation.json"), "w") as fh:
            json.dump(out, fh, indent=2)
    return out
