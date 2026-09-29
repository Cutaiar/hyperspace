"""The controls shell (WP5a): pages, preset strips, project row, ghosts.

Headless imgui, a library on tmp_path — nothing here touches
~/Hyperspace or needs a display. Buttons cannot be clicked without a
mouse, so each test drives the same library calls the strip's buttons
make and checks that every state the strip can be in draws.
"""

import re
from types import SimpleNamespace

import pytest
from imgui_bundle import imgui, implot

from hyperspace import hands, lfo, routing, tempo, ui_presets, ui_routing
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.app import CONTROL_SIZE, LOOP_KEYS
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.overlay import Output
from hyperspace.params import Kind, build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Binding, Bindings, Owned, Router, keymap, padmap
from hyperspace.ui import CHEATSHEET, PAGE_KEYS, PAGES, Panel, apply_style, load_fonts
from hyperspace.view import ViewState


class FakeLeap:
    """A tracker that sees no hands: enough for the HANDS page to draw every
    part of itself (status, switches, box, axes, editor)."""

    status = "tracking"
    on = True

    def latest(self):
        return 0, 0.0, {}

    def close(self):
        pass


@pytest.fixture()
def rig(tmp_path):
    ctx = imgui.create_context()
    pctx = implot.create_context()      # the band editor plots (ui_bands.py)
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(820, 820)
    io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
    apply_style()
    load_fonts()
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
    view = ViewState()
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(view, control, audio, lib.project)
    lib.on_layout("band", control.apply_layout)
    # the rig has everything app.py gives the panel, so every page is
    # measured full: a hands setup over a tracker that sees no hands, an
    # Output, the factory table in a Router, the clock and the LFOs
    settings = hands.HandSettings.from_config({})
    hands.register(reg, settings)
    hands_io = hands.HandsIO(settings, {"out": ""}, source=FakeLeap(), clock=lambda: 0.0)
    clock, lfos = tempo.Clock(now=lambda: 0.0), lfo.LFOs()   # the LFO page (ui_lfo.py)
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    output = Output(None, None)
    output.register(reg)
    lib.attach(reg)
    panel = Panel(control, audio, view, bank=lib.project, registry=reg, library=lib)
    panel.clock, panel.lfos = clock, lfos
    panel.hands, panel.hand_settings = hands_io, settings
    panel.output = output
    router = Router(reg, Bindings.factory(path=tmp_path / "bindings.json"))
    router.table.set_routes(routing.legacy6_routes())   # a house preset's performer rows
    Presets(lib, reg, router)           # the bank and the preset strip, as app.py builds them
    panel.router = router
    r = SimpleNamespace(panel=panel, lib=lib, reg=reg, view=view, chain=chain, router=router)
    try:
        yield r
    finally:
        implot.destroy_context(pctx)
        imgui.destroy_context(ctx)


def frame(panel, page=None):
    if page is not None:
        panel.reg["ui.page"].set(PAGE_KEYS.index(page))
    imgui.new_frame()
    panel.draw(1 / 60, 60.0)
    imgui.end_frame()


# ---------------------------------------------------------------- pages

def test_every_page_draws_with_a_library(rig):
    for k, (key, _, _) in enumerate(PAGES):
        rig.reg["ui.page"].set(k)
        assert rig.panel.page == k
        for _ in range(2):
            frame(rig.panel)
        assert PAGE_KEYS[k] == key


def test_system_page_shows_a_config_error_and_notes(rig, monkeypatch):
    """A config.toml that would not parse, or that still says [overlay], is
    reported on the SYSTEM page (audit L4), beside the other rig notices."""
    import hyperspace.ui as ui_mod

    drawn: list[str] = []
    real_colored, real_disabled = imgui.text_colored, imgui.text_disabled
    monkeypatch.setattr(ui_mod.imgui, "text_colored",
                        lambda col, s: (drawn.append(s), real_colored(col, s)))
    monkeypatch.setattr(ui_mod.imgui, "text_disabled",
                        lambda s: (drawn.append(s), real_disabled(s)))
    rig.panel.config_error = "config: Expected ']' at line 1"
    rig.panel.config_notes = ["config: [overlay] is now [output] — rename the section"]
    frame(rig.panel, "system")
    imgui.end_frame()
    assert rig.panel.config_error in drawn and rig.panel.config_notes[0] in drawn
    drawn.clear()
    rig.panel.config_error, rig.panel.config_notes = "", []
    frame(rig.panel, "system")
    imgui.end_frame()
    assert not any(s.startswith("config:") for s in drawn)


