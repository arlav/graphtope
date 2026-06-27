"""The Dom Narkomfin named productions P1–P8 (spec §7) and the §8 derivation.

Each production is a DPO span faithful to §7's L/K/R, NACs, and grounding
(Appendix A). ``derive(d)`` runs the §8 sequence from the axiom A₀ to the typed
DNF space-adjacency graph; ``hand_built_dnf()`` writes that target graph
independently, so the M5 test can check the derivation reproduces it (up to
typed isomorphism) and that the reverse derivation returns the axiom.

P9 (MIRROR) is defined in ``composite.Mirror`` but not exercised here (§7.4).
"""

from __future__ import annotations

from .alphabet import (
    CORRIDOR, ENTRANCE, GENERIC, H, L_SECTION, STAIRCASE, U_SECTION, V,
)
from .engine import Derivation
from .model import StateGraph
from .rules import Pattern, PEdge, PNode, Production


# === named productions (§7) ==============================================
# P1 · ADD-INTERNAL-VOLUME — subdivide a block by an internal generic space.
P1 = Production(
    "P1",
    lhs=Pattern([PNode("g0", label=GENERIC)]),
    interface={"g0"},
    rhs=Pattern([PNode("g0", label=GENERIC), PNode("g1", label=GENERIC)],
                [PEdge("g0", "g1", orientation=H)]),          # bidirectional H
    instantiates="SPLIT (Divide)",
)

# P2 · ADD-EXTERNAL-VOLUME — attach a generic space externally (one-way).
P2 = Production(
    "P2",
    lhs=Pattern([PNode("g0", label=GENERIC)]),
    interface={"g0"},
    rhs=Pattern([PNode("g0", label=GENERIC), PNode("g1", label=GENERIC)],
                [PEdge("g0", "g1", orientation=H, bidirectional=False)]),
    instantiates="UNION (add-adjacency)",
)

# P3 · ADD-CORRIDOR — replace a direct adjacency with a mediating corridor.
P3 = Production(
    "P3",
    lhs=Pattern([PNode("gi", label=GENERIC), PNode("gj", label=GENERIC)],
                [PEdge("gi", "gj", orientation=H)]),
    interface={"gi", "gj"},
    rhs=Pattern([PNode("gi", label=GENERIC), PNode("gj", label=GENERIC),
                 PNode("c", label=CORRIDOR)],
                [PEdge("gi", "c", orientation=H), PEdge("c", "gj", orientation=H)]),
    nacs=[Pattern([PNode("gi"), PNode("gj"), PNode("cc", label=CORRIDOR)],
                  [PEdge("cc", "gi", orientation=H), PEdge("cc", "gj", orientation=H)])],
    instantiates="+N(corridor) + UNION×2",
)

# P4 · ADD-STAIRCASE — vertical circulation attached to a space (V, one-way).
P4 = Production(
    "P4",
    lhs=Pattern([PNode("x", labels=(GENERIC, CORRIDOR))]),
    interface={"x"},
    rhs=Pattern([PNode("x"), PNode("s", label=STAIRCASE)],
                [PEdge("x", "s", orientation=V, bidirectional=False)]),
    nacs=[Pattern([PNode("x"), PNode("ss", label=STAIRCASE)],
                  [PEdge("x", "ss", orientation=V)])],
    instantiates="+N(staircase) + UNION(V)",
)

# P5 · ADD-GROUND-FLOOR-ENTRANCE — one-way entrance into circulation.
P5 = Production(
    "P5",
    lhs=Pattern([PNode("x", labels=(CORRIDOR, STAIRCASE))]),
    interface={"x"},
    rhs=Pattern([PNode("x"), PNode("e", label=ENTRANCE)],
                [PEdge("e", "x", orientation=H, bidirectional=False)]),
    nacs=[Pattern([PNode("x"), PNode("ee", label=ENTRANCE)],
                  [PEdge("ee", "x", orientation=H)])],
    instantiates="+N(entrance) + UNION(one-way)",
)

# P6 · ADD-TWO-U-SECTION-SPACES — two split-level units served by a corridor.
P6 = Production(
    "P6",
    lhs=Pattern([PNode("c", label=CORRIDOR)]),
    interface={"c"},
    rhs=Pattern([PNode("c"), PNode("u1", label=U_SECTION), PNode("u2", label=U_SECTION)],
                [PEdge("c", "u1", orientation=H), PEdge("c", "u2", orientation=H)]),
    instantiates="+N(u_section)×2 + UNION×2",
)

# P7 · ADD-L-SECTION-SPACE — interlocking unit below the two U-units (V).
P7 = Production(
    "P7",
    lhs=Pattern([PNode("u1", label=U_SECTION), PNode("u2", label=U_SECTION)]),
    interface={"u1", "u2"},
    rhs=Pattern([PNode("u1"), PNode("u2"), PNode("l", label=L_SECTION)],
                [PEdge("u1", "l", orientation=V, bidirectional=False),
                 PEdge("u2", "l", orientation=V, bidirectional=False)]),
    nacs=[Pattern([PNode("u1"), PNode("u2"), PNode("ll", label=L_SECTION)],
                  [PEdge("u1", "ll", orientation=V), PEdge("u2", "ll", orientation=V)])],
    instantiates="+N(l_section) + UNION(V)",
)

