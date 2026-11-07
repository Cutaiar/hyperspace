"""One row per display (wave 5 SC2): the file both Macs share, what the rows want open, a launch
over stand-in monitors, and the rows on the real panel. `tests/test_root_frame.py` has a render
on two displays with different flips through real GL."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from imgui_bundle import imgui
from test_app_boundary import _PlaceGlfw, _TwinGlfw
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace import app, config, displays, placement, sharedfile, ui_displays, ui_graph
from hyperspace.displays import CONTROL, COPY, FILE, SCHEMA, DisplayList, Running, row, wanted
from hyperspace.outputs import Slot, Switches
from hyperspace.placement import Screen
from hyperspace.ui import PAGE_KEYS

LAPTOP = Screen("Built-in", 0, 38, 1728, 1041, (0, 0))
TV_LEFT = Screen("TV", 1728, 0, 1920, 1080, (1728, 0))
TV_RIGHT = Screen("TV", 3648, 0, 1920, 1080, (3648, 0))
SCREENS = [LAPTOP, TV_RIGHT, TV_LEFT]       # listed out of order, as a plug order may


@pytest.fixture
def macs(tmp_path):
    """The library, and two homes."""
    root, one, two = tmp_path / "Drive", tmp_path / "one", tmp_path / "two"
    for d in (root, one, two):
        d.mkdir()
    return root, one, two


def on_disk(root: Path) -> dict:
    return json.loads((root / FILE).read_text())["displays"]


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def opened(root, home, seed=None, **kw) -> DisplayList:
    store = DisplayList(root, home, seed=seed, **kw)
    store.sync()
    return store


# ---- what should be open


def test_a_display_has_one_target_and_a_target_may_go_to_several():
    want = wanted({"Built-in": row(CONTROL), "TV #1": row("output.1", flip_x=True),
                   "TV #2": row("output.1", fullscreen=True)}, SCREENS)
    assert want.control.display == "Built-in"
    (left, right) = want.renders[1]
    assert (left.display, left.index, left.flip_x, left.fullscreen) == ("TV #1", 2, True, False)
    assert (right.display, right.index, right.flip_x, right.fullscreen) == ("TV #2", 1, False, True)
    assert want.shown == {"Built-in": CONTROL, "TV #1": "output.1", "TV #2": "output.1"}


def test_the_control_window_goes_to_one_whatever_two_macs_wrote():
    want = wanted({"Built-in": row(CONTROL), "TV #1": row(CONTROL), "TV #2": row("output.9")}, SCREENS)
    assert want.control.display == "Built-in", "the first across the desk"
    assert want.shown["TV #1"] == "" and want.shown["TV #2"] == ""
    assert not want.renders
    assert len(want.notes) == 2 and "goes to one" in want.notes[0] and "output.9" in want.notes[1]


def test_a_row_on_a_display_away_says_so_and_opens_nothing():
    want = wanted({"Projector": row("output.2")}, [LAPTOP])
    assert not want.renders and want.away == {2: ["Projector"]} and want.shown == {"Built-in": ""}


def test_a_lone_display_and_the_first_of_a_pair_are_one_memory():
    assert wanted({"TV": row("output.1")}, [LAPTOP, TV_LEFT, TV_RIGHT]).shown["TV #1"] == "output.1"
    assert wanted({"TV #1": row("output.1")}, [LAPTOP, TV_LEFT]).shown["TV"] == "output.1"
    both = wanted({"TV": row("output.1"), "TV #1": row("output.2")}, [TV_LEFT, TV_RIGHT])
    assert both.shown["TV #1"] == "output.2" and both.shown["TV #2"] == ""


def test_an_order_of_plugging_doesnt_move_a_job():
    rows = {"TV #1": row("output.1"), "TV #2": row("output.2")}
    a = wanted(rows, [LAPTOP, TV_LEFT, TV_RIGHT])
    b = wanted(rows, [LAPTOP, TV_RIGHT, TV_LEFT])
    assert a.renders[1][0].index == 1 and b.renders[1][0].index == 2
    assert a.renders[2][0].index == 2 and b.renders[2][0].index == 1


def test_what_waits_for_a_restart_is_what_differs_from_whats_open():
    rows = {"Built-in": row(CONTROL), "TV #1": row("output.2")}
    opened_now = {"Built-in": CONTROL, "TV #1": "output.1"}
    assert displays.pending(rows, SCREENS, opened_now) == [("TV #1", "output.2")]
    assert displays.pending(rows, SCREENS, {"Built-in": CONTROL, "TV #1": "output.2"}) == []


# ---- the seed


def _cfg(**output):
    return {"output": {**config.DEFAULTS["output"], **output}}


def test_the_seed_says_where_each_window_would_have_opened():
    notes = []
    cfg = _cfg(monitor="TV #2", control_monitor=0, fullscreen=True)
    assert displays.seed_rows(cfg, SCREENS, {}, notes) == {
        "TV #2": row("output.1", fullscreen=True), "Built-in": row(CONTROL)}
    assert not notes


def test_the_seed_of_a_list_keeps_each_entrys_flips_and_says_a_clash():
    notes = []
    cfg = _cfg(screens=[{**config.SCREEN, "monitor": 1, "flip_x": True},
                        {**config.SCREEN, "monitor": "TV #1", "fullscreen": True},
                        {**config.SCREEN, "monitor": 1},
                        {**config.SCREEN, "window": False, "syphon": "x"}])
    rows = displays.seed_rows(cfg, SCREENS, {}, notes)
    assert rows["TV #2"] == row("output.1", flip_x=True)
    assert rows["TV #1"] == row("output.2", fullscreen=True)
    assert "output.3" not in {e["target"] for e in rows.values()}
    assert len(notes) == 1 and "output 3" in notes[0] and "one target" in notes[0]


def test_the_seed_of_no_say_is_where_the_windows_were_and_the_control_floats_on_a_render():
    notes = []
    rows = displays.seed_rows(_cfg(), [LAPTOP], {}, notes)
    assert rows == {"Built-in": row("output.1")}, "one display: the render has it, the control floats"
    seen = {"render": [{"x": 3700, "y": 100, "w": 800, "h": 500}], "control": {"x": 100, "y": 90, "w": 800, "h": 800}}
    rows = displays.seed_rows(_cfg(), [LAPTOP, TV_LEFT, TV_RIGHT], seen, notes)
    assert rows == {"TV #2": row("output.1"), "Built-in": row(CONTROL)}


def test_a_name_away_is_remembered_and_an_index_away_is_not():
    notes = []
    assert displays.seed_rows(_cfg(monitor="Projector", control_monitor=9), [LAPTOP], {}, notes) == {
        "Projector": row("output.1")}
    assert any("control_monitor = 9" in n for n in notes)


# ---- the file


def test_a_first_launch_makes_the_file_and_a_later_one_doesnt_read_the_config(macs):
    root, one, _ = macs
    notes = []
    opened(root, one, seed={"TV": row("output.1")}, notes=notes)
    assert on_disk(root) == {"TV": row("output.1")}
    assert json.loads((root / FILE).read_text())["schema"] == SCHEMA == "displays/1"
    assert any("made from" in n for n in notes)
    notes = []
    opened(root, one, seed={"TV": row("output.2"), "New": row("output.3")}, config_says=["monitor"], notes=notes)
    assert on_disk(root) == {"TV": row("output.1")}, "the seed is spent"
    assert any("config.toml's monitor isn't read" in n for n in notes)


def test_a_mac_that_finds_rows_adds_what_they_lack_and_the_shared_row_stands(macs):
    root, one, two = macs
    opened(root, one, seed={"TV": row("output.1")})
    opened(root, two, seed={"TV": row("output.2"), "DELL": row(CONTROL)})
    assert on_disk(root) == {"TV": row("output.1"), "DELL": row(CONTROL)}


def test_a_config_that_didnt_read_seeds_nothing_and_spends_nothing(macs):
    root, one, _ = macs
    held = opened(root, one, seed={"TV": row("output.1")}, hold_seed=True)
    assert not (root / FILE).exists(), "a default nobody chose isn't written"
    assert held.current == {"TV": row("output.1")} and "didn't read" in held.said
    # a display chosen meanwhile is kept
    held.set("DELL", target="output.2")
    held.sync()
    assert list(on_disk(root)) == ["DELL"]
    again = opened(root, one, seed={"TV": row("output.1")})
    assert set(on_disk(root)) == {"TV", "DELL"} and again.seeded, "the next good launch reads it"


def test_the_open_reads_the_configured_library_and_a_bad_toml_holds(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    root.mkdir()
    home.mkdir()
    cfg = {**_cfg(monitor=0), "library": {"path": str(root)}}
    store = DisplayList.open(cfg, home, [LAPTOP])
    store.sync()
    assert on_disk(root) == {"Built-in": row("output.1")} and store.path.parent == root
    assert (home / COPY).exists()
    bad = {**_cfg(), "library": {"path": str(root)}, "error": "config.toml: bad"}
    (home / COPY).unlink()
    store = DisplayList.open(bad, home, [LAPTOP])
    assert not store.seeded and store.held


def test_two_macs_converge_with_no_ping_pong(macs, monkeypatch):
    root, one, two = macs
    wrote = []
    real = sharedfile.put
    monkeypatch.setattr(sharedfile, "put", lambda p, t, n=None: (wrote.append(p.name), real(p, t, n)))
    wall_a, wall_b = Clock(100.0), Clock(100.0)
    a = opened(root, one, wall=wall_a)
    b = opened(root, two, wall=wall_b)
    a.set("TV", target="output.1")
    wall_b.t = 101.0
    b.set("TV", target="output.2")      # the same display, chosen on both, the later wins
    b.set("DELL", target=CONTROL)
    for _ in range(3):
        a.sync()
        b.sync()
    assert a.rows == b.rows == on_disk(root)
    assert read(a, "TV") == "output.2" and read(a, "DELL") == CONTROL
    wrote.clear()
    for _ in range(6):
        a.sync()
        b.sync()
    assert FILE not in wrote, "the file says it, so neither writes"


def read(store, tag):
    return displays.read_row(store.rows[tag])["target"]


def test_an_older_copy_drive_lands_over_ours_loses_once(macs):
    root, one, _ = macs
    store = opened(root, one, wall=Clock(500.0))
    store.set("TV", target="output.2")
    store.sync()
    good = (root / FILE).read_text()
    old = {"TV": row("output.1", at=1.0), "Gone": row("output.3", at=2.0)}
    (root / FILE).write_text(json.dumps({"schema": SCHEMA, "displays": old}))
    store.sync()
    assert on_disk(root)["TV"] == store.rows["TV"] and read(store, "TV") == "output.2"
    assert read(store, "Gone") == "output.3", "and what it held that we didn't is kept"
    assert json.loads(good)["displays"]["TV"] == on_disk(root)["TV"]


def test_an_edit_beats_the_row_it_replaces_whatever_this_macs_clock_says(macs):
    root, one, _ = macs
    (root / FILE).write_text(json.dumps({"schema": SCHEMA, "displays": {"TV": row("output.1", at=9e9)}}))
    store = opened(root, one, wall=Clock(5.0))
    store.set("TV", target="output.2")
    store.sync()
    assert on_disk(root)["TV"]["target"] == "output.2"


@pytest.mark.parametrize("junk", ['{"schema": "displ', "not json", '{"schema": "displays/2", "displays": {}}',
                                  '{"schema": "displays/1", "displays": {"TV": 3}}', "[1]", "\xff"])
def test_a_file_half_synced_or_a_newer_builds_is_never_raised_or_written_over(macs, junk):
    root, one, _ = macs
    (root / FILE).write_text(junk, encoding="latin-1")
    store = opened(root, one, seed={"TV": row("output.1")})
    assert (root / FILE).read_text(encoding="latin-1") == junk
    assert store.current == {"TV": row("output.1")} and "could not be read" in store.said
    store.set("DELL", target="output.2")
    store.sync()
    assert (root / FILE).read_text(encoding="latin-1") == junk
    # good again: what stood goes in, with no restart
    (root / FILE).write_text(json.dumps({"schema": SCHEMA, "displays": {"Other": row("output.3")}}))
    store.sync()
    assert set(on_disk(root)) == {"TV", "DELL", "Other"} and store.said == ""


def test_the_library_not_there_falls_back_on_this_macs_copy_and_says_so(macs):
    root, one, _ = macs
    opened(root, one, seed={"TV": row("output.1")})
    gone = root.with_name("elsewhere")
    root.rename(gone)
    store = opened(root, one)
    assert store.rows == {"TV": row("output.1")} and "isn't there" in store.said
    assert not root.exists(), "nothing is made in a folder that isn't there"
    store.set("TV", target="output.2")
    store.sync()
    json_copy = json.loads((one / COPY).read_text())
    assert json_copy["displays"]["TV"]["target"] == "output.2", "the change waits in the copy"
    # a restart while it's away: the copy carries the change
    store = opened(root, one)
    assert read(store, "TV") == "output.2"
    # back, with no restart
    gone.rename(root)
    store.sync()
    assert on_disk(root)["TV"]["target"] == "output.2" and store.said == ""


def test_a_stalled_drive_holds_up_neither_the_launch_nor_a_frame(macs, monkeypatch):
    root, one, _ = macs
    release = threading.Event()
    real = displays._cycle
    monkeypatch.setattr(displays, "LAUNCH_S", 0.05)
    monkeypatch.setattr(displays, "_cycle", lambda *a: (release.wait(5), real(*a))[1])
    clock = Clock(10.0)
    store = DisplayList(root, one, seed={"TV": row("output.1")}, clock=clock)
    assert store.rows == {"TV": row("output.1")} and "isn't answering" in store.said
    store.set("TV", target="output.2")
    store.look()
    clock.t += displays.STALL_S + 1
    store.look()
    assert "isn't answering" in store.said
    release.set()
    store.sync()
    assert on_disk(root)["TV"]["target"] == "output.2" and store.said == ""


def test_a_quiet_file_costs_one_stat_a_look(macs, monkeypatch):
    root, one, _ = macs
    clock = Clock(10.0)
    store = opened(root, one, seed={"TV": row("output.1")}, clock=clock)
    store.sync()
    reads = []
    real = displays._read
    monkeypatch.setattr(displays, "_read", lambda p, r: reads.append(1) or real(p, r))
    for _ in range(4):
        clock.t += displays.LOOK_S
        store.look()
        store._shared.wait(5)
        store._take()
    assert not reads


def test_the_file_is_the_meta_controllers_and_no_loadable_patch_reaches_it():
    """Two layers: the patch's modules don't import it, nor does the library."""
    pkg = Path(displays.__file__).parent
    for name in ("library", "loadable", "patches", "graph", "render"):
        src = (pkg / f"{name}.py").read_text()
        assert "import displays" not in src and "from .displays" not in src, name


# ---- a launch over stand-in monitors


class _Fake(_PlaceGlfw):
    def __init__(self, mons=None):
        super().__init__(mons)
        self.titles: dict = {}

    def create_window(self, w, h, title, mon, share):
        win = super().create_window(w, h, title, mon, share)
        self.titles[win] = title
        return win


def _launch(monkeypatch, rows, cfg=None, home=None, fake=None):
    g = fake if fake is not None else _Fake()
    monkeypatch.setattr(app, "glfw", g)
    cfg = cfg if cfg is not None else _cfg()
    want = wanted(rows, placement.screens(g))
    slots, ctrl = app._windows(False, cfg, home, "root", want)
    return g, slots, ctrl, cfg, want


def test_every_output_has_a_slot_from_launch_with_or_without_a_display(monkeypatch):
    """So `output.N.*` never appear mid-run (SC3b), and N never renumbers."""
    from hyperspace.overlay import register_switches
    from hyperspace.params import Registry

    g, slots, ctrl, _cfgd, _ = _launch(monkeypatch, {"Projector": row("output.3")})
    assert [s.n for s in slots] == [1, 2, 3, 4]
    assert slots[2].opened and not slots[0].opened and not slots[1].opened and not slots[3].opened
    assert g.pos[slots[2].win] == (1728 + 16, 16)
    assert set(g.size) == {slots[2].win, ctrl}
    reg = Registry()
    ids = register_switches(reg, slots)
    assert {f"output.{n}.{k}" for n in (1, 2, 3, 4) for k in ("scene", "hands", "flip_x", "flip_y", "dim")} == set(ids)


def test_output_1_with_no_display_has_no_window_and_the_control_window_still_opens(monkeypatch):
    from hyperspace.params import Registry

    cfg = _cfg(monitor=1, fullscreen=True)
    g, slots, ctrl, cfg, _ = _launch(monkeypatch, {"Built-in": row(CONTROL)}, cfg)
    assert slots[0].win is None and ctrl and set(g.size) == {ctrl}
    assert g.pos[ctrl][0] < 1728
    assert cfg["output"]["monitor"] == -1 and cfg["output"]["fullscreen"] is False, "the rows say"
    out = app._make_output(slots[0].win, Registry(), cfg)
    out.apply()                     # no window: nothing to do, nothing raised
    assert out.windowed_rect() is None


def test_a_render_on_two_displays_opens_a_window_on_each_with_its_own_flips(monkeypatch):
    fake = _TwinGlfw({"Built-in": (0, 38, 1728, 1041), "TV|b": (3648, 0, 1920, 1080), "TV|a": (1728, 0, 1920, 1080)})
    fake.titles = {}
    rows = {"Built-in": row(CONTROL), "TV #1": row("output.1", flip_x=True), "TV #2": row("output.1", flip_y=True, fullscreen=True)}
    g, slots, ctrl, cfg, want = _launch(monkeypatch, rows, fake=fake)
    one = slots[0]
    assert one.display == "TV #1" and g.pos[one.win] == (1728 + 16, 16)
    assert (one.switches.flip_x, one.switches.flip_y) == (True, False), "its first display's"
    (also,) = one.also
    assert also.display == "TV #2" and g.pos[also.win] == (3648 + 16, 16)
    assert (also.flip_x, also.flip_y) == (False, True)
    assert app._also_output(also, want.renders[1][1]).fullscreen is True
    assert app._slot_windows(slots)[:2] == [one.win, also.win]
    assert displays.opened_of(slots, want.control) == {"TV #1": "output.1", "TV #2": "output.1", "Built-in": CONTROL}
    assert g.pos[ctrl][0] < 1728
    assert not cfg.get("notes")


def test_a_further_window_that_wont_open_goes_and_the_first_stands(monkeypatch, capsys):
    fake = _TwinGlfw({"TV|a": (0, 0, 1920, 1080), "TV|b": (1920, 0, 1920, 1080)})
    real = fake.create_window
    fake.create_window = lambda w, h, t, m, s: None if "TV #2" in t else real(w, h, t, m, s)
    _, slots, _, cfg, _ = _launch(monkeypatch, {"TV #1": row("output.2"), "TV #2": row("output.2")}, fake=fake)
    assert slots[1].opened and slots[1].also == []
    assert any("could not be created" in n for n in cfg["notes"])


def test_a_spot_goes_by_the_display_not_the_outputs_place(monkeypatch, tmp_path, capsys):
    """windows.json: `render[k]` meant an output's place, which a row can now move."""
    fake = _Fake()
    monkeypatch.setattr(app, "glfw", fake)
    scr = placement.screens(fake)
    placement.save(tmp_path, None, [(100, 100, 800, 500)], scr, {"Projector": (1900, 120, 1000, 700)})
    doc = placement.load(tmp_path)
    assert doc["schema"] == "hyperspace.windows/1" and doc["displays"]["Projector"]["x"] == 1900
    assert doc["render"][0]["x"] == 100, "still there for an older build"
    g, slots, *_ = _launch(monkeypatch, {"Projector": row("output.3")}, home=tmp_path)
    assert g.pos[slots[2].win] == (1900, 120) and g.size[slots[2].win] == (1000, 700)
    # the other display's output finds its own, not the output's old place
    placement.save(tmp_path, None, [], scr, {"Built-in": (30, 90, 700, 500)})
    g, slots, *_ = _launch(monkeypatch, {"Built-in": row("output.3")}, home=tmp_path)
    assert g.pos[slots[2].win] == (30, 90)
    assert placement.load(tmp_path)["displays"]["Projector"]["x"] == 1900, "and each keeps its own"