def test_system_page_shows_the_bridge(rig, monkeypatch):
    """The DAW bridge's state — off, a port error, no port, or the ports and
    what went out — is on the SYSTEM page (audit P3), where before its only
    sign of life was a stderr line."""
    import hyperspace.ui as ui_mod

    drawn: list[str] = []
    real_colored, real_disabled = imgui.text_colored, imgui.text_disabled
    monkeypatch.setattr(ui_mod.imgui, "text_colored",
                        lambda col, s: (drawn.append(s), real_colored(col, s)))
    monkeypatch.setattr(ui_mod.imgui, "text_disabled",
                        lambda s: (drawn.append(s), real_disabled(s)))

    def shown() -> list[str]:
        drawn.clear()
        frame(rig.panel, "system")
        imgui.end_frame()
        return [s for s in drawn if s.startswith(("bridge", "no bridge"))]

    assert shown() == ["no bridge — [bridge] enabled = false"]
    b = SimpleNamespace(on=False, name="", error="", encoding="pitch", room=16, sent=0)
    rig.panel.bridge = b
    assert shown() == ["bridge: no port"]
    b.on, b.name, b.sent = True, "out IAC Bus 1", 42
    assert shown() == ["bridge: out IAC Bus 1  ·  pitch, 16 lanes  ·  42 sent"]
    b.error = "no such port"
    assert shown() == ["bridge: no such port"]


def _drawn(monkeypatch) -> list[str]:
    """Every string the page code hands imgui's text calls, in order (every
    ui module shares the one imgui module, so patching it once is enough)."""
    drawn: list[str] = []
    colored, disabled, wrapped = imgui.text_colored, imgui.text_disabled, imgui.text_wrapped
    monkeypatch.setattr(imgui, "text_colored", lambda col, s: (drawn.append(s), colored(col, s)))
    monkeypatch.setattr(imgui, "text_disabled", lambda s: (drawn.append(s), disabled(s)))
    monkeypatch.setattr(imgui, "text_wrapped", lambda s: (drawn.append(s), wrapped(s)))
    return drawn


def test_a_render_error_and_the_dream_error_show_in_the_red_banner(rig, monkeypatch, tmp_path):
    """Plan 14 WP1: a live render error (the render window holding its last
    frame) and a dream worker that would not start are a red banner across
    the control window — drawn even with the panel hidden — not only a
    line on the SYSTEM page."""
    from hyperspace.watchdog import RenderWatch, Watchdog

    drawn = _drawn(monkeypatch)
    rw = RenderWatch(Watchdog(tmp_path / "stall.log"))
    rig.panel.render_watch = rw
    frame(rig.panel)
    assert rig.panel.alerts() == [] and not any("render window" in s for s in drawn)
    rw.failed(ValueError("boom"), 0.0)
    rig.panel.dream_error = "dream worker off: FileNotFoundError: vgg16 weights"
    rig.panel.open = False                     # the banner shows with the panel hidden
    drawn.clear()
    frame(rig.panel)
    # the banner is drawn last, in front of everything else
    assert drawn[-2:] == ["render window stopped — ValueError: boom",
                          "dream worker off: FileNotFoundError: vgg16 weights"]
    # the render recovers: the error stays, as what happened, until dismissed
    rw.drew(1.0)
    drawn.clear()
    frame(rig.panel)
    assert drawn[-2].startswith("the render window stopped once, last at ")
    assert "ValueError: boom" in drawn[-2] and rw.dismissible
    rw.dismiss()
    drawn.clear()
    frame(rig.panel)
    assert drawn[-1] == "dream worker off: FileNotFoundError: vgg16 weights"
    assert not any("render window" in s for s in drawn)
    # the dream's reason dismisses too (SYSTEM and LOOKBACK keep it)
    rig.panel.dismiss_alerts()
    assert rig.panel.alerts() == []


