"""graphtope — a topology-driven graph grammar for architecture (Stage 1).

See ``Topologic_Graph_Grammar_Spec.md`` for the specification and ``CLAUDE.md``
for the carrier (TopologicPy) gotchas. Build status: M1 (carrier + invariants).
"""

from __future__ import annotations

from . import alphabet
from .model import StateGraph

__version__ = "0.1.0"

__all__ = ["StateGraph", "alphabet", "__version__"]
