"""Visualisation of the typed graph and the derivation, step by step.

Stage-1 graphs have no geometry, so coordinates are layout only. This module
draws the *typed adjacency graph* (the figure-5 view): every node is a small
glyph hinting its shape-type (box / elongated / vertical bar / U / L / opening),
coloured by the §3.1 legend; edges are styled by orientation and direction
(H solid, V dashed; arrowhead for one-way, plain line for bidirectional).

``draw`` renders one state; ``draw_grid`` lays out a sequence of derivation
snapshots with a shared, stable layout so nodes don't jump between steps —
giving a step-by-step picture of the shapes as the grammar grows them.

A 3-D Topologic render of the carrier is still available via ``show``/``pyvis``.
"""

from __future__ import annotations

import math

from . import alphabet as A
from . import serialize
from .shape_iface import shape_type

# --- §3.1 legend colours --------------------------------------------------
COLOR = {
    A.GENERIC: "#3a3a3a",
    A.CORRIDOR: "#e8821e",
    A.STAIRCASE: "#2e8b57",
    A.U_SECTION: "#1f6feb",
    A.L_SECTION: "#17becf",
    A.ENTRANCE: "#c0392b",   # spec legend is black; reddened here to read vs generic
}

# glyph proportions (w, h) per shape-type tag from τ (§9) ------------------
_GLYPH = {
    "parallelepiped": (0.30, 0.30),            # generic — box
    "elongated_parallelepiped": (0.52, 0.20),  # corridor — wide
    "vertical_parallelepiped": (0.20, 0.52),   # staircase — tall
    "u_profile_solid": (0.40, 0.36),           # u_section
    "l_profile_solid": (0.40, 0.36),           # l_section
    "ground_floor_opening": (0.30, 0.30),      # entrance — triangle
}


def _as_data(state) -> dict:
    """Accept a StateGraph or an already-serialized dict."""
    return state if isinstance(state, dict) else serialize.to_dict(state)


def _nx_from_frames(frames):
    import networkx as nx
    G = nx.Graph()
    for _, data in frames:
        for n in data["nodes"]:
            G.add_node(n["id"])
        for e in data["edges"]:
            G.add_edge(e["src"], e["tgt"])
    return G


def shared_layout(frames, seed: int = 7) -> dict:
    """A stable position per node id, computed over every node/edge that ever
    appears, so positions don't move between snapshots. Disconnected components
    (e.g. the residential and condenser blocks) are placed in separate bands."""
    import networkx as nx
    G = _nx_from_frames(frames)
    if G.number_of_nodes() == 0:
        return {}
    pos: dict = {}
    x_offset = 0.0
    for comp in sorted(nx.connected_components(G), key=len, reverse=True):
        sub = G.subgraph(comp)
        try:
            p = nx.kamada_kawai_layout(sub, scale=max(1.0, len(comp) ** 0.5))
        except Exception:
            p = nx.spring_layout(sub, seed=seed, k=1.0)
        xs = [xy[0] for xy in p.values()]; ys = [xy[1] for xy in p.values()]
        minx, miny = min(xs), min(ys)
        for node, (x, y) in p.items():           # keep natural spacing; tile in x
            pos[node] = (x - minx + x_offset, y - miny)
        x_offset += (max(xs) - minx) + 2.0       # component width + gap
    return pos


def _glyph(ax, x, y, label, sub):
    import matplotlib.patches as mp
    color = COLOR.get(label, "#777")
    stype = shape_type(label) if label in COLOR else "parallelepiped"
    w, h = _GLYPH.get(stype, (0.3, 0.3))
    if label == A.ENTRANCE:                      # opening → triangle
        patch = mp.RegularPolygon((x, y), numVertices=3, radius=0.20,
                                  orientation=0, facecolor=color, edgecolor="black",
                                  lw=1.0, zorder=3)
    elif label == A.U_SECTION:                   # U glyph
        patch = mp.Polygon(_u_points(x, y, w, h), closed=True, facecolor=color,
                           edgecolor="black", lw=1.0, zorder=3)
    elif label == A.L_SECTION:                   # L glyph
        patch = mp.Polygon(_l_points(x, y, w, h), closed=True, facecolor=color,
                           edgecolor="black", lw=1.0, zorder=3)
    else:                                        # box / elongated / vertical bar
        patch = mp.FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                  boxstyle="round,pad=0.01,rounding_size=0.03",
                                  facecolor=color, edgecolor="black", lw=1.0, zorder=3)
    ax.add_patch(patch)
    tag = sub if sub else label[:4]
    ax.text(x, y - 0.015, tag, ha="center", va="center", color="white",
            fontsize=6.5, fontweight="bold", zorder=4)


def _u_points(x, y, w, h):
    return [(x - w / 2, y + h / 2), (x - w / 2, y - h / 2), (x + w / 2, y - h / 2),
            (x + w / 2, y + h / 2), (x + w / 6, y + h / 2), (x + w / 6, y - h / 6),
            (x - w / 6, y - h / 6), (x - w / 6, y + h / 2)]


def _l_points(x, y, w, h):
    return [(x - w / 2, y + h / 2), (x - w / 6, y + h / 2), (x - w / 6, y - h / 6),
            (x + w / 2, y - h / 6), (x + w / 2, y - h / 2), (x - w / 2, y - h / 2)]