def test_system_page_shows_the_dream_error_and_the_stall_log(rig, monkeypatch, tmp_path):
    """The dream gate's reason sits beside config_error / config_notes; the
    stall log's line appears once the file has entries."""
    from hyperspace import app
    from hyperspace.watchdog import Watchdog

    drawn = _drawn(monkeypatch)
    rig.panel.dream_error = app.dream_error(ModuleNotFoundError("no torch", name="torch"))
    assert rig.panel.dream_error == (
        "dream worker off: torch is not installed — run `uv sync`, "
        "then launch with `uv run hyperspace`")
    wd = Watchdog(tmp_path / "stall.log", preset=lambda: "FACES")
    rig.panel.watchdog = wd
    frame(rig.panel, "system")
    assert rig.panel.dream_error in drawn
    assert not any(s.startswith("stall log:") for s in drawn)
    assert wd.open() and wd.log("stall", "no frame for 2.4 s")
    drawn.clear()
    frame(rig.panel, "system")
    assert f"stall log: {wd.path} (1 stall)" in drawn
    wd.close()


def test_the_lookback_page_says_why_the_worker_is_off(rig, monkeypatch):

    drawn = _drawn(monkeypatch)
    rig.panel.dream_error = "dream worker off: torch is not installed — run `uv sync`"
    frame(rig.panel, "lookback")
    assert rig.panel.dream_error in drawn


def test_page_param_is_ui_state_not_a_preset(rig):
    p = rig.reg["ui.page"]
    assert p.group == "ui" and not p.persist and not p.modulatable
    assert p.names == [label for _, label, _ in PAGES]
    p.set(99)                       # out of range lands on the last page
    frame(rig.panel)
    assert rig.panel.page == len(PAGES) - 1


def test_panel_draws_factory_only(rig):
    """A fresh home: only factory presets, no user files, no saved project."""
    assert rig.lib.list("view") == [] and rig.lib.list("band")
    assert rig.lib.project.path is None
    for page in ("view", "analyzer", "presets"):
        frame(rig.panel, page)


def _page_scroll(rig, monkeypatch) -> dict[str, float]:
    """Draw every page at the control size three times and read each page
    child's scroll range after its own draw."""
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    over = {}
    for key in PAGE_KEYS:
        draw = getattr(Panel, f"_page_{key}")

        def measured(self, dt, _draw=draw, _key=key):
            _draw(self, dt)
            over[_key] = imgui.get_scroll_max_y()
        monkeypatch.setattr(Panel, f"_page_{key}", measured)
    for key in PAGE_KEYS:
        for _ in range(3):              # the window settles its size, then its content
            frame(rig.panel, key)
    return over


def test_every_page_fits_the_control_window(rig, monkeypatch):
    """No page scrolls at the app's control-window size: a control that has
    to be scrolled to is one that cannot be found in a hurry. The rig has
    a hands setup with a tracker, an Output and a Router with the factory
    rows, so HANDS, OUTPUT and ROUTING are measured full (audit U1)."""
    assert rig.panel.hands is not None and rig.panel.output is not None
    assert rig.router.table.routes()
    over = _page_scroll(rig, monkeypatch)
    assert set(over) == set(PAGE_KEYS)
    assert {k: v for k, v in over.items() if v > 0} == {}


