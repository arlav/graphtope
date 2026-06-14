"""Derivation engine: apply / replay / invert (spec §8, §10.2).

``apply(rule, match, params)`` rewrites the graph and appends to a derivation
trace; the trace records enough to **replay** forward and **invert** backward
(§10.2). Reversibility is structural for the operation set and *exact* whenever
the trace is kept (§5.1 note).

Planned for milestone **M5/M6**.
"""

from __future__ import annotations

# TODO(M5/M6): apply(rule, match, params) -> trace; replay(trace); invert(trace).
