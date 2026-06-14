"""Tier-1 core composite operations (spec §5).

The six generic verbs — SPLIT/DIVIDE, MERGE/UNION, DIFFERENCE, REPLACE,
TRANSFORM/MIRROR, OTHER — as recipes over the Tier-0 atomics. SPLIT and MERGE
are the reversible pair at the heart of D-I.

Planned for milestone **M3**.
"""

from __future__ import annotations

# TODO(M3): SPLIT(n, o, π) / MERGE(n1, n2) with embedding map π, label policy ζ,
# weight policy ξ; then DIVIDE, UNION, DIFFERENCE, REPLACE, MIRROR, OTHER.
# Property-test MERGE ∘ SPLIT == id and SPLIT ∘ MERGE == id.
