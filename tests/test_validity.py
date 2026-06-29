"""G1 tests — architectural validity of generated graphs."""

from graphtope import StateGraph, alphabet as A
from graphtope import grammar_dnf as dnf, generate, validity


# -- the reference building is valid --------------------------------------
def test_dnf_is_valid():
    G, _ = dnf.derive_dnf()
    assert validity.is_valid(G)
    assert validity.violations(G) == []


# -- each hard rule rejects the right thing -------------------------------
def test_two_entrances_per_block_rejected():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c")
    g.add_node(A.ENTRANCE, id="e1"); g.add_node(A.ENTRANCE, id="e2")
    g.add_edge("e1", "c", A.H, bidirectional=False)
    g.add_edge("e2", "c", A.H, bidirectional=False)
    assert any("entrances" in v for v in validity.violations(g))


def test_rooms_without_circulation_rejected():
    g = StateGraph()
    g.add_node(A.GENERIC, id="a"); g.add_node(A.GENERIC, id="b"); g.add_node(A.GENERIC, id="c")
    g.add_edge("a", "b", A.H); g.add_edge("b", "c", A.H)      # 3 rooms, no corridor/stair
    assert any("no circulation" in v for v in validity.violations(g))


def test_separate_unserved_room_cluster_rejected():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c"); g.add_node(A.GENERIC, id="r")
    g.add_node(A.GENERIC, id="x"); g.add_node(A.GENERIC, id="y")
    g.add_edge("c", "r", A.H)                                 # served block
    g.add_edge("x", "y", A.H)                                 # a separate block with no circulation
    assert any("no circulation" in v for v in validity.violations(g))


def test_floating_room_rejected():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c"); g.add_node(A.GENERIC, id="r"); g.add_edge("c", "r", A.H)
    g.add_node(A.GENERIC, id="floating")
    assert any("floating" in v for v in validity.violations(g))


def test_lsection_without_usection_rejected():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c"); g.add_node(A.L_SECTION, id="l")
    g.add_edge("c", "l", A.H)                                 # L present, no U above it
    assert any("no u_section above" in v for v in validity.violations(g))


def test_entrance_not_on_circulation_rejected():
    g = StateGraph()
    g.add_node(A.GENERIC, id="r"); g.add_node(A.ENTRANCE, id="e")
    g.add_edge("e", "r", A.H, bidirectional=False)            # entrance into a room, not circulation
    assert any("not adjacent to circulation" in v for v in validity.violations(g))


# -- strict completeness: a circulated block needs an entrance ------------
def test_strict_requires_entrance():
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="c"); g.add_node(A.GENERIC, id="r"); g.add_edge("c", "r", A.H)
    assert validity.is_valid(g)                               # passes the hard rules
    assert not validity.is_valid(g, checks=validity.STRICT_CHECKS)   # but not complete


# -- the keep filter yields only valid buildings --------------------------
def test_catalogue_keep_filters_to_valid():
    cat = generate.catalogue(
        3, axiom_factory=generate.single_block_axiom,
        strategy_factory=lambda i: generate.RandomStrategy(
            seed=i, weights=generate.DEFAULT_WEIGHTS, max_steps=8),
        keep=validity.is_valid, max_attempts=25)
    assert len(cat) >= 1
    assert all(validity.is_valid(d.sg) for d in cat)