def test_the_routing_rows_scroll_in_their_own_child(rig, monkeypatch):
    """ROUTING is the one page whose list may outgrow the window: the rows
    scroll inside a child and the page itself never does, so the preset
    strip and the header stay put (by design; audit U1)."""
    reg, table = rig.reg, rig.router.table
    for p in reg:                       # enough rows to overflow: one per free target
        if p.kind is Kind.CONTINUOUS and p.modulatable and table.owner(p.id) is None:
            try:
                table.add(Binding("lfo:1", p.id, "push", 0.1))
            except Owned:
                continue
        if len(table.routes()) >= 40:
            break
    assert len(table.routes()) >= 40
    inner = []
    row = ui_routing._row

    def measured(panel, router, b, k):
        out = row(panel, router, b, k)
        inner.append(imgui.get_scroll_max_y())   # inside the ##routes child
        return out
    monkeypatch.setattr(ui_routing, "_row", measured)
    over = _page_scroll(rig, monkeypatch)
    assert over["routing"] == 0, "the ROUTING page itself scrolled"
    assert inner and inner[-1] > 0, "the rows' child did not scroll with 40 rows"


def test_the_routing_page_fits_over_a_loaded_preset_and_a_full_desk(rig, monkeypatch):
    """Plan 13 decision 13: the one ROUTING page — head, routes, desk,
    macros, session — never scrolls itself, with the factory preset
    loaded and with a full desk (every preset control mapped, each macro
    subscribed), a refused learn and a dropped desk row in the head."""
    from hyperspace.learn import Learn

    lib, table = rig.lib, rig.router.table
    lib.load("presets", "BIG BLUE WAVE")
    assert table.desk()
    over = _page_scroll(rig, monkeypatch)
    assert over["routing"] == 0, "the ROUTING page scrolled with the factory preset"
    full = [*table.desk(), *[Binding(f"cc:*:{0x10 + k}", "view.speed", "abs",
                                     feedback="ring", layer="preset") for k in range(8)],
            *[Binding(f"note:{k}:{0x36}", "view.shape", "set", float(k), feedback="led",
                      layer="preset") for k in range(8)],
            Binding("cc:0:7", "view.bright", "abs")]          # a fader: dropped, noted
    rig.lib.presets.desk_notes = table.set_desk(full)
    table.set_macros({f"macro.{k}": {"label": f"M{k}", "subs": [
        {"base": "view.depth4", "from": 0.0, "to": 1.0},
        {"depth": {"source": "lane:0", "target": "rot.rate.ZW"}, "from": 0.0, "to": 1.0}]}
        for k in range(1, 9)})
    rig.panel.learn = Learn(rig.reg, table)
    rig.panel.learn.refuse("track knob 1 is on the global layer (the session's) — "
                           "latch SHIFT off to learn into the preset")
    # dark now: only clip row 3's first three buttons (the global band scenes' own)
    assert [f.source for f in ui_routing.unmapped(table)] == [
        f"note:{k}:{0x37}" for k in range(3)]
    over = _page_scroll(rig, monkeypatch)
    assert over["routing"] == 0, "the ROUTING page scrolled with a full desk"


def test_the_hands_page_fits_with_the_tracker_off(rig, monkeypatch):
    """The setup still edits and saves with no tracker: the page draws
    without the switches beside the box and still fits."""
    rig.panel.hands = None
    over = _page_scroll(rig, monkeypatch)
    assert over["hands"] == 0


def test_the_meter_tooltip_names_the_plane_from_the_live_table(rig):
    """The suffix comes from the rot.rate rows, not a static table: the
    factory rows push lane 0 on ZW; a lane with no such row has no suffix."""
    panel, table = rig.panel, rig.router.table
    assert panel._lane_plane(0) == " → ZW forward"
    lane_rows = [b for b in table.of("lane") if b.target.startswith("rot.rate.")]
    for b in lane_rows:
        table.remove(b)
    assert panel._lane_plane(0) == ""
    table.add(Binding("lane:0", "rot.rate.XY", "position"))
    assert panel._lane_plane(0) == " → XY"           # a position row has no direction
    panel.router = None
    assert panel._lane_plane(0) == ""


# ---------------------------------------------------------------- cheat sheet

