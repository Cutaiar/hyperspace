"""Plan 35 T6 (U): the LOOKBACK page as a view of the wires, headless.

"records:" is what is wired into `lookback.capture` (`ui_lookback.
capture_line`), set by a combo of the graph's pictures (`graphview.
set_picture` on that port: a GRAPH edit, one undo step); "draws over:" is
`lookback.image`'s source, words alone (`draws_over_line`)."""

from __future__ import annotations

from test_graph_edit import free_rig
from test_ui_output import DEFAULT, _pairs

from hyperspace import graph as G
from hyperspace import graphview
from hyperspace.ui_lookback import capture_line, draws_over_line


def test_records_says_and_sets_the_capture(tmp_path):
    spec = G.read_graph(DEFAULT)
    assert capture_line(spec) == "records: Scene"
    assert draws_over_line(spec) == "draws over: Scene"
    rig, e, pushed = free_rig(tmp_path, *_pairs(DEFAULT))
    gs = rig.presets.graph
    before = gs.spec.to_json()
    assert graphview.picture_choices(gs.spec, "lookback.capture")[0] == "nothing"
    assert graphview.picture_now(gs.spec, "lookback.capture") == "scene"
    assert graphview.set_picture(e, "lookback.capture", "hands.layer") is None
    assert G.Wire("hands.layer", "lookback.capture") in gs.spec.wires
    assert capture_line(gs.spec) == "records: Hands layer"
    assert graphview.set_picture(e, "lookback.capture", "nothing") is None
    assert not any(w.dst == "lookback.capture" for w in gs.spec.wires)
    assert capture_line(gs.spec) == "records: nothing — the echoes fade"
    assert graphview.set_picture(e, "lookback.capture", "scene") is None
    assert gs.spec.to_json() == before and len(pushed) == 3
    # the look-back over nothing: said
    assert draws_over_line(G.read_graph({"frame": "wired"})) == "draws over: nothing"
    # with no renderer and no preset: the factory frame's words
    assert capture_line(None) == "records: Scene"
