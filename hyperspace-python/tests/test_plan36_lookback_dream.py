
"""Plan 36 T4 (W4, D2, D3): look-back and dream, two nodes.

`lookback` is picture in → trail out: it records what is wired into its
`image` into a ring of its own (`Renderer.ring`, one per instance) and its
picture is the trail, laid over nothing — a composite lays it on. `dream`
is picture in → dreamed picture out: it submits its input to the worker
itself, pulls its own results, and with `dream.on` off passes its input
through and submits nothing, so the worker sleeps. One live dream at a time.
An old loadable patch's one-shader look-back migrates to `scene → lookback →
composite (add)` — and `lookback → dream →` into it with a dream mix above
0 — and its goldens are unmoved (tests/test_golden_frames.py).

Plan 90 H2: the look-back is retired. `seven` still writes the look-back an
old file drew; the ladder's last step (`graphmigrate.lookbacks`) makes it
public parts, so the tests of the migration read its result through that
step; a live frame refuses a look-back wire in words; the dream is kept."""

from __future__ import annotations

import numpy as np
import pytest
from test_graph_faces import (
    Still,
    _empty,
    _faces,
    _fbo,
    _media,
    _px,
    _rgba,
)

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace.lookback import DreamState
from hyperspace.outputs import Switches, View

SIZE = (160, 120)
RED, GREEN = (255, 0, 0), (0, 255, 0)


class Counting:
    """A worker in the dream node's slot: counts the submits, and answers
    each with a flat green frame one submit late."""

    def __init__(self):
        self.submits = 0
        self.done = None

    def submit(self, frame, frame_index):
        self.submits += 1
        out = np.zeros_like(frame)
        out[..., 1] = out[..., 3] = 255
        self.done, self.pending = getattr(self, "pending", None), (out, frame_index)

    def latest(self):
        return self.done


def _wired(*pairs, nodes=()):
    spec = G.read_graph({"frame": "wired", "nodes": list(nodes),
                         "wires": [{"from": a, "to": b} for a, b in pairs]})
    assert not spec.notes, spec.notes
    return spec.wiring()


def _renderer(ctx, wiring, media=None, dream=None):
    from hyperspace.render import Renderer

    r = Renderer(ctx, dream if dream is not None else DreamState())
    r.ghost.state.on = False
    r.media = media
    r.wiring = wiring
    return r


def _frames(ctx, r, s, n=4, views=1):
    vs = [View(Switches(), SIZE, target=_fbo(ctx, *SIZE)) for _ in range(views)]
    for k in range(n):
        s.ang = [a + 0.05 for a in s.ang]
        r.draw_outputs(s, *SIZE, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target) for v in vs]


# a dream laid on its picture: `scene → dream → composite (add, under the
# scene)` (plan 90 H2: the look-back that fed it in an old frame is retired)
WAKE = (("shape", "scene.geometry"), ("scene", "composite.under"),
        ("scene", "dream.image"), ("dream", "composite.over"),
        ("composite", "output.all.image"))
WAKE_NODES = ({"kind": "composite", "blend": "add"}, {"kind": "dream"})


# ---------------------------------------------------------------- the dream off: the worker idle

def test_tracers_with_the_dream_off_submit_nothing(ctx):
    """A dream node that is off (`dream.on` false), against the same frame
    with no dream node: the worker gets no submission — it sleeps — and
    the dream passes its picture through, byte for byte the frame with no
    dream node at all. (Plan 90 H2: what it was laid on, the look-back's
    trail, is public parts now; the dream's own switch is this test's.)"""
    d = DreamState(on=False)
    tracers = _wired(*(p for p in WAKE if p not in (("scene", "dream.image"),
                                                    ("dream", "composite.over"))),
                     ("scene", "composite.over"), nodes=WAKE_NODES[:1])
    plain = _renderer(ctx, tracers, dream=DreamState(**vars(d)))
    plain.dreamer.source = none = Counting()
    want = _frames(ctx, plain, _faces())[0]
    r = _renderer(ctx, _wired(*WAKE, nodes=WAKE_NODES), dream=d)
    r.dreamer.source = worker = Counting()
    got = _frames(ctx, r, _faces())[0]
    assert worker.submits == 0 and none.submits == 0
    assert np.array_equal(got, want), "off, the dream is its picture"
    assert r._graph.nodes["dream"].said.startswith("off: the picture passes through")
    # on, it submits once a frame
    d.on = True
    _frames(ctx, r, _faces(), n=3)
    assert worker.submits == 3


# ---------------------------------------------------------------- the dream alone