_SYMBOLS = {"←": "LEFT", "→": "RIGHT", "↑": "UP", "↓": "DOWN", "space": "SPACE",
            "[": "LEFT_BRACKET", "]": "RIGHT_BRACKET", ",": "COMMA", ".": "PERIOD",
            "?": "SLASH", "Esc": "ESCAPE", "Cmd+R": "SUPER+R"}
_PADS = {"pad A B": ["A", "B"], "pad X Y": ["X", "Y"], "LB / RB": ["LB", "RB"],
         "view/menu": ["VIEW", "MENU"], "sticks": ["LSTICK", "RSTICK"]}
_MOUSE = {"drag", "⇧drag", "scroll", "right-click", "d-pad", "LT / RT"}


def _sheet_keys() -> tuple[set[str], set[str]]:
    """The GLFW key names and pad buttons the sheet's key column names."""
    keys, pads = set(), set()
    for col, _ in CHEATSHEET:
        if col in _MOUSE:
            continue
        if col in _PADS:
            pads.update(_PADS[col])
            continue
        for tok in re.split(r"\s*/\s*|\s+", col):
            if not tok:
                continue
            m = re.fullmatch(r"(F?)(\d+)–F?(\d+)", tok)   # 1–6, F1–F8
            if m:
                keys.update(f"{m[1]}{k}" for k in range(int(m[2]), int(m[3]) + 1))
            else:
                keys.add(_base(_SYMBOLS.get(tok, tok)))
    return keys, pads


def _base(name: str) -> str:
    """SHIFT+B → B: the sheet names the key, the row may add a modifier."""
    return name.rsplit("+", 1)[-1]


def test_the_cheat_sheet_matches_the_tables_and_the_loop_keys():
    """ui.CHEATSHEET is the canonical human list (app.py): every key row in
    the factory table and every key the loop handles itself is on it, and
    it names nothing that is neither (audit U2)."""
    sheet_keys, sheet_pads = _sheet_keys()
    table_keys = {b.key_name for b in keymap()}
    known = table_keys | {_base(k) for k in LOOP_KEYS}
    assert not table_keys - sheet_keys, "table rows missing from the sheet"
    assert not {_base(k) for k in LOOP_KEYS} - sheet_keys, "loop keys missing from the sheet"
    assert not sheet_keys - known, "the sheet names keys nothing handles"
    table_pads = {b.source.split(":", 1)[1] for b in padmap() if b.scheme == "pad"}
    assert table_pads == sheet_pads
    assert any(b.scheme == "hat" for b in padmap()) and any(c == "d-pad" for c, _ in CHEATSHEET)


# ---------------------------------------------------------------- strip

def test_strip_round_trip(rig):
    """save-as → clean → edit → dirty → next/prev → reset, drawing each state."""
    lib, reg, panel = rig.lib, rig.reg, rig.panel
    frame(panel, "view")
    assert lib.current("view") is None
    # the listing is cached on the poll cadence and invalidated by our writes
    assert ui_presets.names(panel, "view") == []
    ui_presets._save_as(panel, "view", "Mine")
    assert lib.current("view") == "Mine" and not lib.is_dirty("view")
    assert ui_presets.names(panel, "view") == ["Mine"]
    frame(panel)
    reg["view.bright"].step(3)
    assert lib.is_dirty("view")
    frame(panel)
    ui_presets._save_as(panel, "view", "Other")
    assert lib.list("view") == ["Mine", "Other"]
    frame(panel)
    # ◀ ▶ walk the names; the dot clears on a load
    assert lib.next("view") == "Mine"
    assert not lib.is_dirty("view")
    frame(panel)
    assert lib.prev("view") == "Other"
    frame(panel)
    # reset: the view group has no default preset, so back to the fresh values
    reg["view.bright"].step(3)
    assert lib.reset("view") is None
    assert lib.current("view") is None
    frame(panel)
    # the band group resets to its factory default, a factory preset that
    # the strip's save is disabled for (as… still works)
    frame(panel, "analyzer")
    assert lib.reset("band") == "Balanced"
    assert lib.is_factory("band", "Balanced")
    frame(panel)


