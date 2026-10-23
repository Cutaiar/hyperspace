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

The timing half: `render.PassTimer` keeps a rolling median in ms per
node of the render graph (A1; per pass before it) in
`Renderer.stats["gpu_ms"]`, shown on the SYSTEM page (`Panel.gpu_lines`),
off with a note on a context with no timer queries — and timing never
changes a pixel.
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
    present; the window's own frame alone (`solo`, the default state) for
    each, and alone through (`solo-scene+hands+through`) for each preset
    with an effect on; and the one cap frame. Each names its pipeline and
    a PNG that exists; every preset loaded with nothing missing. Plan 26
    A3: the graph's other wirings, hands present — the hands in the scene
    and the depth-aware layer for every preset, the history holding the
    hands for each preset with the look-back on — named
    `<wiring>/<state>`. Plan 26 A4b: the recorded point cloud listed as a
    `cloud` device, hands present, named `cloud/<state>`, and nothing
    else."""
    from hyperspace.outputs import NAMES
    from hyperspace.preset import FACTORY_PRESETS

    doc = _manifest()
    eight = [(a, b, c) for a in (True, False) for b in (True, False) for c in (False, True)]
    assert [tuple(sw.values()) for sw in doc["states"].values()] == eight
    assert doc["solo_states"] == {
        "solo": {"scene": True, "hands": True, "through": False},
        "solo-scene+hands+through": {"scene": True, "hands": True, "through": True}}
    assert doc["solo_fx_only"] == ["solo-scene+hands+through"]
    assert doc["wired_states"] == {
        "in-scene": {"wiring": {"hands": "scene"},
                     "states": ["scene+hands", "hands", "hands+through"], "presets": None},
        "depth": {"wiring": {"blend": "depth"},
                  "states": ["scene+hands", "scene+hands+through"], "presets": None},
        "history+hands": {"wiring": {"history": "scene+hands"}, "states": ["scene+hands"],
                          "presets": ["party-wake", "party-tracer"]}}
    tool = _tool()
    assert doc["cloud_states"] == {
        "cloud": {"config": tool.CLOUD_CONFIG, "fixture": "tests/fixtures/clouds/knot.npz",
                  "states": ["scene", "scene+hands"], "presets": ["legacy6", "party-faces"]}}
    assert 'kind = "cloud"' in tool.CLOUD_CONFIG and tool.CLOUD_FIXTURE.is_file()
    assert doc["size"] == [960, 600] and doc["dpr"] == 1.0 and doc["frames"] == 8
    assert abs(doc["dt"] - 1 / 60) < 1e-12
    assert doc["gl_version"]
    keys = {(e["preset"], e["hands"], e["state"]) for e in doc["goldens"]}
    assert len(keys) == len(doc["goldens"])
    fx_on = {p for p, said in doc["presets"].items() if said["absent"]["effects_on"]}
    assert fx_on == {"party-trip", "party-acid", "party-mandala", "party-noita",
                     "lfo-breathe", "hands-fx"}
    want = {(p, h, s) for p in FACTORY_PRESETS for h in ("absent", "present")
            for s in [*doc["states"], "solo"]
            + (["solo-scene+hands+through"] if p in fx_on else [])}
    cap = doc["cap"]
    wired = {(p, "present", f"{name}/{s}") for name, w in doc["wired_states"].items()
             for p in (w["presets"] or FACTORY_PRESETS) for s in w["states"]}
    capped = {(e["preset"], e["hands"], e["state"]) for e in doc["goldens"]
              if e["state"] not in doc["states"] and e["state"] not in doc["solo_states"]
              and "/" not in e["state"]}
    clouded = {(p, "present", f"{name}/{s}") for name, c in doc["cloud_states"].items()
               for p in c["presets"] for s in c["states"]}
    # plan 26 A4: the proof presets, fixtures loaded through a scratch
    # library (never factory presets), hands present, all eight states
    fixture = {(p, f["hands"], s) for p, f in doc["fixture_states"].items() for s in f["states"]}
    assert (keys - capped - wired - clouded - fixture == want and wired <= keys
            and clouded <= keys and fixture <= keys)
    # (plan 30 D1: + 3 × 8, the three placement fixtures' eight states;
    # plan 28 N4: + 2 × 8, the two wire fixtures'; plan 32 T6: + 2 × 8, the
    # two media fixtures'; plan 32 T7: + 3 × 8, the faces' and the aux's)
    assert len(doc["goldens"]) == (23 * 2 * 9 + 6 * 2 + 1 + 23 * 5 + 2 + 2 * 2 + 8 + 3 * 8
                                   + 2 * 8 + 2 * 8 + 3 * 8)
    # alone, the window's frame is drawn direct: the default state over a
    # shown hand is the scene with the hands over; through an effect, the
    # hands go into the chain
    for e in doc["goldens"]:
        if e["state"] == "solo":
            assert e["route"] == "SCENE" and e["hands_over"] is (e["hands"] == "present")
        if e["state"] == "solo-scene+hands+through" and e["hands"] == "present":
            assert e["route"] == "SCENE+HANDS" and not e["hands_over"]
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
    # the fixtures: the tool's list, each a file under tests/fixtures/ and
    # never a factory preset, loaded with nothing missing and no note, its
    # graph landed (the wiring the manifest records is not the default)
    tool = _tool()
    assert list(doc["fixture_states"]) == list(doc["fixtures"]) == list(tool.FIXTURE_PRESETS)
    for slug, f in doc["fixture_states"].items():
        assert (ROOT / f["file"]).is_file() and slug not in FACTORY_PRESETS
        assert f["states"] == list(doc["states"])
        said = doc["fixtures"][slug]["present"]
        assert said["missing"] == [] and said["notes"] == [] and said["hands_shown"]
        # the graph landed as the file says it (the section, not a repr of
        # the Wiring: a field added later moves no golden). Plan 32 T6: a
        # media fixture's proof is its channels — a wire with no node, or
        # no graph at all (the backdrop is a value)
        assert said["graph"] == json.loads((ROOT / f["file"]).read_text()).get("graph")
        assert (said["graph"] or {}).get("nodes") or slug in tool.MEDIA_FIXTURES
    # all three pipelines are reached somewhere, with the hands through an effect
    assert {e["route"] for e in doc["goldens"]} == routes


def test_the_history_wiring_is_recorded_for_every_preset_with_the_look_back_on():
    """The history-with-the-hands goldens cover exactly the factory presets
    whose file turns the look-back on (elsewhere the history holds nothing
    the picture shows, so the frame is the default one)."""
    from hyperspace.preset import FACTORY_PRESETS

    lib = ROOT / "hyperspace" / "library" / "presets"
    on = [slug for slug in FACTORY_PRESETS
          if json.loads((lib / f"{slug}.json").read_text()).get("values", {}).get("dream.on")]
    assert sorted(on) == sorted(_tool().LOOKBACK_ON)


def test_the_gpu_lines_on_the_system_page():
    """One line per node, its median in ms, under a heading; the note
    alone with no timer queries; nothing before a frame was timed."""
    from hyperspace.ui import Panel

    def lines(stats):
        return Panel.gpu_lines(SimpleNamespace(renderer=SimpleNamespace(stats=stats)))

    got = lines({"gpu_ms": {"scene": 1.234, "output.1": 0.2}, "gpu_note": ""})
    assert got[0].startswith("gpu per node")
    assert [ln.split() for ln in got[1:]] == [["scene", "1.23"], ["output.1", "0.20"]]
    assert lines({"gpu_ms": {}, "gpu_note": "no GPU timer queries on this context (Error)"}) \
        == ["gpu: no GPU timer queries on this context (Error)"]
    assert lines({}) == [] and Panel.gpu_lines(SimpleNamespace(renderer=None)) == []


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    """The tool's one context (kept for the process: a released context
    would leave none current for the tests after it)."""
    import gc

    try:
        c = _tool().context()
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    # its objects (gc_mode auto) are freed now, while it is still the
    # current context — never later, on some other module's
    gc.collect()


def test_every_golden_frame_is_drawn_byte_for_byte(ctx):
    """Each factory preset in each state it reaches, hands absent and
    present, and the cap frame: every full-resolution frame's SHA-256 is
    its golden's. Skips (never passes) on another renderer."""
    doc = _manifest()
    tool = _tool()
    here, version = tool.renderer_name(ctx), tool.gl_version(ctx)
    recorded = f"{doc['renderer']!r} (GL_VERSION {doc['gl_version']!r})"
    if here != doc["renderer"]:
        pytest.skip(f"the golden frames expect GL_RENDERER {recorded}; "
                    f"this context is {here!r} (GL_VERSION {version!r}); re-record there "
                    "with tools/golden_frames.py --record")
    shots, said = tool.render_all()
    assert len(shots) == len(doc["goldens"])
    moved = tool.diff(shots, doc)
    assert not moved, (f"frames moved, recorded on {recorded}, drawn on {here!r} "
                       f"(GL_VERSION {version!r}) — run tools/golden_frames.py for a "
                       "contact sheet: " + ", ".join(s.key for s, _ in moved))
    recorded_said = {**doc["presets"], **doc.get("fixtures", {})}
    for slug, info in said.items():
        for hands, got in info.items():
            assert got == recorded_said[slug][hands], (slug, hands)


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


def test_each_node_has_a_rolling_median_in_ms(ctx):
    """A1: one median per node of the frame's graph, in the graph's order
    (`Graph.timed`); a node that did not run counts 0."""
    from hyperspace.render import PassTimer

    r, f = _rig(ctx)
    if not r.timer.on:
        pytest.skip(f"this context has no timer queries: {r.timer.note}")
    _frames(ctx, r, f, PassTimer.LAG)
    assert r.stats["gpu_ms"] == {}                 # nothing read back yet
    _frames(ctx, r, f, 6)
    ms = r.stats["gpu_ms"]
    assert r._graph.timed == ["scene", "cover", "hands", "history", "fx", "capture", "output.1"]
    # plan 30 D0 (decision 5): the effect that ran has its own line, before its end
    assert list(ms) == ["scene", "cover", "hands", "history", "warp", "fx",
                        "capture", "output.1"]
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
