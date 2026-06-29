"""G0 tests — generative derivation: strategy, generate, catalogue (dedup)."""

from graphtope import StateGraph, serialize
from graphtope import generate
from graphtope.compare import typed_isomorphic


def test_generated_variant_is_well_formed_and_invertible():
    d = generate.generate(generate.RandomStrategy(seed=3, max_steps=10))
    assert d.sg.is_well_formed()
    assert len(d.steps) <= 10
    axiom = serialize.to_dict(StateGraph.axiom())
    d.invert()
    assert serialize.to_dict(d.sg) == axiom        # still fully reversible


def test_generation_is_deterministic_by_seed():
    g1 = generate.generate(generate.RandomStrategy(seed=7)).sg
    g2 = generate.generate(generate.RandomStrategy(seed=7)).sg
    assert serialize.to_dict(g1) == serialize.to_dict(g2)


def test_different_seeds_give_different_buildings():
    graphs = [generate.generate(generate.RandomStrategy(seed=s, max_steps=6)).sg
              for s in range(5)]
    distinct = sum(1 for i in range(len(graphs)) for j in range(i + 1, len(graphs))
                   if not typed_isomorphic(graphs[i], graphs[j]))
    assert distinct >= 6                             # most of the 10 pairs differ


def test_catalogue_is_deduped():
    cat = generate.catalogue(6, strategy_factory=lambda i: generate.RandomStrategy(
        seed=i, weights=generate.DEFAULT_WEIGHTS, max_steps=8))
    assert 1 < len(cat) <= 6
    for i in range(len(cat)):
        for j in range(i + 1, len(cat)):
            assert not typed_isomorphic(cat[i].sg, cat[j].sg)


def test_strategy_stops_when_no_production_applies():
    # an empty graph has no matches → generation stops immediately
    d = generate.generate(generate.RandomStrategy(seed=0), axiom=StateGraph())
    assert d.steps == [] and d.sg.order() == 0


def test_weights_bias_the_mix():
    # weighting P1 only → the variant grows by P1 (add internal volume) alone
    only_p1 = {"P1": 1.0}
    d = generate.generate(
        generate.RandomStrategy(seed=1, weights=only_p1, max_steps=5))
    assert [s.rule for s in d.steps] == ["P1"] * 5
