"""Alphabets Σ (node labels) and Θ (edge types), defaults, and validators.

Implements spec §3. Σ is *open* — finer distinctions live in ``αN["subtype"]``
rather than expanding Σ (§3.1). Θ has a single type, ``adjacency`` (§3.2, D-I).
"""

from __future__ import annotations

# --- Σ : node-label alphabet (§3.1) ---------------------------------------
GENERIC = "generic"
CORRIDOR = "corridor"
STAIRCASE = "staircase"
U_SECTION = "u_section"
L_SECTION = "l_section"
ENTRANCE = "entrance"

NODE_LABELS = frozenset(
    {GENERIC, CORRIDOR, STAIRCASE, U_SECTION, L_SECTION, ENTRANCE}
)
#: terminal labels — final at the space-adjacency level (§3.1, §7.6.1)
TERMINALS = frozenset({GENERIC, CORRIDOR, STAIRCASE, ENTRANCE})
#: non-terminal labels — placeholders refined by a sub-grammar (§7.6.2)
NON_TERMINALS = frozenset({U_SECTION, L_SECTION})
DEFAULT_NODE_LABEL = GENERIC

# --- Θ : edge-type alphabet (§3.2) ----------------------------------------
ADJACENCY = "adjacency"
EDGE_TYPES = frozenset({ADJACENCY})
DEFAULT_EDGE_TYPE = ADJACENCY

# --- adjacency orientation (§3.2) -----------------------------------------
H = "H"  # horizontal: shared vertical boundary; default bidirectional
V = "V"  # vertical: a → b means "a directly above b"; ordered, one-way
ORIENTATIONS = frozenset({H, V})

#: default edge weight ω (§3.2)
DEFAULT_WEIGHT = 1.0


def is_node_label(x) -> bool:
    return x in NODE_LABELS


def is_edge_type(x) -> bool:
    return x in EDGE_TYPES


def is_orientation(x) -> bool:
    return x in ORIENTATIONS


def is_terminal(label) -> bool:
    return label in TERMINALS


def is_non_terminal(label) -> bool:
    return label in NON_TERMINALS


def default_bidirectional(orientation: str) -> bool:
    """Spec §3.2 default: H is mutually adjacent, V is one-way (above→below)."""
    return orientation == H
