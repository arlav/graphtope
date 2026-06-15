"""JSON serialization for the state graph (spec §10.1).

Round-trips through our own clean schema (not topologic's ``ExportToJSON``) so
the injected ontology vocabulary never leaks into the file.
"""

from __future__ import annotations

import json

from .model import StateGraph


def to_dict(sg: StateGraph) -> dict:
    """State graph -> the §10.1 JSON-able dict.

    Emitted in a **canonical order** (nodes by id, edges by endpoints/type) so
    the form is deterministic — the carrier's vertex ordering is not stable.
    """
    nodes = sorted(
        (
            {"id": nid, "label": sg.node_label(nid), "attrs": sg.node_attrs(nid)}
            for nid in sg.nodes()
        ),
        key=lambda n: n["id"],
    )
    edges = sorted(
        (
            {
                "src": e["src"], "tgt": e["tgt"], "type": e["type"],
                "orientation": e["orientation"],
                "bidirectional": e["bidirectional"], "weight": e["weight"],
                "attrs": e["attrs"],
            }
            for e in sg.edges()
        ),
        key=lambda e: (e["src"], e["tgt"], e["type"], e["orientation"]),
    )
    return {"directed": True, "multigraph": True, "nodes": nodes, "edges": edges}


def from_dict(data: dict) -> StateGraph:
    """The §10.1 dict -> a reconstructed state graph."""
    sg = StateGraph()
    for n in data.get("nodes", []):
        sg.add_node(n.get("label"), id=n["id"], **(n.get("attrs") or {}))
    for e in data.get("edges", []):
        sg.add_edge(
            e["src"], e["tgt"], e["orientation"],
            bidirectional=e.get("bidirectional"),
            weight=e.get("weight", 1.0),
            type=e.get("type", "adjacency"),
            **(e.get("attrs") or {}),
        )
    return sg


def to_json(sg: StateGraph, path: str, *, indent: int = 2) -> None:
    with open(path, "w") as fh:
        json.dump(to_dict(sg), fh, indent=indent)


def from_json(path: str) -> StateGraph:
    with open(path) as fh:
        return from_dict(json.load(fh))
