"""Plan 66 stage 3a — Time Displace (`shaders/fx/timedisplace.glsl`, its
Python half `timedisplace.py`): each pixel reads a look-back's past at
`now − field × Span`.

What it must keep honest:

- Span 0 is its input, byte for byte, and so is a field of 0 (the edge a
  line ramp starts at), so a lane on Span fades it in from nothing;
- the flat field at a frame's age shows that frame: the echo node is the
  constant field; between two frames it blends them by time, or takes the
  nearer; older than the ring holds, the oldest;
- a line ramp is the slit-scan: now at one edge, Span ago at the other;
- the aux's brightness is the field: black now, white Span ago;
- with nothing to read (no rings on its chain, no look-back of that number,
  a ring with nothing in it, one being remade) it is its input;
- the renderer hands its chain its own rings, so the effect in a real graph
  reads the look-back that graph records.

The GL tests skip without a standalone context."""

from __future__ import annotations

import numpy as np
import pytest

from hyperspace import lookback, timedisplace
from hyperspace.fx import FxChain, FxState
from hyperspace.lookback import Lookback

moderngl = pytest.importorskip("moderngl")

W, H = 64, 48
NOW = 10.0                       # the ring's clock when a pass runs
NAME = "timedisplace"
# (colour, age in seconds) of the frames written into the ring, newest first
RING = (((0, 0, 255), 0.25), ((0, 255, 0), 0.5), ((255, 0, 0), 1.0))
GREY = (128, 128, 128)


def _flat(rgb, w=W, h=H) -> np.ndarray:
    pic = np.zeros((h, w, 4), np.uint8)
    pic[...] = (*rgb, 255)
    return pic


def _ring(ctx, frames=RING) -> Lookback:
    """A ring at the test's size holding `frames` (colour, age) at NOW."""
    lb = Lookback(ctx)
    assert lb._ensure(W, H)
    ew, eh = lb.echo
    for slot, (rgb, age) in enumerate(reversed(frames)):
        lb.write_slot(slot, _flat(rgb, ew, eh), at=NOW - age)
    lb.clock, lb._ticked = NOW, True
    return lb


def _pass(ctx, rings, picture=None, aux=None, t=0.0, **values) -> np.ndarray:
    st = FxState()
    st.values[NAME].update(on=True, mix=1.0, **values)
    chain = FxChain(ctx, st)
    chain.rings = rings
    src = ctx.texture((W, H), 4, (picture if picture is not None else _flat(GREY)).tobytes())
    aux_tex = ctx.texture((W, H), 4, aux.tobytes()) if aux is not None else None
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    chain.run_one(NAME, src, out, t, opaque=1, aux=aux_tex)
    assert ctx.error == "GL_NO_ERROR"
    assert chain.errors == {} and st.errors == {}
    px = np.frombuffer(out.read(components=4), np.uint8).reshape(H, W, 4).copy()
    for o in (src, out, aux_tex):
        if o is not None:
            o.release()
    return px


