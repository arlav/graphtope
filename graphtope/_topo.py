"""Thin wrappers over the TopologicPy primitives the carrier leans on.

Centralises the 0.9.43 gotchas documented in
``docs/Topologic_Carrier_Contribution_Briefing.md`` so the rest of the package
never has to remember them:

* address vertices by stable ``id`` (``VertexByKeyValue``), never by cached
  object reference (object identity is not preserved across operations);
* pass ``transferEdgeDictionaries=True`` to ``AddEdge`` or edge dicts are lost;
* bools are stored as ints in dictionaries — coerce back on read;
* topologic injects ontology keys — strip them on read.
"""

from __future__ import annotations

from topologicpy.Graph import Graph
from topologicpy.Vertex import Vertex
from topologicpy.Edge import Edge
from topologicpy.Dictionary import Dictionary
from topologicpy.Topology import Topology

#: keys topologic injects that are not part of our data model
ONTOLOGY_KEYS = frozenset(
    {"category", "ontology_class", "ontology_uri", "src", "dst", "index"}
)


def to_dictionary(d: dict):
    """Python dict -> topologic Dictionary."""
    return Dictionary.ByKeysValues(list(d.keys()), list(d.values()))


def py_dict(topo) -> dict:
    """topologic Topology -> its dictionary as a plain dict (or {})."""
    dd = Topology.Dictionary(topo)
    if dd is None:
        return {}
    return Dictionary.PythonDictionary(dd) or {}


def clean(d: dict) -> dict:
    """Drop topologic-injected ontology keys."""
    return {k: v for k, v in d.items() if k not in ONTOLOGY_KEYS}


def set_dict(topo, d: dict):
    """Attach a python dict to a vertex/edge, returning the updated topology."""
    return Topology.SetDictionary(topo, to_dictionary(d))


def id_of(vertex):
    return py_dict(vertex).get("id")


def empty_graph():
    return Graph.ByVerticesEdges([], [], silent=True)


def vertex_at(graph, vid):
    """Live vertex carrying ``id == vid`` (or None)."""
    return Graph.VertexByKeyValue(graph, "id", vid)
