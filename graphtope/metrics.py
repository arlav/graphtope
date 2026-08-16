"""Metrics & the design-space map (G4).

Measure a population of grammar-driven variants along three families of axes and
lay them out as a 2-D *design space* with the reference (``G_DNF``) marked, so a
catalogue can be browsed by *what it is* rather than by index:

- **graph metrics** (level-1 topology, any ``StateGraph``): unit count, type mix,
  K:F ratio, circulation depth from the entrance, level count, components.
- **geometry metrics** (Stage-2, from the placed boxes a slab carries): gross
  floor area, volume, footprint, compactness, area per unit.
- **interior richness** (level-2, a refined graph): interior rooms, voids, and
  rooms per unit — the second grammar level (``bridge.refine_units``) made
  measurable.

``feature_vector(slab)`` is the ordered numeric signature used for the map;
``design_space(slabs, reference=…)`` standardises the signatures and embeds them
in 2-D by classical multidimensional scaling (numpy only — no sklearn), returning
coordinates plus the reference's index. See ``docs/Generative_Variation_Research_Plan.md`` (G4).
"""

from __future__ import annotations

from collections import Counter, deque

from . import alphabet as A
from . import validity
from .model import StateGraph

#: interior room subtypes — derived from the registered sub-alphabet (SG1),
#: never restated here
from .interior import ROOM_SUBTYPES as INTERIOR_SUBTYPES  # noqa: E402


# === graph metrics (level-1 topology) ====================================
def _undirected_adj(sg: StateGraph) -> dict:
    adj = {n: set() for n in sg.nodes()}
    for e in sg.edges():
        adj[e["src"]].add(e["tgt"])
        adj[e["tgt"]].add(e["src"])
    return adj


def type_mix(sg: StateGraph) -> dict:
    """Count of nodes by label — the programme at a glance."""
    return dict(Counter(sg.node_label(n) for n in sg.nodes()))


def unit_count(sg: StateGraph) -> int:
    """Habitable spaces (generic / u_section / l_section — §validity.HABITABLE)."""
    return sum(1 for n in sg.nodes() if sg.node_label(n) in validity.HABITABLE)


def kf_ratio(sg: StateGraph) -> float:
    """K:F ratio — u_sections per l_section. ``inf`` if there are K's but no F,
    ``0.0`` if neither (a plain slab); the built section interlocks the two."""
    k = sum(1 for n in sg.nodes() if sg.node_label(n) == A.U_SECTION)
    f = sum(1 for n in sg.nodes() if sg.node_label(n) == A.L_SECTION)
    if f == 0:
        return float("inf") if k else 0.0
    return k / f


def circulation_depth(sg: StateGraph) -> int:
    """The deepest habitable space, measured in adjacencies from the nearest
    circulation (corridor/staircase) — 1 = docked straight onto a corridor, 2 =
    entered through another room (a banked ``R`` room), etc. ``0`` if there is no
    circulation. A shallow, legible plan scores low."""
    adj = _undirected_adj(sg)
    sources = [n for n in sg.nodes() if sg.node_label(n) in validity.CIRCULATION]
    if not sources:
        return 0
    dist = {s: 0 for s in sources}
    q = deque(sources)
    while q:
        n = q.popleft()
        for m in adj[n]:
            if m not in dist:
                dist[m] = dist[n] + 1
                q.append(m)
    hab = [dist[n] for n in sg.nodes()
           if sg.node_label(n) in validity.HABITABLE and n in dist]
    return max(hab) if hab else 0


def _levels(sg: StateGraph) -> set:
    out = set()
    for n in sg.nodes():
        lv = sg.node_attrs(n).get("level")
        if lv is not None:
            out.add(int(lv))
    return out


def level_count(sg: StateGraph) -> int:
    """Distinct storeys the graph occupies (from the ``level`` attr; 0 if none)."""
    return len(_levels(sg))


def component_count(sg: StateGraph) -> int:
    """Connected building blocks (1 = a single coherent building)."""
    adj = _undirected_adj(sg)
    seen, comps = set(), 0
    for n in sg.nodes():
        if n in seen:
            continue
        comps += 1
        stack = [n]; seen.add(n)
        while stack:
            c = stack.pop()
            for m in adj[c]:
                if m not in seen:
                    seen.add(m); stack.append(m)
    return comps


