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
                     "lfo-breathe", "hands-fx", "seq-demo"}
    # plan 31 P: seq-demo drawn with play pressed (`seq.run` is no preset's)
    assert doc["sequencer_running"] == ["seq-demo"] == list(_tool().RUNNING)
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
    # plan 28 N4: + 2 × 8, the two wire fixtures'; plan 31 P: seq-demo, a
    # 24th factory preset and a 7th with an effect on; plan 32 T6: + 2 × 8,
    # the two media fixtures'; plan 32 T7: + 3 × 8, the faces' and the aux's;
    # plan 33 T4: + 3 × 8, the faces', the backdrop's and the two sizes' branches;
    # plan 33 T5: + 8, the switch onto the faces; plan 34 T2: + 2 × 8, the
    # delay onto the faces and the trails' loop; plan 34 T3: + 8, an echo
    # onto the faces; plan 35 T3: + 3 × 8, the three wired frames; plan 34
    # T4: + 2 × 8, the resize into a delay onto the faces and the crop;
    # plan 39 T2: + 8, a matte wired straight into All outputs)
    assert len(doc["goldens"]) == (24 * 2 * 9 + 7 * 2 + 1 + 24 * 5 + 2 + 2 * 2 + 8 + 3 * 8
                                   + 2 * 8 + 2 * 8 + 3 * 8 + 3 * 8 + 8 + 2 * 8 + 8 + 3 * 8
                                   + 2 * 8 + 8)
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
    # (plan 35 T4: the retired route table's names, kept as the tool's data)
    routes = {name for name, _ in tool.ROUTES.values()}
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
    # never a factory preset, loaded with nothing missing and no note — (plan
    # 36 T3) every fixture an old file, a migration input — its graph landed
    # as its `/7`
    tool = _tool()
    assert list(doc["fixture_states"]) == list(doc["fixtures"]) == list(tool.FIXTURE_PRESETS)
    for slug, f in doc["fixture_states"].items():
        assert (ROOT / f["file"]).is_file() and slug not in FACTORY_PRESETS
        assert f["states"] == list(doc["states"])
        said = doc["fixtures"][slug]["present"]
        # (plan 35 T3: a wired fixture draws only what it wires — its states
        # are the windows' mutes, not switches emulated: the blank frame and
        # the channel alone wire no hands, so none is shown, and the blank
        # frame builds the outputs and nothing else)
        from hyperspace.preset import NO_GRAPH_SAID

        # (the blank frame: the strip says it holds nothing, plan 36 T3)
        want = [NO_GRAPH_SAID] if slug == "blank-frame" else []
        assert said["missing"] == [] and said["notes"] == want, slug
        # (plan 39 T2: the matte into All outputs wires no hands either)
        no_hands = ("blank-frame", "channel-out-only", "mask-as-picture")
        assert said["hands_shown"] is (slug not in no_hands), slug
        if slug == "blank-frame":
            assert all(n.startswith("output.") for n in said["nodes"]), said["nodes"]
        # the graph landed as its `/7` says it (the section, not a repr of
        # the Wiring: a field added later moves no golden) — plan 36 T3: a
        # wired frame that reads as it is, no placement in it, every hands
        # entry and `laid` written. Plan 35 T3: the blank one holds nothing
        # but its hands entry
        from hyperspace.graph import FRAME_KEY, PLACE_KEYS, WIRED_FRAME, read_graph

        landed = said["graph"]
        assert landed[FRAME_KEY] == WIRED_FRAME and read_graph(landed).to_json() == landed
        assert not any(k in e for e in landed["nodes"] for k in PLACE_KEYS), slug
        assert any(e.get("kind") == "hands" and "laid" in e for e in landed["nodes"]), slug
        assert landed.get("wires") or slug == "blank-frame", slug
    # all three pipelines are reached somewhere, with the hands through an effect
    assert {e["route"] for e in doc["goldens"]} == routes


def test_the_history_wiring_is_recorded_for_every_preset_with_the_look_back_on():
    """The history-with-the-hands goldens cover exactly the factory presets
    whose file draws a look-back (elsewhere the history holds nothing the
    picture shows, so the frame is the default one). Plan 36 T4: a
    look-back is drawn — a wire into `lookback.image` — where the old file
    turned it on (`factory-sources`' `dream.on`)."""
    from hyperspace.preset import FACTORY_PRESETS

    lib = ROOT / "hyperspace" / "library" / "presets"
    drawn = [slug for slug in FACTORY_PRESETS
             if any(w.get("to") == "lookback.image" for w in json.loads(
                 (lib / f"{slug}.json").read_text())["graph"].get("wires", []))]
    on = [slug for slug in FACTORY_PRESETS
          if json.loads((_tool().FACTORY_SOURCES / f"{slug}.json").read_text())
          .get("values", {}).get("dream.on")]
    assert sorted(drawn) == sorted(on) == sorted(_tool().LOOKBACK_ON)


