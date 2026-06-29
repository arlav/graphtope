"""Parameterised block productions — macro variation (G2).

The named productions P1–P8 are fixed (P6 adds *exactly* two u_sections, P3 one
corridor). To widen the design space we build **parameterised** productions as
factories that return ordinary DPO ``Production`` objects — so they remain
matchable, NAC-able, reversible, validity-checkable, and droppable straight into
the generative pool (``generate``). ``Mirror`` (P9, §5.3) is exposed as a
grammar-level wing/floor operator.

Graph-level note: "single- vs double-loaded corridor" is **not** a topological
distinction (the graph has no left/right) — it is an apartment *count* plus a
``loading`` attribute on the corridor that the Stage-2 layout reads to place
rooms on one or both sides. See ``docs/Generative_Variation_Research_Plan.md`` (G2).
"""

from __future__ import annotations

from . import alphabet as A
from .composite import Mirror
from .rules import Pattern, PEdge, PNode, Production


def add_units(unit_label: str, k: int, *, host_label: str = A.CORRIDOR,
              orientation: str = A.H, name: str | None = None) -> Production:
    """Attach ``k`` ``unit_label`` nodes to a matched host (generalises P6)."""
    host = PNode("h", label=host_label)
    units = [PNode(f"u{i}", label=unit_label) for i in range(k)]
    edges = [PEdge("h", f"u{i}", orientation=orientation,
                   bidirectional=(orientation == A.H)) for i in range(k)]
    return Production(name or f"add-{k}-{unit_label}",
                      lhs=Pattern([host]), interface={"h"},
                      rhs=Pattern([host, *units], edges),
                      instantiates=f"+N({unit_label})×{k} + UNION×{k}")


def corridor_block(per_side: int, *, loading: str = "single",
                   host_label: str = A.GENERIC, name: str | None = None) -> Production:
    """Develop a generic block into a corridor serving apartments: ``per_side``
    for a single-loaded corridor, ``2·per_side`` for double-loaded. The corridor
    carries ``loading`` / ``per_side`` attributes for the Stage-2 layout."""
    n = per_side * (2 if loading == "double" else 1)
    g = PNode("g", label=host_label)
    c = PNode("c", label=A.CORRIDOR, attrs={"loading": loading, "per_side": per_side})
    apts = [PNode(f"a{i}", label=A.GENERIC, subtype="apartment") for i in range(n)]
    edges = [PEdge("g", "c", orientation=A.H)] + \
            [PEdge("c", f"a{i}", orientation=A.H) for i in range(n)]
    return Production(name or f"corridor-{loading}-{per_side}",
                      lhs=Pattern([g]), interface={"g"},
                      rhs=Pattern([g, c, *apts], edges),
                      instantiates=f"+N(corridor)+N(apartment)×{n}")


def add_staircase_tower(levels: int, *, host_label=(A.CORRIDOR,),
                        name: str | None = None) -> Production:
    """Attach a stack of ``levels`` staircase nodes (V) to a host — a vertical
    core spanning multiple floors."""
    host = PNode("h", labels=tuple(host_label))
    tower = [PNode(f"s{i}", label=A.STAIRCASE) for i in range(levels)]
    edges = [PEdge("h", "s0", orientation=A.V, bidirectional=False)]
    edges += [PEdge(f"s{i-1}", f"s{i}", orientation=A.V, bidirectional=False)
              for i in range(1, levels)]
    return Production(name or f"stair-tower-{levels}",
                      lhs=Pattern([host]), interface={"h"},
                      rhs=Pattern([host, *tower], edges),
                      instantiates=f"+N(staircase)×{levels} (V tower)")


def mirror(sg, nodes, seam, *, orientation: str = A.H, weight: float = A.DEFAULT_WEIGHT):
    """Reflect a sub-assembly — a side **wing** (``orientation=H``) or a stacked
    **floor plate** (``orientation=V``). Returns ``(inverse, copies)`` and is
    reversible (P9 / §5.3)."""
    op = Mirror(list(nodes), list(seam), seam_orientation=orientation, seam_weight=weight)
    inverse = op.apply(sg)
    return inverse, op.copies


def variation_pool(*, unit_counts=(2, 3, 4), apartment_counts=(3, 4, 5),
                   loadings=("single", "double")) -> dict:
    """The base grammar P1–P8 plus a spread of parameterised variants — ready to
    hand to ``generate.RandomStrategy(productions=...)``."""
    from .grammar_dnf import PRODUCTIONS
    pool = dict(PRODUCTIONS)
    for k in unit_counts:
        p = add_units(A.U_SECTION, k); pool[p.name] = p
    for n in apartment_counts:
        for loading in loadings:
            p = corridor_block(n, loading=loading); pool[p.name] = p
    return pool
