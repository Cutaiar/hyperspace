
"""Look-back and dream, two nodes.

`lookback` is picture in → trail out: it records what is wired into its
`image` into a ring of its own (`Renderer.ring`, one per instance) and its
picture is the trail, laid over nothing — a composite lays it on. `dream`
is picture in → dreamed picture out: it submits its input to the worker
itself, pulls its own results, and with `dream.on` off passes its input
through and submits nothing, so the worker sleeps. One live dream at a time.
An old loadable patch's one-shader look-back migrates to `scene → lookback →
composite (add)` — and `lookback → dream →` into it with a dream mix above
0 — and its goldens are unmoved (tests/test_golden_frames.py).

The look-back is retired. `seven` still writes the look-back an
old file drew; the ladder's last step (`graphmigrate.lookbacks`) makes it
public parts, so the tests of the migration read its result through that
step; a live frame refuses a look-back wire in words. The dream
node is retired too — the dream is an effect (tests/test_dream_effect.py) and
`seven`'s `{"kind": "dream"}` opens as its parts (tests/test_dream_migration.py);
the tests of the old node went with it."""

from __future__ import annotations

import pytest

from hyperspace import graph as G
from hyperspace import graphmigrate as M

# ---------------------------------------------------------------- no look-back

def test_a_live_frame_refuses_a_look_back_in_words():
    """A look-back (`lookback`, `lookback.<n>`) and its echo pins
    are no live nodes — a saved one is public parts by the ladder's last
    step — so a live frame refuses each wire on one in words, the rest
    standing."""
    words = G.LOOKBACK_RETIRED
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "lookback", "instance": 2}],
                         "wires": [{"from": "shape", "to": "scene.geometry"},
                                   {"from": "scene", "to": "lookback.2.image"},
                                   {"from": "lookback.2", "to": "output.2.image"},
                                   {"from": "lookback.echo.1", "to": "output.3.image"}]})
    assert f"lookback.2: {words}" in spec.notes
    assert f"wire scene → lookback.2.image — lookback.2: {words}" in spec.notes
    assert f"wire lookback.2 → output.2.image — lookback.2: {words}" in spec.notes
    assert f"wire lookback.echo.1 → output.3.image — lookback.echo.1: {words}" in spec.notes
    assert spec.wires == (G.Wire("shape", "scene.geometry"),)


# ---------------------------------------------------------------- the migration

def _pairs(section):
    return [(w["from"], w["to"]) for w in section["wires"]]


@pytest.mark.parametrize(("values", "dream"), [
    ({"dream.on": True, "dream.mix": 0.5}, True),
    ({"dream.on": True, "dream.mix": 0.0}, False),
    ({"dream.on": False, "dream.mix": 0.5}, None),
])
def test_an_old_dream_loadable_migrates_to_the_drawn_chain(values, dream):
    """An old file's look-back: on with a dream mix, `scene → lookback →
    dream → composite (add, under the scene) → All outputs`, the cover and
    the occluder its own wires, `dream.on` on; on with no mix, the same
    without the dream and `dream.on` off; off, no look-back at all — the
    scene straight into All outputs, as it drew. The ladder's
    last step makes that look-back public parts — its picture, the last
    Cut's, where the look-back's went — and that graph reads clean."""
    out, notes = M.seven({"schema": "hyperspace.preset/2", "values": dict(values)}, {})
    assert notes == [] and out["schema"] == M.WIRED_SCHEMA
    got = _pairs(out["graph"])
    done, lb_notes = M.lookbacks(out)
    spec = G.read_graph(done["graph"])
    assert spec.notes == () and G.read_graph(spec.to_json()).to_json() == spec.to_json()
    if dream is None:
        assert done is out and lb_notes == []
        assert ("scene", "output.all.image") in got
        assert not any("lookback" in a or "lookback" in b for a, b in got)
        assert out["values"]["dream.on"] is False
        return
    head = [("scene", "lookback.occluder"), ("scene", "composite.under")]
    head += ([("lookback", "dream.image"), ("dream", "composite.over")] if dream
             else [("lookback", "composite.over")])
    i = got.index(head[0])
    assert got[i:i + len(head)] == head
    assert {("composite", "output.all.image"), ("scene", "lookback.image"),
            ("scene.cover", "lookback.cover")} <= set(got)
    assert {"kind": "composite", "blend": "add"} in out["graph"]["nodes"]
    assert ({"kind": "dream"} in out["graph"]["nodes"]) is dream
    assert out["values"]["dream.on"] is dream
    assert out["values"]["dream.mix"] == values["dream.mix"]          # its meaning kept
    # (the parts, the scene recorded and cut by itself and its cover)
    parts = _pairs(done["graph"])
    assert not any("lookback" in a or "lookback" in b for a, b in parts)
    assert {("scene", "fade.image"), ("delay", "trail.stack"), ("trail", "cut.image"),
            ("scene", "matte.image"), ("scene.cover", "cut.2.mask"),
            ("scene", "composite.under"), ("composite", "output.all.image")} <= set(parts)
    assert (("cut.2", "dream.image") in parts and ("dream", "composite.over") in parts) is dream
    assert (("cut.2", "composite.over") in parts) is not dream
    assert done["values"]["dream.on"] is dream and done["values"]["dream.mix"] == values[
        "dream.mix"]
    assert len(lb_notes) == 1 and lb_notes[0].startswith("lookback is public parts now")