def test_the_dream_alone_on_a_channel_refreshes(ctx):
    """`channel.a → dream → output.all.image`, no look-back anywhere: the
    dream submits the channel's picture, pulls its own results and lays
    them over it — the window turns from the red still to the green dream;
    off, it is the still again."""
    d = DreamState(on=True, mix=1.0, darken=0.0, contrast=1.0)
    m = _media(a=Still(_rgba(16, 9, RED)))
    m.channels["a"].fit = 2                                   # stretch: fills
    r = _renderer(ctx, _wired(("channel.a", "dream.image"), ("dream", "output.all.image"),
                              nodes=[{"kind": "dream"}]), media=m, dream=d)
    worker = r.dreamer.source = Counting()
    first = _frames(ctx, r, _empty(), n=1)[0]
    assert "lookback" not in r._graph.nodes and worker.submits == 1
    h, w = first.shape[:2]
    assert tuple(first[h // 2, w // 2, :3]) == RED            # no result yet: its picture
    got = _frames(ctx, r, _empty(), n=3)[0]
    assert r.dreamer.dream_frame >= 1 and worker.submits == 4
    assert tuple(got[h // 2, w // 2, :3]) == GREEN, got[h // 2, w // 2]
    d.on = False
    off = _frames(ctx, r, _empty(), n=1)[0]
    assert tuple(off[h // 2, w // 2, :3]) == RED and worker.submits == 4


# ---------------------------------------------------------------- one live dream (D2)

def test_a_second_dream_is_refused_in_words():
    """D2: one worker, one GPU job — a wire on `dream.2` is refused, said,
    the rest stands; the entry alone reads."""
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "dream"},
                                                     {"kind": "dream", "instance": 2}],
                         "wires": [{"from": "scene", "to": "dream.image"},
                                   {"from": "scene", "to": "dream.2.image"},
                                   {"from": "dream.2", "to": "output.all.image"}]})
    words = G.ONE_DREAM.format(name="dream.2")
    assert spec.notes == (f"wire scene → dream.2.image — {words}",
                          f"wire dream.2 → output.all.image — {words}")
    assert spec.wires == (G.Wire("scene", "dream.image"),)
    assert G.DreamAt(2).to_json() == {"kind": "dream", "instance": 2}
    assert spec.dream == G.DreamAt(1)


# ---------------------------------------------------------------- no look-back (plan 90 H2)

def test_a_live_frame_refuses_a_look_back_in_words():
    """Plan 90 H2: a look-back (`lookback`, `lookback.<n>`) and its echo pins
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
    scene straight into All outputs, as it drew. Plan 90 H2: the ladder's
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
    # (plan 90 H2: the parts, the scene recorded and cut by itself and its cover)
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
    # (plan 90 H2: the look-back public parts, last; the routes untouched)
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


def test_plan_34s_echo_and_dream_readers_fold_into_the_two_nodes():
    """An old section's `echo.3 →` reads the look-back's pin `lookback.echo.3`
    (the look-back off: drawn only to record for it); its `dream →` reads
    the dream node, fed the look-back, `dream.on` on so it dreams. Plan 90
    H2: the ladder's last step makes the pin a Read of the delay at 2,
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
    """A `/7` frame is read as it is: `lookback.capture` and plan 34's
    `echo.<k>` are refused in words (the migration alone reads them) —
    plan 90 H2: as is every look-back wire, the look-back retired."""
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


# ---------------------------------------------------------------- fix round 1: `dream.on`'s meaning

def test_click_to_map_offers_a_migrated_tracers_trail_knobs():
    """`dream.on` gates the dream's knobs alone: a migrated party-tracer
    (`dream.on` false, its look-back drawn) can show its trail knobs, and
    click-to-map offers them among its own — the dream's own knobs it
    cannot show (no dream drawn). Plan 90 H2: its trail knobs are its
    public parts' (`fx.trail.level`, `fx.trail.fade`, `delay.depth`,
    `cut.amount`), migrated on by the ladder's last step."""
    import json

    from conftest import CORPUS

    from hyperspace import learn
    from hyperspace.fx import FxState

    doc = M.forward(json.loads((CORPUS / "loadable" / "party-tracer.json").read_text()),
                    {}).doc
    values = doc["values"]
    assert values["dream.on"] is False
    drawn = learn.drawn_of(G.read_graph(doc["graph"], effects=set(FxState().specs)))
    assert {"trail", "delay", "cut"} <= drawn and "dream" not in drawn
    assert "lookback" not in drawn
    for pid in ("fx.trail.level", "fx.trail.fade", "delay.depth", "cut.amount"):
        assert learn.cannot_show(pid, values, drawn=drawn) is None, pid
    assert learn.cannot_show("dream.mix", values, drawn=drawn) == "no dream"
    assert learn.cannot_show("dream.k", values) == "dream off"       # no graph to ask
    params = [("fx.trail.level", "fx"), ("fx.trail.fade", "fx"), ("dream.mix", "dream")]
    used, _ = learn.ranked(params, values, {}, set(), set(), drawn=drawn)
    assert [pid for pid, _ in used] == ["fx.trail.level", "fx.trail.fade"]
    assert dict(used)["fx.trail.fade"] == learn.ON
    # the trail's off: its knobs are dead
    assert learn.cannot_show("fx.trail.fade", {**values, "fx.trail.on": False},
                             drawn=drawn) == "trail off"


def test_the_tracer_only_group_loadable_leaves_the_worker_idle(ctx, tmp_path):
    """The dream group's `tracer-only` (echoes alone, mix 0) says the dream
    off since plan 36 T4: applied over a frame drawing a dream, the dream
    passes through and the worker gets no submission; its note says a
    values-only loadable patch draws no node. (Plan 90 H2: its retired
    look-back knobs land quietly — they drew nothing in a module preset.)"""
    from conftest import seed
    from test_lookback import registry

    from hyperspace.library import Library

    d = DreamState(on=True)
    reg = registry(d)
    seed(tmp_path, "dream")          # (the corpus's dream module presets)
    lib = Library(tmp_path, period=0.0)
    lib.attach(reg)
    assert lib.load("dream", "tracer-only") == [] and d.on is False
    assert "cannot draw or remove a look-back" in lib.read("dream", "tracer-only")["note"]
    r = _renderer(ctx, _wired(*WAKE, nodes=WAKE_NODES), dream=d)
    r.dreamer.source = worker = Counting()
    _frames(ctx, r, _faces(), n=3)
    assert worker.submits == 0
    assert not lib.warning, lib.warning
    assert "dream.echo_mix" not in reg and reg["dream.darken"].value == 0.3
