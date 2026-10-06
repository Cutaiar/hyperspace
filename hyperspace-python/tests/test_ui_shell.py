"""The controls shell (WP5a): pages, preset strips, project row, ghosts.

Headless imgui, a library on tmp_path — nothing here touches
~/Hyperspace or needs a display. Buttons cannot be clicked without a
mouse, so each test drives the same library calls the strip's buttons
make and checks that every state the strip can be in draws.
"""

import re
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from imgui_bundle import imgui, implot

from hyperspace import hands, lfo, routing, tempo, ui_presets, ui_routing
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.app import CONTROL_SIZE, LOOP_KEYS
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.outputs import Slot
from hyperspace.overlay import Output, register_switches
from hyperspace.params import PLANES, Kind, build_registry
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


@contextmanager
def build_rig(tmp_path, renderer=None):
    """The panel with everything app.py gives it, on a headless imgui
    context. With a `renderer` the registry's `dream.*` and `fx.*` are its
    own states and the panel draws over it, as in the app."""
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
    live = {} if renderer is None else {"dream": renderer.lookback.state,
                                        "fx": renderer.fx.state}
    reg = build_registry(view, control, audio, lib.project, **live)
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
    # four render outputs, the most the config allows (plan 21 WP4): the
    # OUTPUT page measured full, each with its switches and its own dim
    slots = [Slot(k + 1, name=nm, win=f"w{k + 1}")
             for k, nm in enumerate(("glass", "projector", "wall", "floor"))]
    slots[0].size = (1920, 1080)
    register_switches(reg, slots)
    # the table before attach, as app.main reads it: the desk's session
    # param (`desk.slew`) is the table's and exists when the show lands
    table = Bindings.factory(path=tmp_path / "bindings.json")
    routing.register_desk(reg, table)
    lib.attach(reg)
    panel = Panel(control, audio, view, renderer=renderer, bank=lib.project, registry=reg,
                  library=lib)
    panel.clock, panel.lfos = clock, lfos
    panel.hands, panel.hand_settings = hands_io, settings
    panel.output = output
    panel.outputs = slots
    router = Router(reg, table)
    router.table.set_routes(routing.legacy6_routes())   # a house preset's performer rows
    Presets(lib, reg, router)           # the bank and the preset strip, as app.py builds them
    panel.router = router
    r = SimpleNamespace(panel=panel, lib=lib, reg=reg, view=view, chain=chain, router=router,
                        slots=slots)
    try:
        yield r
    finally:
        implot.destroy_context(pctx)
        imgui.destroy_context(ctx)


@pytest.fixture()
def rig(tmp_path):
    with build_rig(tmp_path) as r:
        yield r


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
    assert rig.panel.desk                   # the desk diagram on (plan 14 WP7)
    assert rig.router.table.routes()
    over = _page_scroll(rig, monkeypatch)
    assert set(over) == set(PAGE_KEYS)
    assert {k: v for k, v in over.items() if v > 0} == {}


def _hands_page_text(rig, monkeypatch) -> tuple[list[str], float]:
    """Every line the HANDS page draws as text, and its scroll range, at
    the control size (three frames: the window settles, then its content)."""
    import hyperspace.hands.panel as hp

    drawn: list[str] = []
    room: list[float] = []
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    with monkeypatch.context() as m:
        real_colored, real_disabled = imgui.text_colored, imgui.text_disabled
        m.setattr(hp.imgui, "text_colored", lambda col, s: (drawn.append(s), real_colored(col, s)))
        m.setattr(hp.imgui, "text_disabled", lambda s: (drawn.append(s), real_disabled(s)))
        draw = Panel._page_hands

        def measured(self, dt):
            draw(self, dt)
            room.append(imgui.get_scroll_max_y())
        m.setattr(Panel, "_page_hands", measured)
        for _ in range(3):
            drawn.clear()
            frame(rig.panel, "hands")
    return drawn, room[-1]


def _ghost_more(rig, monkeypatch) -> tuple[list[str], list[str], tuple]:
    """Open the ghost's "more ▸" popup with a click on its chip: (the chip
    labels the page drew, the lines the popup drew, the chip's rect)."""
    import hyperspace.hands.panel as hp

    chips: list[tuple[str, tuple]] = []
    lines: list[str] = []
    real_chip = hp.ui.lit_chip
    real_begin = imgui.begin_popup
    inside = [False]

    def lit_chip(label, *a, **k):
        hit = real_chip(label, *a, **k)
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        chips.append((label, (lo.x, lo.y, hi.x, hi.y)))
        return hit

    def begin_popup(str_id, *a, **k):
        inside[0] = real_begin(str_id, *a, **k) and str_id == hp.GHOST_POPUP
        return inside[0]
    with monkeypatch.context() as m:
        m.setattr(hp.ui, "lit_chip", lit_chip)
        m.setattr(hp.imgui, "begin_popup", begin_popup)
        real_colored, real_disabled = imgui.text_colored, imgui.text_disabled
        m.setattr(hp.imgui, "text_colored", lambda col, s: (
            inside[0] and lines.append(s), real_colored(col, s))[1])
        m.setattr(hp.imgui, "text_disabled", lambda s: (
            inside[0] and lines.append(s), real_disabled(s))[1])
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        for _ in range(3):
            chips.clear()
            frame(rig.panel, "hands")
        more = [(lb, r) for lb, r in chips if lb.endswith("##ghost.more")]
        assert len(more) == 1, chips
        label, rect = more[0]
        _click(rig.panel, rect)
        lines.clear()
        frame(rig.panel, "hands")
    return [label.split("##")[0]], list(lines), rect


def test_the_hands_page_says_the_ghost_axes_are_unmeasured(rig, monkeypatch):
    """Plan 21 WP5 R6: screentop's and HMD's ghost bases are reasoned, not
    seen; with the ghost on in such a mode the HANDS page says so — the
    "more ▸" chip turns to "! more ▸" and its popup carries the note.
    Desktop (the measured table) and the ghost off say nothing."""
    import hyperspace.hands.panel as hp

    rig.reg["ghost.on"].set(True)
    for mode, said in (("desktop", False), ("screentop", True), ("hmd", True),
                       ("sideways", False)):        # unknown: drawn as desktop
        rig.panel.hands.cfg["mode"] = mode
        assert any("unmeasured" in t and mode in t for t, _ in hp.ghost_notes(rig.panel)) \
            is said, mode
        labels, lines, _ = _ghost_more(rig, monkeypatch)
        assert labels == [hp.GHOST_MORE_WARN if said else hp.GHOST_MORE], mode
        assert any("unmeasured" in s and mode in s for s in lines) is said, mode
    rig.reg["ghost.on"].set(False)
    rig.panel.hands.cfg["mode"] = "hmd"
    assert hp.ghost_notes(rig.panel) == []
    assert not any("unmeasured" in s for s in _hands_page_text(rig, monkeypatch)[0])


def test_the_hands_page_says_why_the_ghost_or_the_tracker_is_off(rig, monkeypatch):
    """Plan 21 WP5 R2 / R10: `Ghost.error` (a pass that would not build or
    draw, the tethers' labels) shows on the HANDS page; a tracker that
    would not open shows `app._open_hands`' note there instead of "tracker
    off", which is only for a tracker not asked for."""
    why = "ghost tethers: OSError: cannot open resource"
    rig.panel.renderer = SimpleNamespace(ghost=SimpleNamespace(error=why))
    assert why in _hands_page_text(rig, monkeypatch)[0]
    rig.panel.renderer.ghost.error = ""
    assert not any(s.startswith("ghost") for s in _hands_page_text(rig, monkeypatch)[0])
    note = "hands: [Errno 2] No such file or directory: '/nowhere/tape.json'"
    rig.panel.hands = None
    rig.panel.config_notes = ["config: something else", note]
    drawn, _ = _hands_page_text(rig, monkeypatch)
    assert note in drawn and not any(s.startswith("tracker off") for s in drawn)
    rig.panel.config_notes = []
    assert any(s.startswith("tracker off") for s in _hands_page_text(rig, monkeypatch)[0])


LONG_GHOST_ERROR = ("ghost hands: ValueError: setting an array element with a sequence. The "
                    "requested array has an inhomogeneous shape after 1 dimensions.")


def _every_ghost_line(rig) -> None:
    """The ghost at its fullest: on, a guide, tethers, MARIONETTE (the
    longest style), an unmeasured mode and a long error."""
    for pid, v in (("ghost.on", True), ("ghost.guide", 2), ("ghost.tethers", True),
                   ("ghost.style", 4)):
        rig.reg[pid].set(v)
    rig.panel.hands.cfg["mode"] = "screentop"
    rig.panel.renderer = SimpleNamespace(ghost=SimpleNamespace(error=LONG_GHOST_ERROR))


def test_the_hands_page_fits_with_every_ghost_line(rig, monkeypatch):
    """The HANDS page at its tallest for the ghost: on, a guide, tethers,
    an unmeasured mode and an error — and it still does not scroll. The
    ghost is two lines; the notes are in its "more ▸" popup, whole."""
    import hyperspace.hands.panel as hp

    _every_ghost_line(rig)
    _, over = _hands_page_text(rig, monkeypatch)
    assert over <= 0
    labels, lines, _ = _ghost_more(rig, monkeypatch)
    assert labels == [hp.GHOST_MORE_WARN]
    assert LONG_GHOST_ERROR in lines and any("unmeasured" in s for s in lines)


