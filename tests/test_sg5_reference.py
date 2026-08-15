"""SG5 tests — the reproduction result: the sub-grammars derive the reference.

The level-2 analogue of §8.1's fig-5 reproduction. The reference is
*reconstructed* (no room-labelled source exists — plan risk R1): module
dimensions from the imported model, room arrangement from the published
section. Its boxes are authored so the face-adjacency is exactly the default
G_U / G_L adjacency — so "the grammar derives the reference" is a typed-
isomorphism claim over graphs read from geometry, not a tautology over the
grammar's own output.
"""

import pytest

from graphtope import alphabet as A, reference, serialize
from graphtope.exchange import classify_space


def test_the_reference_imports_with_room_labels():
    ref_k = reference.reference_graph("K")
    subs = {ref_k.node_attrs(n)["subtype"] for n in ref_k.nodes()}
    assert subs == {"living", "sleeping", "kitchen", "bath", "void", "internal"}
    assert ref_k.node_label(next(n for n in ref_k.nodes()
                                 if ref_k.node_attrs(n)["subtype"] == "sleeping")) \
        == A.GENERIC                                   # rooms are generic subtypes
    stair = next(n for n in ref_k.nodes()
                 if ref_k.node_label(n) == A.STAIRCASE)
    assert ref_k.node_attrs(stair)["subtype"] == "internal"
    # the section, read from geometry: the gallery and the void both sit
    # V-above the living; the void opens onto the sleeping gallery
    liv = next(n for n in ref_k.nodes() if ref_k.node_attrs(n)["subtype"] == "living")
    above = {e["src"] for e in ref_k.edges()
             if e["orientation"] == A.V and e["tgt"] == liv}
    assert {ref_k.node_attrs(n)["subtype"] for n in above} == {"sleeping", "void"}


@pytest.mark.parametrize("unit,rooms", [
    ("K", {"living", "sleeping", "kitchen", "bath", "void", "internal"}),
    ("F", {"entry", "living", "kitchen", "bath", "internal"}),
])
def test_subgrammar_reproduces_the_reference(unit, rooms):
    """G_U / G_L at their defaults derive the reference interior from the
    non-terminal — verified by typed isomorphism (the strongest claim the
    sub-grammar phase can make, plan slot G)."""
    r = reference.reproduce(unit)
    assert r["ok"]
    subs = {r["derived"].node_attrs(n)["subtype"] for n in r["derived"].nodes()}
    assert subs == rooms


def test_reverse_subderivation_returns_the_nonterminal():
    host0 = reference._host("K")
    before = serialize.to_dict(host0)
    r = reference.reproduce("K")
    r["inverse"].apply(r["host"])
    assert serialize.to_dict(r["host"]) == before           # exact (§4)
    assert r["host"].has_node("u")                          # the non-terminal is back


def test_reference_provenance_is_stated_in_the_model():
    with open(reference.REFERENCE_OBJ) as fh:
        header = fh.read(600)
    assert "RECONSTRUCTED" in header                        # honest, per R1


def test_classify_space_knows_the_sigma_int_vocabulary():
    assert classify_space("K_unit_living") == (A.GENERIC, "living")
    assert classify_space("F_unit_entry") == (A.GENERIC, "entry")
    assert classify_space("K_unit_stair_internal") == (A.STAIRCASE, "internal")
    assert classify_space("K_unit_void") == (A.GENERIC, "void")
    # block-level names keep their Appendix A readings
    assert classify_space("3-4-5_apartment.016") == (A.GENERIC, "apartment")
    assert classify_space("mesonete_f_2") == (A.L_SECTION, None)
