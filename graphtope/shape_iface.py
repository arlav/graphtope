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
