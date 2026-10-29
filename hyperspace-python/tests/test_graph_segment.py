
"""Plan 39 T4 — `segment`: any picture → foreground, background and mask
(W4; decisions 3, 4, 5).

`segment[.n]` takes the picture on its `image` port and makes three pins:
`segment.fg` (the picture where the matte passes, cut away elsewhere),
`segment.bg` (the reverse) and `segment.mask` (the matte itself). In
person mode the matte is the renderer's worker's (`Renderer.segmenter`),
fed by the shortcut (a channel's own CPU frame) or the readback (any other
picture), only when the input moved; in motion mode it is a background
model in GLSL on the frame thread; subject is refused in words. Before the
first matte, off, with no worker (the hold's preview) or on an error: the
picture whole on `fg`, nothing on `bg` and `mask`.

The node is tested with a fake worker (as test_dream.py does): what it is
fed and by which path (a count on each), the pins from a known matte, the
orientation of a rows-top-first matte on every consumer (a cut, a window by
the promotion, `lookback.cover` by the mask port's refit), `on` off idling
the worker, a removed node closing it, the preview making none, motion on
two stills, and the `/7` round trip of the entry and its values
(`segment-motion`, the fixture the goldens draw). The GL tests use
test_graph_faces' harness and skip without a standalone context."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from test_graph_faces import (
    Still,
    _fbo,
    _media,
    _px,
    _rgba,
)
from test_graph_resize import FACTORY_FRAME
from test_graph_wired import wired

from hyperspace import graph as G
from hyperspace import params, view
from hyperspace.media.frame import MediaFrame
from hyperspace.outputs import Switches, View
from hyperspace.render import SIZED_KEEP_FRAMES
from hyperspace.view import SegmentState

SEGMENT = {"kind": "segment"}
SEGMENT2 = {"kind": "segment", "instance": 2}
COMPOSITE = {"kind": "composite"}
CUT = {"kind": "cut"}
FIXTURE = Path(__file__).parent / "fixtures" / "presets" / "segment-motion.json"


def _read(*pairs, nodes=(SEGMENT,)):
    return G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=list(nodes)))


def _spec(*pairs, nodes=(SEGMENT,)):
    spec = _read(*pairs, nodes=nodes)
    assert not spec.notes, spec.notes
    return spec


def _views(n=2, size=(64, 48)):
    return [View(Switches(), size) for _ in range(n)]


# ---------------------------------------------------------------- the node and its entry

def test_the_segment_node_says_what_it_is():
    assert G.SegmentNode.KIND == "segment" and G.SegmentNode.TIMED
    assert G.SegmentNode.INPUTS == {"image": G.IMAGE} and G.SegmentNode.OUTPUT == G.MASK
    assert G.SegmentPin.INPUTS == {"segment": G.MASK} and G.SegmentPin.OUTPUT == G.IMAGE
    assert G.WIRED_MAKES["segment"] is None
    assert G.WIRED_TAKES["segment"] == {"image": G.IMAGE}
    for pin, typ in (("fg", G.IMAGE), ("bg", G.IMAGE), ("mask", G.MASK)):
        assert G.WIRED_MAKES[pin] == typ and G.WIRED_TAKES[pin] == {}
        for seg in ("segment", "segment.2"):
            name = f"{seg}.{pin}"
            assert G.wire_node_kind(name, wired=True) == pin
            assert G.pin_node(name) == seg and G.segment_pin(name) == (seg, pin)
    assert G.PINS["segment.fg"] == "segment" and G.PINS["segment.mask"] == "segment"
    assert "segment" in G.DECLARED and "segment" in G.RESERVED
    assert G.wire_node_kind("segment", wired=True) == "segment"
    assert G.wire_node_kind("segment.2", wired=True) == "segment"
    assert G.wire_node_kind("segment.1", wired=True) is None
    assert G.segment_pin("scene.depth") is None and G.segment_pin("segment") is None


def test_a_segment_entry_round_trips():
    for e in (SEGMENT, SEGMENT2):
        name = G.SegmentAt(e.get("instance", 1)).name
        spec = G.read_graph(wired(("channel.a", f"{name}.image"), nodes=[e]))
        assert spec.segments == (G.SegmentAt(e.get("instance", 1)),)
        assert G.read_graph(spec.to_json()).to_json() == spec.to_json()
        assert e in spec.to_json()["nodes"]
    with pytest.raises(G.GraphError):
        G.read_graph(wired(nodes=[{"kind": "segment", "instance": 0}]))
    with pytest.raises(G.GraphError):
        G.read_graph(wired(nodes=[{"kind": "segment", "mode": "motion"}]))   # a value


def test_a_segment_must_be_declared_and_its_pins_are_its():
    spec = _read(("channel.a", "segment.image"), ("segment.fg", "output.2.image"), nodes=())
    assert spec.notes and all('add one: {"kind": "segment"}' in n for n in spec.notes), \
        spec.notes
    spec = _read(("channel.a", "segment.2.image"), ("segment.2.bg", "output.2.image"))
    assert spec.notes and 'add one: {"kind": "segment"}' in spec.notes[0], spec.notes


def test_the_segment_makes_its_pictures_on_its_pins():
    spec = _read(("channel.a", "segment.image"), ("segment", "output.2.image"))
    assert spec.notes == (("wire segment → output.2.image — segment makes its pictures on "
                           "its pins: segment.fg (the foreground), segment.bg (the "
                           "background), segment.mask (the matte)"),)
    nodes = [SEGMENT, COMPOSITE, CUT, {"kind": "effect", "file": "acid", "instance": 2}]
    for src, dst in (("segment.fg", "composite.over"), ("segment.bg", "composite.under"),
                     ("segment.fg", "acid.2.image"), ("segment.mask", "cut.mask"),
                     ("segment.fg", "cut.image"), ("segment.mask", "output.2.image"),
                     ("segment.mask", "shape.faces")):
        spec = G.read_graph(wired(("channel.a", "segment.image"), (src, dst),
                                  ("cut", "output.3.image"), ("composite", "output.4.image"),
                                  ("acid.2", "output.5.image"), *FACTORY_FRAME, nodes=nodes))
        assert not [n for n in spec.notes if src in n], (src, dst, spec.notes)
    # a picture pin is never a mask
    spec = _read(("channel.a", "segment.image"), ("segment.fg", "lookback.cover"),
                 ("scene", "lookback.image"), ("lookback", "output.2.image"))
    assert spec.notes and "put a matte between" in spec.notes[0], spec.notes


# ---------------------------------------------------------------- the build

def test_the_pins_are_built_over_one_segment():
    spec = _spec(("channel.a", "segment.image"), ("segment.fg", "output.2.image"),
                 ("segment.bg", "output.3.image"), ("segment.mask", "output.4.image"))
    g = G.build_graph(_views(4), spec.wiring())
    seg = g.nodes["segment"]
    assert isinstance(seg, G.SegmentNode) and seg.inputs["image"] is g.nodes["channel.a"]
    fg, bg = g.nodes["segment.fg"], g.nodes["segment.bg"]
    assert isinstance(fg, G.SegmentPin) and fg.which == "fg" and fg.inputs["segment"] is seg
    assert isinstance(bg, G.SegmentPin) and bg.which == "bg" and bg.inputs["segment"] is seg
    # the matte into a picture port reads through its promotion
    pic = g.nodes["segment(picture)"]
    assert isinstance(pic, G.MaskPicture) and pic.inputs["mask"] is seg


def test_a_segment_no_wire_reaches_or_fed_nothing_is_not_built():
    spec = _spec(("channel.a", "segment.image"))
    g = G.build_graph(_views(), spec.wiring())
    assert "segment" not in g.nodes
    spec = _spec(("segment.fg", "output.2.image"))
    g = G.build_graph(_views(), spec.wiring())
    assert "segment" not in g.nodes and "segment.fg" not in g.nodes
    assert g.dormant["segment"] == "segment is fed by nothing here: wire its image"


def test_graph_py_never_imports_segment_py():
    import ast

    tree = ast.parse(Path(G.__file__).read_text())
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[-1]] + [a.name for a in node.names]
        elif isinstance(node, ast.Import):
            names = [a.name.split(".")[-1] for a in node.names]
        assert "segment" not in names and "Vision" not in names and "torch" not in names


def test_a_scene_through_a_segment_laid_over_keeps_its_see_through_ground():
    """As through an effect or a cut (T3's rule): a scene into a segment
    whose fg (or bg) is laid over clears see-through, so before a matte,
    off, or in the preview the under shows where the scene draws nothing."""
    for pin in ("fg", "bg"):
        spec = _spec(("scene", "segment.image"), (f"segment.{pin}", "composite.over"),
                     ("channel.c", "composite.under"), ("composite", "output.2.image"),
                     nodes=(SEGMENT, COMPOSITE))
        g = G.build_graph(_views(), spec.wiring())
        assert g.nodes["scene"].ground == 0.0, pin
    spec = _spec(("scene", "segment.2.image"), ("segment.2.fg", "composite.over"),
                 ("channel.c", "composite.under"), ("composite", "output.2.image"),
                 nodes=(SEGMENT2, COMPOSITE))
    assert G.build_graph(_views(), spec.wiring()).nodes["scene"].ground == 0.0
    # … not when its pins go straight to a window, nor through its mask
    spec = _spec(("scene", "segment.image"), ("segment.fg", "output.2.image"))
    assert G.build_graph(_views(), spec.wiring()).nodes["scene"].ground is None


def test_smooth_near_one_still_reaches_the_new_matte():
    """`segment.smooth` keeps the smoothed matte in float: at 0.99 a region
    that leaves (255 → 0) decays all the way to 0, and one that arrives to
    255 — never stalling short (a re-quantised 8-bit matte stalls at ~50)."""
    from types import SimpleNamespace

    class Tex:
        def __init__(self):
            self.data = b""

        def write(self, data, alignment=1):
            self.data = data

    tex = Tex()
    r = SimpleNamespace(_frame_target=lambda key, size, components=1: (tex, None))
    frame = SimpleNamespace(r=r)
    node = G.SegmentNode("segment")
    w = FakeWorker(np.full((2, 2), 255, np.uint8))
    st = SegmentState(smooth=0.99)
    node._pull(frame, w, st)
    assert tex.data == bytes([255] * 4)
    for _ in range(1000):
        w.set(np.zeros((2, 2), np.uint8))
        node._pull(frame, w, st)
    assert tex.data == bytes([0] * 4)
    for _ in range(1000):
        w.set(np.full((2, 2), 255, np.uint8))
        node._pull(frame, w, st)
    assert tex.data == bytes([255] * 4)


def test_the_canvas_knows_the_segment():
    from hyperspace import graphview

    assert graphview.LABELS["segment"] == "Segment" and graphview.HOVERS["segment"]
    assert graphview.FRAME_CLASS["segment"] is G.SegmentNode
    assert graphview.PICKER_GROUP["segment"] == "media"      # (plan 39 T5: W6's MEDIA)
    stand = graphview._stand_in("segment.2")
    assert isinstance(stand, G.SegmentNode) and stand.name == "segment.2"
    owner = graphview.OWNERS["segment"]
    assert owner("segment.2.mode", None) == "segment.2"
    assert owner("segment.feather", None) == "segment"
    assert graphview._node_name({"kind": "segment", "instance": 3}) == "segment.3"
    # its pins are drawn on its node (the scene's pins' rule), by their type
    pins = {pin: G.WIRED_MAKES[graphview.kind_of(pin)]
            for pin, owner in G.PINS.items() if owner == "segment"}
    assert pins == {"segment.fg": G.IMAGE, "segment.bg": G.IMAGE, "segment.mask": G.MASK}


# ---------------------------------------------------------------- the params

def test_declare_segments_comes_and_goes():
    reg = params.Registry()
    got = params.declare_segments(reg, ["segment", "segment.2"])
    ids = params.segment_ids("segment") + params.segment_ids("segment.2")
    assert sorted(got) == sorted(ids) and len(ids) == 14
    for pid in ids:
        assert reg[pid].group == params.SEGMENT_GROUP == "segment", pid
        assert params.is_segment_id(pid), pid
        key = pid.rpartition(".")[2]
        assert reg[pid].modulatable is (key not in ("mode", "quality")), pid
    st = SegmentState()
    assert (st.mode, st.quality, st.feather, st.smooth, st.on, st.sense, st.learn) == \
        (0, 0, 0.0, 0.0, True, 0.1, 3.0)
    assert reg["segment.mode"].choices == ["person", "motion", "subject"]
    assert reg["segment.quality"].choices == ["fast", "balanced", "accurate"]
    assert (reg["segment.feather"].lo, reg["segment.feather"].hi) == (0.0, 32.0)
    assert (reg["segment.learn"].lo, reg["segment.learn"].hi) == (0.1, 30.0)
    gone = params.declare_segments(reg, ["segment"])
    assert sorted(gone) == sorted(params.segment_ids("segment.2"))
    assert "segment.2" not in reg.segment_state
    reg["segment.smooth"].set(0.5)
    assert reg.segment_state["segment"].smooth == 0.5
    kept = reg.segment_state["segment"]
    assert params.declare_segments(reg, ["segment"]) == []
    assert reg.segment_state["segment"] is kept
    assert not params.is_segment_id("segment.1.on") and params.is_segment_id("segment.12.mode")
    groups = params.PERFORMANCE_GROUPS
    assert groups.index("segment") == groups.index("cut") + 1


def test_the_registry_writes_the_view_states_segments():
    from types import SimpleNamespace

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control

    v = view.ViewState()
    assert v.segments == {}
    chain = Analyzer(Analyser())
    reg = params.build_registry(v, Control(chain), SimpleNamespace(chain=chain))
    assert reg.segment_state is v.segments
    params.declare_segments(reg, ["segment"])
    reg["segment.mode"].set(1)
    assert v.segments["segment"].mode == 1


def test_the_fixture_saves_and_loads_as_seven(tmp_path):
    """`segment-motion` (a `/7` wired frame with a segment and a composite
    and their values), loaded, saved and loaded into a fresh rig, lands the
    same `GraphSpec` and the same segment values, and saves `/7`."""
    from test_presets import boot

    src = json.loads(FIXTURE.read_text())
    assert src["schema"] == "hyperspace.preset/7"
    spec, saved = None, None
    for home in (tmp_path / "a", tmp_path / "b"):
        (home / "presets").mkdir(parents=True, exist_ok=True)
        (home / "presets" / FIXTURE.name).write_text(saved or FIXTURE.read_text())
        r = boot(home)
        r.presets.load("segment-motion")
        got = r.presets.graph.spec
        assert got is not None and got.wired and not got.notes
        assert got.segments == (G.SegmentAt(1),)
        assert [n for n in r.presets.notes if n.startswith("graph:")] == []
        assert r.reg["segment.mode"].value == 1
        assert r.reg["segment.feather"].value == pytest.approx(2.0)
        assert r.reg["segment.learn"].value == pytest.approx(3.0)
        if spec is not None:
            assert got == spec
        spec = got
        saved = r.presets.save_as("segment-motion").read_text()
        doc = json.loads(saved)
        assert doc["schema"] == "hyperspace.preset/7"
        assert {"kind": "segment"} in doc["graph"]["nodes"]
        assert doc["values"]["segment.mode"] == 1


def test_a_new_preset_holds_no_segment_values(tmp_path):
    from test_presets import boot

    home = tmp_path / "h"
    (home / "presets").mkdir(parents=True)
    (home / "presets" / FIXTURE.name).write_text(FIXTURE.read_text())
    r = boot(home)
    r.presets.load("segment-motion")
    r.presets.new()
    doc = json.loads(r.presets.save_as("fresh").read_text())
    assert not [k for k in doc["values"] if params.is_segment_id(k)]


# ---------------------------------------------------------------- GL
moderngl = pytest.importorskip("moderngl")

SIZE = (64, 48)
COLOUR = (200, 100, 50)
BLUE = (0, 0, 255)


class FakeWorker:
    """The worker's shape (segment.SegmentWorker) with a matte the test
    sets: what it was fed, by index and quality, and whether it is closed."""

    def __init__(self, result: np.ndarray | None = None):
        self.submits: list[tuple[np.ndarray, int, str]] = []
        self.error = ""
        self.closed = False
        self.index = 0
        self.result = None
        if result is not None:
            self.set(result)

    def set(self, mask: np.ndarray) -> None:
        self.index += 1
        self.result = (mask, self.index, (mask.shape[1], mask.shape[0]))

    def wants(self) -> bool:
        return not self.closed

    def input_size(self, src, quality=None):
        return (32, 24)

    def submit(self, frame, index, quality=None):
        self.submits.append((np.array(frame), index, quality))

    def latest(self):
        return self.result

    def said(self) -> str:
        return self.error or ("fake fast" if self.result else "waiting for fake fast")

    def stop(self) -> None:
        self.closed = True

    def close(self, timeout: float = 1.0) -> None:
        self.closed = True

    alive = False


def _left(w=32, h=24) -> np.ndarray:
    """A matte passing the left half (rows top first, as a worker's)."""
    m = np.zeros((h, w), np.uint8)
    m[:, : w // 2] = 255
    return m


def _top(w=32, h=24) -> np.ndarray:
    """A matte passing the top half, rows top first (the orientation's)."""
    m = np.zeros((h, w), np.uint8)
    m[: h // 2] = 255
    return m


def _renderer(ctx, media, pairs, nodes=(SEGMENT,), worker=None, cfg=None):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    made: list[str] = []
    if worker is not None:
        r.segment_cfg = {} if cfg is None else cfg

        def factory(c, name):
            made.append(name)
            return worker

        r.segment_factory = factory
    r.made = made
    spec = G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=list(nodes)),
                        effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    return r


def _s(**seg) -> view.ViewState:
    from hyperspace.view import ViewState

    return ViewState(lines=False, points=False, faces=False,
                     segments={"segment": SegmentState(**seg)})


def _draw(ctx, r, s, size=SIZE, n=2, t=2.0, views=None):
    vs = views or [View(Switches(), size, target=_fbo(ctx, *size)) for _ in range(n)]
    r.draw_outputs(s, *size, 1.0, vs, t_now=t)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target) for v in vs]


def _sources(**over):
    got = {"a": Still(_rgba(*SIZE, COLOUR)), "c": Still(_rgba(*SIZE, BLUE))}
    got.update(over)
    return _media(**{k: v for k, v in got.items() if v is not None})


def _lr(px):
    h, w = px.shape[:2]
    return px[h // 2, w // 4], px[h // 2, 3 * w // 4]


def _tb(px):
    h, w = px.shape[:2]
    return px[h // 4, w // 2], px[3 * h // 4, w // 2]


PINS3 = [("channel.a", "segment.image"), ("segment.fg", "output.2.image"),
         ("segment.bg", "output.3.image"), ("segment.mask", "output.4.image")]


def test_before_the_first_matte_fg_is_the_picture_whole(ctx):
    w = FakeWorker()
    r = _renderer(ctx, _sources(), PINS3, worker=w)
    _, fg, bg, mask = _draw(ctx, r, _s(), n=4)
    assert tuple(_lr(fg)[0][:3]) == COLOUR and tuple(_lr(fg)[1][:3]) == COLOUR
    assert tuple(bg[24, 32][:3]) == (0, 0, 0) and tuple(mask[24, 32][:3]) == (0, 0, 0)
    seg = r._graph.nodes["segment"]
    assert seg.said == "waiting for fake fast: its picture through, whole until the first matte"
    assert r.made == ["segment"] and len(w.submits) == 1


def test_fg_bg_and_mask_from_a_known_matte(ctx):
    w = FakeWorker(_left())
    pairs = [*PINS3, ("segment.fg", "composite.over"), ("channel.c", "composite.under"),
             ("composite", "output.5.image")]
    r = _renderer(ctx, _sources(), pairs, nodes=(SEGMENT, COMPOSITE), worker=w)
    _, fg, bg, mask, comp = _draw(ctx, r, _s(), n=5)
    left, right = _lr(fg)
    assert tuple(left[:3]) == COLOUR and tuple(right[:3]) == (0, 0, 0)
    left, right = _lr(bg)
    assert tuple(left[:3]) == (0, 0, 0) and tuple(right[:3]) == COLOUR
    left, right = _lr(mask)                     # the matte promoted: white where it passes
    assert tuple(left[:3]) == (255, 255, 255) and tuple(right[:3]) == (0, 0, 0)
    left, right = _lr(comp)                     # the foreground over what is under
    assert tuple(left[:3]) == COLOUR and tuple(right[:3]) == BLUE
    assert r._graph.nodes["segment"].said == "fake fast"
    # the fg's own picture is cut to transparent where the matte does not pass
    tex = r._frames["segment.fg#cut"][0]
    alpha = np.frombuffer(tex.read(), np.uint8).reshape(SIZE[1], SIZE[0], 4)[::-1, :, 3]
    assert alpha[24, 10] == 255 and alpha[24, 54] == 0


def test_the_shortcut_for_a_channel_with_pixels_and_the_readback_for_one_without(ctx):
    """A channel fitted by cover whose frame has CPU pixels is handed over
    as it is (no readback); one fitted otherwise — or any other picture —
    is downsampled and read back once, rows turned top first. A count on
    each path."""
    px = _rgba(*SIZE, (20, 20, 20))
    px[:24, :32, :3] = 230                      # bright top-left quarter, rows top first
    w = FakeWorker()
    media = _sources(a=Still(px))
    r = _renderer(ctx, media, [("channel.a", "segment.image"),
                               ("segment.fg", "output.2.image")], worker=w)
    _draw(ctx, r, _s())
    seg = r._graph.nodes["segment"]
    assert seg.taken == {"shortcut": 1, "readback": 0}
    frame, index, quality = w.submits[0]
    assert frame.shape == (48, 64, 4) and quality == "fast" and index == 1
    assert (frame == px).all()                  # the channel's own array
    # the same frame again: not moved, not fed
    _draw(ctx, r, _s(), t=2.1)
    assert len(w.submits) == 1
    # a new level is a new input for the model
    _draw(ctx, r, _s(quality=1), t=2.2)
    assert len(w.submits) == 2 and w.submits[1][2] == "balanced"
    # fitted by stretch: the readback, at the worker's input size, top first
    media.channels["a"].fit = 2
    w2 = FakeWorker()
    r2 = _renderer(ctx, media, [("channel.a", "segment.image"),
                                ("segment.fg", "output.2.image")], worker=w2)
    _draw(ctx, r2, _s())
    assert r2._graph.nodes["segment"].taken == {"shortcut": 0, "readback": 1}
    frame = w2.submits[0][0]
    assert frame.shape == (24, 32, 4)
    assert frame[4, 4, 0] > 200 and frame[20, 4, 0] < 60 and frame[4, 28, 0] < 60
    # a picture that is no channel: read back every frame the worker would take
    w3 = FakeWorker()
    r3 = _renderer(ctx, media, [("scene", "segment.image"), ("segment.fg", "output.2.image")],
                   worker=w3)
    _draw(ctx, r3, _s())
    _draw(ctx, r3, _s(), t=2.1)
    assert r3._graph.nodes["segment"].taken == {"shortcut": 0, "readback": 2}
    assert len(w3.submits) == 2 and w3.submits[1][0].shape == (24, 32, 4)


def test_a_rows_top_first_matte_lands_the_right_way_up_everywhere(ctx):
    """The orientation risk (spec "Risks"): a worker's matte passing its
    top half (its array's first rows) keeps the top half of the picture on
    a cut, shows white at the top on a window (the promotion), and is bound
    the right way up into `lookback.cover` (the mask port's refit)."""
    w = FakeWorker(_top())
    pairs = [("channel.a", "segment.image"), ("segment.fg", "output.2.image"),
             ("segment.mask", "output.3.image"), ("channel.a", "cut.image"),
             ("segment.mask", "cut.mask"), ("cut", "output.4.image"),
             ("scene", "lookback.image"), ("segment.mask", "lookback.cover"),
             ("lookback", "output.5.image")]
    r = _renderer(ctx, _sources(), pairs, nodes=(SEGMENT, CUT), worker=w)
    _, fg, mask, cut, _ = _draw(ctx, r, _s(), n=5)
    top, bottom = _tb(fg)
    assert tuple(top[:3]) == COLOUR and tuple(bottom[:3]) == (0, 0, 0)
    top, bottom = _tb(mask)
    assert tuple(top[:3]) == (255, 255, 255) and tuple(bottom[:3]) == (0, 0, 0)
    top, bottom = _tb(cut)
    assert tuple(top[:3]) == COLOUR and tuple(bottom[:3]) == (0, 0, 0)
    seg = r._graph.nodes["segment"]
    assert r._graph.nodes["lookback"].inputs["cover"] is seg
    tex = r._frames["segment#fit"][0]           # what lookback.cover binds
    assert tex.size == SIZE and tex.components == 1
    rows = np.frombuffer(tex.read(), np.uint8).reshape(SIZE[1], SIZE[0])[::-1]  # top first
    assert rows[10, 32] == 255 and rows[38, 32] == 0


def test_on_off_idles_the_worker_and_passes_the_picture_whole(ctx):
    w = FakeWorker(_left())
    r = _renderer(ctx, _sources(), PINS3, worker=w)
    _, fg, bg, _ = _draw(ctx, r, _s(on=False), n=4)
    assert w.submits == []
    assert tuple(_lr(fg)[1][:3]) == COLOUR and tuple(bg[24, 32][:3]) == (0, 0, 0)
    assert r._graph.nodes["segment"].said == \
        "off: its picture through, whole, the worker idle"


def test_a_scene_through_a_segment_turned_off_shows_the_under(ctx):
    """The review's case: scene → segment (off) → fg → composite.over, a
    colour under — the scene draws nothing here, so the under shows."""
    w = FakeWorker(_left())
    pairs = [("scene", "segment.image"), ("segment.fg", "composite.over"),
             ("channel.c", "composite.under"), ("composite", "output.2.image")]
    r = _renderer(ctx, _sources(), pairs, nodes=(SEGMENT, COMPOSITE), worker=w)
    _, out = _draw(ctx, r, _s(on=False))
    left, right = _lr(out)
    assert tuple(left[:3]) == BLUE and tuple(right[:3]) == BLUE


def test_subject_is_refused_in_words(ctx):
    w = FakeWorker(_left())
    r = _renderer(ctx, _sources(), PINS3, worker=w)
    _, fg, _, _ = _draw(ctx, r, _s(mode=2), n=4)
    assert w.submits == [] and tuple(_lr(fg)[1][:3]) == COLOUR
    assert r._graph.nodes["segment"].said.startswith("subject is not in this build")


def test_an_error_mid_show_passes_the_picture_whole_and_says_it(ctx):
    w = FakeWorker(_left())
    r = _renderer(ctx, _sources(), PINS3, worker=w)
    w.error = "Vision: RuntimeError: the Neural Engine is busy"
    _, fg, bg, _ = _draw(ctx, r, _s(), n=4)
    assert tuple(_lr(fg)[1][:3]) == COLOUR and tuple(bg[24, 48][:3]) == (0, 0, 0)
    assert r._graph.nodes["segment"].said.startswith("Vision: RuntimeError")
    w.error = ""
    _, fg, _, _ = _draw(ctx, r, _s(), n=4, t=2.1)
    assert tuple(_lr(fg)[1][:3]) == (0, 0, 0)    # cut again


def test_a_channel_with_no_frame_says_so(ctx):
    w = FakeWorker(_left())
    still = Still(_rgba(*SIZE, COLOUR))
    still.gone = True
    r = _renderer(ctx, _sources(a=still), PINS3, worker=w)
    _draw(ctx, r, _s(), n=4)
    assert r._graph.nodes["segment"].said == "no frame on channel a: its picture through, whole"
    assert w.submits == []


def test_a_removed_node_closes_its_worker(ctx):
    w = FakeWorker(_left())
    media = _sources()
    r = _renderer(ctx, media, PINS3, worker=w)
    _draw(ctx, r, _s(), n=4)
    assert "segment" in r._segmenters and not w.closed
    spec = G.read_graph(wired(("channel.a", "output.2.image"), *FACTORY_FRAME),
                        effects=set(r.fx.state.specs))
    r.wiring = spec.wiring()
    for k in range(SIZED_KEEP_FRAMES):
        _draw(ctx, r, _s(), n=2, t=3.0 + k / 60)
    assert w.closed and "segment" not in r._segmenters


def test_several_segments_are_several_workers(ctx):
    """AJ.8's headless line: two segment nodes, two workers, each by its
    node's name, each fed its own channel."""
    made: dict[str, FakeWorker] = {}
    media = _sources()
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    r.segment_cfg = {}
    r.segment_factory = lambda cfg, name: made.setdefault(name, FakeWorker())
    spec = G.read_graph(wired(("channel.a", "segment.image"), ("channel.c", "segment.2.image"),
                              ("segment.fg", "output.2.image"),
                              ("segment.2.fg", "output.3.image"), *FACTORY_FRAME,
                              nodes=[SEGMENT, SEGMENT2]), effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    s = _s()
    s.segments["segment.2"] = SegmentState()
    _draw(ctx, r, s, n=3)
    assert sorted(made) == ["segment", "segment.2"] and made["segment"] is not made["segment.2"]
    assert tuple(made["segment"].submits[0][0][0, 0, :3]) == COLOUR
    assert tuple(made["segment.2"].submits[0][0][0, 0, :3]) == BLUE
    r.close()
    assert all(w.closed for w in made.values())


def test_the_preview_runs_no_worker_and_closing_it_leaves_the_programs(ctx):
    """Plan 38's seam: a second renderer on the same context with no
    `segment_cfg` (as `hold.mirror` makes the preview) builds the same
    graph, its segment passing its picture through and saying why, with no
    worker made; closing it leaves the program renderer's worker alive."""
    w = FakeWorker(_left())
    media = _sources()
    program = _renderer(ctx, media, PINS3, worker=w)
    _draw(ctx, program, _s(), n=4)
    preview = _renderer(ctx, media, PINS3)
    assert preview.segment_cfg is None
    _, fg, bg, _ = _draw(ctx, preview, _s(), n=4)
    assert tuple(_lr(fg)[1][:3]) == COLOUR and tuple(bg[24, 32][:3]) == (0, 0, 0)
    assert preview._graph.nodes["segment"].said == \
        "no worker in the preview: its picture through, whole"
    assert preview._segmenters == {} and preview.segmenter("segment") is None
    preview.close()
    assert not w.closed and program._segmenters["segment"] is w
    program.close()
    assert w.closed and program._segmenters == {}


def test_motion_on_two_stills_makes_the_moved_region_foreground(ctx):
    """Motion mode needs no worker: the first frame is learnt whole (no
    foreground), and on the second still the square that moved is the
    foreground — the rest, unchanged, is cut away."""
    first = _rgba(*SIZE, (40, 40, 40))
    still = Still(first)
    media = _sources(a=still)
    r = _renderer(ctx, media, [("channel.a", "segment.image"),
                               ("segment.fg", "output.2.image"),
                               ("segment.mask", "output.3.image")])
    _, fg, mask = _draw(ctx, r, _s(mode=1), n=3)
    assert (mask[..., :3] == 0).all() and (fg[..., :3] == 0).all()
    assert r.made == []                          # (no worker in motion mode)
    second = first.copy()
    second[8:20, 8:20, :3] = 220                 # a square appears top-left
    still.f = MediaFrame(second, 2.0, 1)
    _, fg, mask = _draw(ctx, r, _s(mode=1), n=3, t=2.0 + 1 / 60)
    assert tuple(fg[14, 14][:3]) == (220, 220, 220) and tuple(fg[36, 50][:3]) == (0, 0, 0)
    assert tuple(mask[14, 14][:3]) == (255, 255, 255) and tuple(mask[36, 50][:3]) == (0, 0, 0)
    seg = r._graph.nodes["segment"]
    assert seg.said == "64×48 · motion · sense 0.10 · learns in 3 s"
    # (motion's matte is a GL pass's, the right way up; a worker's is its array's)
    from types import SimpleNamespace

    assert seg.rows_top_first(SimpleNamespace(segments={"segment": SegmentState(mode=1)})) \
        is False
    assert seg.rows_top_first(SimpleNamespace(segments={"segment": SegmentState()})) is True
    # a still that stays still fades into the background at the learn rate
    s = _s(mode=1, learn=0.1)
    for k in range(2, 40):
        _, fg, mask = _draw(ctx, r, s, n=3, t=2.0 + k * 0.05)
    assert tuple(mask[14, 14][:3]) == (0, 0, 0)