def test_the_exits_save_every_windows_spot_by_its_display(monkeypatch, tmp_path):
    from hyperspace.overlay import Output

    fake = _TwinGlfw({"TV|a": (0, 0, 1920, 1080), "TV|b": (1920, 0, 1920, 1080)})
    rows = {"TV #1": row("output.2"), "TV #2": row("output.2")}
    _, slots, ctrl, *_ = _launch(monkeypatch, rows, fake=fake)

    class Backend:
        def window_rect(self, win):
            return (*fake.pos[win], *fake.size[win])

    two = slots[1]
    two.output = Output(two.win, Backend())
    two.also[0].output = Output(two.also[0].win, Backend())
    app._save_windows(tmp_path, None, ctrl, None, [s.output for s in slots[1:]], slots)
    doc = placement.load(tmp_path)
    assert doc["displays"]["TV #1"]["x"] == 16 and doc["displays"]["TV #2"]["x"] == 1936


def test_a_publisher_with_no_display_keeps_publishing_and_an_empty_slot_is_not_drawn(monkeypatch):
    cfg = _cfg(screens=[{**config.SCREEN}, {**config.SCREEN, "name": "td", "syphon": "RIG"}])
    _, slots, *_ = _launch(monkeypatch, {"Built-in": row("output.1")}, cfg)
    assert slots[1].publish_only and slots[1].drawn and slots[1].syphon == "RIG"
    assert not slots[2].drawn and not slots[2].publish_only and slots[2].missing == ""