# === geometry metrics (Stage-2 boxes) ====================================
def _boxes(slab: StateGraph) -> dict:
    from . import narkomfin as nf
    return nf.boxes_of(slab)


def gross_floor_area(slab: StateGraph, boxes: dict | None = None) -> float:
    """Sum of each placed cell's footprint w·d (m²) — total built floor area."""
    boxes = boxes if boxes is not None else _boxes(slab)
    return round(sum(w * d for _, _, _, w, d, _ in boxes.values()), 2)


def volume(slab: StateGraph, boxes: dict | None = None) -> float:
    """Sum of placed cell volumes w·d·h (m³)."""
    boxes = boxes if boxes is not None else _boxes(slab)
    return round(sum(w * d * h for _, _, _, w, d, h in boxes.values()), 2)


def bbox_extents(boxes: dict) -> tuple:
    """The population's ``(dx, dy, dz)`` bounding-box extents (m)."""
    xs0 = [x for x, _, _, _, _, _ in boxes.values()]
    ys0 = [y for _, y, _, _, _, _ in boxes.values()]
    zs0 = [z for _, _, z, _, _, _ in boxes.values()]
    xs1 = [x + w for x, _, _, w, _, _ in boxes.values()]
    ys1 = [y + d for _, y, _, _, d, _ in boxes.values()]
    zs1 = [z + h for _, _, z, _, _, h in boxes.values()]
    return (max(xs1) - min(xs0), max(ys1) - min(ys0), max(zs1) - min(zs0))


def footprint(slab: StateGraph, boxes: dict | None = None) -> float:
    """Ground footprint = the x·y area of the bounding box (m²)."""
    boxes = boxes if boxes is not None else _boxes(slab)
    dx, dy, _ = bbox_extents(boxes)
    return round(dx * dy, 2)


def compactness(slab: StateGraph, boxes: dict | None = None) -> float:
    """Packing efficiency: built volume ÷ bounding-box volume (0–1). A dense
    double-loaded block scores high; a thin single-loaded slab low."""
    boxes = boxes if boxes is not None else _boxes(slab)
    dx, dy, dz = bbox_extents(boxes)
    env = dx * dy * dz
    return round(volume(slab, boxes) / env, 3) if env > 0 else 0.0


def area_per_unit(slab: StateGraph, boxes: dict | None = None) -> float:
    """Gross floor area per habitable unit (m²/unit) — 0 if no units."""
    boxes = boxes if boxes is not None else _boxes(slab)
    n = unit_count(slab)
    return round(gross_floor_area(slab, boxes) / n, 2) if n else 0.0


# === interior richness (level-2 refined graph) ===========================
def interior_rooms(refined: StateGraph) -> int:
    """Interior rooms across all refined units (living/sleeping/kitchen/bath/…)."""
    return sum(1 for n in refined.nodes()
               if refined.node_attrs(n).get("subtype") in INTERIOR_SUBTYPES)


def void_count(refined: StateGraph) -> int:
    """Double-height voids introduced by the K sub-grammar."""
    return sum(1 for n in refined.nodes()
               if refined.node_attrs(n).get("subtype") == "void")


def rooms_per_unit(refined: StateGraph, slab: StateGraph) -> float:
    """Interior rooms ÷ the slab's unit count — how finely units are developed."""
    n = unit_count(slab)
    return round(interior_rooms(refined) / n, 2) if n else 0.0


# === the design-space signature & map ====================================
#: ordered numeric features used to embed the design space (graph + geometry)
FEATURES = ("unit_count", "kf_ratio", "circulation_depth", "level_count",
            "gross_floor_area", "volume", "footprint", "compactness",
            "area_per_unit")


