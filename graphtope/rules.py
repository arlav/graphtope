"""DPO productions and the typed-attributed directed matcher (spec §6).

A production is a span ``L ⊇ K ⊆ R`` applied at a match ``m: L → G`` (§6.1).
Matching is a typed, attributed, directed subgraph monomorphism preserving node
labels/subtypes, edge type + orientation, and edge direction (§6.2), guarded by
negative application conditions (§6.3).

Planned for milestone **M4**. Note (per the carrier briefing, gap C3):
``Graph.SubGraphMatches`` matches vertices but not edge attributes/direction, so
the matcher is implemented here (optionally via the ``StateGraph.to_networkx``
``MultiDiGraphMatcher`` escape hatch).
"""

from __future__ import annotations

# TODO(M4): Production(L, K, R, nacs); typed-attributed directed monomorphism;
# NAC checking. Tests: matches respect labels/orientation/direction; NAC blocks.