def test_strip_name_field_draws(rig):
    """The inline save-as field replaces the strip while a name is typed."""
    panel = rig.panel
    frame(panel, "camera")
    ui_presets._begin_naming(panel, "camera", "seed")
    st = ui_presets._state(panel)
    assert st["naming"] == "camera" and st["buf"] == "seed"
    frame(panel)                    # draws the field, not the strip
    frame(panel)
    st["naming"] = None             # Esc
    frame(panel)


def test_strip_survives_a_bad_library_call(rig):
    """A LibraryError from a strip action shows in lib.error, never raises."""
    panel, lib = rig.panel, rig.lib
    assert ui_presets._guard(panel, lib.load, "view", "no such preset") is None
    assert "no preset" in lib.error
    frame(panel, "view")


def test_dirty_dots_follow_the_poll_cadence(rig):
    panel, reg, lib = rig.panel, rig.reg, rig.lib
    frame(panel, "camera")
    assert not ui_presets.dirty(panel, "camera")
    assert not ui_presets.dirty(panel, "camera", polled=True)
    reg["camera.zoom"].set_value(2.0)
    assert ui_presets.dirty(panel, "camera")                 # live: at once
    assert not ui_presets.dirty(panel, "camera", polled=True)  # the rail: next poll
    for _ in range(int(ui_presets.LIST_POLL * 60) + 2):
        frame(panel)
    assert ui_presets.dirty(panel, "camera", polled=True)
    assert lib.is_dirty("camera")


# ---------------------------------------------------------------- project

def test_project_row_and_dirty_state(rig, tmp_path):
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    proj = lib.project
    frame(panel, "presets")
    assert proj.is_dirty()          # never saved
    ui_presets._project_save_as(panel, "Show")
    assert proj.name == "Show" and proj.path == tmp_path / "projects" / "show.hyp.json"
    assert not proj.is_dirty()
    assert ui_presets.names(panel, ui_presets.PROJECT) == ["default", "party", "show"]
    frame(panel)
    gain = rig.chain.gain
    reg["master.gain"].set(gain + 1.0)             # a session move
    assert proj.is_dirty()
    frame(panel)
    ui_presets._guard(panel, proj.save)
    assert not proj.is_dirty()
    # load / new go through the same row
    proj.new("scratch")
    assert proj.is_dirty() and proj.path is None and rig.chain.gain == gain
    frame(panel)
    proj.load("show")
    assert rig.chain.gain == gain + 1.0 and not proj.is_dirty()
    frame(panel)