def test_an_output_whose_display_is_away_says_so_on_its_block(monkeypatch):
    _, slots, *_ = _launch(monkeypatch, {"Built-in": row("output.1"), "Glass": row("output.2")})
    assert not slots[1].opened and slots[1].missing == "its display is not connected (Glass)"
    assert slots[2].missing == ""


def test_the_laptop_leaves_the_rows_alone(monkeypatch, tmp_path):
    """`--laptop`: `main` makes no `DisplayList`, and with no `want` the config says as before."""
    import inspect

    src = inspect.getsource(app.main)
    assert "None if args.laptop else\n" in src and "DisplayList.open(cfg, home" in src
    g = _Fake()
    monkeypatch.setattr(app, "glfw", g)
    cfg = _cfg(monitor=1, fullscreen=True, screens=[{**config.SCREEN, "monitor": 1}, {**config.SCREEN}])
    config.laptop(cfg)
    slots, _ = app._windows(False, cfg, None, "root")
    assert len(slots) == 1 and slots[0].opened and slots[0].monitor == -1 and not slots[0].fullscreen
    assert "neither read nor written" in cfg["notes"][-1]


# ---- the rows on the real panel


class _Win:
    """A window's settings, as the rows see them."""

    def __init__(self):
        self.fullscreen = False


