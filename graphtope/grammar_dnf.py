"""The Dom Narkomfin named productions P1–P9 (spec §7).

    P1 add-internal-volume   P2 add-external-volume   P3 add-corridor
    P4 add-staircase         P5 add-ground-entrance   P6 add-two-u-sections
    P7 add-l-section         P8 add-three-small-rooms  P9 mirror (future)

Planned for milestone **M5**: applying P1–P8 to axiom A₀ reproduces the figure-5
DNF space-adjacency graph (verified by ``Graph.IsIsomorphic`` + reverse run).
"""

from __future__ import annotations

# TODO(M5): P1–P8 as Production instances; the §8 derivation script A₀ →* G_DNF.
