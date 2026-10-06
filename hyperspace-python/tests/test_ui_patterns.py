"""Plan 22 B2: the FACES page (ui_patterns.py) — the pattern browser and the
eight inputs, named, with what each does in the mode on show and what
drives it. Headless imgui over the real registry (test_fx's PageRig, with
this page in its frame); the swatches are the renderer's and a headless
panel has none, so the chips draw their placeholder discs.

The page's fit is measured here in this container's font metrics, which
are not the owner's Mac's (test_fx's own fit tests miss there by 18 px):
it is asserted with slack and reported as unverified.
"""

import pytest
from test_fx import PageRig

from hyperspace import patterns, ui_patterns, ui_routing
from hyperspace.patterns import INPUTS, MODES, N_INPUTS
from hyperspace.routing import Binding, Bindings, Macro, Router, Sub


class FacesRig(PageRig):
    """PageRig with the FACES page in its frame, at the page's own width
    (the control window less the rail), and the mode chips' and the
    links' rects recorded too."""

    def __init__(self, tmp_path, monkeypatch, r=None):
        super().__init__(tmp_path, monkeypatch, r)
        imgui = self.imgui
        real = imgui.invisible_button

        def rec(label, *a, **k):
            out = real(label, *a, **k)
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            self.rects[label.split("##", 1)[-1]] = (lo.x, lo.y, hi.x, hi.y)
            return out
        monkeypatch.setattr(imgui, "invisible_button", rec)
        self.tips: list[str] = []
        real_tip = imgui.set_tooltip
        monkeypatch.setattr(imgui, "set_tooltip",
                            lambda t, *a: (self.tips.append(t), real_tip(t.replace("%", "%%")))[1])

    def frame(self) -> None:
        from hyperspace.ui import PANEL_W, RAIL_W

        imgui = self.imgui
        self.rects.clear()
        self.texts.clear()
        self.wrapped.clear()
        imgui.new_frame()
        imgui.set_next_window_pos(imgui.ImVec2(0, 0))
        imgui.set_next_window_size(imgui.ImVec2(PANEL_W - RAIL_W, self.size[1]))
        imgui.begin("page", None, imgui.WindowFlags_.no_title_bar | imgui.WindowFlags_.no_move)
        ui_patterns.page(self.panel, 1 / 60)
        imgui.end()
        imgui.end_frame()

    def hover(self, item: str) -> None:
        io = self.imgui.get_io()
        self.frame()
        x0, y0, x1, y1 = self.rects[item]
        io.add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
        self.tips.clear()
        self.frame()
        self.frame()


@pytest.fixture()
def faces(tmp_path, monkeypatch):
    rig = FacesRig(tmp_path, monkeypatch)
    rig.panel.router = Router(rig.reg, Bindings([]))
    rig.reg["view.faces"].set(True)
    yield rig
    rig.close()


def test_the_faces_page_is_in_pages_and_draws_this_module(faces, monkeypatch):
    from hyperspace import ui
    from hyperspace.hotreload import MODULES

    assert ("faces", "faces", "pattern") in ui.PAGES
    seen = []
    monkeypatch.setattr(ui_patterns, "page", lambda panel, dt: seen.append(panel))
    faces.reg["ui.page"].set(ui.PAGE_KEYS.index("faces"))
    faces.imgui.new_frame()
    faces.panel.draw(1 / 60, 60.0)
    faces.imgui.end_frame()
    assert seen == [faces.panel]
    assert MODULES.index("ui_patterns") < MODULES.index("ui")


def test_every_mode_has_a_chip_and_its_line(faces):
    faces.frame()
    for k, m in enumerate(MODES):
        assert f"mode.{k}" in faces.rects, m.name
        faces.hover(f"mode.{k}")
        assert f"{m.name} — {m.about}" in faces.tips


def test_a_chip_click_shows_that_mode_and_its_about(faces):
    p = faces.reg["view.pattern"]
    for k in (7, 3, 0, 11):
        faces.click(f"mode.{k}")
        assert p.base == k
        faces.frame()
        line = ui_patterns.FLAT_NOTE if k == 0 else MODES[k].about
        assert line in faces.texts, MODES[k].name