# the `goldens` list as T3 left it (sha256 of its JSON): plan 35 T4's
# `--names` rewrites recorded node names only, never an entry. Plan 34 T4's
# two fixtures' entries (`GOLDENS_SINCE`) are left out of the digest: the
# 741 before them are the same list, byte for byte
# Plan 36 T1 re-recorded four entries (the stand-down gone, a hands mute
# inside a through chain: `party-trip`, `party-noita`, `lfo-breathe`
# absent|hands+through and `through-one-output` present|scene+through) and
# the route words of those presets' through states
# (plan 39 T2: and `mask-as-picture`'s, new pictures — none of the 741 moved)
GOLDENS_SINCE = ("resize-faces", "resize-crop", "mask-as-picture")
# (plan 36 T3: re-pinned for the four goldens re-recorded — palette-glass's
# scene+hands+through and wired-outputs' scene+hands, scene, scene+through:
# D1's `into output.N` sat on the window's shown picture, which no wire
# names; as the wire it stood for the edges filter apart, by eye the same)
# (plan 36 T4: re-pinned for one golden re-recorded — wired-outputs' present
# scene+hands+through, 6029 px off by 1/255, mean 0.0029: its `history →
# acid.2` read the off look-back's copy pass, which no drawn node makes; as
# `scene → acid.2` the effect folds the scene's own texture)
GOLDENS_DIGEST = "886d0ce807e1504b546a48adaccd08b1c6bc9fc70f4c7bccccb9e64b6cc704a1"
# the render names the pipelines' graph used, gone in plan 35 T4 (V2: the
# render nodes are named in the new ids)
OLD_RENDER_NAMES = ("ghost", "history", "readout", "capture", "cover", "grounded", "fx",
                    "shown(history)")


def test_renaming_moved_no_golden():
    """Plan 35 T4: `tools/golden_frames.py --names` rewrote the fixtures'
    recorded render node names in the new ids (`lookback`, `hands.layer`,
    `lookback(capture)` …) and touched no `goldens` entry — the list is
    byte for byte the one T3 recorded."""
    import hashlib

    doc = _manifest()
    kept = [e for e in doc["goldens"] if e["preset"] not in GOLDENS_SINCE]
    assert len(kept) == 741
    assert hashlib.sha256(json.dumps(kept).encode()).hexdigest() == GOLDENS_DIGEST
    for slug, said in doc["fixtures"].items():
        names = said["present"].get("nodes") or []
        assert not set(names) & set(OLD_RENDER_NAMES), (slug, names)
        assert not any(n.startswith(("media.", "hands(")) for n in names), (slug, names)


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
    # plan 35 T4: the ends that ran, where the pipelines were
    got = lines({"gpu_ms": {"scene": 1.0}, "gpu_note": "", "ends": ["shown(acid)", "shown(copy)"]})
    assert got[-1] == "ends: shown(acid) · shown(copy)"


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


@pytest.fixture
def exact(ctx):
    """The context, on the renderer the goldens were recorded on — skips
    (never passes) on another."""
    doc = _manifest()
    tool = _tool()
    here, version = tool.renderer_name(ctx), tool.gl_version(ctx)
    if here != doc["renderer"]:
        pytest.skip(f"the golden frames expect GL_RENDERER {doc['renderer']!r} (GL_VERSION "
                    f"{doc['gl_version']!r}); this context is {here!r} (GL_VERSION "
                    f"{version!r}); re-record there with tools/golden_frames.py --record")
    return ctx


def _job_ids() -> list[str]:
    """Every job's id, from the manifest (collection reads no GL and imports
    no tool; `test_every_golden_belongs_to_one_of_the_tools_jobs` proves
    the set is the tool's `jobs()`)."""
    seen: dict[str, None] = {}
    for e in _manifest()["goldens"]:
        seen.setdefault(_tool_free_job_of(e))
    return list(seen)


def _tool_free_job_of(e: dict) -> str:
    # (= tools/golden_frames.py `job_of`, asserted below)
    return "cap" if "@" in e["state"] else f"{e['preset']}|{e['hands']}"


def test_every_golden_belongs_to_one_of_the_tools_jobs():
    """The goldens are drawn one job per test (`tool.jobs()`: a factory
    preset with the hands absent or present, a fixture, the cap): every
    entry belongs to exactly one job the tool draws, and every job has
    entries — so the jobs' tests together check every golden, and each
    job's test checks that it drew exactly its own entries."""
    tool = _tool()
    doc = _manifest()
    ids = [j.id for j in tool.jobs()]
    assert len(set(ids)) == len(ids) and set(ids) == set(_job_ids())
    assert all(tool.job_of(e) == _tool_free_job_of(e) for e in doc["goldens"])
    assert sum(1 for e in doc["goldens"] if tool.job_of(e) == "cap") == 1


