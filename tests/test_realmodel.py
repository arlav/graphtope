"""B2 tests — importing the real Dom Narkomfin OBJ with actual sizes."""

import os

import networkx as nx
import pytest

import graphtope
from graphtope import alphabet as A, exchange

MODEL = os.path.join(os.path.dirname(graphtope.__file__), "models",
                     "3d_Dom_Narkomfin_building_only_2026.obj")
have_model = pytest.mark.skipif(not os.path.exists(MODEL), reason="real model OBJ not present")


# -- the Appendix-A name classifier (no file needed) ----------------------
def test_classify_space_maps_appendix_a_vocabulary():
    assert exchange.classify_space("Corridor_first_floor") == (A.CORRIDOR, None)
    assert exchange.classify_space("Auxiliary_corridor_second_floor.003") == (A.CORRIDOR, None)
    assert exchange.classify_space("Staircase_North") == (A.STAIRCASE, None)
    assert exchange.classify_space("mesonete_f_1_2") == (A.L_SECTION, None)  # F-type = L-section
    assert exchange.classify_space("3-4-5_apartment.014") == (A.GENERIC, "apartment")
    assert exchange.classify_space("Condenser_toilet_1") == (A.GENERIC, "toilet")
    assert exchange.classify_space("Lobby_ground_floor") == (A.GENERIC, "lobby")
    assert exchange.classify_space("auxiliary_ground_f_entrance_curved") == (A.ENTRANCE, None)


def test_classify_space_skips_structural_elements():
    assert exchange.classify_space("Condenser_Slab") is None
    assert exchange.classify_space("COLUMNS_mesh_.006") is None


# -- importing the real model --------------------------------------------
@have_model
def test_real_model_imports_to_a_valid_connected_graph():
    g, boxes = exchange.graph_from_model(MODEL)
    assert g.is_well_formed()
    assert g.order() >= 50 and g.size() >= 100
    nxg = nx.Graph(); nxg.add_nodes_from(g.nodes())
    nxg.add_edges_from((e["src"], e["tgt"]) for e in g.edges())
    assert nx.number_connected_components(nxg) == 1          # one connected building
    labels = {g.node_label(n) for n in g.nodes()}
    assert {A.CORRIDOR, A.STAIRCASE, A.L_SECTION, A.GENERIC, A.ENTRANCE} <= labels


@have_model
def test_real_model_nodes_carry_actual_dimensions():
    g, boxes = exchange.graph_from_model(MODEL)
    for n in g.nodes():
        a = g.node_attrs(n)
        assert a["width"] > 0 and a["depth"] > 0 and a["height"] > 0
        assert a["volume"] > 0 and a["level"] >= 0
    # the spine corridor is the long, highly-connected one (~73 m)
    nxg = nx.Graph(); nxg.add_nodes_from(g.nodes())
    nxg.add_edges_from((e["src"], e["tgt"]) for e in g.edges())
    corridors = [n for n in g.nodes() if g.node_label(n) == A.CORRIDOR]
    spine = max(corridors, key=lambda n: nxg.degree(n))
    assert g.node_attrs(spine)["width"] > 40                 # tens of metres long
    assert nxg.degree(spine) >= 8


@have_model
def test_real_model_has_multiple_storeys():
    g, _ = exchange.graph_from_model(MODEL)
    levels = {g.node_attrs(n)["level"] for n in g.nodes()}
    assert len(levels) >= 4                                  # a multi-storey building
