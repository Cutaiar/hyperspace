"""Plan 26 A0: golden frames and GPU timing per pass.

The goldens (`tests/golden/frames/frames.json`, written by
`tools/golden_frames.py --record`) are every factory preset in each of
the eight output states, with the synthetic hands absent and present,
plus one frame at the 1080p cap: a SHA-256 of the full-resolution RGBA
frame each. The render test draws them all again and compares every
hash exactly; it runs only on the renderer they were recorded on
(`GL_RENDERER`) and skips anywhere else with a note naming it. A golden
that moves in A1 means A1 is wrong; in A2–A4 a moved golden needs its
reason in the PR (re-record with `--only`).

The timing half: `render.PassTimer` keeps a rolling median in ms per pass
of `Renderer._draw_frame` in `Renderer.stats["gpu_ms"]`, shown on the
SYSTEM page (`Panel.gpu_lines`), off with a note on a context with no
timer queries — and timing never changes a pixel.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "golden" / "frames" / "frames.json"


def _tool():
    """tools/golden_frames.py as a module (registered, for its dataclass)."""
    import sys

    if "golden_frames" in sys.modules:
        return sys.modules["golden_frames"]
    spec = importlib.util.spec_from_file_location("golden_frames",
                                                  ROOT / "tools" / "golden_frames.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["golden_frames"] = mod
    spec.loader.exec_module(mod)
    return mod


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text())


# ---------------------------------------------------------------- no GL

def test_every_factory_preset_has_every_state_recorded_and_nothing_else():
    """No preset or state is skipped silently: each factory preset has a
    golden for each of the eight `Switches` states, hands absent and
    present, and the one cap frame is there; each names its pipeline and
    a PNG that exists; every preset loaded with nothing missing."""
    from hyperspace.outputs import NAMES
    from hyperspace.preset import FACTORY_PRESETS

    doc = _manifest()
    eight = [(a, b, c) for a in (True, False) for b in (True, False) for c in (False, True)]
    assert [tuple(sw.values()) for sw in doc["states"].values()] == eight
    assert doc["size"] == [960, 600] and doc["dpr"] == 1.0 and doc["frames"] == 8
    assert abs(doc["dt"] - 1 / 60) < 1e-12
    keys = {(e["preset"], e["hands"], e["state"]) for e in doc["goldens"]}
    assert len(keys) == len(doc["goldens"])
    want = {(p, h, s) for p in FACTORY_PRESETS for h in ("absent", "present")
            for s in doc["states"]}
    cap = doc["cap"]
    capped = {(e["preset"], e["hands"], e["state"]) for e in doc["goldens"]
              if e["state"] not in doc["states"]}
    assert keys - capped == want
    assert len(capped) == 1
    (p, h, s), = capped
    assert (p, h) == (cap["preset"], cap["hands"]) and s.startswith(cap["state"] + "@")
    routes = set(NAMES.values()) | {"none"}
    for e in doc["goldens"]:
        assert e["route"] in routes, e
        assert len(e["sha256"]) == 64
        assert (MANIFEST.parent / e["png"]).is_file(), e["png"]
    assert set(doc["presets"]) == set(FACTORY_PRESETS)
    for slug, said in doc["presets"].items():
        for hands in ("absent", "present"):
            assert said[hands]["missing"] == [], slug
            assert said[hands]["hands_shown"] is (hands == "present"), slug
    # all three pipelines are reached somewhere, with the hands through an effect
    assert {e["route"] for e in doc["goldens"]} == routes


def test_the_gpu_lines_on_the_system_page():
    """One line per pass, its median in ms, under a heading; the note
    alone with no timer queries; nothing before a frame was timed."""
    from hyperspace.ui import Panel

    def lines(stats):
        return Panel.gpu_lines(SimpleNamespace(renderer=SimpleNamespace(stats=stats)))

    got = lines({"gpu_ms": {"scene": 1.234, "compose": 0.2}, "gpu_note": ""})
    assert got[0].startswith("gpu per pass")
    assert [ln.split() for ln in got[1:]] == [["scene", "1.23"], ["compose", "0.20"]]
    assert lines({"gpu_ms": {}, "gpu_note": "no GPU timer queries on this context (Error)"}) \
        == ["gpu: no GPU timer queries on this context (Error)"]
    assert lines({}) == [] and Panel.gpu_lines(SimpleNamespace(renderer=None)) == []


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    """The tool's one context (kept for the process: a released context
    would leave none current for the tests after it)."""
    try:
        c = _tool().context()
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    return c


def test_every_golden_frame_is_drawn_byte_for_byte(ctx):
    """Each factory preset in each state it reaches, hands absent and
    present, and the cap frame: every full-resolution frame's SHA-256 is
    its golden's. Skips (never passes) on another renderer."""
    doc = _manifest()
    tool = _tool()
    here = tool.renderer_name(ctx)
    if here != doc["renderer"]:
        pytest.skip(f"the golden frames expect GL_RENDERER {doc['renderer']!r}; "
                    f"this context is {here!r} (re-record there with "
                    "tools/golden_frames.py --record)")
    shots, said = tool.render_all()
    assert len(shots) == len(doc["goldens"])
    moved = tool.diff(shots, doc)
    assert not moved, ("frames moved (run tools/golden_frames.py for a contact sheet): "
                       + ", ".join(s.key for s, _ in moved))
    for slug, info in said.items():
        for hands, got in info.items():
            assert got == doc["presets"][slug][hands], (slug, hands)


