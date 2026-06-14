"""Visualisation + layout helpers (Stage-1 coordinates are layout only).

Thin wrappers over TopologicPy's renderers so a ``StateGraph`` can be shown
inline in the notebook. This is also where the Stage-2 geometry seam will grow.
"""

from __future__ import annotations

from topologicpy.Graph import Graph


def show(sg, *, vertex_label_key: str = "label", **kwargs):
    """Render a ``StateGraph`` with TopologicPy's Plotly viewer.

    Pass ``vertex_label_key="id"`` to label by node id instead of by label.
    Extra kwargs are forwarded to ``Graph.Show``.
    """
    return Graph.Show(sg.topologic_graph, vertexLabelKey=vertex_label_key, **kwargs)


def pyvis(sg, **kwargs):
    """Interactive HTML view via ``Graph.PyvisGraph`` (good for notebooks)."""
    return Graph.PyvisGraph(sg.topologic_graph, **kwargs)