def _running(store, scr, slots, opened_now):
    return Running(store, lambda: scr, slots, opened_now)


@pytest.fixture
def rows(tmp_path, monkeypatch):
    """The real panel over four slots and a real store in a scratch library, over stand-in
    displays: two with one name, and a render on both, each with its own flips."""
    root = tmp_path / "Drive"
    root.mkdir()
    (tmp_path / "home").mkdir()
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(1600, 900)
        r.store = opened(root, tmp_path / "home", seed={
            "Built-in": row(CONTROL), "TV #1": row("output.1", flip_x=True), "TV #2": row("output.1", flip_y=True)})
        r.root = root
        slots = r.panel.outputs
        slots[0].win, slots[0].display = "w1", "TV #1"
        slots[0].switches.flip_x = True
        slots[0].output = r.panel.output
        r.also = app.Also("TV #2", win="w2", flip_y=True, output=_Win())
        slots[0].also = [r.also]
        for sl in slots[1:]:
            sl.win = None
        r.panel.displays = _running(r.store, SCREENS, slots, {
            "Built-in": CONTROL, "TV #1": "output.1", "TV #2": "output.1"})
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        r.reg["ui.page"].set(PAGE_KEYS.index("output"))
        d.run(d.wait(3))
        r.d = d
        yield r


