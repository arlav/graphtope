"""Architectural validity for generated graphs (G1).

The generative engine (G0) explores the *derivation* space freely, so it also
produces graphs that are not buildings — rooms with no circulation, several
entrances in one block (the entrance NAC is only local), an ``l_section`` with no
``u_section`` above it. These predicates define what a *building* is, per
connected "block", and are used to filter a catalogue to valid variants (and to
explain why a variant was rejected).

They are deliberately structural (Stage-1, graph-level). ``violations(sg)``
returns the list of reasons a graph fails; ``is_valid(sg)`` is the boolean.
See ``docs/Generative_Variation_Research_Plan.md`` (G1).
"""

from __future__ import annotations

from . import alphabet as A

HABITABLE = frozenset({A.GENERIC, A.U_SECTION, A.L_SECTION})
CIRCULATION = frozenset({A.CORRIDOR, A.STAIRCASE})


def _adjacency(sg) -> dict:
    adj = {n: set() for n in sg.nodes()}
    for e in sg.edges():
        adj[e["src"]].add(e["tgt"])
        adj[e["tgt"]].add(e["src"])
    return adj


def _components(sg, adj) -> list:
    seen, comps = set(), []
    for n in sg.nodes():
        if n in seen:
            continue
        stack, comp = [n], set()
        seen.add(n)
        while stack:
            c = stack.pop(); comp.add(c)
            for m in adj[c]:
                if m not in seen:
                    seen.add(m); stack.append(m)
        comps.append(comp)
    return comps


# === individual checks (each returns a list of reason strings) ===========
def check_circulation_reaches_all(sg, comps, adj) -> list:
    """Every multi-room block must contain circulation. (A block is one connected
    component, so once it has circulation every room reaches it — the content is
    therefore 'a block of >1 rooms has at least one corridor/staircase'.)"""
    out = []
    for comp in comps:
        hab = [n for n in comp if sg.node_label(n) in HABITABLE]
        circ = [n for n in comp if sg.node_label(n) in CIRCULATION]
        if len(hab) > 1 and not circ:
            out.append(f"block of {len(hab)} rooms has no circulation")
    return out


def check_at_most_one_entrance_per_block(sg, comps, adj) -> list:
    out = []
    for comp in comps:
        ents = [n for n in comp if sg.node_label(n) == A.ENTRANCE]
        if len(ents) > 1:
            out.append(f"block has {len(ents)} entrances (max 1): {sorted(ents)}")
    return out


def check_entrance_adjacent_to_circulation(sg, comps, adj) -> list:
    out = []
    for n in sg.nodes():
        if sg.node_label(n) != A.ENTRANCE:
            continue
        if not any(sg.node_label(m) in CIRCULATION for m in adj[n]):
            out.append(f"entrance {n!r} is not adjacent to circulation")
    return out


def check_lsection_paired_with_usection(sg, comps, adj) -> list:
    out = []
    for e_tgt in [n for n in sg.nodes() if sg.node_label(n) == A.L_SECTION]:
        above_u = any(e["tgt"] == e_tgt and e["orientation"] == A.V
                      and sg.node_label(e["src"]) == A.U_SECTION for e in sg.edges())
        if not above_u:
            out.append(f"l_section {e_tgt!r} has no u_section above it (V)")
    return out


def check_no_floating_habitable(sg, comps, adj) -> list:
    if sg.order() <= 1:
        return []
    return [f"floating room {n!r} (degree 0)"
            for n in sg.nodes() if sg.node_label(n) in HABITABLE and not adj[n]]


def check_every_block_has_entrance(sg, comps, adj) -> list:
    """Completeness (strict): a circulated block must have an entrance at grade."""
    out = []
    for comp in comps:
        has_circ = any(sg.node_label(n) in CIRCULATION for n in comp)
        has_ent = any(sg.node_label(n) == A.ENTRANCE for n in comp)
        if has_circ and not has_ent:
            out.append(f"block of {len(comp)} spaces has circulation but no entrance")
    return out


#: hard rules — a graph that breaks these is not a building (no contradictions)
DEFAULT_CHECKS = (
    check_circulation_reaches_all,
    check_at_most_one_entrance_per_block,
    check_entrance_adjacent_to_circulation,
    check_lsection_paired_with_usection,
    check_no_floating_habitable,
)
#: + completeness: every circulated block is entered
STRICT_CHECKS = DEFAULT_CHECKS + (check_every_block_has_entrance,)


def violations(sg, checks=DEFAULT_CHECKS) -> list:
    """All reasons ``sg`` is not a valid building (empty list ⇒ valid)."""
    adj = _adjacency(sg)
    comps = _components(sg, adj)
    out = []
    for check in checks:
        out.extend(check(sg, comps, adj))
    return out


def is_valid(sg, checks=DEFAULT_CHECKS) -> bool:
    return not violations(sg, checks)