def _ghost_rects(rig, monkeypatch, display=CONTROL_SIZE, panel_w=None):
    """Every item the ghost block draws — the checks, the label cells'
    dummies (the label text is drawn in them), the slider, the combos and
    the chip — as screen rects, and the page's right edge, after three
    frames at `display` with the CONTROLS window `panel_w` wide."""
    import hyperspace.hands.panel as hp
    import hyperspace.ui as ui_mod

    rects: list[tuple[str, tuple]] = []
    right: list[float] = []
    live = [False]

    def item(name, real):
        def rec(label, *a, **k):
            out = real(label, *a, **k)
            if live[0]:
                lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
                key = label if isinstance(label, str) else name
                rects.append((key, (lo.x, lo.y, hi.x, hi.y)))
            return out
        return rec
    real_ghost = hp._ghost

    def ghost(panel):
        right.append(imgui.get_cursor_screen_pos().x + imgui.get_content_region_avail().x)
        live[0] = True
        try:
            real_ghost(panel)
        finally:
            live[0] = False
    with monkeypatch.context() as m:
        for fn in ("checkbox", "slider_float", "slider_int", "combo", "button", "dummy"):
            m.setattr(ui_mod.imgui, fn, item(fn, getattr(imgui, fn)))
        m.setattr(hp, "_ghost", ghost)
        imgui.get_io().display_size = imgui.ImVec2(*display)
        for _ in range(3):
            rects.clear()
            imgui.new_frame()
            if panel_w is not None:
                imgui.set_window_size("CONTROLS", imgui.ImVec2(panel_w, display[1] - 24))
            rig.panel.reg["ui.page"].set(PAGE_KEYS.index("hands"))
            rig.panel.draw(1 / 60, 60.0)
            imgui.end_frame()
    return rects, right[-1]


@pytest.mark.parametrize("display, panel_w", [
    (CONTROL_SIZE, None),                     # the app's control window, the panel as it opens
    ((320, CONTROL_SIZE[1]), None),           # the narrowest window placement opens (MIN_SIZE)
    (CONTROL_SIZE, 440),                      # the panel dragged narrower: the groups wrap
])
def test_the_ghost_controls_never_overlap_or_run_off_the_page(rig, monkeypatch, display, panel_w):
    """The owner's report of 2026-10-05: with the ghost on, the opacity,
    mirror and guide controls were drawn over the "Ghost hands" label —
    `_label_cell` put the control at a fixed offset from the line's start
    even mid-line. With every ghost control showing, no two of the ghost's
    items overlap and none runs past the page's right edge."""
    from hyperspace import placement

    assert placement.MIN_SIZE[0] == 320
    _every_ghost_line(rig)
    rects, right = _ghost_rects(rig, monkeypatch, display, panel_w)
    names = [k.split("##")[-1] for k, _ in rects]
    for want in ("ghost.on", "ghost.alpha", "ghost.style", "ghost.guide", "ghost.more"):
        assert want in names, (want, names)
    for k, (a, ra) in enumerate(rects):
        assert ra[2] <= right + 0.5, f"{a!r} runs past the page ({ra[2]:.1f} > {right:.1f})"
        for b, rb in rects[k + 1:]:
            apart = ra[2] <= rb[0] + 0.5 or rb[2] <= ra[0] + 0.5 \
                or ra[3] <= rb[1] + 0.5 or rb[3] <= ra[1] + 0.5
            assert apart, f"{a!r} {ra} overlaps {b!r} {rb}"
    lines = sorted({round(r[1]) for _, r in rects})
    if panel_w is None:
        assert len(lines) == 2, lines             # two lines at the panel's own width
    else:
        assert len(lines) > 2, lines              # narrower: a group wraps rather than overlaps


def test_a_percent_readout_reaches_imgui_doubled(rig, monkeypatch):
    """A slider's readout is imgui's printf format: Ghost opacity's "60%"
    goes in as "60%%", so the slider shows "60%" and not "60"."""
    fmts: list[str] = []
    real = imgui.slider_float
    monkeypatch.setattr(imgui, "slider_float", lambda label, v, lo, hi, fmt="%.3f", *a: (
        fmts.append((label, fmt)), real(label, v, lo, hi, fmt, *a))[1])
    rig.reg["ghost.on"].set(True)
    assert rig.reg["ghost.alpha"].text() == "60%"
    frame(rig.panel, "hands")
    assert ("##ghost.alpha", "60%%") in fmts


def test_the_ghost_more_popup_has_mirror_and_tethers(rig, monkeypatch):
    """Mirror and Tethers are in the "more ▸" popup; Tethers is greyed out
    with "with a guide on" until a guide is chosen. A click on Mirror in
    the popup sets ghost.mirror."""
    labels: list[str] = []
    real = imgui.checkbox
    rects: dict[str, tuple] = {}

    def checkbox(label, v):
        out = real(label, v)
        labels.append(label)
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        rects[label] = (lo.x, lo.y, hi.x, hi.y)
        return out
    rig.reg["ghost.on"].set(True)
    monkeypatch.setattr(imgui, "checkbox", checkbox)
    _, lines, _ = _ghost_more(rig, monkeypatch)
    assert "Mirror##ghost.mirror" in labels and "Tethers##ghost.tethers" in labels
    assert "with a guide on" in lines
    assert rig.reg["ghost.mirror"].value is False
    _click(rig.panel, rects["Mirror##ghost.mirror"])
    assert rig.reg["ghost.mirror"].value is True
    rig.reg["ghost.guide"].set(1)
    _, lines, _ = _ghost_more(rig, monkeypatch)
    assert "with a guide on" not in lines


class StandInWorker:
    """In the dream worker's place on the look-back page: it answers each
    submit with the frame it was given, one submit late (so a dream frame
    shows and its thumbnail is drawn), and says `line` as its status."""

    def __init__(self, line: str):
        self.line = line
        self.pending = self.done = None

    def submit(self, frame, frame_index):
        self.done, self.pending = self.pending, (frame.copy(), frame_index)

    def latest(self):
        return self.done

    def status(self) -> str:
        return self.line


# the worker's status at its shortest, and with everything it can say at
# once (dream.DreamWorker.status: drops, NaN resets, the clamp, and an
# error cut at 120 characters); and app.dream_error's line with no worker
WORKER_SHORT = "mps · alias · conv3_3 fp32 · 11.3 ms · 1 behind"
WORKER_LONG = ("cuda · staging · inception4e fp16 · 1234.5 ms · 12 behind · 3456 dropped · "
               "12 nan reset(s) · step clamped · " + ("RuntimeError: " + "out of memory " * 9)[:120])
NO_TORCH = ("dream worker off: torch is not installed — run `uv sync`, "
            "then launch with `uv run hyperspace`")


def lookback_page_room(tmp_path, monkeypatch) -> dict[str, tuple[float, float]]:
    """The look-back page drawn as the app draws it — over a real offscreen
    `Renderer` whose look-back has captured eight echoes, so the thumbnail
    row is its 48 px row of images and not the one line of text a page gets
    with no renderer — in every state that changes its height. Returns
    state → (scroll range, room left under the last row), in pixels at the
    control size."""
    moderngl = pytest.importorskip("moderngl")
    from hyperspace.render import Renderer

    try:
        gl = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    w, h = 1280, 820
    tex = gl.texture((w, h), 4)
    fbo = gl.framebuffer(color_attachments=[tex])
    renderer = Renderer(gl)
    lb, t = renderer.lookback, [0.0]
    room: dict[str, tuple[float, float]] = {}
    try:
        with build_rig(tmp_path, renderer) as rig:
            imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
            panel, reg, view = rig.panel, rig.reg, rig.view
            view.shape = 3
            got: list[tuple[float, float]] = []
            draw = Panel._page_lookback

            def measured(self, dt):
                draw(self, dt)
                got.append((imgui.get_scroll_max_y(),
                            imgui.get_content_region_avail().y + imgui.get_style().item_spacing.y))
            monkeypatch.setattr(Panel, "_page_lookback", measured)

            def render(n: int) -> None:
                for _ in range(n):
                    t[0] += 1 / 60
                    view.ang[3] += 0.03
                    fbo.use()
                    gl.viewport = (0, 0, w, h)
                    renderer.draw(view, w, h, t_now=t[0])

            def measure(state: str) -> None:
                render(4)
                for _ in range(3):          # the window settles its size, then its content
                    frame(panel, "lookback")
                room[state] = got[-1]

            reg["dream.on"].set(True)
            assert reg["dream.echoes"].value == 8 and lb.state.on
            lb.source = StandInWorker(WORKER_SHORT)
            render(40)
            assert len(lb.thumbnails()) == 8 and lb.dream_frame >= 0 and lb.atlas is not None
            measure("on, worker")
            lb.source.line = WORKER_LONG
            measure("on, worker saying everything")
            lb.error = "_common.glsl:1: syntax error"     # the post pass on its fallback
            measure("on, worker saying everything, GLSL error")
            lb.error = ""
            reg["dream.tint_from"].set(1)                 # the tint from the scene
            measure("on, tint from the scene")
            reg["dream.tint_from"].set(0)
            lb.source = None
            panel.dream_error = NO_TORCH
            measure("on, no worker: torch missing")
            panel.dream_error = ""
            measure("on, no worker")
            reg["dream.on"].set(False)
            measure("off, no worker")
            lb.source = StandInWorker(WORKER_LONG)
            measure("off, worker saying everything")
    finally:
        fbo.release()
        tex.release()
        gl.release()
    return room