def test_one_row_per_connected_display_across_the_desk(rows):
    r = rows
    drawn = r.d.rects
    assert {f"display.{k}.target" for k in range(3)} <= set(drawn)
    assert "display.3.target" not in drawn
    assert "output.monitor" not in drawn, "it isn't a dropdown any more"
    assert "output.fullscreen" not in drawn, "fullscreen is a row's"
    assert "output.1.flip_x" not in drawn, "and so are its flips"
    assert "display.0.flip_x" not in drawn, "the control window has neither"
    assert "display.1.flip_x" in drawn and "display.2.fullscreen" in drawn


def test_a_render_on_two_displays_has_flips_on_each_at_once(rows):
    r, d = rows, rows.d
    one = r.panel.outputs[0]
    assert (one.switches.flip_x, one.switches.flip_y) == (True, False)
    d.run(d.click("display.1.flip_y"), d.park(), d.wait(2))
    assert (one.switches.flip_x, one.switches.flip_y) == (True, True), "its first display's: the param"
    assert (r.also.flip_x, r.also.flip_y) == (False, True), "the other's are its own"
    d.run(d.click("display.2.flip_x"), d.park(), d.wait(2))
    assert (r.also.flip_x, r.also.flip_y) == (True, True)
    assert (one.switches.flip_x, one.switches.flip_y) == (True, True)
    d.run(d.click("display.2.fullscreen"), d.park(), d.wait(2))
    assert r.also.output.fullscreen is True and r.panel.output.fullscreen is False
    d.run(d.click("display.1.fullscreen"), d.park(), d.wait(2))
    assert r.panel.output.fullscreen is True
    r.store.sync()
    disk = on_disk(r.root)
    assert (disk["TV #1"]["flip_x"], disk["TV #1"]["flip_y"], disk["TV #1"]["fullscreen"]) == (True, True, True)
    assert (disk["TV #2"]["flip_x"], disk["TV #2"]["flip_y"], disk["TV #2"]["fullscreen"]) == (True, True, True)


