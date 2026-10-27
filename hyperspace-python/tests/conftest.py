"""Shared fixtures.

Every test runs with ``HYPERSPACE_HOME`` pointed at its own tmp_path
(audit L7), so nothing can read or write the owner's ~/Hyperspace by
accident — a test that needs a specific home still sets the variable
itself, on top of this. ``library.home()`` reads the variable on every
call, so there is no cache to clear.

``owner_home`` (plan 19 WP1) is a home shaped like the owner's, for every
test that proves a rule about the owner's files "on a copy".
"""

import os

import pytest

# ---------------------------------------------------------------- test tiers
# A bare `pytest` runs the fast tier in parallel (pyproject addopts:
# -n auto -m "not golden and not slow and not live"); `pytest --all` runs
# everything. The markers are applied here, by name, so no test file carries
# them: re-measure with `pytest --all --durations=60` and edit these tables
# when a test is added or its time changes.

_FAST = "not golden and not slow and not live"      # = pyproject's addopts -m
_GOLDEN_FILES = {"test_golden_frames.py"}
# whole files: torch on MPS, or loopbacks with multi-second timeouts
_LIVE_FILES = {"test_media_live.py", "test_media_publish.py"}
_SLOW_FILES = {"test_dream.py"}
# single tests, "file::function" (any parametrisation)
_LIVE_TESTS = {
    "test_media_render.py::test_a_syphon_frame_samples_through_the_fit_pass",
    "test_media_core.py::test_bad_file_is_an_error",      # polls; fails under load
}
_SLOW_TESTS = {
    "test_media_core.py::test_heic_opens",
    "test_media_channels.py::test_close_with_a_hung_source_returns_within_two_seconds",
    "test_media_channels.py::test_rapid_switching_with_slow_closes_stays_fast_and_balances",
    "test_media_channels.py::test_a_video_stuck_opening_never_jams_the_closer",
    "test_media_channels.py::test_a_slow_close_never_holds_the_frame_thread",
    "test_graph_free.py::test_every_old_preset_saves_as_six_and_is_a_fixed_point",
    "test_undo.py::test_an_idle_app_makes_no_step",
    "test_undo.py::test_a_performers_round_off_lights_no_dot",
    "test_graph_areas.py::test_every_node_has_one_area_and_the_three_concerns_are_separate",
    "test_ghost.py::test_tethers_draw_only_when_toggled_and_keep_the_alpha",
    "test_ghost.py::test_a_style_never_draws_the_guide",
    "test_analyzer.py::test_manual_normalisation_makes_trim_monotonic",
    "test_geometry.py::test_warm_all_fills_every_shapes_caches",
    "test_app_boundary.py::test_the_app_exits_within_two_seconds_with_reads_and_a_transcode_stuck",
    "test_graph_legible.py::test_every_node_has_a_label_and_a_hover",
    "test_routing.py::test_every_factory_preset_lands_the_same_values_one_frame_earlier",
    "test_graph_delay.py::test_nothing_of_plan_33_has_an_own_size",
    "test_plan12_presets.py::test_each_hand_axis_moves_its_target_as_the_table_says",
    "test_migrate_library.py::test_the_real_picture_check_passes_an_old_preset",
    "test_watchdog.py::test_a_stall_that_holds_the_gil_is_caught_by_the_c_backstop",
    "test_render.py::test_nothing_aimed_at_the_faces_is_the_old_frame_exactly",
    "test_render.py::test_every_layout_and_motion_draws_any_count",
    "test_desk_coverage.py::test_the_committed_report_is_fresh_and_regenerates_byte_identical",
    "test_presets.py::test_each_orbit_axis_moves_its_camera_param_as_its_row_says",
}


def pytest_addoption(parser):
    parser.addoption("--all", action="store_true",
                     help="run every tier (golden, slow, live), not just the fast one")


def pytest_configure(config):
    # (an explicit `-m` with --all still wins: only the default is lifted)
    if config.getoption("--all") and config.option.markexpr == _FAST:
        config.option.markexpr = ""


def pytest_collection_modifyitems(config, items):
    for item in items:
        path = item.path.name
        key = f"{path}::{item.originalname or item.name}"
        if path in _GOLDEN_FILES:
            item.add_marker(pytest.mark.golden)
        if path in _LIVE_FILES or key in _LIVE_TESTS:
            item.add_marker(pytest.mark.live)
            # loopbacks share global Syphon / NDI names: one worker at a time
            item.add_marker(pytest.mark.xdist_group("live"))
        if path in _SLOW_FILES or key in _SLOW_TESTS:
            item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)