def feature_vector(slab: StateGraph, boxes: dict | None = None) -> dict:
    """The ordered numeric signature of a realised slab (``FEATURES``). ``inf``
    K:F (K's, no F) is clamped to a finite sentinel so the map stays metric."""
    boxes = boxes if boxes is not None else _boxes(slab)
    r = kf_ratio(slab)
    return {
        "unit_count": float(unit_count(slab)),
        "kf_ratio": 4.0 if r == float("inf") else float(r),
        "circulation_depth": float(circulation_depth(slab)),
        "level_count": float(level_count(slab)),
        "gross_floor_area": gross_floor_area(slab, boxes),
        "volume": volume(slab, boxes),
        "footprint": footprint(slab, boxes),
        "compactness": compactness(slab, boxes),
        "area_per_unit": area_per_unit(slab, boxes),
    }


def _matrix(vectors: list):
    import numpy as np
    return np.array([[v[f] for f in FEATURES] for v in vectors], dtype=float)


def _standardise(m):
    """Z-score each column (guard zero variance) so no single axis dominates."""
    import numpy as np
    mu = m.mean(axis=0)
    sd = m.std(axis=0)
    sd = np.where(sd == 0, 1.0, sd)
    return (m - mu) / sd


def distance_matrix(slabs: list):
    """Pairwise Euclidean distance between standardised feature signatures."""
    import numpy as np
    z = _standardise(_matrix([feature_vector(s) for s in slabs]))
    diff = z[:, None, :] - z[None, :, :]
    return np.sqrt((diff ** 2).sum(axis=-1))


def _classical_mds(dist):
    """Classical MDS (Torgerson): embed a distance matrix in 2-D via the top two
    eigenvectors of the double-centred Gram matrix. Deterministic (numpy eigh)."""
    import numpy as np
    n = dist.shape[0]
    if n == 1:
        return np.zeros((1, 2))
    j = np.eye(n) - np.ones((n, n)) / n
    b = -0.5 * j @ (dist ** 2) @ j
    vals, vecs = np.linalg.eigh(b)
    order = np.argsort(vals)[::-1][:2]
    coords = vecs[:, order] * np.sqrt(np.clip(vals[order], 0, None))
    if coords.shape[1] < 2:                      # degenerate (all coincident)
        coords = np.pad(coords, ((0, 0), (0, 2 - coords.shape[1])))
    return coords


def design_space(slabs: list, *, reference: StateGraph | None = None) -> dict:
    """Lay the population out as a 2-D map. ``slabs`` are realised (box-carrying)
    slabs; pass the DNF's realised slab as ``reference`` to mark it. Returns
    ``{"coords": (N[+1]×2 array), "reference_index": int|None, "features":
    [dict,…]}`` — the reference, if given, is the last row."""
    items = list(slabs) + ([reference] if reference is not None else [])
    dist = distance_matrix(items)
    coords = _classical_mds(dist)
    return {"coords": coords,
            "reference_index": (len(items) - 1) if reference is not None else None,
            "features": [feature_vector(s) for s in items]}


# === SG3 — the interior design space (level 2) ===========================
#: ordered numeric features of one refined interior (the level-2 signature)
INTERIOR_FEATURES = ("interior_rooms", "void_count", "wet_rooms",
                     "habitable_rooms", "door_count", "window_count",
                     "storage_count")


def interior_feature_vector(refined: StateGraph) -> dict:
    """The ordered numeric signature of a refined (level-2) graph — counts
    derived from the Σ_int registry's flags (SG1), never hand-listed."""
    from . import interior as I
    subs = [refined.node_attrs(n).get("subtype") for n in refined.nodes()]
    return {
        "interior_rooms": float(interior_rooms(refined)),
        "void_count": float(void_count(refined)),
        "wet_rooms": float(sum(1 for s in subs if s in I.WET_SUBTYPES)),
        "habitable_rooms": float(sum(1 for s in subs
                                     if s in I.HABITABLE_SUBTYPES)),
        "door_count": float(subs.count(I.DOOR)),
        "window_count": float(subs.count(I.WINDOW)),
        "storage_count": float(subs.count(I.STORAGE)),
    }