def test_a_change_of_target_is_written_and_says_it_waits_for_a_restart(rows):
    r, d = rows, rows.d
    said = _texts(r, d)
    assert not any(t.startswith(ui_displays.ON_RESTART) for t in said)
    d.run(d.pick("display.2.target", 3), d.park(), d.wait(2))     # nothing, control, output 1, output 2
    r.store.sync()
    assert on_disk(r.root)["TV #2"]["target"] == "output.2"
    assert r.panel.displays.opened["TV #2"] == "output.1", "nothing has opened or closed"
    said = _texts(r, d)
    assert any(t.startswith(ui_displays.ON_RESTART) and "TV #2" in t for t in said), said


def test_choosing_the_control_window_takes_it_from_where_it_was(rows):
    r, d = rows, rows.d
    d.run(d.pick("display.1.target", 1), d.park(), d.wait(2))
    r.store.sync()
    disk = on_disk(r.root)
    assert disk["TV #1"]["target"] == CONTROL and disk["Built-in"]["target"] == ""
    assert wanted(r.store.current, SCREENS).control.display == "TV #1"
    assert "display.1.flip_x" not in r.d.rects


def test_a_window_with_other_target_chosen_keeps_its_flips_until_the_restart(rows):
    r, d = rows, rows.d
    one = r.panel.outputs[0]
    d.run(d.pick("display.1.target", 3), d.park(), d.wait(2))
    d.run(d.click("display.1.flip_y"), d.park(), d.wait(2))
    assert one.switches.flip_y is False, "what's open is output 1's: the row waits for ⌘R"
    r.store.sync()
    assert on_disk(r.root)["TV #1"]["flip_y"] is True