def test_prev_and_next_step_round_the_modes(faces):
    p = faces.reg["view.pattern"]
    p.set(len(MODES) - 1)
    faces.click("next.view.pattern")
    assert p.base == 0
    faces.click("prev.view.pattern")
    assert p.base == len(MODES) - 1


@pytest.mark.parametrize("mode", range(1, len(MODES)), ids=[m.name for m in MODES[1:]])
def test_the_eight_rows_are_named_and_say_what_each_does_in_this_mode(faces, mode):
    faces.reg["view.pattern"].set(mode)
    faces.frame()
    for k, i in enumerate(INPUTS):
        assert f"pattern.mod.{k}" in faces.rects, i.name    # the slider
        assert f"neutral.pattern.mod.{k}" in faces.rects
        assert patterns.effect(mode, k) in faces.texts, (i.name, patterns.effect(mode, k))
    assert f"inputs · {MODES[mode].name}".upper() in faces.texts


def test_flat_says_it_reads_no_input(faces):
    faces.reg["view.pattern"].set(0)
    faces.frame()
    assert faces.texts.count(ui_patterns.FLAT_ROW) == N_INPUTS


def test_a_rows_slider_hover_says_what_the_input_means(faces):
    for k in (0, patterns.SPREAD):
        faces.hover(f"pattern.mod.{k}")
        assert any(INPUTS[k].meaning in t for t in faces.tips), INPUTS[k].name


def test_a_routed_input_shows_its_source_and_a_click_opens_routing(faces):
    from hyperspace import ui

    table = faces.panel.router.table
    table.add(Binding("lane:1", "pattern.mod.1", "push", 0.5))
    faces.reg["view.pattern"].set(1)
    said = ui_patterns.drivers(faces.panel, "pattern.mod.1")
    assert said.startswith("lane 1 pushes +0.5") or "pushes +0.5" in said
    faces.frame()
    assert "drv.pattern.mod.1" in faces.rects
    assert "drv.pattern.mod.0" not in faces.rects                   # nothing on SCALE
    faces.click("drv.pattern.mod.1")
    assert faces.reg["ui.page"].value == ui.PAGE_KEYS.index("routing")
    assert ui_routing._state(faces.panel)["find"] == "pattern.mod.1"


def test_the_driver_line_names_the_macro_desk_and_base_subscribers(faces):
    table = faces.panel.router.table
    b = Binding("lfo:0", "pattern.mod.6", "push", 0.5)
    table.add(b)
    table.macros = {"macro.2": Macro("wash", [Sub(depth=("lfo:0", "pattern.mod.6"))]),
                    "macro.4": Macro("", [Sub(base="pattern.mod.7")])}
    assert "pushes +0.5 × wash" in ui_patterns.drivers(faces.panel, "pattern.mod.6")
    assert ui_patterns.drivers(faces.panel, "pattern.mod.7") == "macro.4 sets its base"
    b.enabled = False
    assert ui_patterns.drivers(faces.panel, "pattern.mod.6").endswith("(off)")


def test_an_undriven_input_offers_the_conventions_source_and_stays_here(faces):
    from hyperspace import ui

    faces.reg["ui.page"].set(ui.PAGE_KEYS.index("faces"))
    faces.reg["view.pattern"].set(4)
    names = faces.panel.audio.chain.band_names
    assert ui_patterns.suggest(faces.panel, 0) == ("lane:0", names[0])
    assert ui_patterns.suggest(faces.panel, patterns.HUE) == ("lfo:0", "LFO 1")
    assert ui_patterns.suggest(faces.panel, patterns.SPREAD) == ("lfo:1", "LFO 2")
    faces.frame()
    faces.click("route.pattern.mod.0")
    (b,) = faces.panel.router.table.routes_to("pattern.mod.0")
    assert (b.source, b.op, b.value) == ("lane:0", "push", ui_patterns.ROUTE_DEPTH)
    assert faces.reg["ui.page"].value == ui.PAGE_KEYS.index("faces")
    faces.frame()
    assert "drv.pattern.mod.0" in faces.rects and "route.pattern.mod.0" not in faces.rects