def _route(target):
    return {"source": "apc40.pad.1", "target": target, "mode": "toggle"}


def test_a_driven_dream_on_at_rest_off_draws_the_chain_and_says_so():
    """Final review: a file with `dream.on` off at rest but a route on it (a
    pad toggling the tracers live) drew its look-back whenever the pad was
    on, so the chain is drawn — and with `dream.mix` driven too, the dream
    — `dream.on` keeping its rest value (the pad switches the dream), and
    the load says what changed. The routes survive."""
    doc = {"schema": "hyperspace.preset/2",
           "values": {"dream.on": False, "dream.mix": 0.0},
           "routes": [_route("dream.on"), _route("dream.mix")]}
    out, notes = M.seven(doc, {})
    got = _pairs(out["graph"])
    assert ("scene", "lookback.image") in got
    assert ("lookback", "dream.image") in got and ("dream", "composite.over") in got
    assert ("composite", "output.all.image") in got
    assert out["values"]["dream.on"] is False
    assert [r["target"] for r in out["routes"]] == ["dream.on", "dream.mix"]
    assert M.LIVE_LOOK_NOTES["dream.on"] in notes
    assert M.LIVE_LOOK_NOTES["dream.mix"] in notes
    # (the look-back public parts, last; the routes untouched)
    done, _ = M.lookbacks(out)
    assert ("cut.2", "dream.image") in _pairs(done["graph"])
    assert [r["target"] for r in done["routes"]] == ["dream.on", "dream.mix"]
    assert G.read_graph(done["graph"]).notes == ()


def test_a_driven_dream_on_with_no_mix_draws_the_trail_alone():
    out, notes = M.seven({"schema": "hyperspace.preset/6",
                          "values": {"dream.on": False, "dream.mix": 0.0},
                          "desk": [{"source": "apc40.pad.2", "target": "dream.on"}]}, {})
    got = _pairs(out["graph"])
    assert ("lookback", "composite.over") in got
    assert not any(n.get("kind") == "dream" for n in out["graph"]["nodes"])
    assert notes == [M.LIVE_LOOK_NOTES["dream.on"]]


def test_a_driven_dream_mix_at_zero_draws_the_dream():
    """`dream.on` on at rest, `dream.mix` 0 but pushed by a macro: the dream
    is drawn (it was, once pushed), `dream.on` on."""
    doc = {"schema": "hyperspace.preset/3", "values": {"dream.on": True, "dream.mix": 0.0},
           "macros": {"1": {"subs": [{"base": "dream.mix"}]}}}
    out, notes = M.seven(doc, {})
    got = _pairs(out["graph"])
    assert ("lookback", "dream.image") in got and ("dream", "composite.over") in got
    assert out["values"]["dream.on"] is True
    assert notes == [M.LIVE_LOOK_NOTES["dream.mix"]]