def _library_home(tmp_path):
    # set in os.environ directly, not through monkeypatch: a test that calls
    # monkeypatch.undo() mid-way would otherwise drop the variable and run
    # its remaining lines against the owner's real home
    before = os.environ.get("HYPERSPACE_HOME")
    os.environ["HYPERSPACE_HOME"] = str(tmp_path / "home")
    yield
    if before is None:
        os.environ.pop("HYPERSPACE_HOME", None)
    else:
        os.environ["HYPERSPACE_HOME"] = before


@pytest.fixture(autouse=True)
def _no_real_midi(monkeypatch):
    """No test reaches the machine's MIDI: the port lists are empty and an
    open raises, unless the test patches mido itself (a later setattr wins).
    A real scan creates a CoreMIDI client, which reaches the owner's desk
    and, when CoreMIDI refuses one, aborts the process inside rtmidi where
    no `except` can catch it (the crash of 2026-10-04 22:36)."""
    import mido

    def closed(name=None, *a, **k):
        raise OSError(f"the tests have no MIDI ports ({name})")

    monkeypatch.setattr(mido, "get_input_names", list)
    monkeypatch.setattr(mido, "get_output_names", list)
    monkeypatch.setattr(mido, "open_input", closed)
    monkeypatch.setattr(mido, "open_output", closed)


@pytest.fixture(autouse=True)
def _renderers_draw_todays_frame(request, monkeypatch):
    """Plan 36 T3 (W3): the app's `Renderer` starts on the empty frame
    (`graph.EMPTY`, black) until a preset's graph lands. The tests' bare
    renderers draw a scene to look at, so here — the tests' word, never the
    app's — a new one is handed today's frame as the one-way migration
    writes it for a section-less old preset (`graphmigrate.wired_wiring(
    Wiring())`). A test marked `empty_frame` gets the app's own."""
    if request.node.get_closest_marker("empty_frame") is not None:
        return
    from hyperspace import render
    from hyperspace.graph import Wiring
    from hyperspace.graphmigrate import look_of, wired_wiring

    init = render.Renderer.__init__

    def today(self, *a, **k):
        init(self, *a, **k)
        # (plan 36 T4: its look-back as the old words had it — drawn while
        # `dream.on` was on, with the dream while its mix is above 0)
        st = self.lookback.state
        self.wiring = wired_wiring(Wiring(), look_of({"dream.on": bool(st.on),
                                                      "dream.mix": st.mix}))

    monkeypatch.setattr(render.Renderer, "__init__", today)


@pytest.fixture(autouse=True)
def _no_undo_left_installed():
    """`undo.install` is one per process (the app has one Undo): a test
    that installs one must not leave it for the next test's push sites."""
    yield
    from hyperspace import undo

    undo.install(None)


def opened_last(home, show: str = "house"):
    """A home whose last opened show is `show` (library.LAST_SHOW) — what
    the tests written against the house moods, the factory default until
    plan 14 WP3 made the party show the one a fresh home opens, stand on."""
    from pathlib import Path

    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    (home / "last_show").write_text(f"{show}\n")
    return home


# ------------------------------------------------ plan 19: a home like the owner's

# the three presets `owner_home` holds, saved through `Presets.save_as`
OWNER_PRESETS = ("NIGHT ONE", "NIGHT TWO", "NIGHT THREE")
# in NIGHT TWO: a pad of clip row 4 the owner re-aimed, as its desk row,
# and a device knob the owner learned (knob 1–8, target)
OWNER_PAD = {"source": "note:2:56", "target": "fx.acid.on", "op": "toggle", "feedback": "led"}
OWNER_KNOB = (3, "fx.mix")
# the session row of bindings.json the owner changed: (source, new target)
OWNER_ROW = ("cc:0:15", "master.gain")
OWNER_SHOWS = ("mine", "party")           # each with an eight-name bank


