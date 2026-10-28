# ruff: noqa: F811 — `ctx` is test_graph_faces' fixture, taken as each GL test's argument
"""Plan 36 T4 (W4, D2, D3): look-back and dream, two nodes.

`lookback` is picture in → trail out: it records what is wired into its
`image` into a ring of its own (`Renderer.ring`, one per instance) and its
picture is the trail, laid over nothing — a composite lays it on. `dream`
is picture in → dreamed picture out: it submits its input to the worker
itself, pulls its own results, and with `dream.on` off passes its input
through and submits nothing, so the worker sleeps. One live dream at a time.
An old preset's one-shader look-back migrates to `scene → lookback →
composite (add)` — and `lookback → dream →` into it with a dream mix above
0 — and its goldens are unmoved (tests/test_golden_frames.py)."""

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
    ctx,  # noqa: F401 — the GL context fixture, taken as each GL test's argument
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


# the factory frame of an old preset with its tracers on and a dream mix
# above 0: `scene → lookback → dream → composite (add, under the scene)`
WAKE = (("shape", "scene.geometry"), ("scene", "lookback.occluder"),
        ("scene", "composite.under"), ("lookback", "dream.image"),
        ("dream", "composite.over"), ("composite", "output.all.image"),
        ("scene", "lookback.image"), ("scene.cover", "lookback.cover"))
WAKE_NODES = ({"kind": "composite", "blend": "add"}, {"kind": "dream"})


# ---------------------------------------------------------------- the dream off: the worker idle

def test_tracers_with_the_dream_off_submit_nothing(ctx):
    """The look-back drawn with no dream node, and with one that is off
    (`dream.on` false): the trail shows, the worker gets no submission —
    it sleeps — and the dream passes its picture through, byte for byte
    the frame with no dream node at all."""
    d = DreamState(on=False, echoes=8, gap=0.0, echo_mix=0.8)
    tracers = _wired(*(p for p in WAKE if p not in (("lookback", "dream.image"),
                                                    ("dream", "composite.over"))),
                     ("lookback", "composite.over"), nodes=WAKE_NODES[:1])
    plain = _renderer(ctx, tracers, dream=DreamState(**vars(d)))
    plain.dreamer.source = none = Counting()
    want = _frames(ctx, plain, _faces())[0]
    r = _renderer(ctx, _wired(*WAKE, nodes=WAKE_NODES), dream=d)
    r.dreamer.source = worker = Counting()
    got = _frames(ctx, r, _faces())[0]
    assert worker.submits == 0 and none.submits == 0
    assert r.lookback.held() > 0
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


# ---------------------------------------------------------------- several look-backs

def test_two_lookbacks_keep_separate_rings(ctx):
    """`lookback` and `lookback.2` (declared by its entry), each recording
    its own picture with its own values (`dream.2.*`: its own count and
    detail): two rings, their echoes held apart; `lookback.2.echo.1` reads
    the second's ring. An undeclared `lookback.3` is refused in words."""
    from hyperspace.params import declare_lookbacks, is_lookback_id, lookback_ids

    assert lookback_ids("lookback.2")[:3] == ["dream.2.echo_mix", "dream.2.fade",
                                              "dream.2.echoes"]
    assert is_lookback_id("dream.2.echoes") and not is_lookback_id("dream.echoes")
    wiring = _wired(("shape", "scene.geometry"), ("scene", "lookback.image"),
                    ("lookback", "output.all.image"),
                    ("channel.a", "lookback.2.image"), ("lookback.2", "output.2.image"),
                    ("lookback.2.echo.1", "output.3.image"),
                    nodes=[{"kind": "lookback", "instance": 2}])
    m = _media(a=Still(_rgba(16, 9, RED)))
    r = _renderer(ctx, wiring, media=m, dream=DreamState(echoes=4, gap=0.0, res=0))
    from hyperspace.view import ViewState

    s = _faces()
    two = DreamState(echoes=2, gap=0.0, res=2)
    s.lookback = {"lookback.2": two}
    _frames(ctx, r, s, n=5, views=3)
    one, other = r.ring("lookback"), r.ring("lookback.2")
    assert one is r.lookback and other is not one and other.state is two
    assert one.atlas is not None and other.atlas is not None and one.atlas is not other.atlas
    assert one.echo != other.echo                         # res 0 against res 2
    assert len(one.layers()) == 4 and len(other.layers()) == 2
    assert r._graph.nodes["lookback.2.echo.1"].lookback == "lookback.2"
    assert isinstance(r._graph.nodes["lookback.2(capture)"], G.Capture)
    # an instance no entry declares
    spec = G.read_graph({"frame": "wired", "wires": [
        {"from": "scene", "to": "lookback.3.image"},
        {"from": "lookback.3", "to": "output.all.image"}]})
    assert spec.notes and 'add one: {"kind": "lookback", "instance": 3}' in spec.notes[0]
    # its params come and go with its entry
    from test_lookback import registry

    reg = registry()
    reg.lookback_state = {}
    assert set(declare_lookbacks(reg, ["lookback", "lookback.2"])) == set(
        lookback_ids("lookback.2"))
    assert "dream.2.echoes" in reg and reg["dream.2.echoes"].value == 8
    declare_lookbacks(reg, ["lookback"])
    assert "dream.2.echoes" not in reg
    assert isinstance(ViewState().lookback, dict)