def interior_design_space(refined_graphs: list, *,
                          reference: StateGraph | None = None) -> dict:
    """SG3 — the level-2 analogue of ``design_space``: embed one slab's
    interior variants (optionally with a reference interior, marked last) in
    2-D by the same deterministic classical MDS."""
    import numpy as np
    items = list(refined_graphs) + ([reference] if reference is not None else [])
    vecs = [interior_feature_vector(g) for g in items]
    z = _standardise(np.array([[v[f] for f in INTERIOR_FEATURES] for v in vecs],
                              dtype=float))
    diff = z[:, None, :] - z[None, :, :]
    coords = _classical_mds(np.sqrt((diff ** 2).sum(axis=-1)))
    return {"coords": coords,
            "reference_index": (len(items) - 1) if reference is not None else None,
            "features": vecs}


# === SG7 — interior quality metrics + the two-level design space ==========
def _unit_entry(refined: StateGraph, unit_nodes: set) -> str | None:
    """The unit's entry: the interior node holding the routed corridor edge;
    fallback by kind (entry hall → living → the banked room itself)."""
    from . import alphabet as A
    for n in unit_nodes:
        for e in refined.edges():
            if n not in (e["src"], e["tgt"]):
                continue
            other = e["tgt"] if e["src"] == n else e["src"]
            if other not in unit_nodes and refined.node_label(other) == A.CORRIDOR:
                return n
    for sub in ("entry", "living", "room"):
        for n in unit_nodes:
            if refined.node_attrs(n).get("subtype") == sub:
                return n
    return None


def _unit_graphs(refined: StateGraph):
    """``[(unit_id, {node ids}]`` — the SG3/SG4 ``unit`` tags group interiors;
    graphs without tags (an imported reference) fall back to connected
    components, which is the same grouping for a per-unit interior."""
    from .validity import _components
    units: dict = {}
    for n in refined.nodes():
        uid = refined.node_attrs(n).get("unit")
        if uid is not None:
            units.setdefault(uid, set()).add(n)
    if units:
        return sorted(units.items())
    adj = _undirected_adj(refined)
    return [(i, comp) for i, comp in enumerate(_components(refined, adj))]



def privacy_gradient(refined: StateGraph) -> float:
    """Mean depth (adjacencies, traversing doors — §5.2) of habitable rooms
    from their unit's entry: the plan's privacy gradient. 1.0 = every
    habitable room opens directly off the entry; deeper = more withdrawn
    (a K's sleeping gallery reaches past the living volume)."""
    from . import interior as I
    adj = _undirected_adj(refined)
    total = count = 0
    for _, nodes in _unit_graphs(refined):
        entry = _unit_entry(refined, nodes)
        if entry is None:
            continue
        dist = {entry: 0}
        q = deque([entry])
        while q:
            n = q.popleft()
            for m in adj[n]:
                if m not in dist:
                    dist[m] = dist[n] + 1
                    q.append(m)
        for n in nodes:
            if refined.node_attrs(n).get("subtype") in I.HABITABLE_SUBTYPES \
                    and n in dist:
                total += dist[n]
                count += 1
    return round(total / count, 3) if count else 0.0


def daylight_ratio(refined: StateGraph) -> float:
    """Habitable rooms with a window ÷ habitable rooms — *real* daylight
    (window nodes, §5.2), not a façade proxy."""
    from . import interior as I
    adj = _undirected_adj(refined)
    lit = hab = 0
    for n in refined.nodes():
        sub = refined.node_attrs(n).get("subtype")
        if sub not in I.HABITABLE_SUBTYPES:
            continue
        hab += 1
        if any(refined.node_attrs(m).get("subtype") == I.WINDOW for m in adj[n]):
            lit += 1
    return round(lit / hab, 3) if hab else 0.0


def circ_area_ratio(refined: StateGraph) -> float:
    """Internal-circulation footprint ÷ habitable footprint (placed rooms,
    SG4). ``0.0`` when the interior carries no geometry."""
    from . import interior as I
    from .interior_geom import boxes
    bx = boxes(refined)
    if not bx:
        return 0.0
    circ = hab = 0.0
    for n, (_, _, _, w, d, _) in bx.items():
        sub = refined.node_attrs(n).get("subtype")
        if sub == I.INTERNAL:
            circ += w * d
        elif sub in I.HABITABLE_SUBTYPES:
            hab += w * d
    return round(circ / hab, 3) if hab else 0.0