def _mid(px) -> tuple[int, ...]:
    return tuple(int(c) for c in px[H // 2, W // 2, :3])


def _near(a, b, d=2) -> bool:
    return all(abs(int(x) - int(y)) <= d for x, y in zip(a, b, strict=True))


def _speckle() -> np.ndarray:
    pic = np.random.default_rng(3).integers(0, 256, (H, W, 4), dtype=np.uint8)
    pic[..., 3] = 255
    return pic


# ---------------------------------------------------------------- without GL

def test_the_hook_holds_the_rings_slot_count_and_names_the_look_backs():
    assert timedisplace.MAX_ECHOES == lookback.MAX_ECHOES
    assert timedisplace.ring_name(1) == "lookback"
    assert timedisplace.ring_name(3) == "lookback.3"
    assert timedisplace.ring_name(0) == "lookback"


def test_the_file_is_hooked_reads_its_aux_and_declares_its_knobs():
    spec = FxState().specs[NAME]
    assert spec.hook == "timedisplace" and spec.aux
    keys = {p.key: p for p in spec.params}
    assert keys["span"].amount and keys["span"].lo == 0.0
    # the ring holds 32 captures at most 0.25 s apart: Span reaches all of it
    assert keys["span"].hi == lookback.MAX_ECHOES * lookback.GAP_HI
    assert keys["shape"].choices == ("line", "rings", "spokes", "flat", "aux")
    assert keys["ring"].integer and (keys["ring"].lo, keys["ring"].hi) == (1, 8)
    assert [c.uniform for c in spec.clocks] == ["u_drift_t"]


def test_with_no_rings_on_its_chain_nothing_is_found():
    class Chain:
        rings = None
    assert timedisplace.ring_of(Chain(), {"ring": 1}) is None
    Chain.rings = {"lookback": "ring one"}
    assert timedisplace.ring_of(Chain(), {"ring": 1}) == "ring one"
    assert timedisplace.ring_of(Chain(), {"ring": 2}) is None
    assert timedisplace.frames_of(None) == []


# ---------------------------------------------------------------- the ring

def test_a_ring_lists_every_frame_it_holds_newest_first(ctx):
    """Not only the `echoes` the trail composites: all of them."""
    lb = _ring(ctx)
    lb.state.echoes = 1
    got = lb.frames()
    assert [round(a, 6) for _, a in got] == [0.25, 0.5, 1.0]
    assert len(lb.layers()) == 1
    lb.release_ring()


# ---------------------------------------------------------------- the pass

def test_span_zero_is_its_input_byte_for_byte(ctx):
    pic = _speckle()
    lb = _ring(ctx)
    for shape in range(5):
        got = _pass(ctx, {"lookback": lb}, pic, span=0.0, shape=shape)
        assert np.array_equal(got, pic), shape
    lb.release_ring()


def test_with_nothing_to_read_it_is_its_input(ctx):
    pic = _speckle()
    lb = _ring(ctx)
    assert np.array_equal(_pass(ctx, None, pic, shape=3), pic)             # a chain of its own
    assert np.array_equal(_pass(ctx, {"lookback": lb}, pic, shape=3, ring=2), pic)
    empty = Lookback(ctx)
    assert empty._ensure(W, H)
    assert np.array_equal(_pass(ctx, {"lookback": empty}, pic, shape=3), pic)
    lb.release_ring()
    empty.release_ring()


def test_a_ring_being_remade_reads_nothing(ctx):
    pic = _speckle()
    lb = _ring(ctx)
    lb._made_for = (W, H)
    lb.state.res = 0 if lb.state.res != 0 else 3       # another size: remade next capture
    assert lb.remaking()
    assert np.array_equal(_pass(ctx, {"lookback": lb}, pic, shape=3), pic)
    lb.release_ring()


@pytest.mark.parametrize("k", range(len(RING)))
def test_the_flat_field_at_a_frames_age_shows_that_frame(ctx, k):
    """The echo node is the constant field."""
    lb = _ring(ctx)
    rgb, age = RING[k]
    got = _pass(ctx, {"lookback": lb}, shape=3, span=age)
    assert _near(_mid(got), rgb), (_mid(got), rgb)
    assert np.abs(got[..., :3].astype(int) - np.array(rgb)).max() <= 2
    lb.release_ring()


def test_between_two_frames_it_blends_by_time_or_takes_the_nearer(ctx):
    lb = _ring(ctx)
    blue, green = RING[0][0], RING[1][0]
    half = _pass(ctx, {"lookback": lb}, shape=3, span=0.375)
    assert _near(_mid(half), tuple((a + b) / 2 for a, b in zip(blue, green, strict=True)))
    near = _pass(ctx, {"lookback": lb}, shape=3, span=0.45, between=1)
    assert _near(_mid(near), green)
    near = _pass(ctx, {"lookback": lb}, shape=3, span=0.3, between=1)
    assert _near(_mid(near), blue)
    lb.release_ring()


def test_between_now_and_the_newest_frame_it_blends_its_input(ctx):
    lb = _ring(ctx)
    got = _pass(ctx, {"lookback": lb}, _flat((0, 0, 0)), shape=3, span=0.125)
    assert _near(_mid(got), (0, 0, 128))
    lb.release_ring()


def test_older_than_the_ring_holds_is_its_oldest(ctx):
    lb = _ring(ctx)
    got = _pass(ctx, {"lookback": lb}, shape=3, span=8.0)
    assert _near(_mid(got), RING[-1][0])
    lb.release_ring()


def test_a_line_is_the_slit_scan_now_at_one_edge_the_past_at_the_other(ctx):
    """Angle 0: the left edge is now (its input), the right edge Span ago;
    a quarter turn: the bottom now, the top Span ago (y up)."""
    lb = _ring(ctx)
    got = _pass(ctx, {"lookback": lb}, _flat(GREY), shape=0, span=1.0)
    assert _near(tuple(got[H // 2, 0, :3]), GREY, 8)
    assert _near(tuple(got[H // 2, W - 1, :3]), RING[-1][0], 12)
    # every column along the ramp is one moment: the rows agree
    assert np.abs(got[0, :, :3].astype(int) - got[H - 1, :, :3].astype(int)).max() <= 1
    up = _pass(ctx, {"lookback": lb}, _flat(GREY), shape=0, span=1.0, angle=np.pi / 2)
    assert _near(tuple(up[0, W // 2, :3]), GREY, 8)          # GL row 0 is the bottom
    assert _near(tuple(up[H - 1, W // 2, :3]), RING[-1][0], 12)
    flip = _pass(ctx, {"lookback": lb}, _flat(GREY), shape=0, span=1.0, flip=1)
    assert _near(tuple(flip[H // 2, 0, :3]), RING[-1][0], 12)
    lb.release_ring()


def test_steps_and_nearest_make_hard_bands(ctx):
    lb = _ring(ctx)
    got = _pass(ctx, {"lookback": lb}, _flat(GREY), shape=0, span=1.0, steps=2, between=1)
    colours = {tuple(int(c) for c in got[H // 2, x, :3]) for x in range(W)}
    assert colours <= {GREY, RING[1][0], RING[2][0]}, colours
    assert len(colours) == 3
    lb.release_ring()


def test_rings_run_from_now_at_the_centre(ctx):
    lb = _ring(ctx)
    got = _pass(ctx, {"lookback": lb}, _flat(GREY), shape=1, span=1.0)
    assert _near(_mid(got), GREY, 12)
    corner = tuple(int(c) for c in got[0, 0, :3])
    assert _near(corner, RING[-1][0], 30), corner
    lb.release_ring()


def test_the_aux_brightness_is_the_field(ctx):
    """Black now, white Span ago: the left half of the aux black, the right white."""
    lb = _ring(ctx)
    aux = _flat((0, 0, 0))
    aux[:, W // 2:, :3] = 255
    got = _pass(ctx, {"lookback": lb}, _flat(GREY), aux=aux, shape=4, span=1.0)
    assert _near(tuple(got[H // 2, 4, :3]), GREY)
    assert _near(tuple(got[H // 2, W - 4, :3]), RING[-1][0])
    lb.release_ring()


def test_drift_sweeps_the_ramp(ctx):
    """One pass a quarter second after another at Drift 1: the line has moved."""
    lb = _ring(ctx)
    st = FxState()
    st.values[NAME].update(on=True, mix=1.0, shape=0, span=1.0, drift=1.0)
    chain = FxChain(ctx, st)
    chain.rings = {"lookback": lb}
    src = ctx.texture((W, H), 4, _flat(GREY).tobytes())
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    shots = []
    for t in (0.0, 0.25):
        chain.run_one(NAME, src, out, t, opaque=1)
        shots.append(np.frombuffer(out.read(components=4), np.uint8).reshape(H, W, 4).copy())
    assert np.abs(shots[0].astype(int) - shots[1].astype(int)).max() > 40
    lb.release_ring()


# ---------------------------------------------------------------- in the renderer

def test_the_renderer_hands_its_chain_its_rings(ctx):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    assert r.fx.rings is r.rings
    two = r.ring("lookback.2")
    assert r.fx.rings["lookback.2"] is two


def test_in_a_graph_it_reads_the_look_back_that_graph_records(ctx):
    """A wired frame: the look-back recording (an echo read keeps its ring),
    Time Displace on the frame into output 2. With frames written by hand
    and the clock set, the flat field past the ring's oldest shows red; at
    Span 0 the output is the frame, not red."""
    from test_graph_faces import _draw, _empty, _fbo, _renderer

    from hyperspace.outputs import Switches, View

    nodes = [{"kind": "echo", "index": 1}, {"kind": "effect", "file": NAME}]
    pairs = [("frame", f"{NAME}.image"), (NAME, "output.2.image"),
             ("echo.1", "output.1.image")]
    size = (160, 120)

    def frame(span):
        r = _renderer(ctx, None, pairs, nodes,
                      values={NAME: {"on": True, "mix": 1.0, "shape": 3, "span": span}})
        r.lookback.state.on, r.lookback.state.gap = False, 0.0
        lb = r.lookback
        assert lb._ensure(*size)
        ew, eh = lb.echo
        lb.write_slot(0, _flat((255, 0, 0), ew, eh), at=-5.0)
        lb.write_slot(1, _flat((0, 0, 255), ew, eh), at=-4.0)
        vs = [View(Switches(), size, target=_fbo(ctx, *size)) for _ in range(2)]
        got = _draw(ctx, r, _empty(), size, vs)[1]
        assert NAME in r._graph.nodes
        return got

    past = frame(8.0)
    h, w = past.shape[:2]
    assert _near(tuple(int(c) for c in past[h // 2, w // 2, :3]), (255, 0, 0)), past[h // 2, w // 2]
    now = frame(0.0)
    assert not _near(tuple(int(c) for c in now[h // 2, w // 2, :3]), (255, 0, 0))