def test_the_look_back_page_fits_with_thumbnails(tmp_path, monkeypatch):
    """Plan 20 WP4: the look-back page does not scroll in the app. The page
    test above draws it with no renderer, where the thumbnail row is a line
    of text; with a renderer and echoes it is a 48 px row of images, and the
    page as it was overflowed by 23 px there. Measured here with a real
    `Renderer` that has captured eight echoes, a source with a status line
    and a dream frame shown, the dream on and off, and the worker's status
    at its longest."""
    room = lookback_page_room(tmp_path, monkeypatch)
    assert len(room) == 8
    assert {k: v for k, v in room.items() if v[0] > 0 or v[1] < 0} == {}


# the VIEW page's field row (plan 20 WP6): the controls it rearranged
FIELD_ROW = ("view.inst_layout", "view.inst_motion", "view.inst_amp", "view.inst_rate")
ROT_RATES = tuple(f"rot.rate.{name}" for name in PLANES)


def view_page_room(rig, monkeypatch) -> dict[tuple[int, int, int], tuple[float, float]]:
    """The VIEW page at the control size with the field row showing: every
    (count, layout, motion) that changes the row. Returns state → (scroll
    range, room left under the last row), in pixels."""
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    got: list[tuple[float, float]] = []
    draw = Panel._page_view

    def measured(self, dt):
        draw(self, dt)
        got.append((imgui.get_scroll_max_y(),
                    imgui.get_content_region_avail().y + imgui.get_style().item_spacing.y))
    monkeypatch.setattr(Panel, "_page_view", measured)
    room = {}
    for n in (1, 7, 9, 100):
        for layout in (0, 1, 2):
            for motion in (0, 1):
                rig.reg["view.instances"].set(n)
                rig.reg["view.inst_layout"].set(layout)
                rig.reg["view.inst_motion"].set(motion)
                for _ in range(3):          # the window settles its size, then its content
                    frame(rig.panel, "view")
                room[(n, layout, motion)] = got[-1]
    return room


def test_the_view_page_fits_with_a_field_in_motion(rig, monkeypatch):
    """Plan 20 WP6: the VIEW page does not scroll with more than one copy.
    The page test above draws it at one copy, where the field row is
    hidden; above one the row shows (and the page as it was scrolled by
    19 px there). Measured with 7, 9 and 100 copies in every layout, still
    and in motion, and at one copy."""
    room = view_page_room(rig, monkeypatch)
    assert len(room) == 24
    assert {k: v for k, v in room.items() if v[0] > 0 or v[1] < 0} == {}


def test_the_field_row_and_the_rate_cells_keep_their_menus(rig, monkeypatch):
    """The controls WP6 moved — the layout, motion, amp and rate in one row,
    the six plane rates two to a row — each open their own binding menu on
    a right-click, and the row's controls sit side by side on one line
    inside the page."""
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    rects: dict[str, tuple[float, float, float, float]] = {}
    opened: list[str] = []

    def item(fn):
        real = getattr(imgui, fn)

        def rec(label, *a, **k):
            out = real(label, *a, **k)
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            rects[label.split("##", 1)[-1]] = (lo.x, lo.y, hi.x, hi.y)
            return out
        monkeypatch.setattr(imgui, fn, rec)
    for fn in ("combo", "slider_float", "slider_int"):
        item(fn)
    real_popup = imgui.begin_popup_context_item

    def popup(str_id, *a, **k):
        out = real_popup(str_id, *a, **k)
        if out:
            opened.append(str_id)
        return out
    monkeypatch.setattr(imgui, "begin_popup_context_item", popup)

    rig.reg["view.instances"].set(7)
    rig.reg["view.inst_layout"].set(1)
    rig.reg["view.inst_motion"].set(1)
    for _ in range(3):
        frame(rig.panel, "view")
    row = [rects[pid] for pid in FIELD_ROW]
    assert len({round(r[1]) for r in row}) == 1                    # one line
    assert all(row[k][2] < row[k + 1][0] for k in range(3))        # none overlaps the next
    cells = [rects[pid] for pid in ROT_RATES]
    assert len({round(r[1]) for r in cells}) == 3                  # three rows of two
    assert all(cells[k][2] < cells[k + 1][0] for k in (0, 2, 4))
    assert max(r[2] for r in row + cells) <= CONTROL_SIZE[0]
    # a lane on a plane rate (the party presets route them) reads
    # `base → effective` in the cell: the widest such readout fits it
    from hyperspace import ui
    p = rig.reg["rot.rate.XY"]
    widest = f"{p.fmt(p.lo)} → {p.fmt(p.lo)}"
    imgui.new_frame()
    imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
    need = imgui.calc_text_size(widest).x + 2 * imgui.get_style().frame_padding.x
    imgui.pop_font()
    imgui.end_frame()
    assert all(r[2] - r[0] >= need for r in cells), (widest, need, cells[0])

    io = imgui.get_io()
    io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard      # Escape closes a menu
    for pid in FIELD_ROW + ROT_RATES:
        x0, y0, x1, y1 = rects[pid]
        opened.clear()
        io.add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
        frame(rig.panel)
        io.add_mouse_button_event(1, True)
        frame(rig.panel)
        io.add_mouse_button_event(1, False)
        frame(rig.panel)
        frame(rig.panel)
        assert f"##ctx.{pid}" in opened, (pid, opened)
        assert set(opened) == {f"##ctx.{pid}"}, (pid, opened)
        io.add_mouse_pos_event(-1.0, -1.0)
        io.add_key_event(imgui.Key.escape, True)
        frame(rig.panel)
        io.add_key_event(imgui.Key.escape, False)
        frame(rig.panel)
        frame(rig.panel)
    # a right-click sets nothing
    assert rig.view.instances == 7 and rig.view.inst_layout == 1 and rig.view.inst_motion == 1


def test_the_dim_is_first_on_output_and_the_footer_says_so_while_dimmed(rig, monkeypatch):
    """Plan 15 WP3: the master dim is the OUTPUT page's first row, and on
    every page the footer reads `dim NN%` while it is under full — a dark
    picture is never a mystery — and says nothing at full."""
    rows: list[str] = []
    real = Panel._row
    monkeypatch.setattr(Panel, "_row",
                        lambda self, pid, *a, **k: (rows.append(pid), real(self, pid, *a, **k))[1])
    drawn = _drawn(monkeypatch)
    frame(rig.panel, "output")
    assert rows[0] == "output.dim"
    assert not any("dim " in s for s in drawn)
    rig.reg["output.dim"].set(0.4)
    for page in ("output", "view", "system"):
        drawn.clear()
        frame(rig.panel, page)
        assert "·  dim 40%" in drawn, page
    rig.reg["output.dim"].set(0.0)
    drawn.clear()
    frame(rig.panel, "view")
    assert "·  dim black" in drawn
    # a dim the driver refused is said on the OUTPUT page (review of PR #81)
    rig.panel.renderer = SimpleNamespace(dim_error="dim: Error: refused", pattern_error="",
                                         bitmap_error="")
    drawn.clear()
    frame(rig.panel, "output")
    assert "dim: Error: refused — the picture is not dimmed" in drawn


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
            "?": "SLASH", "Esc": "ESCAPE", "Cmd+R": "SUPER+R", "Cmd+Z": "SUPER+Z",
            "Home": "HOME"}
_PADS = {"pad A B": ["A", "B"], "pad X Y": ["X", "Y"], "LB / RB": ["LB", "RB"],
         "view/menu": ["VIEW", "MENU"], "sticks": ["LSTICK", "RSTICK"]}
_MOUSE = {"drag", "⇧drag", "scroll", "right-click", "d-pad", "LT / RT",
          "APC40"}                                   # the desk's glyph legend, not a key


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


def _windows(monkeypatch) -> list[str]:
    """The name of every window a frame begins, in order."""
    begun: list[str] = []
    real = imgui.begin
    monkeypatch.setattr(imgui, "begin", lambda name, *a, **k: (begun.append(name),
                                                               real(name, *a, **k))[1])
    return begun


def test_the_cheat_sheet_is_off_at_launch_and_the_desk_is_on(rig, monkeypatch):
    """Plan 16 WP1: a fresh panel draws the desk diagram and no legend —
    the sheet was in the way at every launch. Its checkbox says how to get
    it back."""
    panel = rig.panel
    assert panel.cheatsheet is False and panel.desk is True
    assert rig.reg["ui.cheatsheet"].base is False and rig.reg["ui.desk"].base is True
    begun = _windows(monkeypatch)
    for _ in range(2):
        frame(panel)
    assert "##desk" in begun and "##cheatsheet" not in begun
    sheet = rig.reg["ui.cheatsheet"]
    assert "/" in sheet.tip and "bottom-left" in sheet.tip
    assert not sheet.persist and not sheet.modulatable      # off every launch, nobody's target