def wet_core_compactness(refined: StateGraph) -> float:
    """Mean graph distance between a unit's wet rooms (kitchen/bath/wc —
    Σ_int's ``wet`` flag), averaged over units: the wet core's clustering.
    0.0 = one wet room (or none) per unit — trivially compact; larger = the
    plumbing spreads through the plan."""
    from . import interior as I
    adj = _undirected_adj(refined)

    def bfs(s):
        dist = {s: 0}
        q = deque([s])
        while q:
            n = q.popleft()
            for m in adj[n]:
                if m not in dist:
                    dist[m] = dist[n] + 1
                    q.append(m)
        return dist

    total = count = 0
    for _, nodes in _unit_graphs(refined):
        wet = [n for n in nodes
               if refined.node_attrs(n).get("subtype") in I.WET_SUBTYPES]
        for i, a in enumerate(wet):
            d = bfs(a)
            for b in wet[i + 1:]:
                total += d.get(b, 0)
                count += 1
    return round(total / count, 3) if count else 0.0


def interior_type_mix(refined: StateGraph) -> float:
    """Mean distinct room kinds per unit — the interior's own programme mix."""
    from . import interior as I
    mixes = []
    for _, nodes in _unit_graphs(refined):
        kinds = {refined.node_attrs(n).get("subtype") for n in nodes
                 if refined.node_attrs(n).get("subtype") in I.ROOM_SUBTYPES}
        mixes.append(len(kinds))
    return round(sum(mixes) / len(mixes), 3) if mixes else 0.0


#: ordered interior-quality features (SG7, paper Figure 8's micro axes)
INTERIOR2_FEATURES = ("privacy_gradient", "daylight_ratio", "circ_area_ratio",
                      "wet_core_compactness", "interior_type_mix")


def interior_quality_vector(refined: StateGraph) -> dict:
    """The ordered interior-quality signature of a refined graph."""
    return {f: float(globals()[f](refined)) for f in INTERIOR2_FEATURES}


def two_level_design_space(pairs: list, *,
                           reference: tuple | None = None) -> dict:
    """SG7 — the joint map: ``pairs = [(slab, refined), …]`` (a *building with
    an interior architecture* per point). Macro coordinates embed the block
    signatures (``FEATURES``), micro coordinates the interior-quality
    signatures (``INTERIOR2_FEATURES``) — each by the deterministic classical
    MDS, standardised independently, so the two levels contribute independent
    axes. ``reference = (slab, refined)`` is appended and marked last."""
    import numpy as np
    items = list(pairs) + ([reference] if reference is not None else [])
    macro = _standardise(_matrix([feature_vector(s) for s, _ in items]))
    micro = _standardise(np.array(
        [[v[f] for f in INTERIOR2_FEATURES]
         for v in (interior_quality_vector(r) for _, r in items)], dtype=float))
    emb = lambda z: _classical_mds(np.sqrt(((z[:, None, :] - z[None, :, :]) ** 2)
                                           .sum(axis=-1)))
    return {"macro": emb(macro), "micro": emb(micro),
            "reference_index": (len(items) - 1) if reference is not None else None,
            "macro_features": [feature_vector(s) for s, _ in items],
            "micro_features": [interior_quality_vector(r) for _, r in items]}


def cluster(coords, k: int, *, seed: int = 0):
    """Deterministic k-means over the 2-D map — a coarse grouping of the design
    space. Returns an integer label per point (0…k-1). ``k`` is clamped to the
    point count."""
    import numpy as np
    pts = np.asarray(coords, dtype=float)
    n = len(pts)
    k = max(1, min(k, n))
    rng = np.random.default_rng(seed)
    centres = pts[rng.choice(n, size=k, replace=False)].copy()
    labels = np.zeros(n, dtype=int)
    for _ in range(50):
        d = np.sqrt(((pts[:, None, :] - centres[None, :, :]) ** 2).sum(-1))
        new = d.argmin(axis=1)
        if np.array_equal(new, labels) and _ > 0:
            break
        labels = new
        for c in range(k):
            members = pts[labels == c]
            if len(members):
                centres[c] = members.mean(axis=0)
    return labels