def test_preset_bank_and_strip_on_the_presets_page(rig):
    """Plan 13 WP2: the bank row loads and saves presets by F-key param,
    the one preset strip shows what is loaded and its dirty dot."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    frame(panel, "presets")
    reg["view.shape"].set(5)
    reg["preset.save.2"].fire()
    assert lib.project.active == 2 and lib.project.bank[2] == "STROBE CAGE"
    assert lib.read("presets", "STROBE CAGE")["values"]["view.shape"] == 5
    assert lib.current("presets") == "STROBE CAGE" and not lib.is_dirty("presets")
    reg["view.shape"].set(1)
    assert ui_presets.dirty(panel, "presets")
    frame(panel)
    reg["preset.load.2"].fire()
    assert rig.view.shape == 5 and not lib.is_dirty("presets")
    frame(panel)


# ---------------------------------------------------------------- ghosts

def _hold(reg, offsets: dict):
    """One frame of a source riding those params, as the router would."""
    for pid, u in offsets.items():
        reg[pid].modulate(u)
    reg.apply()


def test_modulated_params_draw_a_ghost(rig):
    panel, reg = rig.panel, rig.reg
    frame(panel, "view")
    assert panel.ghosts == 0
    bright = reg["view.bright"]
    base = bright.base
    # a fader, a toggle (corner tick) and an enum (corner tick), one frame
    _hold(reg, {"view.bright": 0.2, "view.faces": 1.0, "view.shape": 0.3})
    assert bright.modulated and bright.base == base and bright.value != base
    frame(panel)
    assert panel.ghosts == 3
    # the readout shows base → effective
    assert panel._eff_text(bright) == bright.fmt(bright.value)
    assert panel._eff_text(reg["view.faces"]) == "on"
    # the frame nothing holds, the base comes back and the ghosts go
    reg.apply()
    frame(panel)
    assert not bright.modulated and panel.ghosts == 0


def test_tooltip_names_the_performer(rig):
    """Plan 09 WP2: the modulation line reads `base → effective` and, with
    a router attached, who is performing — the owner row's describe().
    Without a router, or on a param nothing in the table owns, it says
    only that the param is modulated."""
    panel, reg = rig.panel, rig.reg
    bright = reg["view.bright"]
    _hold(reg, {"view.bright": 0.2})
    assert panel._performer(bright) == ""                      # no router attached
    arrow = f"{bright.text()} → {panel._eff_text(bright)}"     # the widgets' readout
    assert panel._mod_text(bright) == arrow
    assert panel._mod_line(bright) == f"Brightness: {arrow} (modulated)"
    assert panel._hint(bright, bright) == panel._mod_line(bright)
    bright.tip = "How bright."                                 # a tip goes first
    assert panel._hint(bright, bright) == f"How bright.\n{panel._mod_line(bright)}"
    panel.router = Router(reg, Bindings([Binding("hand:0", "view.bright", "push", 0.3)]))
    panel.router.feed("hand", [1.0])
    panel.router.modulate()
    reg.apply()
    assert panel._performer(bright) == "performed by hand 0 pushes +0.3"
    arrow = f"{bright.text()} → {panel._eff_text(bright)}"     # the push moved the effective
    assert panel._mod_line(bright) == f"Brightness: {arrow}, performed by hand 0 pushes +0.3"
    panel.router.labels["hand"] = ["L height"]                 # the adapter's name for it
    assert panel._performer(bright) == "performed by L height pushes +0.3"
    assert panel._performer(reg["view.speed"]) == ""           # owned by nothing
    assert panel._hint(bright, reg["view.speed"]) == bright.tip   # not modulated: the tip
    frame(panel, "view")                                       # draws with a router attached
    assert panel.ghosts == 1


def test_ghost_on_a_compact_slider_and_a_fader_in_a_table(rig):
    panel, reg = rig.panel, rig.reg
    _hold(reg, {"camera.zoom": 0.1})   # a _row on the camera page (log range)
    frame(panel, "camera")
    assert panel.ghosts == 1
    # the selected band's strip (two columns) on the analyzer page, and a
    # master fader, which sits with the source on the audio page
    _hold(reg, {"band.0.atk": 0.1, "master.gain": -0.1})
    frame(panel, "analyzer")
    assert panel.ghosts == 1
    _hold(reg, {"band.0.atk": 0.1, "master.gain": -0.1})
    frame(panel, "audio")
    assert panel.ghosts == 1


def test_every_panel_attribute_the_frame_reads_is_a_real_panels(rig):
    """`app.frame` reads the panel through `h.panel.<name>`, and the frame-order
    test drives it over a stub, so a name only the stub has (it was
    `restart_requested`: every launch crashed on its first frame) must fail
    here, against the real Panel the app builds."""
    import ast
    import inspect

    from hyperspace import app

    tree = ast.parse(inspect.getsource(app.frame))
    names = {n.attr for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute)
             and n.value.attr == "panel" and isinstance(n.value.value, ast.Name)
             and n.value.value.id == "h"}
    assert "restart_requested" in names
    missing = sorted(n for n in names if not hasattr(rig.panel, n))
    assert not missing, f"app.frame reads h.panel.{missing} that Panel never sets"
    assert rig.panel.restart_requested is False