def test_slash_still_toggles_the_cheat_sheet(rig, monkeypatch):
    """The key row is the factory table's, and a press of the real key
    through the router draws the sheet on the next frame and hides it on
    the one after the second press."""
    import glfw

    rows = [b for b in rig.router.table.of("key") if b.key_name == "SLASH"]
    assert [(b.source, b.target, b.op) for b in rows] == [("key:SLASH", "ui.cheatsheet", "toggle")]

    keys = SimpleNamespace(pressed=lambda key: key == glfw.KEY_SLASH)   # one press, no modifier
    begun = _windows(monkeypatch)

    def press_and_draw() -> list[str]:
        rig.router.keys(keys)
        begun.clear()
        frame(rig.panel)
        return list(begun)

    frame(rig.panel)
    assert "##cheatsheet" not in begun
    assert "##cheatsheet" in press_and_draw() and rig.panel.cheatsheet is True
    assert "##desk" in begun                                # the desk moves up, it does not go
    assert "##cheatsheet" not in press_and_draw() and rig.panel.cheatsheet is False
    assert "##desk" in begun


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
    assert not proj.is_dirty() and proj.factory   # a factory show as it shipped: clean
    ui_presets._project_save_as(panel, "Show")
    assert proj.name == "Show" and proj.path == tmp_path / "projects" / "show.hyp.json"
    assert not proj.is_dirty()
    assert ui_presets.names(panel, ui_presets.PROJECT) == ["house", "party", "show"]
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