def old_shape_pads() -> list[dict]:
    """The sixteen shape pads of clip rows 4 and 5 as a preset saved before
    plan 19 WP2 holds them in its `desk` (`preset.desk_json` of the rows
    `apc40.DEFAULT_MAP` had on the preset layer): pad k of row 4 sets shape
    k, pad k of row 5 shape 8 + k."""
    from hyperspace import apc40, preset
    from hyperspace.routing import Binding

    return preset.desk_json(
        Binding(f"note:{k}:{apc40.N_CLIP[3 + row]}", "view.shape", "set", float(8 * row + k),
                feedback="led", on=apc40.GREEN, layer="preset")
        for row in range(2) for k in range(8))


def boot_home(home):
    """The app's construction order (app.main), headless, over `home` as it
    is: the library, the registry, the table from `<home>/bindings.json`,
    the router, the presets, the launch's migration and the startup preset."""
    from types import SimpleNamespace

    from hyperspace import lfo, preset, routing, tempo
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.fx import FxState
    from hyperspace.library import Library
    from hyperspace.lookback import DreamState
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState

    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.project,
                         dream=DreamState(), fx=FxState())
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    lib.on_load("band", control.scene_loaded)
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    table = routing.Bindings.load(routing.bindings_path(home), legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    router = routing.Router(reg, table)
    presets = preset.Presets(lib, reg, router)
    preset.migrate_home(lib, router)
    lib.project.load_startup()
    return SimpleNamespace(lib=lib, reg=reg, view=view, control=control, chain=chain,
                           router=router, presets=presets, clock=clock, home=home)


def _with_old_pads(path, re_aimed: dict | None = None) -> None:
    """A preset file as a build from before plan 19 WP2 saved it: every one
    of the sixteen pads of clip rows 4 and 5 has its row in `desk` — the
    old shape row, or `re_aimed` on its pad. Today's writer puts them there
    itself and the file is left alone; once the desk stops mapping those
    pads (WP2) they are written in, in the kind's own text."""
    import json

    from hyperspace import preset

    doc = json.loads(path.read_text())
    # (the fresh layer's device knobs, apc40.SCENE, came with plan 19 WP3:
    # a preset saved before it had none — its knobs dark, or what was learned)
    scene = preset.desk_json(b for b in preset.fresh_desk() if preset._is_device_knob(b))
    desk = [row for row in doc.get("desk") or [] if row not in scene]
    have = {row["source"] for row in desk}
    want = [re_aimed if re_aimed and row["source"] == re_aimed["source"] else row
            for row in old_shape_pads()]
    missing = [row for row in want if row["source"] not in have]
    if missing or len(desk) != len(doc.get("desk") or []):
        doc["desk"] = desk + missing
        path.write_text(preset.dumps(doc))


def far_pads() -> list[str]:
    """The sources of the bank's sixteen pads on clip rows 4 and 5 (slots
    9–24), in slot order."""
    from hyperspace import apc40, library

    return [f"note:{ch}:{n}" for n, ch in apc40.BANK_PADS[library.F_KEYS:]]


def _without_bank_pads(path) -> None:
    """A bindings.json as a build from before plan 19 WP2 wrote it: no row
    on the pads of clip rows 4 and 5 (they were the preset layer's shape
    pads, which the session file never held). Today's writer puts the
    bank's sixteen rows there, so they are taken out again, in the table's
    own text — the rest of the file is byte for byte what was written."""
    import json

    from hyperspace import routing

    doc = json.loads(path.read_text())
    far = set(far_pads())
    rows = [row for row in doc["bindings"]
            if not (row["source"] in far and row["target"] == "preset.select")]
    if len(rows) != len(doc["bindings"]):
        path.write_text(routing.dumps_doc(dict(doc, bindings=rows)))


@pytest.fixture()
def owner_home(tmp_path):
    """`build_owner_home` in a temp folder of the test's own: a home shaped
    like the owner's, for a rule about the owner's files proved "on a
    copy". Returns the home's path, with ``HYPERSPACE_HOME`` pointing at
    it. A test opens it with `boot_home(owner_home)` and compares what its
    rule says is untouched byte for byte (`tree`)."""
    home = tmp_path / "owner-home"
    os.environ["HYPERSPACE_HOME"] = str(home)       # (the autouse fixture puts it back)
    return build_owner_home(home)


def build_owner_home(home):
    """Make `home` (a folder that does not exist yet) a home shaped like
    the owner's after a night on the build from before plan 19, by running
    the writers (`Presets.save_as`, `Project.save`, `Bindings.write`,
    `placement.save`, `to_trash`), not by hand-written JSON, so it tracks
    the formats (tools/bank_demo.py builds its home here too):

    - ``projects/mine.hyp.json`` and ``projects/party.hyp.json`` (a user
      copy of the party show), each with an **eight-name** bank; ``mine``
      names the three presets below and is the show opened last;
    - ``presets/``: NIGHT ONE, NIGHT TWO, NIGHT THREE (`OWNER_PRESETS`),
      each with a `desk` holding the sixteen shape pads of clip rows 4–5
      (`old_shape_pads`); NIGHT TWO has one of those pads re-aimed
      (`OWNER_PAD`) and a learned device knob (`OWNER_KNOB`);
    - ``bindings.json`` as the table wrote it before plan 19 WP2 — no row
      on clip rows 4 and 5 (`_without_bank_pads`) — one session row changed
      (`OWNER_ROW`);
    - ``last_show``, ``windows.json``, a ``stall.log``, a file under
      ``weights/`` and one file already in ``trash/presets/``.

    Returns `home`. Never run on a real home: it is built from nothing."""
    import json
    from pathlib import Path

    from hyperspace import library, placement, preset
    from hyperspace.routing import Binding

    home = Path(home)
    if home.exists():
        raise FileExistsError(f"{home}: an owner-like home is built in a new folder")
    r = boot_home(home)                             # a fresh home: the factory party show
    reg, pr, table = r.reg, r.lib.project, r.router.table
    one, two, three = OWNER_PRESETS
    # NIGHT ONE: TUMBLE, dimmer
    reg["view.bright"].set(reg["view.bright"].value * 0.8)
    r.presets.save_as(one)
    # NIGHT TWO: a pad of row 4 re-aimed and a device knob learned
    rows = [b for b in table.desk() if b.source != OWNER_PAD["source"]]
    rows.append(Binding.from_json({**OWNER_PAD, "layer": "preset"}))
    rows.append(preset.device_knob(*OWNER_KNOB))
    table.set_desk(rows, load=False)
    reg["view.speed"].set(reg["view.speed"].value * 0.5)
    r.presets.save_as(two)
    # NIGHT THREE: WAKE with its eight device knobs, the trail longer
    r.presets.load("WAKE")
    reg["dream.fade"].set_norm(0.7)
    r.presets.save_as(three)
    folder = home / library.PRESETS
    for name in OWNER_PRESETS:
        _with_old_pads(folder / f"{library.slug(name)}.json",
                       OWNER_PAD if name == two else None)
    # the user copy of the party show, with the eight names it had before
    # plan 19 gave the factory one a ninth
    pr.load("party", startup=False)
    pr.bank[library.F_KEYS:] = [None] * (len(pr.bank) - library.F_KEYS)
    pr.save()
    # mine: the three presets and five of the party's, starting on NIGHT ONE
    pr.bank[:3] = [one, two, three]
    pr.startup = one
    pr.save("mine")
    # bindings.json: the session's rows, one of them the owner's own
    source, target = OWNER_ROW
    row = next(b for b in table.bindings if b.source == source and b.layer != "preset")
    row.target = target
    table.write()
    _without_bank_pads(table.path)
    placement.save(home, (40, 60, 960, 900), [(1040, 60, 1280, 720)],
                   [placement.Screen("test", 0, 0, 2560, 1440)])
    (home / "stall.log").write_text("2026-10-03 23:58:01 stall 2.4 s in frame (dream)\n")
    (home / "weights").mkdir()
    (home / "weights" / "model.safetensors").write_bytes(bytes(range(256)) * 4)
    assert library.to_trash(folder / f"{library.slug(one)}.json", home) is not None
    for show in OWNER_SHOWS:
        doc = json.loads((home / "projects" / f"{show}.hyp.json").read_text())
        assert len(doc["bank"]) == library.F_KEYS, show
    return home


def tree(home, *, but: tuple[str, ...] = ()) -> dict:
    """Every file under `home` — {path: (bytes, mtime_ns)} — less those
    whose relative path starts with one of `but`: what "untouched, byte
    for byte" compares."""
    from pathlib import Path

    home = Path(home)
    return {p.relative_to(home).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(home.rglob("*"))
            if p.is_file() and not p.relative_to(home).as_posix().startswith(but)}