def test_neutral_puts_one_input_back_and_all_neutral_every_one(faces, monkeypatch):
    from hyperspace import undo

    ps = [faces.reg[f"pattern.mod.{k}"] for k in range(N_INPUTS)]
    for k, p in enumerate(ps):
        p.set_value(0.2 + 0.3 * k)
    faces.click("neutral.pattern.mod.2")
    assert ps[2].base == 1.0 and ps[0].base == pytest.approx(0.2)
    pushes = []
    monkeypatch.setattr(undo, "push", lambda label, **k: pushes.append(label))
    faces.click("neutral.all")
    assert [p.base for p in ps] == [1.0] * N_INPUTS
    assert pushes == [ui_patterns.NEUTRAL_STEP]
    faces.click("neutral.all")                       # nothing to move: no step
    assert pushes == [ui_patterns.NEUTRAL_STEP]


def test_a_driven_input_reads_base_against_effective(faces):
    """The slider is the panel's: `base → effective` while a source rides it."""
    p = faces.reg["pattern.mod.0"]
    p.modulate(0.2)
    faces.reg.apply()
    faces.frame()
    assert p.modulated and faces.panel.ghosts >= 1


def test_faces_off_says_so_and_mends(faces):
    f = faces.reg["view.faces"]
    f.set(False)
    faces.frame()
    assert ui_patterns.FACES_OFF in faces.texts
    faces.click("idle.view.faces")
    assert f.base is True
    faces.frame()
    assert ui_patterns.FACES_OFF not in faces.texts


def test_the_glsl_error_line_is_kept(faces):
    from types import SimpleNamespace

    faces.panel.renderer = SimpleNamespace(pattern_error="2:14: syntax error")
    faces.frame()
    assert "GLSL: 2:14: syntax error" in faces.texts


def test_the_page_asks_the_renderer_for_swatches_and_draws_them(faces):
    from types import SimpleNamespace

    asked, got = [], []
    tex = SimpleNamespace(glo=0)
    faces.panel.renderer = SimpleNamespace(pattern_error="", want_swatches=lambda: asked.append(1),
                                           swatch=lambda k: got.append(k) or tex)
    faces.frame()
    assert asked == [1] and got == list(range(len(MODES)))


def test_the_page_fits_with_every_row_driven_and_flat_or_the_longest_mode(tmp_path, monkeypatch):
    """The whole panel at the control size, FACES open: no scroll, with
    every input driven (the longest second lines), on FLAT and on each
    mode, with each of what the line under the chips can say — the GLSL
    error, Faces off, and the mode's own line, which wraps and so is the
    tallest of the three. UNVERIFIED on the owner's Mac: this container's
    font metrics differ (test_fx's fit tests miss here by 18 px), so some
    slack is asked: 12 px."""
    from types import SimpleNamespace

    from hyperspace.ui import PAGE_KEYS, Panel
    rig = FacesRig(tmp_path, monkeypatch)
    try:
        imgui, reg, panel = rig.imgui, rig.reg, rig.panel
        panel.router = Router(reg, Bindings([
            Binding(f"lane:{k}", f"pattern.mod.{k}", "push", 0.5) for k in range(6)]
            + [Binding(f"lfo:{k - 6}", f"pattern.mod.{k}", "push", 0.5) for k in (6, 7)]))
        panel.router.table.macros = {"macro.1": Macro("a long macro name", [
            Sub(depth=(f"lane:{k}", f"pattern.mod.{k}")) for k in range(6)])}
        spare = []
        draw = Panel._page_faces

        def measured(self, dt):
            draw(self, dt)
            spare.append((imgui.get_scroll_max_y(), imgui.get_scroll_max_x(),
                          imgui.get_content_region_avail().y))
        monkeypatch.setattr(Panel, "_page_faces", measured)
        reg["ui.page"].set(PAGE_KEYS.index("faces"))
        for err, faces in (("2:14: 'u_modd' : undeclared identifier", False), ("", False),
                           ("", True)):
            panel.renderer = SimpleNamespace(pattern_error=err, fx=None)
            reg["view.faces"].set(faces)
            for mode in range(len(MODES)):
                reg["view.pattern"].set(mode)
                for _ in range(3):
                    imgui.new_frame()
                    panel.draw(1 / 60, 60.0)
                    imgui.end_frame()
                over_y, over_x, room = spare[-1]
                said = (MODES[mode].name, err[:4], faces)
                assert over_y == 0 and over_x == 0, said
                assert room >= 12, (*said, room)
        print("FACES spare height px:", min(s[2] for s in spare))
    finally:
        rig.close()