def draw(state, ax=None, pos=None, title=None, seed: int = 7):
    """Draw one typed-graph state (StateGraph or serialized dict)."""
    import matplotlib.pyplot as plt
    data = _as_data(state)
    if pos is None:
        pos = shared_layout([("", data)], seed=seed)
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))

    # edges first, under the glyphs
    for e in data["edges"]:
        if e["src"] not in pos or e["tgt"] not in pos:
            continue
        x0, y0 = pos[e["src"]]; x1, y1 = pos[e["tgt"]]
        style = "dashed" if e["orientation"] == A.V else "solid"
        color = "#888" if e["orientation"] == A.H else "#555"
        arrow = "-" if e["bidirectional"] else "-|>"
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle=arrow, color=color, lw=1.3,
                                    linestyle=style, shrinkA=12, shrinkB=12), zorder=1)

    labels = {n["id"]: (n["label"], (n.get("attrs") or {}).get("subtype")) for n in data["nodes"]}
    for nid, (label, sub) in labels.items():
        if nid in pos:
            _glyph(ax, pos[nid][0], pos[nid][1], label, sub)

    ax.set_title(title or "", fontsize=10)
    ax.set_aspect("equal"); ax.axis("off")
    ax.margins(0.18)
    return ax


def draw_grid(frames, pos=None, ncols: int = 4, panel: float = 3.2, seed: int = 7):
    """Draw a sequence of ``(title, state)`` snapshots on a shared layout.

    ``frames`` is a list of ``(title, StateGraph-or-dict)``. Returns the figure.
    """
    import matplotlib.pyplot as plt
    frames = [(t, _as_data(s)) for t, s in frames]
    if pos is None:
        pos = shared_layout(frames, seed=seed)
    n = len(frames)
    ncols = min(ncols, n) or 1
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(panel * ncols, panel * nrows))
    axes = [axes] if n == 1 else list(axes.flat)
    for ax, (title, data) in zip(axes, frames):
        draw(data, ax=ax, pos=pos, title=title)
    for ax in axes[n:]:
        ax.axis("off")
    fig.legend(handles=legend_handles(), loc="lower center", ncol=len(COLOR),
               frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return fig


def legend_handles():
    """Matplotlib proxy handles for the node-type legend."""
    import matplotlib.patches as mp
    return [mp.Patch(facecolor=c, edgecolor="black", label=l) for l, c in COLOR.items()]


# --- record a derivation as drawable frames ------------------------------
def record_frames(axiom, run):
    """Run a derivation, capturing a snapshot after each step.

    ``axiom`` is a fresh ``StateGraph``; ``run(d)`` applies productions to the
    ``Derivation`` ``d``. Returns ``(frames, derivation)`` where ``frames`` is
    ``[(title, dict), …]`` starting from the axiom.
    """
    from .engine import Derivation
    frames = [("A₀ axiom", serialize.to_dict(axiom))]
    d = Derivation(axiom, on_apply=lambda step, sg: frames.append((step.rule, serialize.to_dict(sg))))
    run(d)
    return frames, d


# --- Stage-2 3-D massing render (the realised cells) ---------------------
def _cuboid_faces(x, y, z, sx, sy, sz):
    p = [(x, y, z), (x + sx, y, z), (x + sx, y + sy, z), (x, y + sy, z),
         (x, y, z + sz), (x + sx, y, z + sz), (x + sx, y + sy, z + sz), (x, y + sy, z + sz)]
    return [[p[0], p[1], p[2], p[3]], [p[4], p[5], p[6], p[7]],
            [p[0], p[1], p[5], p[4]], [p[2], p[3], p[7], p[6]],
            [p[1], p[2], p[6], p[5]], [p[0], p[3], p[7], p[4]]]


def draw_massing(sg, ax=None, boxes=None, inset: float = 0.06,
                 elev: int = 22, azim: int = -58):
    """Draw the realised cells as a 3-D massing model, coloured by node type.

    Each node becomes a (variable-size) cell at its grid box (z = level);
    adjacency edges are the shared faces between touching cells (spec §9). Cells
    are inset slightly so individual rooms read."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from .realise import box_layout

    if boxes is None:
        boxes, _, _ = box_layout(sg)
    if ax is None:
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
    for nid, (gx, gy, gz, w, d, h) in boxes.items():
        color = COLOR.get(sg.node_label(nid), "#777")
        pc = Poly3DCollection(
            _cuboid_faces(gx + inset, gy + inset, gz + inset, w - 2 * inset, d - 2 * inset, h - 2 * inset),
            facecolor=color, edgecolor="black", linewidths=0.4, alpha=0.92)
        ax.add_collection3d(pc)
    xs = [b[0] for b in boxes.values()] + [b[0] + b[3] for b in boxes.values()]
    ys = [b[1] for b in boxes.values()] + [b[1] + b[4] for b in boxes.values()]
    zs = [b[2] for b in boxes.values()] + [b[2] + b[5] for b in boxes.values()]
    ax.set_xlim(min(xs), max(xs)); ax.set_ylim(min(ys), max(ys))
    ax.set_zlim(min(zs), max(zs))
    ax.set_box_aspect((max(xs) - min(xs), max(ys) - min(ys) + 0.01, max(zs) - min(zs) + 0.5))
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("level")
    return ax


# --- 3-D Topologic carrier render (unchanged) ----------------------------
def show(sg, *, vertex_label_key: str = "label", **kwargs):
    """Render the underlying Topologic graph with the Plotly viewer."""
    from topologicpy.Graph import Graph
    return Graph.Show(sg.topologic_graph, vertexLabelKey=vertex_label_key, **kwargs)


def pyvis(sg, **kwargs):
    from topologicpy.Graph import Graph
    return Graph.PyvisGraph(sg.topologic_graph, **kwargs)