# P8 · ADD-THREE-SMALL-ROOMS — a connected triad of toilet rooms.
P8 = Production(
    "P8",
    lhs=Pattern([PNode("x")]),
    interface={"x"},
    rhs=Pattern([PNode("x"),
                 PNode("ta", label=GENERIC, subtype="toilet"),
                 PNode("tb", label=GENERIC, subtype="toilet"),
                 PNode("tc", label=GENERIC, subtype="toilet")],
                [PEdge("x", "ta", orientation=H), PEdge("ta", "tb", orientation=H),
                 PEdge("tb", "tc", orientation=H), PEdge("ta", "tc", orientation=H)]),
    instantiates="DIVIDE / +N×3",
)

PRODUCTIONS = {p.name: p for p in (P1, P2, P3, P4, P5, P6, P7, P8)}


# === the §8 derivation A₀ →* G_DNF =======================================
def derive_residential(d: Derivation, root: str = "b1") -> Derivation:
    """Develop the residential block from its root generic node (§8)."""
    r2 = d.apply(P1, {"g0": root})["g1"]          # spine: root — r2
    r3 = d.apply(P1, {"g0": r2})["g1"]            #        root — r2 — r3
    c1 = d.apply(P3, {"gi": root, "gj": r2})["c"]  # root — c1 — r2 (corridor mediates)
    c2 = d.apply(P3, {"gi": r2, "gj": r3})["c"]   # r2 — c2 — r3
    d.apply(P4, {"x": c1})                        # North staircase off c1
    d.apply(P4, {"x": c2})                        # South staircase off c2
    d.apply(P5, {"x": c1})                        # residential entrance into c1
    u = d.apply(P6, {"c": c2})                    # two u_section units off c2
    d.apply(P7, {"u1": u["u1"], "u2": u["u2"]})   # one l_section below them (V)
    return d


def derive_condenser(d: Derivation, root: str = "b2") -> Derivation:
    """Develop the condenser block from its root generic node (§8)."""
    d.apply(P2, {"g0": root})                     # external generic volume
    sc = d.apply(P4, {"x": root})["s"]            # condenser staircase
    d.apply(P5, {"x": sc})                        # condenser entrance
    d.apply(P8, {"x": root})                      # three toilet rooms
    return d


def derive(d: Derivation) -> Derivation:
    """Apply P1–P8 from axiom A₀ to build the full DNF graph (both blocks)."""
    derive_residential(d, "b1")
    derive_condenser(d, "b2")
    return d


def derive_dnf() -> tuple[StateGraph, Derivation]:
    """Fresh axiom → full DNF graph; returns (graph, derivation)."""
    d = Derivation(StateGraph.axiom())
    derive(d)
    return d.sg, d


# === the independently hand-built target (figure 5) ======================
def hand_built_dnf() -> StateGraph:
    """The typed DNF space-adjacency graph, written out directly (Appendix A)."""
    g = StateGraph()
    # residential block
    g.add_node(GENERIC, id="R1"); g.add_node(GENERIC, id="R2"); g.add_node(GENERIC, id="R3")
    g.add_node(CORRIDOR, id="C1"); g.add_node(CORRIDOR, id="C2")
    g.add_node(STAIRCASE, id="SN"); g.add_node(STAIRCASE, id="SS")
    g.add_node(ENTRANCE, id="ER")
    g.add_node(U_SECTION, id="U1"); g.add_node(U_SECTION, id="U2")
    g.add_node(L_SECTION, id="L1")
    g.add_edge("R1", "C1", H); g.add_edge("C1", "R2", H)       # spine via corridors
    g.add_edge("R2", "C2", H); g.add_edge("C2", "R3", H)
    g.add_edge("C1", "SN", V); g.add_edge("C2", "SS", V)        # staircases (one-way)
    g.add_edge("ER", "C1", H, bidirectional=False)             # entrance (one-way)
    g.add_edge("C2", "U1", H); g.add_edge("C2", "U2", H)       # two U units
    g.add_edge("U1", "L1", V); g.add_edge("U2", "L1", V)       # L unit below (one-way)
    # condenser block
    g.add_node(GENERIC, id="M"); g.add_node(GENERIC, id="X")
    g.add_node(STAIRCASE, id="SC"); g.add_node(ENTRANCE, id="EC")
    g.add_node(GENERIC, id="T1", subtype="toilet")
    g.add_node(GENERIC, id="T2", subtype="toilet")
    g.add_node(GENERIC, id="T3", subtype="toilet")
    g.add_edge("M", "X", H, bidirectional=False)               # external volume
    g.add_edge("M", "SC", V)                                   # condenser staircase
    g.add_edge("EC", "SC", H, bidirectional=False)             # condenser entrance
    g.add_edge("M", "T1", H); g.add_edge("T1", "T2", H)        # toilet triad
    g.add_edge("T2", "T3", H); g.add_edge("T1", "T3", H)
    return g
