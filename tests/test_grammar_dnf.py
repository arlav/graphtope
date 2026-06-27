"""M5 tests — the DNF grammar P1–P8 and the §8 derivation (spec §7–§8)."""

import networkx as nx

from graphtope import StateGraph, alphabet as A
from graphtope import serialize
from graphtope.engine import Derivation
from graphtope import grammar_dnf as dnf


def _typed_nx(sg):
    """Typed comparison graph: bidirectional H edges are undirected (both
    directions present), one-way edges (V, entrance) stay directed. Nodes carry
    only (label, subtype) — the figure-5 graph is typed, not attributed."""
    G = nx.DiGraph()
    for n in sg.nodes():
        G.add_node(n, label=sg.node_label(n), subtype=sg.node_attrs(n).get("subtype"))
    for e in sg.edges():
        a = {"orientation": e["orientation"], "type": e["type"]}
        G.add_edge(e["src"], e["tgt"], **a)
        if e["bidirectional"]:
            G.add_edge(e["tgt"], e["src"], **a)
    return G


def typed_iso(g1, g2):
    return nx.is_isomorphic(_typed_nx(g1), _typed_nx(g2),
                            node_match=lambda a, b: a == b,
                            edge_match=lambda a, b: a == b)


# -- recovery: A₀ →* G_DNF reproduces the hand-built graph ----------------
def test_derivation_reproduces_hand_built_dnf():
    derived, _ = dnf.derive_dnf()
    assert derived.is_well_formed()
    assert typed_iso(derived, dnf.hand_built_dnf())


def test_dnf_has_expected_typed_composition():
    g, _ = dnf.derive_dnf()
    labels = sorted(g.node_label(n) for n in g.nodes())
    assert labels.count(A.GENERIC) == 8     # 3 apartments + main + external + 3 toilets
    assert labels.count(A.CORRIDOR) == 2
    assert labels.count(A.STAIRCASE) == 3   # North, South, condenser
    assert labels.count(A.ENTRANCE) == 2    # one per block
    assert labels.count(A.U_SECTION) == 2
    assert labels.count(A.L_SECTION) == 1
    toilets = [n for n in g.nodes() if g.node_attrs(n).get("subtype") == "toilet"]
    assert len(toilets) == 3
    assert g.order() == 18


def test_dnf_is_not_fully_refined():
    g, _ = dnf.derive_dnf()
    assert not g.is_fully_refined()         # u_section / l_section are non-terminals


# -- the grammar runs both ways: reverse derivation returns A₀ ------------
def test_reverse_derivation_returns_axiom():
    d = Derivation(StateGraph.axiom())
    dnf.derive(d)
    axiom_canon = serialize.to_dict(StateGraph.axiom())
    d.invert()
    assert serialize.to_dict(d.sg) == axiom_canon   # back to b1, b2 (isolated generics)
    assert d.sg.is_well_formed()


# -- determinism: replaying the script yields the same graph --------------
def test_derivation_is_deterministic():
    g1, _ = dnf.derive_dnf()
    g2, _ = dnf.derive_dnf()
    assert typed_iso(g1, g2)
    assert serialize.to_dict(g1) == serialize.to_dict(g2)


# -- P3 genuinely deletes the direct adjacency (edge-deleting DPO) --------
def test_p3_replaces_direct_adjacency_with_corridor():
    g = StateGraph()
    g.add_node(A.GENERIC, id="a"); g.add_node(A.GENERIC, id="b")
    g.add_edge("a", "b", A.H)
    c = dnf.P3.apply_at(g, {"gi": "a", "gj": "b"}).produced["c"]
    assert not g.has_edge("a", "b") and not g.has_edge("b", "a")   # direct edge gone
    assert g.node_label(c) == A.CORRIDOR
    assert g.has_edge("a", c) or g.has_edge(c, "a")
    assert g.has_edge(c, "b") or g.has_edge("b", c)


# -- NAC: a second corridor between the same pair is blocked --------------
def test_p3_nac_blocks_second_corridor():
    g = StateGraph()
    g.add_node(A.GENERIC, id="a"); g.add_node(A.GENERIC, id="b")
    g.add_edge("a", "b", A.H)
    dnf.P3.apply_at(g, {"gi": "a", "gj": "b"})
    # now a and b are mediated by a corridor; re-adding direct adjacency...
    g.add_edge("a", "b", A.H)
    assert dnf.P3.matches(g) == []          # NAC: corridor already adjacent to both


# -- the trace records every step -----------------------------------------
def test_trace_records_all_steps():
    d = Derivation(StateGraph.axiom())
    dnf.derive(d)
    tr = d.trace()
    assert [s["rule"] for s in tr] == [
        "P1", "P1", "P3", "P3", "P4", "P4", "P5", "P6", "P7",  # residential
        "P2", "P4", "P5", "P8",                                 # condenser
    ]
    assert all("match" in s and "produced" in s for s in tr)
