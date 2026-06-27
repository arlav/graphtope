"""The graph→shape interface τ (spec §9) — the Stage-2 boundary.

τ : Σ → ShapeType maps each semantic label to a shape type (generic ↦ box,
corridor ↦ elongated box, staircase ↦ vertical box spanning levels, …). Stage 1
hands this single rule forward; Stage 2 realises nodes as Topologic Cells and
adjacency edges as shared faces. No geometry is built here.
"""

from __future__ import annotations

from . import alphabet as A

#: label → shape-type tag (no geometry yet; §9)
SHAPE_TYPE = {
    A.GENERIC: "parallelepiped",
    A.CORRIDOR: "elongated_parallelepiped",
    A.STAIRCASE: "vertical_parallelepiped",
    A.U_SECTION: "u_profile_solid",
    A.L_SECTION: "l_profile_solid",
    A.ENTRANCE: "ground_floor_opening",
}


def shape_type(label: str) -> str:
    """τ : Σ → ShapeType (tag only; Stage-2 stub)."""
    return SHAPE_TYPE[label]


#: adjacency orientation → the shared face Stage 2 will realise (§9):
#: V ⇒ shared horizontal face (slab), H ⇒ shared vertical face (wall)
SHARED_FACE = {A.V: "shared_horizontal_face_slab", A.H: "shared_vertical_face_wall"}


def realise_node_types(sg) -> dict:
    """τ over a whole graph: node id → shape-type tag (no geometry)."""
    return {n: shape_type(sg.node_label(n)) for n in sg.nodes()}


def realise_edge_faces(sg) -> list:
    """Each adjacency edge → the shared face it becomes at Stage 2 (no geometry)."""
    return [{"src": e["src"], "tgt": e["tgt"], "face": SHARED_FACE[e["orientation"]]}
            for e in sg.edges()]
