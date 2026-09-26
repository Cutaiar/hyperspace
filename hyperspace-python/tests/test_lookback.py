"""WP6a — the look-back core: history ring, age-weighted composite, the
dream slot's copy path, the dream.* params and their presets, the page.

Everything runs offscreen on a standalone GL context (skipped where there
is none). The composite is checked against a numpy transcription of the
shader's math at the echo's own size, so sampling is one-to-one and the
only tolerance is 8-bit rounding.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

from hyperspace.lookback import (
    MAX_ECHOES,
    RES,
    DreamState,
    LookbackSource,
    NullSource,
    echo_size,
)
from hyperspace.render import Renderer, ViewState

VIEW = {"ang": [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], "yaw": 0.4, "pitch": 0.25}


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


class Rig:
    """A renderer on an RGBA texture target of size (w, h), read back as arrays."""

    def __init__(self, ctx, w, h, bg_alpha=1.0, dream=None):
        self.ctx, self.w, self.h = ctx, w, h
        self.tex = ctx.texture((w, h), 4)
        self.fbo = ctx.framebuffer(color_attachments=[self.tex])
        self.r = Renderer(ctx, dream)
        self.r.bg_alpha = bg_alpha
        self.lb = self.r.lookback
        self.s = ViewState(shape=3, ang=list(VIEW["ang"]), yaw=VIEW["yaw"], pitch=VIEW["pitch"])

    def frame(self, t=0.0):
        self.fbo.use()
        self.ctx.viewport = (0, 0, self.w, self.h)
        self.r.draw(self.s, self.w, self.h, t_now=t)
        self.s.ang[3] += 0.03

    def read(self):
        return np.frombuffer(self.fbo.read(components=4), dtype=np.uint8).reshape(
            self.h, self.w, 4).copy()

    def scene(self):
        """The scene texture as the post pass sees it."""
        return np.frombuffer(self.r.scene.fbo.read(components=4), dtype=np.uint8).reshape(
            self.h, self.w, 4).copy()

    def release(self):
        self.fbo.release()
        self.tex.release()


# ---------------------------------------------------------------- the ring

def test_echo_size_keeps_aspect():
    assert echo_size(256, 1280, 820) == (400, 256)
    assert echo_size(256, 820, 1280) == (256, 400)
    assert echo_size(128, 1920, 1080) == (224, 128)
    assert echo_size(256, 256, 256) == (256, 256)


def test_ring_depth_and_age(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=4, every=1, res=0))
    lb = rig.lb
    assert lb.layers() == []
    for _ in range(3):
        rig.frame()
    # three captures, aged against the frame about to be drawn: 3, 2, 1
    assert lb.frame == 3
    assert [age for _, age in lb.layers()] == [3, 2, 1]
    for _ in range(5):
        rig.frame()
    # the ring holds the newest `echoes`, oldest first
    assert [age for _, age in lb.layers()] == [4, 3, 2, 1]
    slots = [slot for slot, _ in lb.layers()]
    assert len(set(slots)) == 4 and all(0 <= s < MAX_ECHOES for s in slots)
    # weights are echo_mix · decay^age
    lb.state.echo_mix, lb.state.decay = 0.5, 0.8
    assert [w for _, w in lb.weights()] == pytest.approx([0.5 * 0.8 ** a for a in (4, 3, 2, 1)])
    # a shallower ring drops the oldest; zero composites nothing
    lb.state.echoes = 2
    assert [age for _, age in lb.layers()] == [2, 1]
    lb.state.echoes = 0
    assert lb.layers() == []
    rig.release()


def test_capture_cadence(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=8, every=3, res=0))
    for _ in range(9):
        rig.frame()
    # captures land on frames 3, 6, 9 → ages 7, 4, 1 against frame 10
    assert [age for _, age in rig.lb.layers()] == [7, 4, 1]
    rig.release()


def test_off_forgets_the_history(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=4, every=1, res=0))
    for _ in range(4):
        rig.frame()
    assert len(rig.lb.layers()) == 4
    rig.lb.state.on = False
    rig.frame()
    assert rig.lb.layers() == []
    rig.lb.state.on = True
    rig.frame()
    assert [age for _, age in rig.lb.layers()] == [1]
    rig.release()


def test_res_rebuilds_the_atlas(ctx):
    rig = Rig(ctx, 400, 256, dream=DreamState(on=True, echoes=4, every=1, res=0))
    rig.frame()
    assert rig.lb.echo == (200, 128)
    assert rig.lb.atlas.size == (200, 128 * MAX_ECHOES)
    rig.lb.state.res = 2
    rig.frame()
    assert rig.lb.echo == (400, 256)
    assert rig.lb.dream.size == (400, 256)
    assert ctx.error == "GL_NO_ERROR"
    rig.release()


# ---------------------------------------------------------------- the composite

def grade(c, contrast, darken):
    return np.power(np.maximum(c, 1e-6), contrast) * (1.0 - darken)


def reference(scene, layers, darken, contrast):
    """The shader's math in numpy: scene (h, w, 4) float, layers [(rgba, w)]
    oldest first; returns (h, w, 4) float."""
    wake = np.zeros(scene.shape[:2] + (3,), dtype=np.float64)
    wa = np.zeros(scene.shape[:2], dtype=np.float64)
    for rgba, w in layers:
        c = grade(rgba[..., :3], contrast, darken)
        a = w * c.max(axis=2)
        wake = wake * (1.0 - a)[..., None] + c * w
        wa = wa + a - wa * a
    out = np.empty_like(scene)
    out[..., :3] = np.minimum(scene[..., :3] + wake, 1.0)
    out[..., 3] = scene[..., 3] + wa - scene[..., 3] * wa
    return out


def synthetic(h, w, seed):
    """A smooth, coloured test image with black ground on one side."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    img = np.zeros((h, w, 4), dtype=np.float64)
    for ch in range(3):
        f = rng.uniform(0.02, 0.08, 2)
        img[..., ch] = 0.5 + 0.5 * np.sin(xx * f[0] + yy * f[1] + rng.uniform(0, 6))
    img[:, : w // 4] = 0.0          # a black quarter: covers nothing
    img[..., 3] = 1.0
    return (img * 255).round().astype(np.uint8)


def test_composite_matches_numpy_reference(ctx):
    # target at the echo size, so atlas sampling is one texel per pixel
    w, h = echo_size(128, 400, 256)
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=3, every=1, res=0,
                                          echo_mix=0.7, decay=0.8, darken=0.25, contrast=1.6,
                                          mix=0.5))
    rig.frame()                        # builds the ring; one real capture in slot 0
    lb = rig.lb
    assert lb.echo == (w, h)
    imgs = [synthetic(h, w, k) for k in range(3)]
    lb.frame = 10                      # slot 0's capture (frame 1) falls off the ring
    now = lb.frame + 1
    for k, img in enumerate(imgs):     # slots 1..3 hold frames aged 3, 2, 1
        lb.write_slot(k + 1, img, frame_index=now - 3 + k)
    assert [age for _, age in lb.layers()] == [3, 2, 1]
    dream = synthetic(h, w, 9)
    lb.write_from(dream, frame_index=now - 1)
    rig.fbo.use()
    ctx.viewport = (0, 0, w, h)
    lb.composite(rig.r.scene.tex, rig.fbo)
    out = rig.read().astype(np.float64) / 255.0
    scene = rig.scene().astype(np.float64) / 255.0
    layers = [(img.astype(np.float64) / 255.0, 0.7 * 0.8 ** age)
              for img, age in zip(imgs, (3, 2, 1))]
    layers.append((dream.astype(np.float64) / 255.0, 0.5))
    ref = reference(scene, layers, 0.25, 1.6)
    err = np.abs(out - ref)
    assert err.max() <= 2.5 / 255, f"max error {err.max() * 255:.2f}/255"
    assert err.mean() <= 0.4 / 255
    # the wake is really there: the composite is not the scene
    assert np.abs(out - scene).mean() > 0.02
    # the black quarter of every layer adds nothing over the scene
    assert np.array_equal((out[:, : w // 4] * 255).round(), (scene[:, : w // 4] * 255).round())
    rig.release()


def test_composite_is_a_copy_when_nothing_is_layered(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=0, every=1, res=0))
    rig.frame()
    rig.frame()
    assert np.array_equal(rig.read(), rig.scene())
    rig.release()


def test_alpha_preserved_on_a_transparent_ground(ctx):
    """Overlay mode: the ground clears to alpha 0. The wake may only raise
    alpha where an echo has light — premultiplied, colour ≤ coverage — and
    where nothing ever was the desktop stays clear."""
    w, h = echo_size(128, 400, 256)
    rig = Rig(ctx, w, h, bg_alpha=0.0,
              dream=DreamState(on=True, echoes=6, every=1, res=0, echo_mix=0.8, decay=0.9,
                               darken=0.0, contrast=1.0))
    rig.s.faces = True
    for _ in range(7):
        rig.frame()
    out = rig.read().astype(int)
    scene = rig.scene().astype(int)
    assert (scene[..., 3] == 0).any(), "the ground must be see-through"
    assert (out[..., 3] >= scene[..., 3]).all()
    assert (out[..., 3] > scene[..., 3]).any(), "the wake must show somewhere"
    # alpha rises only where the wake has light: a pixel the wake left
    # black keeps the scene's alpha exactly
    lit = (out[..., :3] > scene[..., :3]).any(axis=2)
    assert (out[..., 3][~lit] == scene[..., 3][~lit]).all()
    # the corners never saw content: still fully clear
    assert out[:8, :8].max() == 0 and out[-8:, -8:].max() == 0
    rig.release()


def test_cut_through_toggle_on_an_opaque_ground(ctx):
    """Faces on an opaque ground: cut-through on (the default) lowers the
    window's alpha under the fills; off, every pixel stays opaque."""
    rig = Rig(ctx, 256, 256, bg_alpha=1.0)
    rig.s.faces, rig.s.lines, rig.s.points = True, False, False
    assert rig.s.cut_through
    rig.frame()
    assert rig.read()[..., 3].min() < 255, "the fills must cut the alpha"
    rig.s.cut_through = False
    rig.frame()
    out = rig.read()
    assert (out[..., 3] == 255).all()
    assert out[..., :3].max() > 0, "the fills must still draw"
    rig.release()


# ---------------------------------------------------------------- the dream slot

class Echo:
    """A source that answers every submit with the frame it was given,
    tagged, one call late — enough to prove the hand-off both ways."""

    def __init__(self):
        self.pending = None
        self.done = None
        self.submitted = []
        self.buffers = 0

    def buffer(self, shape):
        self.buffers += 1
        return np.empty(shape, dtype=np.uint8)

    def submit(self, frame, frame_index):
        self.submitted.append((frame, frame_index))
        self.done = self.pending
        self.pending = (frame.copy(), frame_index)

    def latest(self):
        return self.done


def test_source_protocol():
    assert isinstance(NullSource(), LookbackSource)
    assert isinstance(Echo(), LookbackSource)
    n = NullSource()
    n.submit(np.zeros((2, 2, 4), np.uint8), 7)
    assert n.frame_index == 7 and n.latest() is None


def test_dream_slot_round_trip(ctx):
    w, h = echo_size(128, 400, 256)
    src = Echo()
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=0, every=1, res=0, mix=1.0,
                                          darken=0.0))
    rig.lb.source = src
    rig.frame()
    frame1, idx = src.submitted[-1]
    assert idx == 1 and frame1.shape == (h, w, 4) and src.buffers == 1
    # the submitted pixels are the newest echo: a downsample of the scene
    assert frame1.max() > 0
    # nothing answered yet: the composite is a copy
    assert rig.lb.dream_frame == -1
    rig.frame()            # submit 2; latest() now answers submit 1
    rig.frame()            # pulled before this composite
    assert rig.lb.dream_frame == 1
    out = rig.read().astype(int)
    scene = rig.scene().astype(int)
    assert (out[..., :3] >= scene[..., :3]).all()
    assert np.abs(out - scene).mean() > 0.5, "the dream layer must show"
    # the third capture's submit answered the second; a result already
    # shown is not uploaded again
    assert rig.lb.pull() is True and rig.lb.dream_frame == 2
    assert rig.lb.pull() is False
    rig.release()