def test_the_footer_says_what_was_undone(rig, monkeypatch):
    """Plan 15 WP1: the footer's message slot shows, on every page, the
    newest of the undo's status, the library's status and the library's
    warning for `MESSAGE_S` after it changes; a launch says nothing; a
    line too long for the room beside the show's name is cut, not wrapped."""
    from hyperspace import ui, undo

    panel, reg, lib = rig.panel, rig.reg, rig.lib
    clock = [1000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    u = panel.undo = undo.Undo(reg, rig.router.table)
    drawn = _drawn(monkeypatch)

    def shown(page=None) -> list[str]:
        drawn.clear()
        frame(panel, page)
        return [s for s in drawn if s.startswith("·  ")]

    lib.status, lib.warning = "show: party", ""
    assert shown("view") == []                         # the first look only remembers
    p = reg["view.bright"]
    was = p.base
    p.set(was + 0.4)
    u.tick(1.0)
    u.tick(2.0)                                        # a second of quiet: the step closed
    assert shown() == []                               # an edit says nothing
    assert u.undo() and p.base == was
    line = f"·  undid {p.label} {p.fmt(was)} → {p.fmt(was + 0.4)}"
    for page in ("view", "routing", "presets", "system"):
        clock[0] += 0.5
        assert shown(page) == [line], page
    clock[0] += ui.MESSAGE_S                           # …and it goes
    assert shown() == []
    u.undo()                                           # nothing left: said, and said again
    assert shown() == ["·  nothing to undo"]
    clock[0] += ui.MESSAGE_S + 1
    assert shown() == []
    u.tick(3.0)
    u.undo()
    assert shown() == ["·  nothing to undo"]
    # the library's lines, without opening the PRESETS page: the newest wins
    clock[0] += 1.0
    lib.status = "presets: saved TRIP 2"
    assert shown("lfo") == ["·  presets: saved TRIP 2"]
    lib.warning = "F3: an empty slot — ⇧F3 saves the live state into it"
    assert shown("lfo") == [f"·  {lib.warning}"]
    u.redo()
    assert shown("lfo") == [f"·  {u.status}"] and u.status.startswith("redid ")
    # a line longer than the room is cut to fit beside the show's name
    clock[0] += 1.0
    lib.status = "presets: " + "a very long preset name " * 12
    (cut,) = shown("view")
    assert cut.endswith("…") and cut.startswith("·  presets: a very long")
    assert imgui.calc_text_size(cut).x < ui.PANEL_W
    assert ui.fit_text("short", 500.0) == "short"
    # …and shorter still while the dim readout (plan 15 WP3) shares the line
    reg["output.dim"].set(0.4)
    dimmed, readout = shown("view")
    assert dimmed.endswith("…") and len(dimmed) < len(cut) and readout == "·  dim 40%"
    reg["output.dim"].set(1.0)
    # a panel with no undo and no library still draws its footer
    panel.undo = None
    clock[0] += ui.MESSAGE_S + 1
    assert shown() == []


def test_preset_bank_and_strip_on_the_presets_page(rig):
    """Plan 13 WP2: the bank row loads and saves presets by F-key param,
    the one preset strip shows what is loaded and its dirty dot."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    frame(panel, "presets")
    reg["view.shape"].set(5)
    reg["preset.save.2"].fire()
    assert lib.project.active == 2 and lib.project.bank[2] == "FIELD"
    assert lib.read("presets", "FIELD")["values"]["view.shape"] == 5
    assert lib.current("presets") == "FIELD" and not lib.is_dirty("presets")
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


# ------------------------------------------------- plan 17: the right-click menu

def menu(panel, monkeypatch, pid: str, page: str, click: str | None = None
         ) -> tuple[list[str], list[str]]:
    """One frame of `page` with the context menu of `pid` open: (the lines
    of text it draws, its clickable items). A submenu is listed as
    "Unbind ▸" and its items as "Unbind/both"; every submenu is opened.
    `click` names the one item that reports a click. Nothing here has a
    mouse: the popup's `begin` is answered for it, so its contents draw
    into the page's own window."""
    lines: list[str] = []
    items: list[str] = []
    st = {"open": False, "path": []}
    real = {n: getattr(imgui, n) for n in (
        "begin_popup_context_item", "end_popup", "menu_item_simple", "begin_menu", "end_menu",
        "text", "text_disabled", "text_colored")}

    def begin_ctx(str_id=None, *a, **k):
        if str_id == f"##ctx.{pid}" and not st["open"]:
            st["open"] = True
            return True
        return False

    def end_popup():
        if st["open"]:
            st["open"] = False
        else:
            real["end_popup"]()

    def item(label, *a, **k):
        if not st["open"]:
            return real["menu_item_simple"](label, *a, **k)
        name = "/".join([*st["path"], label])
        items.append(name)
        return name == click

    def begin_menu(label, *a, **k):
        if not st["open"]:
            return real["begin_menu"](label, *a, **k)
        items.append("/".join([*st["path"], label]) + " ▸")
        st["path"].append(label)
        return True

    def end_menu():
        if st["open"]:
            st["path"].pop()
        else:
            real["end_menu"]()

    def text(name):
        def draw(*a):
            if st["open"]:
                lines.append(a[-1])
            return real[name](*a)
        return draw

    with monkeypatch.context() as m:
        m.setattr(imgui, "begin_popup_context_item", begin_ctx)
        m.setattr(imgui, "end_popup", end_popup)
        m.setattr(imgui, "menu_item_simple", item)
        m.setattr(imgui, "begin_menu", begin_menu)
        m.setattr(imgui, "end_menu", end_menu)
        for name in ("text", "text_disabled", "text_colored"):
            m.setattr(imgui, name, text(name))
        frame(panel, page)
    return lines, items


def _learn_over(rig):
    from hyperspace.learn import Learn

    rig.panel.learn = Learn(rig.reg, rig.router.table, lane=rig.router.lane)
    return rig.panel.learn


def test_the_menu_lists_and_unbinds_with_no_midi_adapter(rig, monkeypatch):
    """Plan 17 WP1: the menu reads the table, never the adapter. With
    `panel.midi` None the desk row's line is drawn with its glyph and
    Akai's name, each route has its line, and one Unbind removes what the
    lines list: a plain item with one kind bound, a submenu (desk / route /
    both) with both. "Unbind hand" and "performed by …" are gone."""
    panel, table = rig.panel, rig.router.table
    lrn = _learn_over(rig)
    assert panel.midi is None
    # Brightness: a knob and two step buttons, no route → a plain Unbind
    lines, items = menu(panel, monkeypatch, "view.bright", "view")
    assert lines[0] == "VIEW.BRIGHT"
    assert lines[1:] == ["K1 (track knob 1)", "B16 (▲) · step +3", "B17 (▼) · step -3"]
    assert "Unbind" in items and not any("▸" in i and "Unbind" in i for i in items)
    assert not any(i.startswith("Unbind hand") for i in items)
    # Speed: its knob, a hand route and — disabled — an LFO route → a submenu
    table.add(Binding("hand:8", "view.speed", "position"))
    table.add(Binding("lfo:0", "view.speed", "push", 0.5, enabled=False))
    rig.router.labels["hand"] = ["L x", "L depth", "L height", "L pitch", "L roll", "L yaw",
                                 "R x", "R depth", "R height"]
    lines, items = menu(panel, monkeypatch, "view.speed", "view")
    assert lines[1] == "K2 (track knob 2)"
    assert lines[2].startswith("R height positions") and lines[3].endswith("(off)")
    assert not any(s.startswith("performed by") for s in lines)
    unbind = [i for i in items if i.startswith("Unbind")]
    assert unbind[0] == "Unbind ▸" and unbind[1] == "Unbind/desk — K2"
    assert unbind[2].startswith("Unbind/route — R height, ") and unbind[3] == "Unbind/both"
    # by kind, from the submenu
    menu(panel, monkeypatch, "view.speed", "view", click="Unbind/desk — K2")
    assert not [b for b in table.desk() if b.target == "view.speed"]
    assert len(table.routes_to("view.speed")) == 2 and lrn.last.startswith("unbound view.speed")
    lines, items = menu(panel, monkeypatch, "view.speed", "view")
    assert "Unbind" in items and "Unbind ▸" not in items       # routes only now: plain
    menu(panel, monkeypatch, "view.speed", "view", click="Unbind")
    assert not table.routes_to("view.speed")
    lines, items = menu(panel, monkeypatch, "view.speed", "view")
    assert lines == ["VIEW.SPEED"] and not any(i.startswith("Unbind") for i in items)
    # both at once
    table.add(Binding("lfo:1", "view.bright", "push", 0.2))
    menu(panel, monkeypatch, "view.bright", "view", click="Unbind/both")
    assert not [b for b in table.bindings if b.target == "view.bright" and (b.is_midi or b.op == "push")]
    assert "K1 (track knob 1)" in lrn.last and lrn.last.startswith("unbound view.bright from ")
    # a panel with no learn object: the lines, and no Unbind
    table.bindings.append(Binding("cc:0:48", "view.bright", "abs", layer="preset"))
    panel.learn = None
    lines, items = menu(panel, monkeypatch, "view.bright", "view")
    assert "K1 (track knob 1)" in lines and "no learn" in lines
    assert not any(i.startswith("Unbind") for i in items)


def test_unbind_is_not_offered_on_a_session_only_param(rig, monkeypatch):
    """A fader's param is the session's (D6): its row's line reads
    "invariant", dim, and there is no Unbind item — none that could only
    refuse. A route on it brings a plain Unbind for the route alone."""
    panel, table = rig.panel, rig.router.table
    _learn_over(rig)
    lines, items = menu(panel, monkeypatch, "master.gain", "audio")
    assert "SM (MASTER fader) · invariant" in lines
    assert not any(i.startswith("Unbind") for i in items)
    session = [b.to_json() for b in table.midi() if b.layer != "preset"]
    table.add(Binding("lfo:0", "master.gain", "push", 0.1))
    lines, items = menu(panel, monkeypatch, "master.gain", "audio", click="Unbind")
    assert "Unbind" in items and "Unbind ▸" not in items
    assert not table.routes_to("master.gain")
    assert [b.to_json() for b in table.midi() if b.layer != "preset"] == session


def _learn_items(items: list[str]) -> list[str]:
    return [i for i in items if i.startswith(("Learn", "Cancel"))]


def test_the_menu_offers_learn_desk_and_learn_hand(rig, monkeypatch):
    """Plan 17 WP2, fork 5: the one "Learn" is **Learn desk** and **Learn
    hand ▸ left / right**. With a tracker: both; without: Learn desk only;
    a param a hand cannot drive (not modulatable): no hand item; a file
    path: neither. Each arms the learn with what it waits for; armed, the
    menu reads the hint and offers Cancel. §3's menu count holds."""
    panel = rig.panel
    lrn = _learn_over(rig)
    assert panel.hands is not None and panel.midi is None
    _, items = menu(panel, monkeypatch, "view.speed", "view")
    assert _learn_items(items) == ["Learn desk", "Learn hand ▸", "Learn hand/left",
                                   "Learn hand/right"]
    assert "Learn" not in items
    # §3: unmapped, a rig with hands → Learn desk · Learn hand ▸ · Route a lane here…
    rig.router.table.unbind("view.speed")
    _, items = menu(panel, monkeypatch, "view.speed", "view")
    assert [i for i in items if "/" not in i] == ["Learn desk", "Learn hand ▸",
                                                  "Route a lane here…"]
    # each arms with its want
    menu(panel, monkeypatch, "view.speed", "view", click="Learn desk")
    assert (lrn.learning, lrn.want) == ("view.speed", "desk")
    lines, items = menu(panel, monkeypatch, "view.speed", "view")
    assert _learn_items(items) == ["Cancel learn"]
    assert "click a control on the desk diagram…" in lines   # no adapter: the on-screen desk
    panel.midi = SimpleNamespace(table=rig.router.table)
    lines, _ = menu(panel, monkeypatch, "view.speed", "view")
    assert "turn a knob or press a button on the desk, or click one on the diagram…" in lines
    panel.midi = None
    menu(panel, monkeypatch, "view.speed", "view", click="Cancel learn")
    assert lrn.learning is None and lrn.want is None
    for side in ("left", "right"):
        menu(panel, monkeypatch, "view.speed", "view", click=f"Learn hand/{side}")
        assert (lrn.learning, lrn.want) == ("view.speed", f"hand:{side}")
        lines, _ = menu(panel, monkeypatch, "view.speed", "view")
        assert f"move the {side} hand…" in lines
        lrn.arm(None)
    # a bare learn (no want) keeps the old words
    lrn.arm("view.speed")
    assert panel._learn_hint() == "move a hand…"
    lrn.arm(None)
    # not modulatable: a knob may still set it, a hand may not
    assert not rig.reg["dream.gap"].modulatable
    _, items = menu(panel, monkeypatch, "dream.gap", "lookback")
    assert _learn_items(items) == ["Learn desk"]
    # a file path: nothing to learn (a knob cannot set a path)
    assert rig.reg["view.bmp_file"].kind is Kind.TEXT
    lines, items = menu(panel, monkeypatch, "view.bmp_file", "bitmap")
    assert items == [] and "not modulatable" in lines
    # no tracker: Learn desk only — §3: Learn desk · Route a lane here…
    panel.hands = None
    _, items = menu(panel, monkeypatch, "view.speed", "view")
    assert items == ["Learn desk", "Route a lane here…"]
    # a rig whose axes are one hand's: that side only
    panel.hands = SimpleNamespace(axes=[SimpleNamespace(side="right")])
    assert panel._hand_sides() == ["right"]


def test_the_footer_says_what_a_learn_waits_for_and_what_it_did(rig, monkeypatch):
    """Plan 17 WP2: an armed learn has the footer's message slot on every
    page — what it waits for, in red — and what a learn or an unbind did
    shows there for `MESSAGE_S` like the undo's line: a refusal in the
    warning colour, also while the learn it refused stays armed, and the
    same refusal twice shows twice."""
    from hyperspace import apc40, ui

    panel, table = rig.panel, rig.router.table
    lrn = _learn_over(rig)
    clock = [1000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    shown: list[tuple[str, tuple]] = []
    colored = imgui.text_colored

    def text_colored(col, s):
        if s.startswith("·  "):
            shown.append((s, (round(col.x, 3), round(col.y, 3), round(col.z, 3))))
        return colored(col, s)
    monkeypatch.setattr(imgui, "text_colored", text_colored)

    def footer(page=None) -> list[tuple[str, tuple]]:
        shown.clear()
        frame(panel, page)
        return list(shown)

    def rgb(c) -> tuple:
        return (round(c.x, 3), round(c.y, 3), round(c.z, 3))
    assert footer("view") == []                              # nothing armed, nothing said
    short = min((p.id for p in rig.reg), key=len)            # room for the whole line
    lrn.arm(short, "hand:left")
    line = f"·  learning {short} — move the left hand… (click to cancel)"
    for page in ("view", "routing", "presets", "system", "hands"):
        clock[0] += 0.5
        assert footer(page) == [(line, rgb(ui.RED))], page
    clock[0] += 10 * ui.MESSAGE_S                            # it never times out
    assert footer("lfo") == [(line, rgb(ui.RED))]
    # a longer id: the line keeps what it waits for; "click to cancel" is on the hover
    lrn.arm("fx.kaleido.segments", "hand:right")
    assert footer("lfo") == [("·  learning fx.kaleido.segments — move the right hand…",
                              rgb(ui.RED))]
    # a refusal that leaves it armed: the warning for MESSAGE_S, then the armed line again
    lrn.arm("view.depth4", "desk")
    table.set_layer("global")
    assert not lrn.learn_control("cc:0:48", apc40) and lrn.learning == "view.depth4"
    (said,) = footer("view")
    assert said[0].startswith("·  K1 (track knob 1) is on the global layer")
    assert said[1] == rgb(ui.WARN)
    clock[0] += ui.MESSAGE_S + 0.1
    (said,) = footer("faces")
    assert said[0].startswith("·  learning view.depth4 — ") and said[1] == rgb(ui.RED)
    assert not lrn.learn_control("cc:0:48", apc40)           # the same words again: shown again
    assert footer("faces")[0][1] == rgb(ui.WARN)
    # it lands: said in the faint colour for MESSAGE_S, then nothing
    table.set_layer("preset")
    clock[0] += ui.MESSAGE_S + 0.1
    assert lrn.learn_control("cc:0:48", apc40) and lrn.learning is None
    (said,) = footer("audio")
    assert said[0].startswith("·  learned view.depth4 ← K1 (track knob 1)")
    assert said[1] == rgb(ui.FAINT)
    clock[0] += ui.MESSAGE_S + 0.1
    assert footer("audio") == []
    # an unbind's line, and its refusal, the same way
    lrn.unbind("view.depth4", name=panel._row_name)          # as the menu's item calls it
    assert footer("view")[0][0].startswith("·  unbound view.depth4 from K1 (track knob 1)")
    clock[0] += 1.0
    lrn.unbind("master.gain")
    (said,) = footer("output")
    assert "invariant" in said[0] and said[1] == rgb(ui.WARN)
    # a panel with no learn object still draws its footer
    panel.learn = None
    clock[0] += ui.MESSAGE_S + 0.1
    assert footer("view") == []


# ------------------------------------------- plan 17 WP3: where the menu opens

def _mouse(panel, x, y, button=None, down=False):
    """One frame with the mouse at (x, y), a button going down or up."""
    io = imgui.get_io()
    io.add_mouse_pos_event(x, y)
    if button is not None:
        io.add_mouse_button_event(button, down)
    frame(panel)


def _click(panel, rect, button=0):
    x, y = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    _mouse(panel, x, y)
    _mouse(panel, x, y, button, True)
    _mouse(panel, x, y, button, False)
    frame(panel)


def _popups(monkeypatch) -> tuple[list[str], list[str]]:
    """(the ids of the context popups that are open, the items they draw),
    appended to as frames draw: the real `begin_popup_context_item`, so a
    popup is open only because a real right-click opened it."""
    opened: list[str] = []
    items: list[str] = []
    begin, item = imgui.begin_popup_context_item, imgui.menu_item_simple

    def begin_ctx(str_id=None, *a, **k):
        hit = begin(str_id, *a, **k)
        if hit:
            opened.append(str_id)
        return hit

    def menu_item(label, *a, **k):
        items.append(label)
        return item(label, *a, **k)
    monkeypatch.setattr(imgui, "begin_popup_context_item", begin_ctx)
    monkeypatch.setattr(imgui, "menu_item_simple", menu_item)
    return opened, items


def test_a_rows_label_opens_its_params_menu(rig, monkeypatch):
    """Plan 17 WP3: a right-click on a row's label — the dummy `_row` and
    `half` draw, the label line of a `_fader` — opens the menu the widget
    beside it draws: `open_popup_on_item_click` with the id `_ctx` uses,
    in the same id scope. Real mouse events over the real Panel: the popup
    that opens is the param's own, with its items, and nothing moved."""
    panel, reg = rig.panel, rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)   # the desk clear of the panel
    _learn_over(rig)
    labels: dict[str, tuple] = {}
    real = Panel._ctx_label

    def ctx_label(self, a):
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        labels[a.id] = (lo.x, lo.y, hi.x, hi.y)
        return real(self, a)
    monkeypatch.setattr(Panel, "_ctx_label", ctx_label)
    opened, items = _popups(monkeypatch)
    for page, pid in (("camera", "camera.zoom"),      # a `_row`
                      ("view", "view.bright"),        # a `_fader`
                      ("audio", "master.gain"),       # a fader whose row is the session's
                      ("lfo", "tempo.bpm"),           # a `half`, in a table cell
                      ("lookback", "dream.tint_hue")):
        labels.clear()
        frame(panel, page)
        frame(panel)
        assert pid in labels, f"{pid}: no label on {page}"
        rect = labels[pid]
        assert rect[2] - rect[0] > 8 and rect[3] - rect[1] > 8
        before = reg[pid].base
        opened.clear()
        items.clear()
        _click(panel, rect, button=1)
        assert opened and set(opened) == {f"##ctx.{pid}"}, (pid, opened)
        assert "Learn desk" in items and "Route a lane here…" in items
        assert reg[pid].base == before
        # a left click elsewhere closes it; a left click on the label opens nothing
        _click(panel, (2, 2, 4, 4))
        opened.clear()
        _click(panel, rect, button=0)
        assert opened == [] and reg[pid].base == before


def test_every_meter_has_the_band_select_menu(rig, monkeypatch):
    """Plan 17 WP3: one `_ctx` per meter — it was meter 0 only — each
    under its own key, so no two popups on the page share an id (the band
    combo's is the bare one). A real right-click on the fourth meter opens
    that meter's menu and selects nothing."""
    panel, reg = rig.panel, rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    _learn_over(rig)
    n = rig.chain.n
    keys: list[str] = []
    rects: dict[str, tuple] = {}
    real = Panel._ctx

    def ctx(self, a, key="", extra=None):
        if a.id == "band.select":
            keys.append(key)
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            rects[key] = (lo.x, lo.y, hi.x, hi.y)
        return real(self, a, key, extra)
    monkeypatch.setattr(Panel, "_ctx", ctx)
    frame(panel, "analyzer")
    keys.clear()
    frame(panel)
    meters = [f".{i}" for i in range(n)]
    assert [k for k in keys if k] == meters
    assert len(keys) == len(set(keys)), f"two menus share an id: {keys}"
    opened, items = _popups(monkeypatch)
    sel = reg["band.select"].base
    assert sel != 3
    _click(panel, rects[".3"], button=1)
    assert opened and set(opened) == {"##ctx.band.select.3"}
    assert "Learn desk" in items
    assert reg["band.select"].base == sel             # a right-click selects nothing
    # armed from a meter, the learn's red frame is on the meters too
    framed: list[str] = []
    frame_ = Panel._learn_frame
    monkeypatch.setattr(Panel, "_learn_frame",
                        lambda self, p: (framed.append(p.id), frame_(self, p))[1])
    frame(panel)
    assert framed.count("band.select") >= n
    _click(panel, (2, 2, 4, 4))
    _click(panel, rects[".3"])                        # the left click still selects
    assert reg["band.select"].base == 3


# ------------------------------------------- plan 17 WP4: click a control, then a param

def _control(glyph: str):
    from hyperspace import apc40

    return next(c for c in apc40.LAYOUT if c.glyph == glyph)


def _depths(monkeypatch) -> dict[str, tuple[int, bool]]:
    """Each page as it is entered: {key: (how many `begin_disabled` are
    open around it, `Panel._picking`)}."""
    depth = [0]
    seen: dict[str, tuple[int, bool]] = {}
    begin, end = imgui.begin_disabled, imgui.end_disabled

    def begin_disabled(*a, **k):
        depth[0] += 1
        return begin(*a, **k)

    def end_disabled():
        depth[0] -= 1
        return end()
    monkeypatch.setattr(imgui, "begin_disabled", begin_disabled)
    monkeypatch.setattr(imgui, "end_disabled", end_disabled)
    for key in PAGE_KEYS:
        draw = getattr(Panel, f"_page_{key}")

        def page(self, dt, _draw=draw, _key=key):
            seen[_key] = (depth[0], self._picking)
            return _draw(self, dt)
        monkeypatch.setattr(Panel, f"_page_{key}", page)
    return seen


def test_a_picked_control_dims_every_page_but_routing(rig, monkeypatch):
    """While a mappable control is picked `Panel._draw` draws the open
    page inside `begin_disabled` — dimmed, no widget taking a click — for
    every page but ROUTING; and never otherwise: nothing picked, an
    invariant control picked, the global layer up, a learn armed."""
    from hyperspace import ui_desk

    panel, table = rig.panel, rig.router.table
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    lrn = _learn_over(rig)
    seen = _depths(monkeypatch)

    def pages() -> dict[str, tuple[int, bool]]:
        seen.clear()
        for key in PAGE_KEYS:
            frame(panel, key)
        assert set(seen) == set(PAGE_KEYS)
        return dict(seen)
    idle = {k: (0, False) for k in PAGE_KEYS}
    assert pages() == idle
    lrn.pick(_control("D3").source)
    dimmed = pages()
    assert dimmed.pop("routing") == (0, False)
    assert dimmed == {k: (1, True) for k in PAGE_KEYS if k != "routing"}
    assert panel._picking is False                           # only while the page draws
    lrn.pick(_control("S3").source)                          # invariant: picked for the look only
    assert ui_desk.picked(panel) is not None and pages() == idle
    lrn.pick(_control("D3").source)
    table.set_layer("global")                                # the session's layer: nothing maps
    assert pages() == idle
    table.set_layer("preset")
    assert pages()["view"] == (1, True)
    lrn.arm("view.speed", "desk")                            # arming lets the pick go
    assert lrn.control is None and pages() == idle
    lrn.arm(None)
    lrn.pick(_control("D3").source)
    assert pages()["view"] == (1, True)
    ui_desk.let_go(panel)
    assert pages() == idle


def _widgets(monkeypatch) -> dict[str, tuple]:
    """Where each param's widget was last drawn: {id: its item rect}, read
    as `Panel._ctx` is called on it."""
    rects: dict[str, tuple] = {}
    real = Panel._ctx

    def ctx(self, a, key="", extra=None):
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        rects[a.id] = (lo.x, lo.y, hi.x, hi.y)
        return real(self, a, key, extra)
    monkeypatch.setattr(Panel, "_ctx", ctx)
    return rects


def test_a_click_on_a_param_maps_the_picked_control(rig, monkeypatch):
    """Fork 3 (a), with real mouse events over the real Panel: click D3
    on the desk, then click a param's widget on the dimmed page — the
    control is on that param (the row the knob learn makes, one undo
    step, the old knob named), the widget did not move, the page is
    bright again. A file path is no target. The click that picks a
    control on the big desk — which brings the panel back under the
    mouse — maps nothing."""
    from hyperspace import ui_desk, undo

    panel, table, reg = rig.panel, rig.router.table, rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    lrn = _learn_over(rig)
    pushes: list[str] = []
    push = undo.push
    monkeypatch.setattr(undo, "push", lambda label, *a, **k: (pushes.append(label),
                                                              push(label, *a, **k))[1])
    rects = _widgets(monkeypatch)
    labels: dict[str, tuple] = {}
    ctx_label = Panel._ctx_label

    def label(self, a):
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        labels[a.id] = (lo.x, lo.y, hi.x, hi.y)
        return ctx_label(self, a)
    monkeypatch.setattr(Panel, "_ctx_label", label)
    d3 = _control("D3")
    for _ in range(3):
        frame(panel, "view")
    assert [b.source for b in table.desk() if b.target == "view.speed" and b.kind == "cc"] \
        == ["cc:0:49"]
    _click(panel, ui_desk.rect(panel, d3))
    assert lrn.control == d3.source and ui_desk.picking(panel) is d3
    speed, bright = reg["view.speed"].base, reg["view.bright"].base
    # a click on the dimmed page that is on no param's widget or label
    # (Speed's readout, right of its label): nothing
    _click(panel, (rects["view.speed"][2] - 12, labels["view.speed"][1],
                   rects["view.speed"][2] - 4, labels["view.speed"][3]))
    assert lrn.control == d3.source and pushes == []
    _click(panel, rects["view.speed"])
    assert lrn.control is None and ui_desk.picking(panel) is None
    assert [b.source for b in table.desk() if b.target == "view.speed" and b.kind == "cc"] \
        == [d3.source]
    assert lrn.last == "learned view.speed ← D3 (device knob 3) (into the preset); K2 let go"
    assert pushes == ["learn view.speed"]
    assert (reg["view.speed"].base, reg["view.bright"].base) == (speed, bright)   # nothing moved
    # bright again: the same click now moves the fader
    _click(panel, rects["view.speed"])
    assert reg["view.speed"].base != speed and pushes == ["learn view.speed"]
    # a row's label is the param's too (WP3): a click on the word maps
    lrn.pick(_control("D8").source)
    frame(panel)
    depth = reg["view.depth4"].base
    _click(panel, labels["view.depth4"])
    assert lrn.control is None and reg["view.depth4"].base == depth
    assert any(b.source == "cc:*:23" and b.target == "view.depth4" for b in table.desk())
    # a combo and a check are targets too; a file path is not
    for page, pid in (("view", "view.shape"), ("output", "output.overlay")):
        frame(panel, page)
        frame(panel)
        assert pid in rects, pid
        lrn.pick(_control("D4").source)
        frame(panel)
        before = reg[pid].base
        _click(panel, rects[pid])
        assert lrn.control is None and reg[pid].base == before, pid
        assert any(b.source == "cc:*:19" and b.target == pid for b in table.desk()), pid
    frame(panel, "bitmap")
    frame(panel)
    lrn.pick(_control("D5").source)
    frame(panel)
    n = len(pushes)
    _click(panel, rects["view.bmp_file"])
    assert lrn.control == "cc:*:20" and len(pushes) == n
    ui_desk.let_go(panel)
    # the big desk: the click that picks brings the panel back under the
    # mouse — that click is the desk's, and maps nothing
    panel.reg["ui.panel"].set(False)
    for _ in range(3):
        frame(panel, "view")
    assert ui_desk._state(panel)["unit"][0] >= ui_desk.LABEL_UNIT
    target = next(c for c in ui_desk.apc40.LAYOUT if c.kind == "knob" and c.glyph.startswith("K")
                  and ui_desk.rect(panel, c)[0] > rects["view.speed"][0])
    desk = [b.to_json() for b in table.desk()]
    values = reg.snapshot()
    spot = ui_desk.rect(panel, target)
    _click(panel, spot)
    assert panel.open and lrn.control == target.source
    assert [b.to_json() for b in table.desk()] == desk and len(pushes) == n
    # …and nor does a second click at the same spot (a double click, or
    # "click it again to let go" on a desk that is no longer there): the
    # page is dimmed, so it moves nothing either
    assert ui_desk.picking(panel) is target and not ui_desk.armed(panel)
    _click(panel, spot)
    _click(panel, spot)
    assert lrn.control == target.source and reg.snapshot() == values
    assert [b.to_json() for b in table.desk()] == desk and len(pushes) == n
    # once the mouse has left that spot a click on a param maps as ever
    _click(panel, rects["view.bright"])
    assert lrn.control is None and len(pushes) == n + 1
    assert any(b.source == target.source and b.target == "view.bright" for b in table.desk())


def test_the_footer_says_what_is_picked_and_a_click_lets_go(rig, monkeypatch):
    """The picked state is loud and easy to leave: the footer's slot
    reads what is picked and the seconds left, in red, on every page; the
    desk's header says it too; a real click on the footer's line lets
    go. An invariant pick reads why, in the dim ink."""
    from hyperspace import ui, ui_desk

    panel = rig.panel
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    lrn = _learn_over(rig)
    clock = [3000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    shown: list[tuple[str, tuple, tuple]] = []
    colored = imgui.text_colored

    def text_colored(col, s):
        out = colored(col, s)
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        shown.append((s, (round(col.x, 3), round(col.y, 3), round(col.z, 3)),
                      (lo.x, lo.y, hi.x, hi.y)))
        return out
    monkeypatch.setattr(imgui, "text_colored", text_colored)

    def rgb(c) -> tuple:
        return (round(c.x, 3), round(c.y, 3), round(c.z, 3))

    def lines(page=None) -> list[tuple[str, tuple, tuple]]:
        shown.clear()
        frame(panel, page)
        return list(shown)

    def footer(page=None):
        return [x for x in lines(page) if x[0].startswith("·  ")]
    assert footer("view") == []
    lrn.pick(_control("D3").source)
    for page in ("view", "system", "hands"):
        (said,) = footer(page)
        assert said[0].startswith("·  D3 picked (20 s): click a param"), page
        assert said[1] == rgb(ui.RED)
    # ROUTING is not dimmed — a click there is the widget's own — and both lines say so
    (said,) = footer("routing")
    assert said[0].startswith("·  D3 picked (20 s): click a param on any other page")
    assert [x for x in lines() if x[0].startswith("D3 picked: its line is framed")]
    frame(panel, "view")
    clock[0] += 7.2
    assert footer("view")[0][0].startswith("·  D3 picked (13 s)")
    # the desk's header says it too, with how to let go
    head = [x for x in lines() if x[0].startswith("D3 picked: click a param")]
    assert head and head[0][1] == rgb(ui.RED)
    # a line said before the pick gives way to it; one said after shows first
    lrn.said("unbound view.speed from K2 (track knob 2)")
    clock[0] += 0.1
    assert footer()[0][0].startswith("·  unbound view.speed")
    clock[0] += ui.MESSAGE_S + 0.1
    # a click on a line that is not the pick's own lets nothing go
    lrn.said("unbound view.bright from K1 (track knob 1)")
    clock[0] += 0.1
    (said,) = footer()
    assert said[0].startswith("·  unbound view.bright")
    _click(panel, said[2])
    assert lrn.control is not None
    clock[0] += ui.MESSAGE_S + 0.1
    (said,) = footer()
    assert said[0].startswith("·  D3 picked (") and lrn.control is not None
    _click(panel, said[2])                                   # a real click on the line
    assert lrn.control is None and footer() == []
    lrn.said("learned something")
    clock[0] += 0.1
    assert footer()[0][0] == "·  learned something"
    clock[0] += 1.0
    lrn.pick(_control("D3").source)
    clock[0] += 0.1
    assert footer()[0][0].startswith("·  D3 picked (20 s)")   # the pick is newer: it shows at once
    # an invariant control: why it cannot be mapped, dim
    lrn.pick(_control("S3").source)
    clock[0] += 0.1
    (said,) = footer("view")
    assert said[0].startswith("·  S3 (track fader 3) is invariant") and said[1] == rgb(ui.DIM)
    # with the panel hidden the header alone carries it — the whole line
    panel.reg["ui.panel"].set(False)
    lrn.pick(_control("D3").source)
    frame(panel)
    full = [x[0] for x in lines() if x[0].startswith("D3 picked")]
    assert full and full[0].startswith(
        "D3 picked: click a param to put it here · click D3 again to let go · ")
    # a line said while the panel was hidden (no footer saw it) does not
    # take the slot from the pick the moment the panel comes back
    ui_desk.let_go(panel)
    frame(panel)
    lrn.said("said while the panel was hidden")
    clock[0] += 30.0
    frame(panel)
    ui_desk.click(panel, rig.router.table, _control("D3"), None)
    assert panel.open
    (said,) = footer()
    assert said[0].startswith("·  D3 picked (20 s)")


def test_the_click_wording_is_switched_on(rig, monkeypatch):
    """WP2 wrote the click's wording behind `hasattr(ui_desk, "click")`;
    WP4's `click` switches it on: the armed hint and ROUTING's desk
    section both say a control can be clicked — and ROUTING's line still
    fits its child."""
    from hyperspace import ui_desk

    panel = rig.panel
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    lrn = _learn_over(rig)
    assert callable(ui_desk.click)
    lrn.arm("view.speed", "desk")
    assert panel.midi is None
    assert panel._learn_hint() == "click a control on the desk diagram…"
    panel.midi = SimpleNamespace(table=rig.router.table)
    assert panel._learn_hint() \
        == "turn a knob or press a button on the desk, or click one on the diagram…"
    panel.midi = None
    lrn.arm(None)
    hint: list[tuple[str, float, float]] = []
    colored = imgui.text_colored

    def text_colored(col, s):
        out = colored(col, s)
        if s.startswith("new"):
            hint.append((s, imgui.get_item_rect_max().x,
                         imgui.get_window_pos().x + imgui.get_window_width()))
        return out
    monkeypatch.setattr(imgui, "text_colored", text_colored)
    frame(panel, "routing")
    frame(panel)
    assert hint and hint[-1][0].endswith(", or click a control")
    assert hint[-1][1] <= hint[-1][2], "the desk section's hint runs past its child"


def test_the_ghost_style_is_on_the_hands_page_while_the_ghost_is_on(rig, monkeypatch):
    """Plan 21 WP6: the style combo leads the ghost's second line, the
    guide beside it, while the ghost is on; off, it is not drawn. The page
    still fits with everything showing (test_the_hands_page_fits_with_every_ghost_line)."""
    combos: list[str] = []
    real = Panel._combo

    def seen(self, pid, *a, **k):
        combos.append(pid)
        return real(self, pid, *a, **k)
    monkeypatch.setattr(Panel, "_combo", seen)
    rig.reg["ghost.on"].set(True)
    _hands_page_text(rig, monkeypatch)
    assert "ghost.style" in combos
    combos.clear()
    rig.reg["ghost.on"].set(False)
    _hands_page_text(rig, monkeypatch)
    assert "ghost.style" not in combos


# ---- plan 21 WP4: the OUTPUT page's blocks and the footer ----

def _output_page(rig, monkeypatch, page="output") -> tuple[list[str], list[tuple]]:
    """Every text and checkbox label the page (and the footer) draws, and
    each item's right edge against its window's, at the control size."""
    import hyperspace.ui as ui_mod

    drawn: list[str] = []
    edges: list[tuple] = []
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)

    def rec(s):
        drawn.append(s)
        edges.append((s, imgui.get_item_rect_max().x,
                      imgui.get_window_pos().x + imgui.get_window_width()))

    real = {n: getattr(imgui, n) for n in ("text", "text_colored", "text_disabled", "checkbox")}
    with monkeypatch.context() as m:
        m.setattr(ui_mod.imgui, "text", lambda s: (real["text"](s), rec(s))[0])
        m.setattr(ui_mod.imgui, "text_colored",
                  lambda c, s: (real["text_colored"](c, s), rec(s))[0])
        m.setattr(ui_mod.imgui, "text_disabled", lambda s: (real["text_disabled"](s), rec(s))[0])
        m.setattr(ui_mod.imgui, "checkbox",
                  lambda label, v: (real["checkbox"](label, v), rec(label.split("##")[0]))[0])
        for _ in range(3):
            drawn.clear()
            edges.clear()
            frame(rig.panel, page)
    return drawn, list(edges)


def test_the_output_page_fits_with_four_outputs_and_overlays_rows(rig, monkeypatch):
    """Four outputs (the most), each block's three lines, a missing
    output's line and overlay's three rows showing: the OUTPUT page does not
    scroll at the control size and no line runs past the page's right edge."""
    rig.panel.output.allowed = True
    for sl in rig.slots:
        sl.error = "present: RuntimeError: a long error that the page must cut to fit"
    over = _page_scroll(rig, monkeypatch)
    assert over["output"] <= 0
    drawn, edges = _output_page(rig, monkeypatch)
    assert drawn.count("scene") == 4 and drawn.count("through effects") == 4
    for s, right, edge in edges:
        assert right <= edge + 1, f"{s!r} runs past the page ({right} > {edge})"


def test_the_output_page_says_what_each_output_shows(rig, monkeypatch):
    """Plan 21 WP4 / fork F8: words, not a picture. Each output's "shows:"
    line is `outputs.route`'s answer with master × own dim; a switch that
    can do nothing says why; an output that did not open is one line."""
    from hyperspace.outputs import Switches as S
    from hyperspace.ui import output_shows

    # the words, as a pure function of the switches and the frame
    assert output_shows(S(), False, True, 1.0) == ("scene + hands over the effects", "")
    assert output_shows(S(), False, False, 1.0) == ("scene", "")
    assert output_shows(S(through=True), True, True, 1.0) == (
        "scene + hands through the effects", "")
    assert output_shows(S(scene=False), True, True, 1.0) == ("hands", "")
    assert output_shows(S(scene=False, through=True), True, True, 1.0) == (
        "hands through the effects", "")
    assert output_shows(S(hands=False, dim=0.8), True, True, 0.8) == ("scene · 64%", "")
    assert output_shows(S(scene=False, hands=False), True, True, 1.0) == (
        "black — nothing switched on", "nothing")
    assert output_shows(S(scene=False), True, False, 1.0)[1] == "no hand"
    assert output_shows(S(dim=0.0), True, True, 1.0) == ("black — dim 0", "dim")
    assert output_shows(S(), True, True, 0.0) == ("black — master dim", "master")
    # on the page
    reg, slots = rig.reg, rig.slots
    reg["output.2.hands"].set(False)
    reg["output.2.dim"].set(0.6)
    reg["output.3.scene"].set(False)
    reg["output.3.hands"].set(False)
    reg["output.4.through"].set(True)
    slots[1].error = "present: RuntimeError: lost the context"
    drawn, _ = _output_page(rig, monkeypatch)
    assert "1  glass" in drawn and "2  projector" in drawn
    shows = [s for s in drawn if s.startswith("shows: ")]
    assert shows == ["shows: scene", "shows: scene · 60%", "shows: black — nothing switched on",
                     "shows: scene"]          # no hand shows in this rig: the hands add nothing
    assert "present: RuntimeError: lost the context" in drawn
    # ghost hands off: said beside the outputs whose hands are on; no effect: said on 4
    reg["ghost.on"].set(False)
    drawn, _ = _output_page(rig, monkeypatch)
    why = [s for s in drawn if s.startswith(("hands:", "through:"))]
    assert why[0] == "hands: ghost hands are off (HANDS page)"
    assert why[-1] == "hands: ghost hands are off (HANDS page) · through: no effect on"
    assert "paced by output 1 · frame 1920×1080 · below: output 1's window" in drawn
    # an output the config lists but that did not open: one line, why
    slots[1].win, slots[1].missing = None, "screen 2 is not connected"
    drawn, _ = _output_page(rig, monkeypatch)
    assert "2  projector — screen 2 is not connected" in drawn
    assert len([s for s in drawn if s.startswith("shows: ")]) == 3


def test_the_output_page_with_one_output_has_no_dim_of_its_own(tmp_path, monkeypatch):
    """No list in the config: one block, "1", scene and hands ticked,
    through effects not, and no dim row of its own (hand check Q1)."""
    from hyperspace.overlay import register_switches as reg_sw

    with build_rig(tmp_path) as r:
        for p in list(r.reg):
            if p.id.startswith(("output.2.", "output.3.", "output.4.", "output.1.")):
                r.reg.remove_prefix(p.id.rsplit(".", 1)[0] + ".")
        one = [Slot(1, win="w1")]
        reg_sw(r.reg, one)
        r.panel.outputs = one
        drawn, _ = _output_page(r, monkeypatch)
        assert drawn[drawn.index("1"):drawn.index("1") + 4] == [
            "1", "scene", "hands", "through effects"]
        assert "output.1.dim" not in r.reg and not any(s.startswith("paced") for s in drawn)
        assert [s for s in drawn if s.startswith("shows: ")] == ["shows: scene"]
        assert r.reg["output.1.scene"].label == "Scene"


def test_the_footer_names_a_black_output(rig, monkeypatch):
    """On every page: "· output 2 black" while an output shows nothing for
    a reason other than the master dim (which says "dim black" itself)."""
    reg = rig.reg
    drawn, _ = _output_page(rig, monkeypatch, "view")
    assert not any("black" in s for s in drawn)
    reg["output.2.scene"].set(False)
    reg["output.2.hands"].set(False)
    for page in ("view", "presets", "output"):
        drawn, _ = _output_page(rig, monkeypatch, page)
        assert "·  output 2 black" in drawn, page
    reg["output.4.dim"].set(0.0)
    drawn, _ = _output_page(rig, monkeypatch, "view")
    assert "·  outputs 2, 4 black" in drawn
    # the master at black: the footer's "dim black" says it; no output is named for it
    reg["output.2.scene"].set(True)
    reg["output.4.dim"].set(1.0)
    reg["output.dim"].set(0.0)
    drawn, _ = _output_page(rig, monkeypatch, "view")
    assert "·  dim black" in drawn and not any(s.endswith(" black") and "output" in s
                                                for s in drawn)
