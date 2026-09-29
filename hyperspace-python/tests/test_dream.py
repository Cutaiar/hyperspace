"""WP6b — the dream worker: the LookbackSource contract, the hand-off,
the guards, the copy paths, the config gate, and the real pipeline.

The worker itself needs torch — a main dependency since decision 23 (a),
so a plain ``uv sync`` has it; those tests still skip without it. The fast ones inject a step function in place of the
net, so they need no weights and no GPU; the end-to-end one loads VGG16
conv3_3 for real and is marked slow.
"""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace import config
from hyperspace.lookback import DreamState, LookbackSource, echo_size
from hyperspace.view import ViewState


def registry(dream=None):
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import build_registry

    chain = Analyzer(Analyser())
    return build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain), None,
                          dream=dream)


def blob(h, w, level=200):
    """A frame with one bright block on a black ground, rows bottom-up like GL."""
    f = np.zeros((h, w, 4), np.uint8)
    f[h // 3: 2 * h // 3, w // 3: 2 * w // 3, :3] = level
    f[..., 3] = 255
    return f


def wait_for(fn, timeout=10.0):
    end = time.perf_counter() + timeout
    while time.perf_counter() < end:
        v = fn()
        if v:
            return v
        time.sleep(0.002)
    raise AssertionError("timed out")


# ---------------------------------------------------------------- the rule

def test_core_does_not_import_the_worker():
    """BLUEPRINT §3.6: dream.py depends on the core, never the reverse — and
    with [dream] off torch is never touched."""
    import importlib

    sys.modules.pop("hyperspace.dream", None)
    for m in ("hyperspace.params", "hyperspace.control", "hyperspace.analyzer",
              "hyperspace.routing", "hyperspace.render", "hyperspace.lookback",
              "hyperspace.config", "hyperspace.hotreload", "hyperspace.ui_lookback"):
        importlib.import_module(m)
    assert "hyperspace.dream" not in sys.modules
    # no module under hyperspace/ imports torch at the top except dream.py
    from pathlib import Path

    for f in (Path(__file__).parents[1] / "hyperspace").glob("*.py"):
        if f.name == "dream.py":
            continue
        assert "import torch" not in f.read_text(), f.name


def test_dream_is_on_by_default(tmp_path):
    """Decision 23 (a), 2026-09-29: torch is part of the app and the worker
    opens unless config.toml says `[dream] enabled = false`."""
    cfg = config.load(tmp_path / "config.toml")
    assert cfg["dream"] == {"enabled": True, "device": "auto", "precision": "fp32",
                            "weights_dir": ""}
    (tmp_path / "config.toml").write_text('[dream]\nenabled = false\nprecision = "fp16"\n')
    cfg = config.load(tmp_path / "config.toml")
    assert cfg["dream"]["enabled"] is False and cfg["dream"]["precision"] == "fp16"
    assert cfg["dream"]["device"] == "auto"


def test_open_dream_off_imports_nothing():
    from hyperspace import app

    sys.modules.pop("hyperspace.dream", None)
    assert app._open_dream(registry(), {"dream": {"enabled": False}}) == (None, "")
    assert app._open_dream(registry(), {}) == (None, "")
    assert "hyperspace.dream" not in sys.modules


def test_hotreload_order():
    from hyperspace.hotreload import MODULES

    assert MODULES.index("dream") == MODULES.index("lookback") + 1
    assert MODULES.index("dream") < MODULES.index("render")


def test_guard_step():
    pytest.importorskip("torch")
    from hyperspace.dream import STABLE_RATIO, guard_step

    assert guard_step(0.03, 2, 0.08) == (0.03, False)          # the default
    step, clamped = guard_step(0.06, 3, 0.03)                  # a lane pushed it
    assert clamped and step == pytest.approx(STABLE_RATIO * 0.03 / 3)
    assert guard_step(0.01, 1, 0.3) == (0.01, False)


# ---------------------------------------------------------------- the worker, faked

@pytest.fixture
def dream_mod():
    pytest.importorskip("torch")
    from hyperspace import dream

    return dream


def make_worker(dream_mod, reg, step_fn=None, **kw):
    cfg = {"enabled": True, "device": kw.pop("device", "auto")}
    w = dream_mod.DreamWorker(reg, cfg, step_fn=step_fn, **kw)
    return w


def identity(D, mask, params):
    return D


def test_source_conformance(dream_mod):
    w = make_worker(dream_mod, registry(), identity)
    try:
        assert isinstance(w, LookbackSource)
        assert w.path in ("alias", "staging")
    finally:
        w.close()


def test_round_trip_is_masked_rgb_at_echo_size(dream_mod):
    d = DreamState(k=0.5)
    w = make_worker(dream_mod, registry(d), identity)
    try:
        h, wd = echo_size(128, 400, 256)[::-1]
        buf = w.buffer((h, wd, 4))
        assert buf.shape == (h, wd, 4) and buf.dtype == np.uint8 and buf.flags.writeable
        assert w.latest() is None
        np.copyto(buf, blob(h, wd))
        t0 = time.perf_counter()
        w.submit(buf, 7)
        assert time.perf_counter() - t0 < 0.005, "submit must not wait for the worker"
        got = wait_for(w.latest)
        pixels, idx = got
        assert idx == 7 and w.submitted == 7 and w.answered == 7
        assert pixels.shape == (h, wd, 4) and pixels.dtype == np.uint8
        # premultiplied by the content mask: black ground stays black, the
        # block is lit and carries the mask in alpha
        assert pixels[:8, :8].max() == 0 and pixels[-8:, -8:].max() == 0
        cy, cx = h // 2, wd // 2
        assert pixels[cy, cx, :3].min() > 150 and pixels[cy, cx, 3] == 255
        # a second submit answers with its own index; the first is not repeated
        buf = w.buffer((h, wd, 4))
        np.copyto(buf, blob(h, wd))
        w.submit(buf, 8)
        assert wait_for(lambda: w.latest() if w.latest()[1] == 8 else None)[1] == 8
        assert w.stats()["behind"] == 0 and w.error == ""
        # a foreign array (lookback's own staging) is copied in
        w.submit(blob(h, wd, 90), 9)
        assert wait_for(lambda: w.latest() if w.latest()[1] == 9 else None)[1] == 9
        assert "0 behind" in w.status()
    finally:
        w.close()


def test_latest_wins_under_a_slow_worker(dream_mod):
    def slow(D, mask, params):
        time.sleep(0.05)
        return D

    w = make_worker(dream_mod, registry(), slow)
    try:
        h, wd = 32, 48
        t0 = time.perf_counter()
        for i in range(1, 13):
            buf = w.buffer((h, wd, 4))
            np.copyto(buf, blob(h, wd))
            w.submit(buf, i)
            time.sleep(0.004)
        assert time.perf_counter() - t0 < 0.3, "submits never wait"
        assert w.drain(5.0)
        _, idx = w.latest()
        assert idx == 12, "the newest frame is the one answered"
        assert w.drops >= 6 and w.calls <= 5
        assert w.stats()["behind"] == 0
        assert f"{w.drops} dropped" in w.status()
    finally:
        w.close()


def test_stability_clamp_shows(dream_mod):
    seen = {}

    def spy(D, mask, params):
        seen.update(params)
        return D

    d = DreamState(step=0.06, steps=3, k=0.03)
    w = make_worker(dream_mod, registry(d), spy)
    try:
        h, wd = 32, 48
        w.submit(blob(h, wd), 1)
        assert w.drain(5.0)
        assert w.clamped and seen["step"] == pytest.approx(dream_mod.STABLE_RATIO * 0.03 / 3)
        assert "step clamped" in w.status()
        # a live change lands on the next submit — the params are read each time
        d.step = 0.01
        w.submit(blob(h, wd), 2)
        assert w.drain(5.0)
        assert not w.clamped and seen["step"] == pytest.approx(0.01)
        assert "clamped" not in w.status()
    finally:
        w.close()


def test_nan_resets_the_buffer(dream_mod):
    torch = pytest.importorskip("torch")
    calls = []

    def poison(D, mask, params):
        calls.append(1)
        if len(calls) == 2:
            return D * float("nan")
        return D

    w = make_worker(dream_mod, registry(), poison)
    try:
        h, wd = 32, 48
        for i in range(1, 4):
            w.submit(blob(h, wd), i)
            assert w.drain(5.0)
        assert w.nan_resets == 1 and w.calls == 2
        assert bool(torch.isfinite(w.D).all())
        pixels, idx = w.latest()
        assert idx == 3 and np.isfinite(pixels).all()
        assert "1 nan reset" in w.status()
    finally:
        w.close()


def test_fallback_copy_path(dream_mod):
    w = make_worker(dream_mod, registry(), identity, alias=False)
    try:
        assert w.path == "staging" and not w.alias
        h, wd = 32, 48
        buf = w.buffer((h, wd, 4))
        assert isinstance(buf, np.ndarray) and buf.shape == (h, wd, 4)
        np.copyto(buf, blob(h, wd))
        w.submit(buf, 1)
        pixels, idx = wait_for(w.latest)
        assert idx == 1 and pixels[h // 2, wd // 2, 0] > 150 and pixels[:4, :4].max() == 0
        # three slots rotate: the array handed out is never the one waiting
        a = w.buffer((h, wd, 4))
        w.submit(a, 2)
        b = w.buffer((h, wd, 4))
        assert b is not a
    finally:
        w.close()


def test_alias_copy_path_is_the_tensor(dream_mod):
    torch = pytest.importorskip("torch")
    if not torch.backends.mps.is_available() or not hasattr(torch.mps, "_host_alias_storage"):
        pytest.skip("no MPS host alias here")
    w = make_worker(dream_mod, registry(), identity)
    try:
        assert w.path == "alias"
        buf = w.buffer((16, 24, 4))
        buf[...] = 9
        slot = w._slots[w._writing]
        assert slot.dev is not None and bool((slot.dev.cpu() == 9).all())
    finally:
        w.close()


def test_resize_rebuilds(dream_mod):
    w = make_worker(dream_mod, registry(), identity)
    try:
        w.submit(blob(32, 48), 1)
        assert w.drain(5.0) and w.D.shape[-2:] == (32, 48)
        w.submit(blob(64, 96), 2)
        assert w.drain(5.0) and w.D.shape[-2:] == (64, 96)
        pixels, idx = w.latest()
        assert idx == 2 and pixels.shape == (64, 96, 4)
    finally:
        w.close()


def test_missing_net_means_no_dream(dream_mod, tmp_path, monkeypatch):
    """No weights and no way to get them: the status says so, nothing is
    published, and the worker stays alive."""
    d = DreamState(layer=0)
    cfg = {"enabled": True, "weights_dir": str(tmp_path)}
    monkeypatch.setattr(dream_mod, "load_state",
                        lambda arch, wd: (_ for _ in ()).throw(OSError("offline")))
    w = dream_mod.DreamWorker(registry(d), cfg)
    try:
        w.submit(blob(32, 48), 1)
        assert w.drain(10.0)
        assert w.latest() is None and w.net is None
        assert "no conv2_2" in w.status() and "offline" in w.error
        # not retried every frame; a layer change is
        w.submit(blob(32, 48), 2)
        assert w.drain(5.0) and w.stats()["alive"]
    finally:
        w.close()


# ---------------------------------------------------------------- the real thing

@pytest.mark.slow
def test_end_to_end_offscreen(dream_mod, tmp_path):
    """Renderer + Lookback + DreamWorker on a rotating 24-cell at the spike's
    defaults: the dream layer shows, the black ground stays black."""
    torch = pytest.importorskip("torch")
    moderngl = pytest.importorskip("moderngl")
    if not torch.backends.mps.is_available():
        pytest.skip("the real net needs the GPU")
    if dream_mod.find_weights("vgg16", tmp_path) is None:
        pytest.skip("VGG16 weights are not on this machine")
    try:
        ctx = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"no standalone GL context available: {e}")
    from hyperspace.render import Renderer

    W, H = 1280, 820

    def rig(dream):
        fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
        r = Renderer(ctx, dream)
        s = ViewState(shape=10, faces=True, pattern=2, bright=1.3, speed=3.0)
        s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
        s.yaw, s.pitch = 0.4, 0.25
        return fbo, r, s

    def run(fbo, r, s, worker, frames=90):
        for k in range(frames):
            s.integrate(1 / 60)
            fbo.use()
            ctx.viewport = (0, 0, W, H)
            r.draw(s, W, H, t_now=k / 60)
            if worker is not None:          # paced: every frame gets dreamed
                assert worker.drain(10.0)
        ctx.finish()
        return np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4).copy()

    d = DreamState(on=True, echoes=0, every=1)
    fbo, r, s = rig(d)
    reg = registry(d)
    w = dream_mod.DreamWorker(reg, {"enabled": True, "weights_dir": str(tmp_path)})
    try:
        r.lookback.source = w
        with_dream = run(fbo, r, s, w)
        st = w.stats()
        print(f"\ndream: {w.status()}")
        assert w.error == "" and w.layer == "conv3_3" and w.nan_resets == 0
        assert r.lookback.dream_frame >= 85 and w.calls >= 85
        assert st["ms"] < 60.0
    finally:
        w.close()
        fbo.release()
    fbo, r, s = rig(DreamState(on=True, echoes=0, every=1))
    tracer_only = run(fbo, r, s, None)
    fbo.release()
    a, b = with_dream[..., :3].astype(int), tracer_only[..., :3].astype(int)
    diff = np.abs(a - b)
    assert diff.mean() > 1.0, f"the dream layer must contribute ({diff.mean():.2f})"
    # the additive wake only ever adds
    assert (a >= b - 1).mean() > 0.999
    # the black ground stays black: the mask keeps the dream off it
    for corner in (with_dream[:16, :16], with_dream[:16, -16:], with_dream[-16:, :16],
                   with_dream[-16:, -16:]):
        assert corner[..., :3].max() == 0