def test_read_write_legs(ctx):
    w, h = echo_size(128, 400, 256)
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=1, every=1, res=0))
    rig.frame()
    lb = rig.lb
    buf = np.zeros((h, w, 4), dtype=np.uint8)
    lb.read_into(buf)
    assert buf.max() > 0
    # what came out of the slot is what write_slot put in
    img = synthetic(h, w, 3)
    lb.write_slot(lb.newest(), img)
    lb.read_into(buf)
    assert np.array_equal(buf, img)
    lb.write_from(img, 5)
    assert lb.dream_frame == 5
    back = np.frombuffer(lb.dream.read(), dtype=np.uint8).reshape(h, w, 4)
    assert np.array_equal(back, img)
    rig.release()


@pytest.mark.slow
def test_copy_path_round_trip_under_budget(ctx):
    """The spike's number: glReadPixels of a 256-px echo into a host array
    plus the upload back is ~0.5 ms; the budget here is 1.5 ms p50."""
    w, h = echo_size(256, 1280, 820)
    rig = Rig(ctx, 1280, 820, dream=DreamState(on=True, echoes=1, every=1, res=2))
    rig.frame()
    lb = rig.lb
    buf = np.empty((h, w, 4), dtype=np.uint8)
    for _ in range(5):
        lb.read_into(buf)
        lb.write_from(buf)
    ctx.finish()
    times = []
    for _ in range(40):
        t0 = time.perf_counter()
        lb.read_into(buf)
        lb.write_from(buf)
        ctx.finish()
        times.append(time.perf_counter() - t0)
    p50 = sorted(times)[len(times) // 2] * 1e3
    print(f"\nread_into + write_from at {w}x{h}: p50 {p50:.2f} ms")
    assert p50 < 1.5, f"{p50:.2f} ms"
    rig.release()


# ---------------------------------------------------------------- params & presets

def registry(dream=None):
    from hyperspace.analysis import Analyser
    from hyperspace.bands import Chain
    from hyperspace.control import Control
    from hyperspace.params import build_registry

    chain = Chain(Analyser())
    audio = SimpleNamespace(chain=chain)
    return build_registry(ViewState(), Control(chain), audio, None, dream=dream)


DREAM_IDS = [
    "dream.on", "dream.mix", "dream.echo_mix", "dream.decay", "dream.darken",
    "dream.contrast", "dream.echoes", "dream.every", "dream.res", "dream.steps", "dream.step",
    "dream.k", "dream.layer", "dream.octaves", "dream.mask_decay", "dream.jitter",
]


def test_dream_params_declared():
    d = DreamState()
    reg = registry(d)
    assert [p.id for p in reg.group("dream")] == DREAM_IDS
    for p in reg.group("dream"):
        assert p.persist, p.id
    assert not reg["dream.every"].modulatable and not reg["dream.res"].modulatable
    assert all(reg[pid].modulatable for pid in DREAM_IDS
               if pid not in ("dream.every", "dream.res"))
    assert reg["dream.res"].names == [str(v) for v in RES]
    assert reg["dream.layer"].names[1] == "conv3_3"
    # the params write the state the compositor reads
    reg["dream.on"].set(True)
    reg["dream.echoes"].set_value(8)
    reg["dream.res"].set(3)
    assert d.on and d.echoes == 8 and d.res == 3
    # a fresh state stands in when no renderer is passed
    assert "dream.k" in registry()


def test_dream_snapshot_round_trip():
    d = DreamState()
    reg = registry(d)
    snap = reg.snapshot("dream")
    assert set(snap) == set(DREAM_IDS)
    reg["dream.mix"].set_value(0.9)
    reg["dream.layer"].set(4)
    reg["dream.on"].set(True)
    assert reg.restore(snap) == []
    assert d.mix == pytest.approx(0.4) and d.layer == 1 and d.on is False


def test_factory_presets_load(tmp_path):
    from hyperspace.library import Library

    d = DreamState()
    reg = registry(d)
    lib = Library(tmp_path, period=0.0)
    lib.attach(reg)
    assert "dream" in lib.groups()
    assert lib.list("dream") == ["default", "tracer-only"]
    assert lib.default_name("dream") == "default"
    assert lib.load("dream", "tracer-only") == []
    assert d.on and d.echoes == 8 and d.mix == 0.0 and d.echo_mix > 0
    assert lib.load("dream", "default") == []
    assert not d.on and d.echoes == 4 and d.mix == pytest.approx(0.4)
    # the default preset is the fresh state: loading it leaves nothing dirty
    assert not lib.is_dirty("dream")
    fresh = DreamState()
    for pid, v in lib.read("dream", "default")["values"].items():
        attr = pid.split(".", 1)[1]
        assert getattr(fresh, attr) == pytest.approx(v), pid


# ---------------------------------------------------------------- the page

def test_lookback_page_draws_headless(tmp_path):
    from imgui_bundle import imgui

    from hyperspace import ui_lookback
    from hyperspace.analysis import Analyser
    from hyperspace.bands import Chain
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    assert "lookback" in PAGE_KEYS
    ictx = imgui.create_context()
    try:
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(820, 820)
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        apply_style()
        load_fonts()
        chain = Chain(Analyser())
        control = Control(chain)
        audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        view = ViewState()
        lib = Library(tmp_path, period=0.0)
        d = DreamState()
        reg = build_registry(view, control, audio, lib.bank, dream=d)
        lib.attach(reg)
        # no renderer: the thumbnail row says so instead of drawing textures
        panel = Panel(control, audio, view, presets=lib.bank, registry=reg, library=lib)
        reg["ui.page"].set(PAGE_KEYS.index("lookback"))
        for on in (False, True):
            d.on = on
            imgui.new_frame()
            panel.draw(1 / 60, 60.0)
            imgui.end_frame()
        # a renderer with a live ring: the thumbnails draw as images
        fake = SimpleNamespace(lookback=SimpleNamespace(
            state=d, atlas=SimpleNamespace(glo=1), dream=SimpleNamespace(glo=2),
            echo=(200, 128), dream_frame=3, frame=12,
            thumbnails=lambda: [{"slot": 0, "age": 1, "weight": 0.3, "uv0": (0, 1 / 32),
                                 "uv1": (1, 0)}]))
        panel.renderer = fake
        imgui.new_frame()
        panel.draw(1 / 60, 60.0)
        imgui.end_frame()
        # the page function stands alone as well (hot-reload target)
        imgui.new_frame()
        imgui.begin("x")
        ui_lookback.page(panel, 1 / 60)
        imgui.end()
        imgui.end_frame()
    finally:
        imgui.destroy_context(ictx)