def test_the_old_echo_and_dream_readers_fold_into_the_two_nodes():
    """An old section's `echo.3 →` reads the look-back's pin `lookback.echo.3`
    (the look-back off: drawn only to record for it); its `dream →` reads
    the dream node, fed the look-back, `dream.on` on so it dreams. The
    ladder's last step makes the pin a Read of the delay at 2,
    nearest, and the dream is fed the trail."""
    out, _ = M.seven({"schema": "hyperspace.preset/5", "values": {"dream.on": False},
                      "graph": {"nodes": [{"kind": "echo", "index": 3}, {"kind": "dream"}],
                                "wires": [{"from": "frame", "to": "fx.image"},
                                          {"from": "echo.3", "to": "shape.faces"},
                                          {"from": "dream", "to": "output.2.image"}]}}, {})
    got = _pairs(out["graph"])
    assert ("lookback.echo.3", "shape.faces") in got and ("scene", "lookback.image") in got
    assert ("lookback", "dream.image") in got and ("dream", "output.2.image") in got
    assert ("scene", "output.all.image") in got                     # the look-back was off
    assert not any(n.get("kind") == "echo" for n in out["graph"]["nodes"])
    assert out["values"]["dream.on"] is True
    done, _ = M.lookbacks(out)
    parts = _pairs(done["graph"])
    assert ("delay", "read.stack") in parts and ("read", "shape.faces") in parts
    assert ("trail", "dream.image") in parts and ("dream", "output.2.image") in parts
    assert ("scene", "output.all.image") in parts
    assert (done["values"]["fx.read.at"], done["values"]["fx.read.between"]) == (2.0, 1)
    assert G.read_graph(done["graph"]).notes == ()


def test_the_seven_words_refuse_the_old_ports():
    """A `/7` frame is read as it is: `lookback.capture` and the
    `echo.<k>` pins are refused in words (the migration alone reads them) —
    as is every look-back wire, the look-back retired."""
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "echo", "index": 2}],
                         "wires": [{"from": "scene", "to": "lookback.capture"},
                                   {"from": "lookback", "to": "output.all.image"},
                                   {"from": "echo.2", "to": "output.2.image"}]})
    words = G.LOOKBACK_RETIRED
    assert spec.notes == (
        f"wire scene → lookback.capture — lookback: {words}",
        f"wire lookback → output.all.image — lookback: {words}",
        f"wire echo.2 → output.2.image — echo.2: {words}")
    assert spec.wires == ()


# ---------------------------------------------------------------- `dream.on`'s meaning

def test_click_to_map_offers_a_migrated_tracers_trail_knobs():
    """A migrated party-tracer (its dream off, its look-back drawn) can show
    its trail knobs, and click-to-map offers them among its own; its dream, off and
    undriven, is left out. Its trail knobs are its
    public parts' (`fx.trail.level`, `fx.trail.fade`, `delay.depth`,
    `cut.amount`), migrated on by the ladder's last step."""
    import json

    from conftest import CORPUS

    from hyperspace import learn
    from hyperspace.fx import FxState

    doc = M.forward(json.loads((CORPUS / "loadable" / "party-tracer.json").read_text()),
                    {}).doc
    values = doc["values"]
    # (its dream was off and undriven: left out, its ids gone)
    assert not [pid for pid in values if pid.startswith("dream.")]
    drawn = learn.drawn_of(G.read_graph(doc["graph"], effects=set(FxState().specs)))
    assert {"trail", "delay", "cut"} <= drawn and "dream" not in drawn
    assert "lookback" not in drawn
    for pid in ("fx.trail.level", "fx.trail.fade", "delay.depth", "cut.amount"):
        assert learn.cannot_show(pid, values, drawn=drawn) is None, pid
    params = [("fx.trail.level", "fx"), ("fx.trail.fade", "fx")]
    used, _ = learn.ranked(params, values, {}, set(), set(), drawn=drawn)
    assert [pid for pid, _ in used] == ["fx.trail.level", "fx.trail.fade"]
    assert dict(used)["fx.trail.fade"] == learn.ON
    # the trail's off: its knobs are dead
    assert learn.cannot_show("fx.trail.fade", {**values, "fx.trail.on": False},
                             drawn=drawn) == "trail off"

