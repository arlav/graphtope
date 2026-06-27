"""Smoke tests for the step-by-step visualisation (headless / Agg)."""

import matplotlib
matplotlib.use("Agg")

from graphtope import StateGraph, alphabet as A
from graphtope import grammar_dnf as dnf, topoview


def test_record_frames_captures_axiom_and_every_step():
    frames, d = topoview.record_frames(StateGraph.axiom(), dnf.derive)
    assert len(frames) == 14                       # axiom + 13 productions
    assert frames[0][0] == "A₀ axiom"
    assert [t for t, _ in frames[1:]] == [s["rule"] for s in d.trace()]


def test_shared_layout_separates_components_and_covers_all_nodes():
    frames, _ = topoview.record_frames(StateGraph.axiom(), dnf.derive)
    pos = topoview.shared_layout(frames)
    final_nodes = {n["id"] for n in frames[-1][1]["nodes"]}
    assert final_nodes <= set(pos)                 # every node has a position
    # two blocks → positions span two separated x-bands
    xs = sorted(x for x, _ in pos.values())
    assert max(xs) - min(xs) > 2.0


def test_draw_and_grid_produce_figures():
    frames, d = topoview.record_frames(StateGraph.axiom(), dnf.derive)
    fig = topoview.draw_grid(frames, ncols=4)
    assert len(fig.axes) >= len(frames)
    ax = topoview.draw(d.sg, title="G_DNF")
    assert ax.patches                              # glyphs were drawn