# ---- the renderer's side: swatches only while asked, and the frame untouched ----

def test_swatches_draw_only_while_the_page_asks_and_leave_the_frame_as_it_was():
    moderngl = pytest.importorskip("moderngl")
    import numpy as np

    from hyperspace.render import N_PATTERNS, SWATCH, SWATCH_HOLD, Renderer
    from hyperspace.view import ViewState
    try:
        ctx = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    try:
        r = Renderer(ctx)
        fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((160, 120))])
        s = ViewState(shape=3, faces=True, pattern=1)

        def frame(t):
            fbo.use()
            ctx.viewport = (0, 0, 160, 120)
            r.draw(s, 160, 120, t_now=t)
            assert ctx.fbo.glo == fbo.glo and tuple(ctx.viewport) == (0, 0, 160, 120)
            return np.frombuffer(fbo.read(components=3), np.uint8).copy()

        before = [frame(1.0 + k / 60) for k in range(N_PATTERNS)]
        assert all(r.swatch(k) is None for k in range(N_PATTERNS))     # nobody asked
        r = Renderer(ctx)                               # a fresh clock: the same frames
        r.want_swatches()
        after = [frame(1.0 + k / 60) for k in range(N_PATTERNS)]
        assert [np.array_equal(a, b) for a, b in zip(before, after, strict=True)] == [True] * N_PATTERNS
        assert r.swatch_error == ""
        for k in range(N_PATTERNS):
            tex = r.swatch(k)
            assert tex is not None and tex.size == (SWATCH, SWATCH)
        hot = np.frombuffer(r.swatch(5).read(), np.uint8).reshape(SWATCH, SWATCH, 4)
        assert hot[..., 3].min() == 255 and hot[..., :3].max() > 40    # opaque, lit
        for k in range(SWATCH_HOLD + 1):                # the page went away: they stop
            frame(2.0 + k / 60)
        n = r._swatch_next
        frame(3.0)
        assert r._swatch_next == n
    finally:
        ctx.release()


def test_a_broken_save_keeps_the_last_good_swatches_and_is_compiled_once(tmp_path, monkeypatch):
    """A save of patterns.glsl that does not compile: the face program keeps
    its last good version, and so do the swatches — the save is tried once,
    not once a frame while the page is open (a failed compile costs the
    frame). The next good save lands; a reload of render.py rebuilds the
    swatches' program from its own strings."""
    moderngl = pytest.importorskip("moderngl")
    import os

    from hyperspace import render as R
    from hyperspace.view import ViewState
    try:
        ctx = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    src = R.PATTERNS_GLSL.read_text()
    path = tmp_path / "patterns.glsl"
    path.write_text(src)
    monkeypatch.setattr(R, "PATTERNS_GLSL", path)
    built = []
    real = R._face_fragment
    monkeypatch.setattr(R, "_face_fragment", lambda head, *a: (
        built.append(head is R.TILE_FS_HEAD), real(head, *a))[1])
    try:
        r = R.Renderer(ctx)
        fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((64, 48))])
        s = ViewState(shape=3, faces=True, pattern=1)
        stamp = [path.stat().st_mtime]

        def save(text):
            stamp[0] += 10
            path.write_text(text)
            os.utime(path, (stamp[0], stamp[0]))
            r._patterns_mtime = r._shader_mtime()     # what the every-30-frames check does
            r._build_face_program()

        def frames(n):
            for k in range(n):
                r.want_swatches()
                fbo.use()
                ctx.viewport = (0, 0, 64, 48)
                r.draw(s, 64, 48, t_now=1.0 + k / 60)

        frames(3)
        good = r._ptile[0]
        assert built.count(True) == 1 and r.swatch_error == ""
        save(src + "\nnot glsl;\n")
        assert r.pattern_error
        frames(20)
        assert built.count(True) == 2                       # tried once for the save
        assert r._ptile[0] is good and r.swatch_error == ""  # the last good one draws on
        save(src)
        frames(2)
        assert built.count(True) == 3 and r._ptile[0] is not good
        r.on_reload()
        assert r._ptile is None
        frames(1)
        assert r._ptile is not None and r.swatch_error == ""
    finally:
        ctx.release()