@pytest.mark.parametrize("job_id", _job_ids())
def test_every_golden_frame_is_drawn_byte_for_byte(exact, job_id, tmp_path):
    """Each factory preset in each state it reaches, hands absent and
    present, each fixture, and the cap frame — one job per test: every
    full-resolution frame's SHA-256 is its golden's, and the job drew
    exactly its golden entries. Each frame is hashed as it is read and its
    pixels let go; only a frame that moved keeps them, for a contact sheet
    (golden PNG | now | difference) named in the failure."""
    doc = _manifest()
    tool = _tool()
    job = next(j for j in tool.jobs() if j.id == job_id)
    want = {f"{e['preset']}|{e['hands']}|{e['state']}": e for e in doc["goldens"]
            if tool.job_of(e) == job_id}
    shots, said = tool.run_job(job, keep=tool.moved_only(doc))
    assert [s.key for s in shots if s.key not in want] == [], "frames with no golden"
    assert sorted(s.key for s in shots) == sorted(want), "goldens not drawn"
    moved = tool.diff(shots, doc)
    if moved:
        sheet = tool.contact_sheet(moved, tmp_path / f"golden-diff-{job.slug}.png")
        here, version = tool.renderer_name(exact), tool.gl_version(exact)
        pytest.fail(f"{len(moved)} frames moved, recorded on {doc['renderer']!r} (GL_VERSION "
                    f"{doc['gl_version']!r}), drawn on {here!r} (GL_VERSION {version!r}): "
                    + ", ".join(s.key for s, _ in moved) + f" — contact sheet: {sheet}")
    if said is not None:
        recorded = {**doc["presets"], **doc.get("fixtures", {})}
        assert said == recorded[job.slug][job.hands], job_id


_SHIPPED_FIXTURES = ("palette-glass", "palette-hands", "acid-scene", "wired-outputs")


def _resave_sources() -> list[tuple[str, bool]]:
    """Every factory preset and fixture, by the manifest (its `presets` and
    `fixtures` are the tool's lists: the no-GL test above)."""
    doc = _manifest()
    return [*((slug, True) for slug in doc["presets"]),
            *((slug, False) for slug in doc["fixtures"])]


@pytest.mark.parametrize("slug,factory", _resave_sources(),
                         ids=[slug for slug, _ in _resave_sources()])
def test_every_preset_resaved_as_seven_draws_its_goldens(ctx, tmp_path, slug, factory):
    """Row 394: every factory preset and every fixture, saved untouched as
    `/7` (`headless.resave`, the road tools/migrate_library.py takes; plan
    36 T3) and drawn from that file on the golden rig (`picture`: hands
    present, the eight states as wiring), draws exactly its recorded
    goldens — on the renderer they were recorded on; on another, exactly
    what the original file draws there. A fixture whose D1 placements the
    retired builder laid on each output's switch state (`_placements_wait`)
    is drawn, old file and `/7`, as the rig ships (`SHIPPED`): the states
    are emulated only for an old file."""
    import json

    from hyperspace import headless

    doc = _manifest()
    tool = _tool()
    exact = tool.renderer_name(ctx) == doc["renderer"]
    path = (tool.ROOT / "hyperspace" / "library" / "presets" / f"{slug}.json" if factory
            else tool.FIXTURES / f"{slug}.json")
    raw, _, _ = headless.resave(path, tmp_path / "resaved", factory=factory)
    seven = tmp_path / "seven" / f"{slug}.json"
    seven.parent.mkdir()
    seven.write_bytes(raw)
    assert json.loads(raw)["schema"] == "hyperspace.preset/7", slug
    if slug in _SHIPPED_FIXTURES:
        got, _ = tool.picture(seven, slug=slug, states=tool.SHIPPED)
        assert got == tool.picture(path, slug=slug, states=tool.SHIPPED)[0], slug
        return
    got, _ = tool.picture(seven, slug=slug)
    if exact:
        golden = {(e["preset"], e["hands"], e["state"]): e["sha256"] for e in doc["goldens"]}
        want = [golden[(slug, "present", n)] for n, _ in tool.STATES]
    else:
        want, _ = tool.picture(path, slug=slug)
    assert got == want, slug


def test_a_value_moved_in_the_resaved_file_moves_the_picture(ctx, tmp_path):
    """The resave check can fail: party-trip, its `/7` brighter, is another
    picture."""
    import json

    from hyperspace import headless

    tool = _tool()
    path = tool.ROOT / "hyperspace" / "library" / "presets" / "party-trip.json"
    raw, _, _ = headless.resave(path, tmp_path / "bright", factory=True)
    bright = json.loads(raw)
    bright["values"]["view.bright"] = bright["values"]["view.bright"] * 0.5 + 0.1
    moved = tmp_path / "bright.json"
    moved.write_text(json.dumps(bright))
    assert tool.picture(moved, slug="party-trip")[0] != tool.picture(path, slug="party-trip")[0]


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
    # (plan 36 T4: the "add" composite laying the trail on — its one pass
    # is timed as the look-back's)
    assert r._graph.timed == ["scene", "lookback(cover)", "hands.layer", "lookback",
                              "composite", "shown(warp)", "lookback(capture)", "output.1"]
    # plan 30 D0 (decision 5): the effect that ran has its own line, before its end
    assert list(ms) == ["scene", "lookback(cover)", "hands.layer", "lookback", "composite",
                        "warp", "shown(warp)", "lookback(capture)", "output.1"]
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