def _texts(r, d):
    """The words a frame of the section drew."""
    said: list[str] = []
    real = imgui.text_colored
    imgui.text_colored = lambda c, t: (said.append(t), real(c, t))[1]
    try:
        d.run(d.wait(1))
    finally:
        imgui.text_colored = real
    return said


@pytest.mark.parametrize("width", [240.0, 320.0])
def test_the_rows_fit_the_side_pane(rows, width):
    r, d = rows, rows.d
    ui_graph._state(r.panel)["side_w"] = width
    d.run(d.wait(3))
    right = max(d.rect(f"display.{k}.target")[2] for k in range(3))
    for k in (1, 2):
        for key in ("fullscreen", "flip_x", "flip_y"):
            assert d.rect(f"display.{k}.{key}")[2] <= right + 1, (k, key)


def test_the_panel_says_no_display_shows_a_render(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(1600, 900)
        (tmp_path / "L").mkdir()
        r.panel.displays = _running(opened(tmp_path / "L", None, seed={"Built-in": row(CONTROL)}),
                                    [LAPTOP], r.panel.outputs, {"Built-in": CONTROL})
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        r.reg["ui.page"].set(PAGE_KEYS.index("output"))
        d.run(d.wait(3))
        assert ui_displays.NO_RENDER in _texts(r, d)


def test_a_wire_into_an_output_nothing_shows_is_wanted():
    """A slot is no longer a window: a patch's wire into one nothing shows says so."""
    wire = SimpleNamespace(node="output.3")
    loaded = SimpleNamespace(graph=SimpleNamespace(spec=SimpleNamespace(wires=[wire])), bus=None)
    panel = SimpleNamespace(library=SimpleNamespace(loaded_patch=loaded),
                            outputs=[Slot(1, win="w"), Slot(2), Slot(3), Slot(4)])
    assert ui_graph.window_wants(panel)[0].startswith("this preset wires Output 3")
    panel.outputs[2].win = "w3"
    assert ui_graph.window_wants(panel) == []
    panel.outputs[2].win, panel.outputs[2].missing = None, "its display is not connected (Glass)"
    assert ui_graph.window_wants(panel) == []


def test_no_old_words():
    """The glossary's: a display, a row, an output; no layer of configuration."""
    for mod in (displays, ui_displays):
        src = Path(mod.__file__).read_text().lower()
        assert "venue" not in src and " rig" not in src and "session" not in src, mod.__name__


def test_also_handoff_undoes_output_1s_flips_and_keeps_anothers_mix_right():
    first = Slot(1, switches=Switches(flip_x=True))
    also = app.Also("TV #2", flip_x=False, flip_y=True, size=(1920, 1080))
    ho = app._also_handoff(first, None, also, first, "frame", (1280, 720))
    assert ho.flip == (True, True), "what's in the frame, undone, and its own"
    assert ho.rect == (0, 0, 1920, 1080) and ho.frame == "frame"
    other = Slot(2, switches=Switches(flip_y=True))
    from hyperspace.outputs import Handoff

    view = SimpleNamespace(handoff=Handoff("t", (1280, 720), (0, 0, 800, 450), flip=(False, True), factor=0.5))
    also2 = app.Also("A", flip_x=True, size=(1000, 1000))
    got = app._also_handoff(other, view, also2, first, "frame", (1280, 720))
    assert got.flip == (True, False) and got.factor == 0.5 and got.mix_flip == (True, True)
    assert got.rect == (0, 219, 1000, 562)
    assert app._also_handoff(other, SimpleNamespace(handoff=None), also2, first, "f", (1, 1)) is None
