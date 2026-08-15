"""SG5 — grounding against the built unit (the reproduction result).

The level-2 analogue of §8.1's fig-5 reproduction: the sub-grammars ``G_U``
and ``G_L`` **derive the reference unit interiors** — the room-labelled model
``models/KF_unit_interiors_reference.obj`` — verified by typed isomorphism,
with the reverse sub-derivation returning the non-terminal.

**Provenance (plan risk R1, stated honestly):** no room-labelled survey of the
K/F interiors exists in the sources; the reference is *reconstructed* —
dimensions from the imported model and the module (bay 3.66 m, unit depth
8.42 m, the K section 8.0 m = 5.0 living + 3.0 gallery, the 1.7 m gallery
strip, a 1.0 m stair), the room arrangement from the published Dom Narkomfin
section (Ginzburg's type 2F units) as documented in the repo. The OBJ header
carries the same statement. Weaker than a measured reference, and still a
reproduction result — the claim is that the grammar generates the documented
dwelling, not that it matches a survey.

The reference boxes are authored so that the face-adjacency read by
``exchange.graph_from_model`` is *exactly* the default ``G_U``/``G_L``
adjacency — every shared face is a grammar edge and vice versa (the audit
that guarantees "derives the reference" is a graph property, not a placement
comment).
"""

from __future__ import annotations

import os

from . import alphabet as A
from .model import StateGraph

#: the room-labelled reference model (see module docstring for provenance)
REFERENCE_OBJ = os.path.join(os.path.dirname(__file__), "models",
                             "KF_unit_interiors_reference.obj")


def subgraph_on(sg: StateGraph, ids) -> StateGraph:
    """The node-induced subgraph of ``sg`` on ``ids`` (all edges between them)."""
    ids = set(ids)
    out = StateGraph()
    for n in sg.nodes():
        if n in ids:
            a = sg.node_attrs(n)
            out.add_node(sg.node_label(n), id=n,
                         **{k: v for k, v in a.items() if k != "subtype"},
                         **({"subtype": a["subtype"]} if "subtype" in a else {}))
    for e in sg.edges():
        if e["src"] in ids and e["tgt"] in ids:
            out.add_edge(e["src"], e["tgt"], e["orientation"],
                         bidirectional=e["bidirectional"], weight=e["weight"],
                         type=e["type"], attrs=dict(e["attrs"]))
    return out


def reference_graph(unit: str = "K") -> StateGraph:
    """Import the reference OBJ and return one unit's interior graph
    (``"K"`` → ``G_U``'s, ``"F"`` → ``G_L``'s), with real sizes on the nodes."""
    from .exchange import graph_from_model
    g, _ = graph_from_model(REFERENCE_OBJ)
    ids = [n for n in g.nodes() if n.startswith(f"{unit}_unit_")]
    if not ids:
        raise ValueError(f"no {unit!r} rooms in the reference")
    return subgraph_on(g, ids)


def _host(unit: str) -> StateGraph:
    """The minimal host: a corridor and the unit's non-terminal."""
    from . import narkomfin as nf
    g = StateGraph()
    g.add_node(A.CORRIDOR, id="corridor", **{"x": 0.0, "y": -nf.CORRIDOR_DEPTH,
                                             "z": 0.0, "w": nf.BAY,
                                             "d": nf.CORRIDOR_DEPTH,
                                             "h": nf.FLOOR})
    label = A.U_SECTION if unit == "K" else A.L_SECTION
    g.add_node(label, id="u")
    g.add_edge("corridor", "u", A.H)
    return g


def reproduce(unit: str = "K") -> dict:
    """Run the reproduction: refine the non-terminal with the sub-grammar's
    **defaults** (the built condition) and compare the derived interior with
    the imported reference by typed isomorphism. Returns
    ``{"ok", "derived", "reference", "inverse", "host"}`` — apply
    ``inverse`` on ``host`` to watch the reverse sub-derivation return the
    non-terminal."""
    from .compare import typed_isomorphic
    from .grammar_units import refine_k, refine_f
    host = _host(unit)
    if unit == "K":
        inverse, ids = refine_k(host, "u")
    elif unit == "F":
        inverse, ids = refine_f(host, "u")
    else:
        raise ValueError(f"unit must be 'K' or 'F', got {unit!r}")
    interior = [n for n in host.nodes()
                if host.node_attrs(n).get("unit") == "u"]
    derived = subgraph_on(host, interior)
    return {"ok": typed_isomorphic(derived, reference_graph(unit)),
            "derived": derived, "inverse": inverse, "host": host, "ids": ids}