# ---------------------------------------------------------------- the migration

def _pairs(section):
    return [(w["from"], w["to"]) for w in section["wires"]]


@pytest.mark.parametrize(("values", "dream"), [
    ({"dream.on": True, "dream.mix": 0.5}, True),
    ({"dream.on": True, "dream.mix": 0.0}, False),
    ({"dream.on": False, "dream.mix": 0.5}, None),
])
def test_an_old_dream_preset_migrates_to_the_drawn_chain(values, dream):
    """An old file's look-back: on with a dream mix, `scene → lookback →
    dream → composite (add, under the scene) → All outputs`, the cover and
    the occluder its own wires, `dream.on` on; on with no mix, the same
    without the dream and `dream.on` off; off, no look-back at all — the
    scene straight into All outputs, as it drew."""
    out, notes = M.seven({"schema": "hyperspace.preset/2", "values": dict(values)}, {})
    assert notes == [] and out["schema"] == M.WIRED_SCHEMA
    got = _pairs(out["graph"])
    spec = G.read_graph(out["graph"])
    assert spec.notes == () and G.read_graph(spec.to_json()).to_json() == spec.to_json()
    if dream is None:
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
    assert G.read_graph(out["graph"]).notes == ()


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
    the dream node, fed the look-back, `dream.on` on so it dreams."""
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
    assert G.read_graph(out["graph"]).notes == ()


def test_the_seven_words_refuse_the_old_ports():
    """A `/7` frame is read as it is: `lookback.capture` and plan 34's
    `echo.<k>` are refused in words (the migration alone reads them)."""
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "echo", "index": 2}],
                         "wires": [{"from": "scene", "to": "lookback.capture"},
                                   {"from": "lookback", "to": "output.all.image"},
                                   {"from": "echo.2", "to": "output.2.image"}]})
    assert spec.notes == (
        f"wire scene → lookback.capture — {G.CAPTURE_IS_IMAGE.format(node='lookback')}",
        f"wire echo.2 → output.2.image — {G.ECHO_IS_A_PIN.format(name='echo.2', k=2)}")


# ---------------------------------------------------------------- fix round 1: `dream.on`'s meaning

def test_click_to_map_offers_a_migrated_tracers_trail_knobs():
    """`dream.on` gates the dream's knobs alone: a migrated party-tracer
    (`dream.on` false, its look-back drawn) can show its trail knobs, and
    click-to-map offers them among its own — the dream's own knobs it
    cannot show (no dream drawn). With no look-back drawn, the trail knobs
    are dead."""
    import json

    from conftest import CORPUS

    from hyperspace import learn

    doc = json.loads((CORPUS / "presets" / "party-tracer.json").read_text())
    values = doc["values"]
    assert values["dream.on"] is False
    drawn = learn.drawn_of(G.read_graph(doc["graph"]))
    assert "lookback" in drawn and "dream" not in drawn
    for pid in ("dream.echo_mix", "dream.fade", "dream.echoes", "dream.occlude"):
        assert learn.cannot_show(pid, values, drawn=drawn) is None, pid
    assert learn.cannot_show("dream.mix", values, drawn=drawn) == "no dream"
    assert learn.cannot_show("dream.k", values) == "dream off"       # no graph to ask
    params = [(pid, "dream") for pid in ("dream.echo_mix", "dream.fade", "dream.mix")]
    used, _ = learn.ranked(params, values, {}, set(), set(), drawn=drawn)
    assert [pid for pid, _ in used] == ["dream.echo_mix", "dream.fade"]
    assert dict(used)["dream.fade"] == learn.ON
    plain = learn.drawn_of(G.read_graph({"frame": "wired", "wires": [
        {"from": "scene", "to": "output.all.image"}]}))
    assert learn.cannot_show("dream.fade", values, drawn=plain) == "no look-back"
    assert learn.cannot_show("dream.2.fade", values, drawn=drawn) == "no look-back"


def test_the_tracer_only_group_preset_leaves_the_worker_idle(ctx, tmp_path):
    """The dream group's `tracer-only` (echoes alone, mix 0) says the dream
    off since plan 36 T4: applied over a frame drawing a dream, the dream
    passes through and the worker gets no submission; its note says a
    values-only preset draws no node."""
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
    assert worker.submits == 0 and r.lookback.held() > 0
