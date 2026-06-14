"""Tier-0 atomic operations A1–A7, each with its inverse (spec §4).

    A1 add-node      A2 del-node      A3 add-edge     A4 del-edge
    A5 relabel       A6 reweight      A7 reverse-edge

Planned for milestone **M2**. Each operation states a precondition, an effect,
and an inverse; reversibility is a property of the whole basis (D-I, D-IV).
"""

from __future__ import annotations

# TODO(M2): implement A1–A7 over StateGraph with pre/postcondition asserts and
# explicit inverses; property-test inverse(op) ∘ op == id on random graphs.
