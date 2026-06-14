"""Terminals/non-terminals, sub-grammar refinement (spec §7.6.1–§7.6.2).

``REFINE(n, G_u)`` replaces a non-terminal node with the start graph of its
section sub-grammar; ``ABSTRACT(S → n)`` is its inverse. The non-terminal's
incident edges are the interface ``K`` that refinement must preserve.

Planned for milestone **M7** (deferred). The ``is_fully_refined`` predicate
already lives on ``StateGraph``.
"""

from __future__ import annotations

# TODO(M7): REFINE / ABSTRACT over non-terminals; minimal U-section sub-grammar.