def _rig(ctx, timer_ctx=None):
    """A renderer with an effect on, the look-back on and the hands on
    (test_outputs' rig), and a framebuffer."""
    from test_outputs import fbo, rig

    from hyperspace.render import PassTimer

    r = rig(ctx, effects=("warp",), echoes=True)
    if timer_ctx is not None:
        r.timer = PassTimer(timer_ctx)
    return r, fbo(ctx)


def _frames(ctx, r, f, n):
    import numpy as np
    from test_outputs import H, W, scene_view

    s = scene_view()
    for k in range(n):
        s.ang = [a + 0.05 for a in s.ang]
        f.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=2.0 + k / 60)
    return np.frombuffer(f.read(components=4), dtype=np.uint8)


def test_each_pass_has_a_rolling_median_in_ms(ctx):
    from hyperspace.render import GPU_PASSES, PassTimer

    r, f = _rig(ctx)
    if not r.timer.on:
        pytest.skip(f"this context has no timer queries: {r.timer.note}")
    _frames(ctx, r, f, PassTimer.LAG)
    assert r.stats["gpu_ms"] == {}                 # nothing read back yet
    _frames(ctx, r, f, 6)
    ms = r.stats["gpu_ms"]
    assert list(ms) == list(GPU_PASSES)            # every pass, in frame order
    assert all(v >= 0.0 for v in ms.values())
    assert sum(ms.values()) > 0.0       # (a driver may report a tiny pass as 0)
    assert r.stats["gpu_note"] == ""
    assert all(len(w) == 6 for w in r.timer._ms.values())     # read LAG frames late
    # the old counts are still there
    assert r.stats["chain_runs"] == 1 and r.stats["captures"] == 1 and r.stats["layer"]
    # the window rolls
    _frames(ctx, r, f, PassTimer.WINDOW + 5)
    assert all(len(w) == PassTimer.WINDOW for w in r.timer._ms.values())


def test_no_timer_queries_means_a_note_and_the_same_pixels(ctx):
    """A context whose `query(time=True)` raises: the timer is off, the
    SYSTEM line says why, and the frame is byte for byte the timed one."""
    from hyperspace.ui import Panel

    class NoTimers:
        def query(self, **kw):
            raise moderngl.Error("GL_TIME_ELAPSED is not supported")

    timed, f1 = _rig(ctx)
    plain, f2 = _rig(ctx, timer_ctx=NoTimers())
    assert not plain.timer.on and "no GPU timer queries" in plain.timer.note
    a = _frames(ctx, timed, f1, 8)
    b = _frames(ctx, plain, f2, 8)
    assert (a == b).all()
    assert plain.stats["gpu_ms"] == {} and plain.stats["gpu_note"] == plain.timer.note
    assert Panel.gpu_lines(SimpleNamespace(renderer=plain)) == [f"gpu: {plain.timer.note}"]


def test_a_query_that_fails_mid_run_turns_timing_off_not_the_frame(ctx):
    r, f = _rig(ctx)
    if not r.timer.on:
        pytest.skip(f"this context has no timer queries: {r.timer.note}")
    want = _frames(ctx, *_rig(ctx), 3)

    class Broken:
        elapsed = 0

        def __enter__(self):
            raise moderngl.Error("begin failed")

        def __exit__(self, *a):
            pass

    r.timer._free = [Broken() for _ in range(64)]
    got = _frames(ctx, r, f, 3)
    assert not r.timer.on and "begin failed" in r.timer.note
    assert (got == want).all()
