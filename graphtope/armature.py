"""Circulation-first *shape* grammar — the missing bridge (prototype).

The graph grammar (P1–P8, `generate`) says *which* spaces connect; it does not say
*how* they assemble. This module is the shape-grammar side: build the **armature**
(a corridor spine with staircases at the ends) first, then **anchor** U / L / box
units onto it with **exact interface rules** — units dock onto the corridor face and
interlock in section, the way the real Dom Narkomfin is a precise kit-of-parts.

It returns *both* a typed `StateGraph` (topology, adjacency from real touching) and
`boxes` (exact real-metre geometry where faces coincide) — so the graph grammar and
the geometry stay in step. Dimensions come from the real model (`exchange.typical_sizes`).
"""

from __future__ import annotations

from . import alphabet as A
from .model import StateGraph

# real Narkomfin module (metres) — from the imported model
BAY = 3.66          # structural bay along the slab
CORRIDOR_DEPTH = 2.8
UNIT_DEPTH = 8.42   # maisonette depth
FLOOR = 3.3         # storey height


def slab(n_bays: int, *, double_loaded: bool = True, bay: float = BAY,
         cor_depth: float = CORRIDOR_DEPTH, unit_depth: float = UNIT_DEPTH,
         floor: float = FLOOR, stairs: bool = True, entrance: bool = True) -> tuple:
    """Assemble a Narkomfin slab, circulation-first.

    A corridor spine of ``n_bays`` runs in x at level 0. Each bay anchors a
    maisonette: on the **front** an ``u_section`` rising two floors (z 0→2F); on
    the **back** (if ``double_loaded``) an ``l_section`` dropping/interlocking
    (z −F→F). Both dock exactly onto the corridor faces; adjacent bays touch.
    Staircases cap the ends (full height); an entrance docks to a stair at grade.

    Returns ``(graph, boxes)`` — topology + exact geometry, in step.
    """
    g = StateGraph()
    boxes: dict = {}
    span = n_bays * bay

    # --- armature: corridor spine + end staircases ---
    g.add_node(A.CORRIDOR, id="corridor", loading="double" if double_loaded else "single")
    boxes["corridor"] = (0.0, 0.0, 0.0, span, cor_depth, floor)

    if stairs:
        for sid, x0 in (("stair_W", -bay), ("stair_E", span)):
            g.add_node(A.STAIRCASE, id=sid)
            g.add_edge("corridor", sid, A.H)                 # stair caps the corridor end
            boxes[sid] = (x0, 0.0, -floor, bay, cor_depth, 3 * floor)  # spans the levels served
        if entrance:
            g.add_node(A.ENTRANCE, id="entrance")
            g.add_edge("entrance", "stair_W", A.H, bidirectional=False)  # one-way in at grade
            boxes["entrance"] = (-bay, cor_depth, -floor, bay, 2.5, floor)

    # --- anchor units onto the armature, bay by bay ---
    front_prev = back_prev = None
    for i in range(n_bays):
        x0 = i * bay
        # front maisonette: U rising two floors above the corridor
        fid = f"front_{i}"
        g.add_node(A.U_SECTION, id=fid)
        boxes[fid] = (x0, cor_depth, 0.0, bay, unit_depth, 2 * floor)   # docks at y=cor_depth
        g.add_edge("corridor", fid, A.H)
        if front_prev is not None:
            g.add_edge(front_prev, fid, A.H)                 # neighbouring bays touch
        front_prev = fid

        if double_loaded:
            # back maisonette: L dropping below the corridor (the section interlock)
            bid = f"back_{i}"
            g.add_node(A.L_SECTION, id=bid)
            boxes[bid] = (x0, -unit_depth, -floor, bay, unit_depth, 2 * floor)  # docks at y=0
            g.add_edge("corridor", bid, A.H)
            if back_prev is not None:
                g.add_edge(back_prev, bid, A.H)
            back_prev = bid

    return g, boxes
